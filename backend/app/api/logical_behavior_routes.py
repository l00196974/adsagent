"""
逻辑行为生成API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.logical_behavior import LogicalBehaviorGenerator
from app.core.dependencies import get_logical_behavior_generator
from app.core.logger import app_logger
from app.core.exceptions import BusinessException, DatabaseError, LLMServiceError


router = APIRouter(prefix="/logical-behaviors", tags=["逻辑行为生成"])


class GenerateBatchRequest(BaseModel):
    """批量生成请求"""
    user_ids: Optional[List[str]] = Field(None, description="用户ID列表，为空时处理所有未生成的用户")
    max_workers: int = Field(4, ge=1, le=10, description="并发数")


@router.post("/generate/batch")
async def generate_batch(
    request: GenerateBatchRequest,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """批量生成逻辑行为序列"""
    try:
        import sqlite3
        from pathlib import Path

        user_ids = request.user_ids

        # 如果未指定user_ids，则获取所有未生成的用户
        if not user_ids:
            db_path = Path("data/graph.db")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT DISTINCT user_id
                       FROM user_profiles
                       WHERE user_id NOT IN (
                           SELECT user_id FROM logical_behavior_sequences
                           WHERE status = 'success'
                       )
                       ORDER BY user_id ASC"""
                )
                user_ids = [row[0] for row in cursor.fetchall()]
                app_logger.info(f"未指定用户列表，自动获取 {len(user_ids)} 个未生成的用户")

        if not user_ids:
            return {
                "code": 200,
                "message": "没有需要生成的用户",
                "data": {
                    "total_users": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": []
                }
            }

        result = await generator.generate_batch(user_ids, request.max_workers)
        return {
            "code": 200,
            "message": "批量生成完成",
            "data": result
        }
    except Exception as e:
        app_logger.error(f"批量生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")


@router.post("/generate/{user_id}")
async def generate_for_user(
    user_id: str,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """为单个用户生成逻辑行为序列"""
    try:
        result = await generator.generate_for_user(user_id)
        return {
            "code": 200,
            "message": "生成成功",
            "data": result
        }
    except DatabaseError as e:
        app_logger.error(f"数据库错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except LLMServiceError as e:
        app_logger.error(f"LLM服务错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        app_logger.error(f"生成逻辑行为失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/progress")
async def get_progress(
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """获取生成进度"""
    try:
        progress = generator.get_progress()
        return {
            "code": 200,
            "message": "获取进度成功",
            "data": progress
        }
    except Exception as e:
        app_logger.error(f"获取进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")


@router.get("/query/{user_id}")
async def query_logical_behaviors(
    user_id: str,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """查询用户的逻辑行为序列"""
    try:
        behaviors = generator.query_logical_behaviors(user_id)
        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "user_id": user_id,
                "logical_behaviors": behaviors,
                "count": len(behaviors)
            }
        }
    except DatabaseError as e:
        app_logger.error(f"数据库错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        app_logger.error(f"查询逻辑行为失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/sequences")
async def list_logical_behavior_sequences(
    limit: int = 20,
    offset: int = 0,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """列出所有用户的逻辑行为序列状态（包括未生成的用户）"""
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path("data/graph.db")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 查询所有用户，LEFT JOIN逻辑行为序列状态，并统计原始行为数量
            # 按照：已生成(success) > 失败(failed) > 未生成(pending/NULL) 排序
            cursor.execute(
                """SELECT
                       up.user_id,
                       COALESCE(lbs.status, 'pending') as status,
                       COALESCE(lbs.behavior_count, 0) as logical_behavior_count,
                       lbs.error_message,
                       lbs.updated_at,
                       (SELECT COUNT(*) FROM behavior_data WHERE user_id = up.user_id) as raw_behavior_count
                   FROM user_profiles up
                   LEFT JOIN logical_behavior_sequences lbs ON up.user_id = lbs.user_id
                   ORDER BY
                       CASE
                           WHEN lbs.status = 'success' THEN 1
                           WHEN lbs.status = 'failed' THEN 2
                           WHEN lbs.status = 'processing' THEN 3
                           ELSE 4
                       END,
                       lbs.updated_at DESC,
                       up.user_id ASC
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            )

            sequences = []
            for row in cursor.fetchall():
                logical_behavior_count = row[2]
                raw_behavior_count = row[5]
                sequences.append({
                    "user_id": row[0],
                    "status": row[1],
                    "behavior_count": logical_behavior_count,  # 逻辑行为数量
                    "raw_behavior_count": raw_behavior_count,  # 原始行为数量
                    "has_events": logical_behavior_count > 0,
                    "event_count": logical_behavior_count,
                    "error_message": row[3],
                    "updated_at": row[4]
                })

            # 查询总用户数
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
            total = cursor.fetchone()[0]

            return {
                "code": 200,
                "message": "查询成功",
                "data": {
                    "sequences": sequences,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }

    except Exception as e:
        app_logger.error(f"查询序列列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/users/{user_id}/detail")
async def get_user_detail(
    user_id: str,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """获取用户详细信息（画像+原始行为+逻辑行为）"""
    try:
        import sqlite3
        import json
        from pathlib import Path

        db_path = Path("data/graph.db")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 1. 获取用户画像
            cursor.execute(
                """SELECT user_id, age, gender, city, occupation, properties
                   FROM user_profiles
                   WHERE user_id = ?""",
                (user_id,)
            )
            profile_row = cursor.fetchone()
            if not profile_row:
                raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

            properties = json.loads(profile_row[5]) if profile_row[5] else {}
            profile = {
                "user_id": profile_row[0],
                "age": profile_row[1],
                "gender": profile_row[2],
                "city": profile_row[3],
                "occupation": profile_row[4],
                "age_bucket": properties.get("age_bucket", ""),
                "education": properties.get("education", ""),
                "income_level": properties.get("income_level", ""),
                "interests": properties.get("interests", []),
                "behaviors": properties.get("behaviors", [])
            }

            # 2. 获取app和media的名称映射
            cursor.execute("SELECT app_id, app_name, category FROM app_tags")
            app_map = {row[0]: {"name": row[1], "category": row[2]} for row in cursor.fetchall()}

            cursor.execute("SELECT media_id, media_name, media_type FROM media_tags")
            media_map = {row[0]: {"name": row[1], "type": row[2]} for row in cursor.fetchall()}

            # 3. 获取原始行为（所有行为，不限制数量）
            cursor.execute(
                """SELECT id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties
                   FROM behavior_data
                   WHERE user_id = ?
                   ORDER BY timestamp ASC""",
                (user_id,)
            )

            behaviors = []
            for row in cursor.fetchall():
                props = json.loads(row[8]) if row[8] else {}

                # 构建友好的描述
                action_desc = {
                    "browse": "浏览",
                    "click": "点击",
                    "search": "搜索",
                    "visit_poi": "到访",
                    "use_app": "使用APP",
                    "view_media": "观看媒体",
                    "purchase": "购买",
                    "add_cart": "加购"
                }.get(row[1], row[1])

                # 构建对象描述
                obj_parts = []
                if row[3]:  # item_id
                    obj_parts.append(row[3])
                if row[4] and row[4] in app_map:  # app_id
                    obj_parts.append(f"{app_map[row[4]]['name']}({app_map[row[4]]['category']})")
                elif row[4]:
                    obj_parts.append(row[4])
                if row[5] and row[5] in media_map:  # media_id
                    obj_parts.append(f"{media_map[row[5]]['name']}({media_map[row[5]]['type']})")
                elif row[5]:
                    obj_parts.append(row[5])
                if row[6]:  # poi_id
                    obj_parts.append(row[6])

                description = f"{action_desc} {' | '.join(obj_parts)}" if obj_parts else action_desc

                behaviors.append({
                    "id": row[0],
                    "action": row[1],
                    "action_desc": action_desc,
                    "description": description,
                    "timestamp": row[2],
                    "item_id": row[3],
                    "app_id": row[4],
                    "media_id": row[5],
                    "poi_id": row[6],
                    "duration": row[7],
                    "properties": props
                })
                    "action": row[1],
                    "timestamp": row[2],
                    "item_id": row[3],
                    "app_id": row[4],
                    "media_id": row[5],
                    "poi_id": row[6],
                    "duration": row[7],
                    "properties": props
                })

            # 4. 获取逻辑行为
            cursor.execute(
                """SELECT id, agent, scene, action, object, start_time, end_time, raw_behavior_ids, confidence
                   FROM logical_behaviors
                   WHERE user_id = ?
                   ORDER BY start_time ASC""",
                (user_id,)
            )
            events = []
            for row in cursor.fetchall():
                events.append({
                    "id": row[0],
                    "agent": row[1],
                    "scene": row[2],
                    "action": row[3],
                    "object": row[4],
                    "start_time": row[5],
                    "end_time": row[6],
                    "raw_behavior_ids": row[7].split(",") if row[7] else [],
                    "confidence": row[8]
                })

            return {
                "code": 0,
                "message": "查询成功",
                "data": {
                    "profile": profile,
                    "behaviors": behaviors,
                    "events": events
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"查询用户详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
