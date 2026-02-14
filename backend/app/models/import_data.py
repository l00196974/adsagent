"""
数据持久化模型 - 导入批次和用户数据
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class ImportBatch(Base):
    """导入批次表"""
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_name = Column(String(200), nullable=False, comment="批次名称")
    batch_time = Column(DateTime, default=datetime.now, comment="导入时间")
    file_count = Column(Integer, default=0, comment="文件数量")
    record_count = Column(Integer, default=0, comment="记录数量")
    unique_record_count = Column(Integer, default=0, comment="去重后记录数量")
    file_info = Column(JSON, comment="文件信息列表")
    field_mapping = Column(JSON, comment="字段映射信息")
    status = Column(String(50), default="completed", comment="批次状态: completed, failed")
    description = Column(Text, comment="批次描述")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联的用户数据
    users = relationship("ImportedUser", back_populates="batch", cascade="all, delete-orphan")


class ImportedUser(Base):
    """导入的用户数据表"""
    __tablename__ = "imported_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False, comment="所属批次ID")
    user_id = Column(String(100), nullable=False, comment="用户ID")

    # 基础信息
    age = Column(Integer, comment="年龄")
    gender = Column(String(20), comment="性别")
    education = Column(String(50), comment="学历")
    income_level = Column(String(50), comment="收入水平")
    city_tier = Column(String(50), comment="城市等级")
    occupation = Column(String(100), comment="职业")

    # 资产信息
    has_house = Column(Boolean, comment="是否有房")
    has_car = Column(Boolean, comment="是否有车")
    phone_price = Column(String(50), comment="手机价格")

    # 家庭信息
    marital_status = Column(String(50), comment="婚姻状况")
    has_children = Column(Boolean, comment="是否有孩子")
    commute_distance = Column(Integer, comment="通勤距离")

    # 兴趣和行为
    interests = Column(JSON, comment="兴趣列表")
    behaviors = Column(JSON, comment="行为列表")

    # 品牌偏好
    primary_brand = Column(String(100), comment="主要品牌")
    primary_model = Column(String(100), comment="主要车型")
    brand_score = Column(Integer, comment="品牌分数")

    # 购买意向
    purchase_intent = Column(String(50), comment="购买意向")
    intent_score = Column(Integer, comment="意向分数")
    lifecycle_stage = Column(String(50), comment="生命周期阶段")

    # APP使用行为
    app_open_count = Column(Integer, comment="APP打开次数")
    app_usage_duration = Column(Integer, comment="APP使用时长")
    miniprogram_open_count = Column(Integer, comment="小程序打开次数")

    # 汽车相关行为
    car_search_count = Column(Integer, comment="汽车搜索次数")
    car_browse_count = Column(Integer, comment="汽车浏览次数")
    car_compare_count = Column(Integer, comment="汽车比价次数")
    car_app_payment = Column(Boolean, comment="汽车APP付费")

    # 广告和消息
    push_exposure = Column(Integer, comment="PUSH曝光次数")
    push_click = Column(Integer, comment="PUSH点击次数")
    ad_exposure = Column(Integer, comment="广告曝光次数")
    ad_click = Column(Integer, comment="广告点击次数")

    # 位置和天气
    near_4s_store = Column(Boolean, comment="是否在4S店附近")
    weather_info = Column(String(50), comment="天气信息")

    # 消费行为
    consumption_frequency = Column(Integer, comment="消费频率")

    # 完整数据（JSON格式存储所有字段）
    raw_data = Column(JSON, comment="原始完整数据")

    created_at = Column(DateTime, default=datetime.now)

    # 关联的批次
    batch = relationship("ImportBatch", back_populates="users")

    def to_dict(self):
        """转换为字典"""
        if self.raw_data:
            return self.raw_data

        # 如果没有raw_data，从字段构建
        return {
            "user_id": self.user_id,
            "age": self.age,
            "gender": self.gender,
            "education": self.education,
            "income_level": self.income_level,
            "city_tier": self.city_tier,
            "occupation": self.occupation,
            "has_house": self.has_house,
            "has_car": self.has_car,
            "phone_price": self.phone_price,
            "marital_status": self.marital_status,
            "has_children": self.has_children,
            "commute_distance": self.commute_distance,
            "interests": self.interests,
            "behaviors": self.behaviors,
            "primary_brand": self.primary_brand,
            "primary_model": self.primary_model,
            "brand_score": self.brand_score,
            "purchase_intent": self.purchase_intent,
            "intent_score": self.intent_score,
            "lifecycle_stage": self.lifecycle_stage,
            "app_open_count": self.app_open_count,
            "app_usage_duration": self.app_usage_duration,
            "miniprogram_open_count": self.miniprogram_open_count,
            "car_search_count": self.car_search_count,
            "car_browse_count": self.car_browse_count,
            "car_compare_count": self.car_compare_count,
            "car_app_payment": self.car_app_payment,
            "push_exposure": self.push_exposure,
            "push_click": self.push_click,
            "ad_exposure": self.ad_exposure,
            "ad_click": self.ad_click,
            "near_4s_store": self.near_4s_store,
            "weather_info": self.weather_info,
            "consumption_frequency": self.consumption_frequency,
        }
