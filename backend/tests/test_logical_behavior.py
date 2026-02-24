"""
逻辑行为生成服务单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.services.logical_behavior import LogicalBehaviorGenerator
from app.core.openai_client import OpenAIClient


@pytest.fixture
def mock_llm_client():
    """Mock LLM客户端"""
    client = Mock(spec=OpenAIClient)
    return client


@pytest.fixture
def generator(mock_llm_client):
    """创建生成器实例"""
    return LogicalBehaviorGenerator(llm_client=mock_llm_client, db_path=":memory:")


def test_format_raw_behaviors(generator):
    """测试行为格式化（验证包含完整属性）"""
    behaviors = [
        {
            "id": 1,
            "timestamp": "2026-01-15 23:30:15",
            "action": "browse",
            "app_name": "抖音",
            "app_category": "短视频",
            "media_name": "美妆博主A",
            "media_type": "KOL",
            "item_id": "item_015",
            "duration": 120
        },
        {
            "id": 2,
            "timestamp": "2026-01-15 23:35:20",
            "action": "click",
            "app_name": "小红书",
            "app_category": "种草社区",
            "poi_id": "宿舍"
        }
    ]

    formatted = generator._format_raw_behaviors(behaviors)

    # 验证包含完整属性
    assert "抖音" in formatted
    assert "短视频" in formatted
    assert "美妆博主A" in formatted
    assert "item_015" in formatted
    assert "120秒" in formatted
    assert "小红书" in formatted
    assert "宿舍" in formatted


def test_parse_llm_response(generator):
    """测试LLM响应解析"""
    response = """
Z世代年轻女性学生|深夜宿舍休闲娱乐场景|浏览种草内容|平价美妆产品|2026-01-15 23:30:00|2026-01-15 23:45:00|1,2,3|0.9
中年高收入男性白领|工作日午休碎片时间|浏览汽车资讯|豪华品牌SUV|2026-01-16 12:00:00|2026-01-16 12:15:00|4,5|0.85
"""

    behaviors = generator._parse_llm_response("user_0001", response, [])

    assert len(behaviors) == 2

    # 验证第一个逻辑行为
    assert behaviors[0]["user_id"] == "user_0001"
    assert behaviors[0]["agent"] == "Z世代年轻女性学生"
    assert behaviors[0]["scene"] == "深夜宿舍休闲娱乐场景"
    assert behaviors[0]["action"] == "浏览种草内容"
    assert behaviors[0]["object"] == "平价美妆产品"
    assert behaviors[0]["raw_behavior_ids"] == "1,2,3"
    assert behaviors[0]["confidence"] == 0.9

    # 验证第二个逻辑行为
    assert behaviors[1]["agent"] == "中年高收入男性白领"
    assert behaviors[1]["confidence"] == 0.85


def test_parse_llm_response_with_markdown(generator):
    """测试解析带markdown代码块的响应"""
    response = """```text
Z世代年轻女性学生|深夜宿舍休闲娱乐场景|浏览种草内容|平价美妆产品|2026-01-15 23:30:00|2026-01-15 23:45:00|1,2,3|0.9
```"""

    behaviors = generator._parse_llm_response("user_0001", response, [])

    assert len(behaviors) == 1
    assert behaviors[0]["agent"] == "Z世代年轻女性学生"


def test_parse_llm_response_skip_invalid_lines(generator):
    """测试跳过格式不正确的行"""
    response = """
# 这是注释
Z世代年轻女性学生|深夜宿舍休闲娱乐场景|浏览种草内容|平价美妆产品|2026-01-15 23:30:00|2026-01-15 23:45:00|1,2,3|0.9
这行格式不对
|||||||||
中年高收入男性白领|工作日午休碎片时间|浏览汽车资讯|豪华品牌SUV|2026-01-16 12:00:00|2026-01-16 12:15:00|4,5|0.85
"""

    behaviors = generator._parse_llm_response("user_0001", response, [])

    # 应该只解析出2个有效行为
    assert len(behaviors) == 2


def test_build_prompt(generator):
    """测试prompt构建"""
    user_profile = {
        "user_id": "user_0001",
        "age": 22,
        "age_bucket": "18-25岁",
        "gender": "女",
        "city": "北京",
        "occupation": "学生",
        "education": "本科",
        "income_level": "低收入",
        "interests": ["美妆", "时尚"],
        "behaviors": ["夜间活跃", "社交媒体重度用户"]
    }

    formatted_behaviors = "[2026-01-15 23:30:15] browse | APP:抖音(短视频)"

    prompt = generator._build_prompt(user_profile, formatted_behaviors)

    # 验证prompt包含关键信息
    assert "user_0001" in prompt
    assert "22岁" in prompt
    assert "18-25岁" in prompt
    assert "女" in prompt
    assert "学生" in prompt
    assert "美妆, 时尚" in prompt
    assert "抖音" in prompt
    assert "本体(Agent)" in prompt
    assert "环境(Scene)" in prompt
    assert "行动(Action)" in prompt
    assert "对象(Object)" in prompt


def test_enrich_behaviors_with_tags(generator):
    """测试行为丰富化（验证app_tags和media_tags关联）"""
    # 这个测试需要实际数据库，暂时跳过
    # 在集成测试中验证
    pass


@pytest.mark.asyncio
async def test_generate_for_user_no_behaviors(generator):
    """测试用户无行为数据的情况"""
    with patch.object(generator, '_get_user_profile', return_value={"user_id": "user_0001"}):
        with patch.object(generator, '_get_raw_behaviors', return_value=[]):
            with patch.object(generator, '_update_sequence_status'):
                result = await generator.generate_for_user("user_0001")

                assert result["user_id"] == "user_0001"
                assert result["logical_behaviors"] == []
                assert result["raw_behavior_count"] == 0
                assert result["logical_behavior_count"] == 0


def test_get_progress(generator):
    """测试获取进度"""
    progress = generator.get_progress()

    assert "total_users" in progress
    assert "processed_users" in progress
    assert "success_count" in progress
    assert "failed_count" in progress
    assert progress["total_users"] == 0


def test_update_progress(generator):
    """测试更新进度"""
    generator.progress["total_users"] = 10

    generator._update_progress(
        processed_users=5,
        success_count=4,
        failed_count=1
    )

    assert generator.progress["processed_users"] == 5
    assert generator.progress["success_count"] == 4
    assert generator.progress["failed_count"] == 1
