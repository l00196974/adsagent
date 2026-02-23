"""
高频子序列挖掘API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.logger import app_logger
from app.core.memory_monitor import memory_monitor
from app.services.sequence_mining import SequenceMiningService

router = APIRouter(prefix="/mining", tags=["高频子序列挖掘"])

# 服务实例
mining_service = SequenceMiningService()


# ========== 请求/响应模型 ==========

class MiningRequest(BaseModel):
    algorithm: str = Field("prefixspan", description="算法类型: prefixspan 或 attention")
    min_support: int = Field(2, ge=1, le=100, description="最小支持度")
    max_length: int = Field(3, ge=2, le=5, description="最大序列长度 (限制为5以控制内存使用)")
    top_k: int = Field(20, ge=1, le=100, description="返回前K个模式")


class SavePatternsRequest(BaseModel):
    patterns: List[dict] = Field(..., description="要保存的模式列表")
    algorithm: str = Field(..., description="使用的算法")
    min_support: int = Field(..., description="最小支持度")


# ========== API接口 ==========

@router.post("/mine")
async def mine_frequent_patterns(request: MiningRequest):
    """挖掘高频事件子序列

    支持两种算法:
    - prefixspan: 经典的序列模式挖掘算法
    - attention: 基于共现频率的Attention权重方法

    注意: 为控制内存使用,max_length限制为3,处理序列数量限制为50,000
    """
    try:
        memory_monitor.log_memory_usage("API调用开始")
        app_logger.info(f"开始挖掘高频子序列: algorithm={request.algorithm}, min_support={request.min_support}, max_length={request.max_length}")
        app_logger.warning(f"内存优化模式: max_length限制为{request.max_length}, 将处理最多50,000条序列")

        result = mining_service.mine_frequent_subsequences(
            algorithm=request.algorithm,
            min_support=request.min_support,
            max_length=request.max_length,
            top_k=request.top_k
        )

        memory_monitor.log_memory_usage("API调用完成")

        return {
            "code": 0,
            "message": "挖掘完成",
            "data": result
        }

    except ValueError as e:
        app_logger.error(f"参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"挖掘失败: {e}", exc_info=True)
        memory_monitor.log_memory_usage("API调用失败")
        raise HTTPException(status_code=500, detail=f"挖掘失败: {str(e)}")


@router.post("/patterns/{pattern_id}/examples")
async def get_pattern_examples(pattern_id: str, limit: int = 5):
    """获取某个模式的用户示例

    Args:
        pattern_id: 模式ID (格式: "event1,event2,event3")
        limit: 返回示例数量
    """
    try:
        # 解析模式
        pattern = pattern_id.split(",")

        examples = mining_service.get_pattern_examples(pattern, limit)

        return {
            "code": 0,
            "message": "查询成功",
            "data": {
                "pattern": pattern,
                "examples": examples
            }
        }

    except Exception as e:
        app_logger.error(f"查询示例失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/patterns/save")
async def save_patterns(request: SavePatternsRequest):
    """保存用户确认的高频模式到数据库

    用户可以从挖掘结果中选择感兴趣的模式,确认后保存
    """
    try:
        app_logger.info(f"保存 {len(request.patterns)} 个高频模式")

        result = mining_service.save_patterns(
            patterns=request.patterns,
            algorithm=request.algorithm,
            min_support=request.min_support
        )

        return {
            "code": 0,
            "message": f"成功保存 {result['saved_count']} 个模式",
            "data": result
        }

    except Exception as e:
        app_logger.error(f"保存模式失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get("/patterns/saved")
async def get_saved_patterns(limit: int = 100, offset: int = 0):
    """查询已保存的高频模式"""
    try:
        result = mining_service.get_saved_patterns(limit, offset)

        return {
            "code": 0,
            "message": "查询成功",
            "data": result
        }

    except Exception as e:
        app_logger.error(f"查询保存的模式失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/patterns/{pattern_id}")
async def delete_pattern(pattern_id: int):
    """删除已保存的模式"""
    try:
        mining_service.delete_pattern(pattern_id)

        return {
            "code": 0,
            "message": "删除成功"
        }

    except Exception as e:
        app_logger.error(f"删除模式失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
