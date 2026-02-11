from typing import Dict, List
from app.core.anthropic_client import AnthropicClient
from app.services.sample_manager import SampleManager

class EventGraphBuilder:
    def __init__(self, llm_client: AnthropicClient):
        self.llm = llm_client
        self.sample_manager = SampleManager()
    
    async def build(
        self,
        industry: str = "汽车",
        ratios: Dict[str, int] = None,
        total_samples: int = 1000
    ) -> Dict:
        samples = self.sample_manager.generate_samples(industry, ratios, total_samples)
        stats = self.sample_manager.compute_statistics(samples)
        typical_cases = self.sample_manager.extract_typical_cases(samples)
        
        if not self.llm:
            return self._generate_mock_event_graph(stats, samples)
        
        try:
            result = await self.llm.generate_event_graph(
                statistics=stats,
                typical_cases=typical_cases,
                analysis_focus=str({
                    "causal": "分析高尔夫兴趣对豪华轿车购买的影响",
                    "churn_factors": "流失用户在品牌偏好上的差异",
                    "conversion_path": "从兴趣到购买的转化路径"
                })
            )
        except Exception as e:
            print(f"LLM调用失败: {e}")
            result = self._generate_mock_event_graph(stats, samples)
        
        result["industry"] = industry
        result["sample_stats"] = {
            "positive": len(samples["positive"]),
            "churn": len(samples["churn"]),
            "weak": len(samples["weak"]),
            "control": len(samples["control"])
        }
        
        return result
    
    def _generate_mock_event_graph(self, stats: Dict, samples: Dict) -> Dict:
        return {
            "nodes": [
                {"id": "E001", "type": "行为特征", "name": "高尔夫兴趣", "description": "对高尔夫运动有浓厚兴趣"},
                {"id": "E002", "type": "行为特征", "name": "高收入", "description": "年收入50万以上"},
                {"id": "E003", "type": "行为特征", "name": "商务出行频繁", "description": "每月商务出行3次以上"},
                {"id": "E004", "type": "转化结果", "name": "宝马7系购买意向", "description": "倾向于购买宝马7系"},
                {"id": "E005", "type": "转化结果", "name": "奔驰S级购买意向", "description": "倾向于购买奔驰S级"},
                {"id": "E006", "type": "流失原因", "name": "价格敏感", "description": "对价格较为敏感"},
            ],
            "edges": [
                {"from": "E001", "to": "E004", "relation": "高尔夫兴趣用户更倾向宝马7系", "probability": 0.75, "confidence": 0.88},
                {"from": "E001", "to": "E005", "relation": "高尔夫兴趣用户也关注奔驰S级", "probability": 0.65, "confidence": 0.82},
                {"from": "E002", "to": "E004", "relation": "高收入用户偏好宝马运动感", "probability": 0.70, "confidence": 0.90},
                {"from": "E002", "to": "E005", "relation": "高收入用户认可奔驰品牌调性", "probability": 0.80, "confidence": 0.92},
                {"from": "E003", "to": "E005", "relation": "商务出行频繁者更倾向奔驰S级", "probability": 0.72, "confidence": 0.85},
                {"from": "E006", "to": "流失", "relation": "价格敏感导致流失风险", "probability": 0.45, "confidence": 0.78}
            ],
            "insights": [
                "高尔夫兴趣用户中，宝马7系转化率(75%)高于奔驰S级(65%)",
                "商务出行频繁用户更倾向于选择奔驰S级(72%)",
                "高收入人群中，奔驰S级偏好(80%)略高于宝马7系(70%)",
                "价格敏感是导致流失的主要原因之一"
            ],
            "recommendations": [
                "针对高尔夫兴趣用户，重点投放宝马7系素材",
                "针对商务出行场景，优先推荐奔驰S级",
                "加强宝马7系的商务属性宣传，平衡用户群体"
            ]
        }
