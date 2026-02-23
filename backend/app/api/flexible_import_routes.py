"""
灵活CSV导入API路由
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict
import io
import csv

from app.services.flexible_csv_importer import FlexibleCSVImporter
from app.core.logger import app_logger

router = APIRouter(prefix="/api/v1/flexible-import", tags=["灵活导入"])


@router.post("/behavior-data")
async def import_behavior_data(file: UploadFile = File(...)) -> Dict:
    """导入行为数据CSV

    必需列:
    - user_id: 用户ID
    - event_time 或 timestamp: 事件时间

    其他列（包括action/event_type）会自动打包到event_data中
    """
    try:
        # 保存上传的文件
        temp_file = f"/tmp/{file.filename}"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # 导入数据
        importer = FlexibleCSVImporter()
        result = importer.import_behavior_data(temp_file)

        app_logger.info(f"行为数据导入完成: {result}")

        return {
            "success": True,
            "message": f"成功导入 {result['success']} 条记录",
            "data": result
        }

    except Exception as e:
        app_logger.error(f"导入行为数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-profiles")
async def import_user_profiles(file: UploadFile = File(...)) -> Dict:
    """导入用户画像CSV

    必需列:
    - user_id: 用户ID

    其他列会自动打包到profile_data中
    """
    try:
        # 保存上传的文件
        temp_file = f"/tmp/{file.filename}"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # 导入数据
        importer = FlexibleCSVImporter()
        result = importer.import_user_profiles(temp_file)

        app_logger.info(f"用户画像导入完成: {result}")

        return {
            "success": True,
            "message": f"成功导入 {result['success']} 个用户画像",
            "data": result
        }

    except Exception as e:
        app_logger.error(f"导入用户画像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/behavior-data")
async def download_behavior_template():
    """下载行为数据CSV模板"""

    # 创建CSV模板
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow([
        'user_id',
        'event_time',
        'action',
        'item',
        'duration',
        'app',
        'media',
        'poi'
    ])

    # 写入示例数据
    writer.writerow([
        'user_001',
        '2026-02-22 10:00:00',
        'browse',
        '宝马5系',
        '120',
        '汽车之家',
        '',
        ''
    ])

    writer.writerow([
        'user_001',
        '2026-02-22 10:05:00',
        'search',
        '豪华轿车',
        '',
        '汽车之家',
        '',
        ''
    ])

    writer.writerow([
        'user_002',
        '2026-02-22 10:10:00',
        'browse',
        '奔驰E级',
        '180',
        '',
        '易车网',
        ''
    ])

    writer.writerow([
        'user_003',
        '2026-02-22 10:15:00',
        'visit_poi',
        '',
        '3600',
        '',
        '',
        '宝马4S店'
    ])

    writer.writerow([
        'user_003',
        '2026-02-22 14:30:00',
        'purchase',
        '宝马5系',
        '',
        '',
        '',
        '宝马4S店'
    ])

    # 返回CSV文件
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=behavior_data_template.csv"
        }
    )


@router.get("/template/user-profiles")
async def download_profile_template():
    """下载用户画像CSV模板"""

    # 创建CSV模板
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow([
        'user_id',
        'age',
        'gender',
        'income',
        'occupation',
        'city',
        'interests',
        'has_car',
        'purchase_intent'
    ])

    # 写入示例数据
    writer.writerow([
        'user_001',
        '35',
        '男',
        '25000',
        '互联网从业者',
        '上海',
        '高尔夫,旅游,科技',
        '是',
        '换车'
    ])

    writer.writerow([
        'user_002',
        '28',
        '女',
        '15000',
        '金融从业者',
        '北京',
        '美食,健身,阅读',
        '否',
        '首购'
    ])

    writer.writerow([
        'user_003',
        '42',
        '男',
        '35000',
        '企业管理者',
        '深圳',
        '高尔夫,商务,投资',
        '是',
        '增购'
    ])

    # 返回CSV文件
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=user_profiles_template.csv"
        }
    )


@router.get("/template/instructions")
async def get_template_instructions():
    """获取CSV模板使用说明"""

    return {
        "behavior_data": {
            "description": "行为数据CSV模板",
            "required_columns": [
                {
                    "name": "user_id",
                    "type": "文本",
                    "description": "用户ID（必需，结构化字段）",
                    "example": "user_001"
                },
                {
                    "name": "event_time",
                    "type": "日期时间",
                    "description": "事件发生时间（必需，结构化字段）",
                    "example": "2026-02-22 10:00:00",
                    "format": "YYYY-MM-DD HH:MM:SS"
                }
            ],
            "optional_columns": [
                {
                    "name": "action",
                    "type": "文本",
                    "description": "行为类型（非结构化，会打包到event_data）",
                    "example": "browse, search, click, purchase"
                },
                {
                    "name": "item",
                    "type": "文本",
                    "description": "物品/车型（非结构化）",
                    "example": "宝马5系"
                },
                {
                    "name": "duration",
                    "type": "整数",
                    "description": "持续时间（秒）（非结构化）",
                    "example": "120"
                },
                {
                    "name": "app",
                    "type": "文本",
                    "description": "APP名称（非结构化）",
                    "example": "汽车之家"
                },
                {
                    "name": "media",
                    "type": "文本",
                    "description": "媒体名称（非结构化）",
                    "example": "易车网"
                },
                {
                    "name": "poi",
                    "type": "文本",
                    "description": "地点名称（非结构化）",
                    "example": "宝马4S店"
                }
            ],
            "notes": [
                "只有user_id和event_time是结构化字段",
                "其他所有列（包括action）都会打包到event_data中",
                "可以添加任意自定义列，无需修改数据库结构",
                "空值可以留空或不填",
                "文件编码建议使用UTF-8"
            ]
        },
        "user_profiles": {
            "description": "用户画像CSV模板",
            "required_columns": [
                {
                    "name": "user_id",
                    "type": "文本",
                    "description": "用户ID（必需，结构化字段）",
                    "example": "user_001"
                }
            ],
            "optional_columns": [
                {
                    "name": "age",
                    "type": "整数",
                    "description": "年龄（非结构化）",
                    "example": "35"
                },
                {
                    "name": "gender",
                    "type": "文本",
                    "description": "性别（非结构化）",
                    "example": "男/女"
                },
                {
                    "name": "income",
                    "type": "整数",
                    "description": "月收入（元）（非结构化）",
                    "example": "25000"
                },
                {
                    "name": "occupation",
                    "type": "文本",
                    "description": "职业（非结构化）",
                    "example": "互联网从业者"
                },
                {
                    "name": "city",
                    "type": "文本",
                    "description": "城市（非结构化）",
                    "example": "上海"
                },
                {
                    "name": "interests",
                    "type": "文本",
                    "description": "兴趣爱好（逗号分隔）（非结构化）",
                    "example": "高尔夫,旅游,科技"
                }
            ],
            "notes": [
                "只有user_id是结构化字段",
                "其他所有列都会打包到profile_data中",
                "可以添加任意自定义列，无需修改数据库结构",
                "空值可以留空或不填",
                "文件编码建议使用UTF-8"
            ]
        }
    }
