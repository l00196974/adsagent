"""
导入批次管理服务
"""
from typing import List, Dict, Optional
from datetime import datetime
from app.models.import_data import ImportBatch, ImportedUser
from app.core.database import get_db
from app.core.logger import app_logger


class ImportBatchService:
    """导入批次管理服务"""

    @staticmethod
    def create_batch(
        batch_name: str,
        file_count: int,
        record_count: int,
        unique_record_count: int,
        file_info: List[Dict],
        field_mapping: Dict,
        users_data: List[Dict],
        description: str = ""
    ) -> ImportBatch:
        """创建新的导入批次"""
        with get_db() as db:
            # 创建批次记录
            batch = ImportBatch(
                batch_name=batch_name,
                batch_time=datetime.now(),
                file_count=file_count,
                record_count=record_count,
                unique_record_count=unique_record_count,
                file_info=file_info,
                field_mapping=field_mapping,
                status="completed",
                description=description
            )
            db.add(batch)
            db.flush()  # 获取batch.id

            # 批量创建用户记录
            for user_data in users_data:
                user = ImportedUser(
                    batch_id=batch.id,
                    user_id=user_data.get("user_id", ""),
                    age=user_data.get("age"),
                    gender=user_data.get("gender"),
                    education=user_data.get("education"),
                    income_level=user_data.get("income_level"),
                    city_tier=user_data.get("city_tier"),
                    occupation=user_data.get("occupation"),
                    has_house=user_data.get("has_house"),
                    has_car=user_data.get("has_car"),
                    phone_price=user_data.get("phone_price"),
                    marital_status=user_data.get("marital_status"),
                    has_children=user_data.get("has_children"),
                    commute_distance=user_data.get("commute_distance"),
                    interests=user_data.get("interests"),
                    behaviors=user_data.get("behaviors"),
                    primary_brand=user_data.get("primary_brand"),
                    primary_model=user_data.get("primary_model"),
                    brand_score=user_data.get("brand_score"),
                    purchase_intent=user_data.get("purchase_intent"),
                    intent_score=user_data.get("intent_score"),
                    lifecycle_stage=user_data.get("lifecycle_stage"),
                    app_open_count=user_data.get("app_open_count"),
                    app_usage_duration=user_data.get("app_usage_duration"),
                    miniprogram_open_count=user_data.get("miniprogram_open_count"),
                    car_search_count=user_data.get("car_search_count"),
                    car_browse_count=user_data.get("car_browse_count"),
                    car_compare_count=user_data.get("car_compare_count"),
                    car_app_payment=user_data.get("car_app_payment"),
                    push_exposure=user_data.get("push_exposure"),
                    push_click=user_data.get("push_click"),
                    ad_exposure=user_data.get("ad_exposure"),
                    ad_click=user_data.get("ad_click"),
                    near_4s_store=user_data.get("near_4s_store"),
                    weather_info=user_data.get("weather_info"),
                    consumption_frequency=user_data.get("consumption_frequency"),
                    raw_data=user_data  # 保存完整数据
                )
                db.add(user)

            db.commit()
            db.refresh(batch)
            app_logger.info(f"创建导入批次成功: {batch.batch_name}, ID: {batch.id}")
            return batch

    @staticmethod
    def list_batches(limit: int = 50, offset: int = 0) -> List[ImportBatch]:
        """获取批次列表"""
        with get_db() as db:
            batches = db.query(ImportBatch).order_by(
                ImportBatch.batch_time.desc()
            ).limit(limit).offset(offset).all()
            return batches

    @staticmethod
    def get_batch(batch_id: int) -> Optional[ImportBatch]:
        """获取指定批次"""
        with get_db() as db:
            batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
            return batch

    @staticmethod
    def get_batch_users(batch_id: int, limit: int = 1000, offset: int = 0) -> List[Dict]:
        """获取批次的用户数据"""
        with get_db() as db:
            users = db.query(ImportedUser).filter(
                ImportedUser.batch_id == batch_id
            ).limit(limit).offset(offset).all()
            return [user.to_dict() for user in users]

    @staticmethod
    def delete_batch(batch_id: int) -> bool:
        """删除批次（级联删除用户数据）"""
        with get_db() as db:
            batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
            if batch:
                db.delete(batch)
                db.commit()
                app_logger.info(f"删除导入批次: ID {batch_id}")
                return True
            return False

    @staticmethod
    def get_latest_batch() -> Optional[ImportBatch]:
        """获取最新的批次"""
        with get_db() as db:
            batch = db.query(ImportBatch).order_by(
                ImportBatch.batch_time.desc()
            ).first()
            return batch
