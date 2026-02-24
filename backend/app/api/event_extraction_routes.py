"""
事件抽象模块API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import asyncio
import json
from app.core.logger import app_logger
from app.services.event_extraction import EventExtractionService
from app.services.base_modeling import BaseModelingService

router = APIRouter(prefix="/events", tags=["事件抽象"])

# 服务实例
extraction_service = EventExtractionService()
modeling_service = BaseModelingService()


# ========== 请求/响应模型 ==========

class ExtractEventsRequest(BaseModel):
    user_ids: Optional[List[str]] = None


# ========== 事件抽象接口 ==========

@router.post("/extract/start")
async def start_batch_extract(request: ExtractEventsRequest = None):
    """启动批量事件抽象（后台执行）"""
    try:
        # 检查是否已有任务在运行
        progress = extraction_service.get_progress()
        if progress["status"] == "running":
            raise HTTPException(status_code=400, detail="已有批量抽象任务正在运行")

        user_ids = request.user_ids if request else None
        app_logger.info(f"启动批量事件抽象: user_ids={user_ids}")

        # 启动后台任务
        asyncio.create_task(extraction_service.extract_events_batch(user_ids))

        return {
            "code": 0,
            "message": "批量抽象任务已启动",
            "data": {
                "status": "started"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"启动批量抽象失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.get("/extract/progress")
async def get_extract_progress():
    """获取批量抽象进度"""
    try:
        progress = extraction_service.get_progress()
        return {
            "code": 0,
            "data": progress
        }
    except Exception as e:
        app_logger.error(f"获取进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")


@router.post("/extract/start/stream")
async def start_batch_extract_stream(request: ExtractEventsRequest = None):
    """启动批量事件抽象（流式返回）

    返回SSE流，实时推送：
    - 进度更新
    - 每个用户的处理结果
    - LLM返回的事件内容
    - 错误信息
    """
    async def event_generator():
        try:
            user_ids = request.user_ids if request else None
            app_logger.info(f"启动流式批量事件抽象: user_ids={user_ids}")

            # 发送初始状态
            yield f"data: {json.dumps({'status': 'processing', 'message': '开始批量处理...'}, ensure_ascii=False)}\n\n"

            # 获取要处理的用户列表
            with sqlite3.connect(extraction_service.db_path) as conn:
                cursor = conn.cursor()

                if user_ids:
                    placeholders = ','.join('?' * len(user_ids))
                    cursor.execute(f"""
                        SELECT DISTINCT user_id
                        FROM behavior_data
                        WHERE user_id IN ({placeholders})
                    """, user_ids)
                else:
                    cursor.execute("""
                        SELECT DISTINCT user_id
                        FROM behavior_data
                    """)

                all_user_ids = [row[0] for row in cursor.fetchall()]

            total_users = len(all_user_ids)
            processed = 0
            success_count = 0
            failed_count = 0

            app_logger.info(f"共需处理 {total_users} 个用户")

            # 发送总数
            yield f"data: {json.dumps({'status': 'processing', 'total': total_users, 'processed': 0, 'percentage': 0}, ensure_ascii=False)}\n\n"

            # 逐个处理用户
            for user_id in all_user_ids:
                try:
                    # 查询用户行为
                    with sqlite3.connect(extraction_service.db_path) as conn:
                        cursor = conn.cursor()

                        cursor.execute("""
                            SELECT id, timestamp, behavior_text
                            FROM behavior_data
                            WHERE user_id = ?
                            ORDER BY timestamp ASC
                        """, (user_id,))

                        behaviors = []
                        for row in cursor.fetchall():
                            behaviors.append({
                                "id": row[0],
                                "timestamp": row[1],
                                "behavior_text": row[2]
                            })

                        if not behaviors:
                            processed += 1
                            failed_count += 1
                            yield f"data: {json.dumps({'user_id': user_id, 'success': False, 'error': '没有行为数据', 'progress': {'processed': processed, 'total': total_users, 'percentage': round(processed / total_users * 100, 2)}}, ensure_ascii=False)}\n\n"
                            continue

                        # 查询用户画像
                        cursor.execute("""
                            SELECT age, gender, city, occupation, properties
                            FROM user_profiles
                            WHERE user_id = ?
                        """, (user_id,))

                        profile_row = cursor.fetchone()
                        profile = None
                        if profile_row:
                            import json as json_lib
                            properties = json_lib.loads(profile_row[4]) if profile_row[4] else {}
                            profile = {
                                "age": profile_row[0],
                                "gender": profile_row[1],
                                "city": profile_row[2],
                                "occupation": profile_row[3],
                                "income_level": properties.get("income_level"),
                                "interests": properties.get("interests", [])
                            }

                    # 丰富行为数据
                    enriched_behaviors = extraction_service._enrich_behaviors_with_entities(behaviors)

                    # 获取LLM客户端
                    llm_client = OpenAIClient()

                    # 调用LLM抽象事件
                    llm_result = await llm_client.abstract_events_batch(
                        {user_id: enriched_behaviors},
                        user_profiles={user_id: profile} if profile else None
                    )

                    # 解析结果
                    events_result = llm_result.get("events", {})
                    user_events = events_result.get(user_id, [])

                    # 保存到数据库
                    if user_events:
                        with sqlite3.connect(extraction_service.db_path) as conn:
                            cursor = conn.cursor()

                            # 删除旧事件
                            cursor.execute("DELETE FROM extracted_events WHERE user_id = ?", (user_id,))

                            # 插入新事件并收集 event_id 列表
                            import uuid
                            event_ids = []
                            for event in user_events:
                                event_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
                                event_ids.append(event_id)
                                context_json = json.dumps(event.get("context"), ensure_ascii=False) if isinstance(event.get("context"), dict) else event.get("context")
                                cursor.execute("""
                                    INSERT INTO extracted_events (event_id, user_id, event_type, timestamp, context, event_category, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                                """, (event_id, user_id, event.get("event_type"), event.get("timestamp"), context_json, event.get("category", "engagement")))

                            # 更新event_sequences表 - 存储 event_id 数组
                            cursor.execute("""
                                INSERT OR REPLACE INTO event_sequences (user_id, sequence, start_time, end_time, status)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                user_id,
                                json.dumps(event_ids, ensure_ascii=False),
                                user_events[0].get("timestamp") if user_events else None,
                                user_events[-1].get("timestamp") if user_events else None,
                                "success"
                            ))

                            conn.commit()

                        processed += 1
                        success_count += 1

                        # 发送成功结果
                        yield f"data: {json.dumps({'user_id': user_id, 'success': True, 'events': user_events, 'event_count': len(user_events), 'progress': {'processed': processed, 'total': total_users, 'percentage': round(processed / total_users * 100, 2)}}, ensure_ascii=False)}\n\n"
                    else:
                        processed += 1
                        failed_count += 1
                        yield f"data: {json.dumps({'user_id': user_id, 'success': False, 'error': 'LLM未返回事件', 'progress': {'processed': processed, 'total': total_users, 'percentage': round(processed / total_users * 100, 2)}}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    app_logger.error(f"处理用户 [{user_id}] 失败: {e}", exc_info=True)
                    processed += 1
                    failed_count += 1
                    yield f"data: {json.dumps({'user_id': user_id, 'success': False, 'error': str(e), 'progress': {'processed': processed, 'total': total_users, 'percentage': round(processed / total_users * 100, 2)}}, ensure_ascii=False)}\n\n"

            # 发送完成状态
            yield f"data: {json.dumps({'total_processed': processed, 'success_count': success_count, 'failed_count': failed_count, 'status': 'completed'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            app_logger.error(f"Stream extraction failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e), 'error_type': type(e).__name__}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/extract")
async def extract_events(request: ExtractEventsRequest = None):
    """触发事件抽象（同步版本，保持向后兼容）

    Args:
        user_ids: 用户ID列表,如果为空则处理所有未抽象的用户
    """
    try:
        user_ids = request.user_ids if request else None
        app_logger.info(f"开始事件抽象: user_ids={user_ids}")

        result = await extraction_service.extract_events_batch(user_ids)

        if result["success"]:
            return {
                "code": 0,
                "message": f"事件抽象完成: 成功 {result['success_count']}/{result['total_users']}",
                "data": {
                    "total_users": result["total_users"],
                    "success_count": result["success_count"],
                    "failed_count": result["failed_count"]
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "事件抽象失败"))

    except Exception as e:
        app_logger.error(f"事件抽象失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"事件抽象失败: {str(e)}")


@router.post("/extract/{user_id}")
async def extract_events_for_user(user_id: str):
    """为单个用户触发事件抽象（非流式）"""
    try:
        app_logger.info(f"开始为用户 [{user_id}] 抽象事件")

        result = await extraction_service.extract_events_for_user(user_id)

        if result["success"]:
            return {
                "code": 0,
                "message": f"用户 [{user_id}] 事件抽象完成",
                "data": {
                    "user_id": user_id,
                    "event_count": result["event_count"],
                    "events": result["events"]
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "事件抽象失败"))

    except Exception as e:
        app_logger.error(f"用户 [{user_id}] 事件抽象失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"事件抽象失败: {str(e)}")


@router.post("/extract/{user_id}/llm-stream")
async def extract_events_for_user_llm_stream(user_id: str):
    """为单个用户触发事件抽象（真正的LLM流式响应）

    返回Server-Sent Events格式的流式数据，实时显示LLM的响应内容
    """
    from app.core.openai_client import OpenAIClient
    import sqlite3

    async def event_generator():
        try:
            # 发送开始消息
            yield f"data: {json.dumps({'type': 'start', 'message': f'开始为用户 {user_id} 抽象事件...'}, ensure_ascii=False)}\n\n"

            # 从数据库获取用户行为数据
            db_path = "data/graph.db"
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # 查询用户行为
                cursor.execute("""
                    SELECT id, timestamp, behavior_text
                    FROM behavior_data
                    WHERE user_id = ?
                    ORDER BY timestamp ASC
                """, (user_id,))

                behaviors = []
                for row in cursor.fetchall():
                    behaviors.append({
                        "id": row[0],
                        "timestamp": row[1],
                        "behavior_text": row[2]
                    })

                if not behaviors:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'用户 {user_id} 没有行为数据'}, ensure_ascii=False)}\n\n"
                    return

                # 查询用户画像
                cursor.execute("""
                    SELECT age, gender, city, occupation, properties
                    FROM user_profiles
                    WHERE user_id = ?
                """, (user_id,))

                profile_row = cursor.fetchone()
                profile = None
                if profile_row:
                    import json as json_lib
                    properties = json_lib.loads(profile_row[4]) if profile_row[4] else {}
                    profile = {
                        "age": profile_row[0],
                        "gender": profile_row[1],
                        "city": profile_row[2],
                        "occupation": profile_row[3],
                        "income_level": properties.get("income_level"),
                        "interests": properties.get("interests", [])
                    }

            # 丰富行为数据
            enriched_behaviors = extraction_service._enrich_behaviors_with_entities(behaviors)

            # 获取LLM客户端
            llm_client = OpenAIClient()

            # 发送进度消息
            yield f"data: {json.dumps({'type': 'progress', 'message': f'正在调用LLM分析 {len(enriched_behaviors)} 条行为...'}, ensure_ascii=False)}\n\n"

            # 调用流式LLM
            full_response = ""
            async for chunk in llm_client.abstract_events_batch_stream(
                {user_id: enriched_behaviors},
                {user_id: profile} if profile else None
            ):
                full_response += chunk
                # 实时发送LLM的每个chunk
                yield f"data: {json.dumps({'type': 'llm_chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 解析并保存事件到数据库
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在保存事件到数据库...'}, ensure_ascii=False)}\n\n"

            # 解析LLM响应（文本格式: 用户ID|事件类型|时间戳|上下文信息）
            events = []
            lines = full_response.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 解析每行: 用户ID|事件类型|时间戳|上下文信息
                parts = line.split('|')
                if len(parts) < 3:
                    continue

                parsed_user_id = parts[0].strip()
                # 只保存当前用户的事件
                if parsed_user_id != user_id:
                    continue

                event_type = parts[1].strip()
                timestamp = parts[2].strip()
                context_str = parts[3].strip() if len(parts) > 3 else ""

                # 解析上下文信息
                context = {}
                if context_str:
                    context_items = [item.strip() for item in context_str.split(',')]
                    context['details'] = context_items

                events.append({
                    "event_type": event_type,
                    "timestamp": timestamp,
                    "context": context
                })

            # 保存到数据库
            if events:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()

                    # 删除该用户的旧事件
                    cursor.execute("DELETE FROM extracted_events WHERE user_id = ?", (user_id,))

                    # 插入新事件并收集 event_id 列表
                    import uuid
                    event_ids_list = []
                    for event in events:
                        event_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
                        event_ids_list.append(event_id)
                        cursor.execute("""
                            INSERT INTO extracted_events (event_id, user_id, event_type, timestamp, context, event_category, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                        """, (event_id, user_id, event.get("event_type"), event.get("timestamp"), json.dumps(event.get("context"), ensure_ascii=False), event.get("category", "engagement")))

                    # 更新event_sequences表 - 存储 event_id 数组
                    cursor.execute("""
                        INSERT OR REPLACE INTO event_sequences (user_id, sequence, start_time, end_time, status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        json.dumps(event_ids_list, ensure_ascii=False),
                        events[0].get("timestamp") if events else None,
                        events[-1].get("timestamp") if events else None,
                        "success"
                    ))

                    conn.commit()

                yield f"data: {json.dumps({'type': 'progress', 'message': f'成功保存 {len(events)} 个事件'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'progress', 'message': 'LLM未返回有效事件'}, ensure_ascii=False)}\n\n"

            # 发送完成消息
            yield f"data: {json.dumps({'type': 'done', 'message': '抽象完成', 'event_count': len(events) if events else 0}, ensure_ascii=False)}\n\n"

        except Exception as e:
            app_logger.error(f"用户 [{user_id}] LLM流式事件抽象失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


@router.post("/extract/{user_id}/stream")
async def extract_events_for_user_stream(user_id: str):
    """为单个用户触发事件抽象（流式，带进度反馈）"""
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': f'开始为用户 {user_id} 抽象事件...'}, ensure_ascii=False)}\n\n"

            # 调用服务，传入进度回调
            result = await extraction_service.extract_events_for_user_with_progress(
                user_id,
                progress_callback=lambda msg: event_generator.send_progress(msg)
            )

            if result["success"]:
                yield f"data: {json.dumps({'type': 'result', 'data': result}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'message': '抽象完成'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', '抽象失败')}, ensure_ascii=False)}\n\n"

        except Exception as e:
            app_logger.error(f"用户 [{user_id}] 流式事件抽象失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    # 为生成器添加发送进度的方法
    gen = event_generator()
    gen.send_progress = lambda msg: gen.send(f"data: {json.dumps({'type': 'progress', 'message': msg}, ensure_ascii=False)}\n\n")

    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/sequences")
async def list_event_sequences(limit: int = 100, offset: int = 0):
    """查询用户事件序列列表"""
    try:
        result = extraction_service.get_user_sequences(limit, offset)

        return {
            "code": 0,
            "data": result
        }

    except Exception as e:
        app_logger.error(f"查询用户序列列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/sequences/{user_id}")
async def get_user_sequence(user_id: str):
    """查询单个用户的详细序列"""
    try:
        result = extraction_service.get_user_sequences(limit=1000, offset=0)

        # 查找指定用户
        user_data = None
        for item in result["items"]:
            if item["user_id"] == user_id:
                user_data = item
                break

        if not user_data:
            raise HTTPException(status_code=404, detail=f"用户 [{user_id}] 不存在")

        return {
            "code": 0,
            "data": user_data
        }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"查询用户 [{user_id}] 序列失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/users/{user_id}/detail")
async def get_user_detail(
    user_id: str,
    include_summary: bool = False  # 默认不生成行为总结，避免慢查询
):
    """获取用户的完整信息（画像+行为序列+事件序列+行为总结）

    Args:
        user_id: 用户ID
        include_summary: 是否生成行为总结（需要调用LLM，耗时5-10秒）
    """
    try:
        import time
        start_time = time.time()
        app_logger.info(f"查询用户 [{user_id}] 的完整信息")

        # 优化：直接按 user_id 查询，而不是查询所有再遍历
        profile = None
        profiles_result = modeling_service.query_user_profiles(user_id=user_id, limit=1, offset=0)
        if profiles_result["items"]:
            profile = profiles_result["items"][0]
        app_logger.info(f"查询用户画像耗时: {time.time() - start_time:.3f}秒")

        step_time = time.time()
        behaviors_result = modeling_service.query_behavior_data(user_id=user_id, limit=1000, offset=0)
        behaviors = behaviors_result["items"]
        app_logger.info(f"查询行为数据耗时: {time.time() - step_time:.3f}秒")

        step_time = time.time()
        enriched_behaviors = extraction_service._enrich_behaviors_with_entities(behaviors)
        app_logger.info(f"丰富行为数据耗时: {time.time() - step_time:.3f}秒")

        behavior_summary = ""
        # 只有明确要求时才生成行为总结（需要调用LLM，很慢）
        if include_summary and enriched_behaviors:
            try:
                step_time = time.time()
                behavior_summary = await extraction_service.llm_client.summarize_behavior_sequence(
                    enriched_behaviors,
                    user_profile=profile
                )
                app_logger.info(f"用户 [{user_id}] 行为总结生成成功，耗时: {time.time() - step_time:.3f}秒")
            except Exception as e:
                app_logger.warning(f"用户 [{user_id}] 行为总结生成失败: {e}")
                behavior_summary = "行为总结生成失败"

        # 优化：直接查询数据库获取事件，而不是查询所有用户再遍历
        step_time = time.time()
        events = []
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path("data/graph.db")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_type, timestamp, context
                    FROM extracted_events
                    WHERE user_id = ?
                    ORDER BY timestamp ASC
                """, (user_id,))

                for row in cursor.fetchall():
                    events.append({
                        "event_type": row[0],
                        "timestamp": row[1],
                        "context": row[2]
                    })
        except Exception as e:
            app_logger.warning(f"查询用户 [{user_id}] 事件失败: {e}")
        app_logger.info(f"查询事件数据耗时: {time.time() - step_time:.3f}秒")

        app_logger.info(f"查询用户 [{user_id}] 完整信息总耗时: {time.time() - start_time:.3f}秒")

        return {
            "code": 0,
            "data": {
                "user_id": user_id,
                "profile": profile,
                "behaviors": enriched_behaviors,
                "behavior_summary": behavior_summary,
                "events": events
            }
        }

    except Exception as e:
        app_logger.error(f"查询用户 [{user_id}] 完整信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/stats")
async def get_event_stats():
    """获取事件统计信息"""
    try:
        app_logger.info("查询事件统计信息")

        sequences_result = extraction_service.get_user_sequences(limit=10000, offset=0)
        sequences = sequences_result["items"]

        total_events = 0
        unique_event_types = set()
        user_count = len(sequences)
        users_with_events = 0

        for seq in sequences:
            events = seq.get("event_sequence", [])
            total_events += len(events)
            if len(events) > 0:
                users_with_events += 1
            for event in events:
                if isinstance(event, dict):
                    unique_event_types.add(event.get("event_type", "unknown"))
                else:
                    unique_event_types.add(str(event))

        return {
            "code": 0,
            "data": {
                "total_events": total_events,
                "unique_event_types": len(unique_event_types),
                "user_count": user_count,
                "users_with_events": users_with_events,
                "event_types": list(unique_event_types)
            }
        }

    except Exception as e:
        app_logger.error(f"查询事件统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
