from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Optional, List
import pandas as pd
import json
import io
from app.services.sample_manager import SampleManager
from app.services.field_detector import field_detector
from app.services.import_batch_service import ImportBatchService
from app.core.logger import app_logger
from app.core.exceptions import DataValidationError, BusinessException

router = APIRouter()
_sample_manager = SampleManager()
_batch_service = ImportBatchService()

# Mock样本生成接口已移除，请使用CSV导入功能

@router.post("/statistics")
async def compute_statistics(samples: Dict):
    try:
        stats = _sample_manager.compute_statistics(samples)
        return {"code": 0, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/typical-cases")
async def extract_typical_cases(samples: Dict):
    try:
        cases = _sample_manager.extract_typical_cases(samples)
        return {"code": 0, "data": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-csv")
async def import_samples_csv(file: UploadFile = File(...)):
    """Import user data from CSV file for inference and sample management"""
    try:
        # 验证文件类型
        if not file.filename.endswith('.csv'):
            raise DataValidationError("仅支持CSV文件")

        # 验证MIME类型
        if file.content_type and file.content_type not in ['text/csv', 'application/csv', 'application/vnd.ms-excel']:
            raise DataValidationError("无效的文件类型")

        # 读取文件内容并限制大小（10MB）
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise DataValidationError("文件大小超过10MB限制")

        # 安全解析CSV
        df = pd.read_csv(io.BytesIO(content), engine='python')

        # 自动识别字段
        columns = df.columns.tolist()
        field_mapping = field_detector.auto_detect_fields(columns)

        # 转换为字典列表
        users_data = df.to_dict(orient='records')

        # 标准化数据
        normalized_data = field_detector.normalize_csv_data(users_data, field_mapping)

        # 获取字段识别统计
        field_stats = field_detector.get_field_statistics(field_mapping)

        app_logger.info(f"成功导入CSV文件: {file.filename}, 共 {len(normalized_data)} 条记录")

        return {
            "code": 0,
            "data": {
                "users": normalized_data,
                "field_mapping": field_mapping,
                "field_statistics": field_stats,
                "total_count": len(normalized_data)
            },
            "message": f"成功导入 {len(normalized_data)} 条用户数据"
        }
    except DataValidationError as e:
        app_logger.warning(f"CSV导入验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"CSV导入失败: {e}", exc_info=True)
        raise BusinessException("CSV文件导入失败，请检查文件格式")

@router.post("/infer")
async def infer_user_data(users_data: Dict):
    """Perform inference on user data to calculate purchase intent, churn probability, etc."""
    try:
        users = users_data.get("users", [])
        results = []
        
        for user in users:
            inference = _sample_manager.infer_user(user)
            results.append(inference)
        
        return {
            "code": 0,
            "data": {
                "results": results,
                "total_count": len(results)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-batch")
async def import_batch_csv(files: List[UploadFile] = File(...)):
    """Import multiple CSV files as user behavior data"""
    try:
        if not files:
            raise DataValidationError("请至少上传一个CSV文件")

        if len(files) > 20:
            raise DataValidationError("单次最多上传20个文件")

        all_users = []
        file_results = []

        for file in files:
            app_logger.info(f"处理文件: {file.filename}, MIME类型: {file.content_type}")

            # 验证文件类型（只检查扩展名）
            if not file.filename.endswith('.csv'):
                app_logger.warning(f"跳过非CSV文件: {file.filename}")
                continue

            # 读取文件内容并限制大小（10MB）
            content = await file.read()
            if len(content) > 10 * 1024 * 1024:
                app_logger.warning(f"跳过超大文件: {file.filename} ({len(content)} bytes)")
                continue

            try:
                # 安全解析CSV
                df = pd.read_csv(io.BytesIO(content), engine='python')

                # 自动识别字段
                columns = df.columns.tolist()
                field_mapping = field_detector.auto_detect_fields(columns)

                # 转换为字典列表
                users_data = df.to_dict(orient='records')

                # 标准化数据
                normalized_data = field_detector.normalize_csv_data(users_data, field_mapping)

                # 获取字段识别统计
                field_stats = field_detector.get_field_statistics(field_mapping)

                all_users.extend(normalized_data)

                file_results.append({
                    "filename": file.filename,
                    "status": "success",
                    "record_count": len(normalized_data),
                    "field_mapping": field_mapping,
                    "field_statistics": field_stats
                })

                app_logger.info(f"成功处理文件: {file.filename}, 共 {len(normalized_data)} 条记录")

            except Exception as e:
                app_logger.error(f"处理文件失败 {file.filename}: {e}", exc_info=True)
                file_results.append({
                    "filename": file.filename,
                    "status": "failed",
                    "error": str(e)
                })

        # 数据去重（基于user_id）
        unique_users = {}
        for user in all_users:
            user_id = user.get('user_id')
            if user_id:
                if user_id in unique_users:
                    # 合并数据（后面的覆盖前面的）
                    unique_users[user_id].update(user)
                else:
                    unique_users[user_id] = user
            else:
                # 没有user_id的数据也保留
                unique_users[id(user)] = user

        final_users = list(unique_users.values())

        app_logger.info(f"批量导入完成: {len(files)} 个文件, {len(all_users)} 条原始记录, {len(final_users)} 条去重后记录")

        # 保存到数据库
        try:
            batch_name = f"批次导入_{len(files)}个文件"
            batch = _batch_service.create_batch(
                batch_name=batch_name,
                file_count=len(files),
                record_count=len(all_users),
                unique_record_count=len(final_users),
                file_info=file_results,
                users=final_users
            )
            app_logger.info(f"批次数据已保存到数据库，批次ID: {batch['id']}")
        except Exception as e:
            app_logger.error(f"保存批次数据到数据库失败: {e}", exc_info=True)
            # 即使保存失败，也返回导入的数据

        return {
            "code": 0,
            "data": {
                "users": final_users,
                "file_results": file_results,
                "total_files": len(files),
                "successful_files": len([r for r in file_results if r["status"] == "success"]),
                "total_records": len(all_users),
                "unique_records": len(final_users),
                "batch_id": batch.get('id') if 'batch' in locals() else None
            },
            "message": f"成功导入 {len(final_users)} 条用户数据（来自 {len([r for r in file_results if r['status'] == 'success'])} 个文件）"
        }

    except DataValidationError as e:
        app_logger.warning(f"批量CSV导入验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"批量CSV导入失败: {e}", exc_info=True)
        raise BusinessException("批量CSV文件导入失败")


@router.get("/list")
async def list_samples(
    sample_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """Get paginated list of all samples"""
    try:
        samples = _sample_manager.get_all_samples()

        filtered_samples = {}
        if sample_type and sample_type in samples:
            filtered_samples = {sample_type: samples[sample_type]}
        else:
            filtered_samples = samples

        # Pagination
        paginated_results = {}
        for stype, data in filtered_samples.items():
            start = (page - 1) * page_size
            end = start + page_size
            paginated_results[stype] = {
                "data": data[start:end],
                "total": len(data),
                "page": page,
                "page_size": page_size,
                "total_pages": (len(data) + page_size - 1) // page_size
            }

        return {"code": 0, "data": paginated_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 批次管理API ==========

@router.get("/batches")
async def list_batches(
    page: int = 1,
    page_size: int = 20
):
    """获取导入批次列表"""
    try:
        batches = _batch_service.list_batches(page=page, page_size=page_size)
        return {
            "code": 0,
            "data": batches,
            "message": "获取批次列表成功"
        }
    except Exception as e:
        app_logger.error(f"获取批次列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取批次列表失败")


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: int):
    """获取批次详情"""
    try:
        batch = _batch_service.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="批次不存在")

        return {
            "code": 0,
            "data": batch,
            "message": "获取批次详情成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取批次详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取批次详情失败")


@router.get("/batches/{batch_id}/users")
async def get_batch_users(
    batch_id: int,
    page: int = 1,
    page_size: int = 100
):
    """获取批次的用户数据"""
    try:
        users = _batch_service.get_batch_users(batch_id, page=page, page_size=page_size)
        return {
            "code": 0,
            "data": users,
            "message": "获取批次用户数据成功"
        }
    except Exception as e:
        app_logger.error(f"获取批次用户数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取批次用户数据失败")


@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: int):
    """删除批次"""
    try:
        success = _batch_service.delete_batch(batch_id)
        if not success:
            raise HTTPException(status_code=404, detail="批次不存在")

        return {
            "code": 0,
            "message": "删除批次成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"删除批次失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除批次失败")


@router.get("/batches/latest/users")
async def get_latest_batch_users():
    """获取最新批次的用户数据"""
    try:
        users = _batch_service.get_latest_batch_users()
        return {
            "code": 0,
            "data": users,
            "message": "获取最新批次用户数据成功"
        }
    except Exception as e:
        app_logger.error(f"获取最新批次用户数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取最新批次用户数据失败")
