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
    user_ids: List[str] = Field(..., description="用户ID列表")
    max_workers: int = Field(4, ge=1, le=10, description="并发数")


@router.post("/generate/batch")
async def generate_batch(
    request: GenerateBatchRequest,
    generator: LogicalBehaviorGenerator = Depends(get_logical_behavior_generator)
):
    """批量生成逻辑行为序列"""
    try:
        result = await generator.generate_batch(request.user_ids, request.max_workers)
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

            # 查询所有用户，LEFT JOIN逻辑行为序列状态
            # 按照：已生成(success) > 失败(failed) > 未生成(pending/NULL) 排序
            cursor.execute(
                """SELECT
                       up.user_id,
                       COALESCE(lbs.status, 'pending') as status,
                       COALESCE(lbs.behavior_count, 0) as behavior_count,
                       lbs.error_message,
                       lbs.updated_at
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
                behavior_count = row[2]
                sequences.append({
                    "user_id": row[0],
                    "status": row[1],
                    "behavior_count": behavior_count,
                    "has_events": behavior_count > 0,  # 前端需要
                    "event_count": behavior_count,      # 前端需要
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

            # 2. 获取原始行为（最多100条）
            cursor.execute(
                """SELECT id, action, timestamp, item_id, app_id, media_id, poi_id, duration, properties
                   FROM behavior_data
                   WHERE user_id = ?
                   ORDER BY timestamp ASC
                   LIMIT 100""",
                (user_id,)
            )
            behaviors = []
            for row in cursor.fetchall():
                props = json.loads(row[8]) if row[8] else {}
                behaviors.append({
                    "id": row[0],
                    "action": row[1],
                    "timestamp": row[2],
                    "item_id": row[3],
                    "app_id": row[4],
                    "media_id": row[5],
                    "poi_id": row[6],
                    "duration": row[7],
                    "properties": props
                })

            # 3. 获取逻辑行为
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
