from typing import Dict, List
from collections import defaultdict
import math
from app.core.anthropic_client import AnthropicClient
from app.services.sample_manager import SampleManager
from app.core.logger import app_logger

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
    
    async def build_from_real_data(
        self,
        users: List[Dict],
        analysis_focus: Dict = None
    ) -> Dict:
        """从真实用户数据构建事理图谱"""
        app_logger.info(f"开始从 {len(users)} 条真实数据构建事理图谱")

        # 计算真实统计数据
        stats = self._calculate_real_statistics(users)

        # 提取典型案例
        typical_cases = self._extract_real_typical_cases(users, stats)

        # 如果有LLM，使用LLM生成事理图谱
        if self.llm:
            try:
                result = await self.llm.generate_event_graph(
                    statistics=stats,
                    typical_cases=typical_cases,
                    analysis_focus=str(analysis_focus) if analysis_focus else "分析用户行为与购买意向的因果关系"
                )
                app_logger.info("成功使用LLM生成事理图谱")
            except Exception as e:
                app_logger.warning(f"LLM调用失败，使用基于规则的方法: {e}")
                result = self._generate_rule_based_event_graph(stats, users)
        else:
            app_logger.info("未配置LLM，使用基于规则的方法生成事理图谱")
            result = self._generate_rule_based_event_graph(stats, users)

        result["data_source"] = "real_csv_data"
        result["total_users"] = len(users)
        result["statistics"] = stats

        return result

    def _calculate_real_statistics(self, users: List[Dict]) -> Dict:
        """计算真实数据的统计信息"""
        stats = {
            "total_users": len(users),
            "interest_distribution": defaultdict(int),
            "brand_distribution": defaultdict(int),
            "behavior_distribution": defaultdict(int),
            "intent_distribution": defaultdict(int),
            "interest_brand_correlation": defaultdict(lambda: defaultdict(int)),
            "behavior_intent_correlation": defaultdict(lambda: defaultdict(int))
        }

        for user in users:
            # 统计兴趣分布
            interests = user.get("interests", [])
            if isinstance(interests, list):
                for interest in interests:
                    stats["interest_distribution"][interest] += 1

            # 统计品牌分布
            brand = user.get("primary_brand")
            if brand:
                stats["brand_distribution"][brand] += 1

                # 统计兴趣-品牌相关性
                if isinstance(interests, list):
                    for interest in interests:
                        stats["interest_brand_correlation"][interest][brand] += 1

            # 统计行为分布
            behaviors = user.get("behaviors", [])
            if isinstance(behaviors, list):
                for behavior in behaviors:
                    stats["behavior_distribution"][behavior] += 1

            # 统计购买意向分布
            intent = user.get("purchase_intent")
            if intent:
                stats["intent_distribution"][intent] += 1

                # 统计行为-意向相关性
                if isinstance(behaviors, list):
                    for behavior in behaviors:
                        stats["behavior_intent_correlation"][behavior][intent] += 1

        return stats

    def _extract_real_typical_cases(self, users: List[Dict], stats: Dict) -> Dict:
        """从真实数据中提取典型案例"""
        typical_cases = {
            "high_intent_users": [],
            "low_intent_users": [],
            "popular_interests": [],
            "popular_brands": []
        }

        # 提取高意向用户
        for user in users:
            intent_score = user.get("intent_score", 0)
            if isinstance(intent_score, (int, float)) and intent_score > 0.7:
                typical_cases["high_intent_users"].append({
                    "user_id": user.get("user_id"),
                    "interests": user.get("interests", []),
                    "brand": user.get("primary_brand"),
                    "intent_score": intent_score
                })

        # 提取低意向用户
        for user in users:
            intent_score = user.get("intent_score", 0)
            if isinstance(intent_score, (int, float)) and intent_score < 0.3:
                typical_cases["low_intent_users"].append({
                    "user_id": user.get("user_id"),
                    "interests": user.get("interests", []),
                    "brand": user.get("primary_brand"),
                    "intent_score": intent_score
                })

        # 提取热门兴趣
        typical_cases["popular_interests"] = sorted(
            stats["interest_distribution"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # 提取热门品牌
        typical_cases["popular_brands"] = sorted(
            stats["brand_distribution"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return typical_cases

    def _generate_rule_based_event_graph(self, stats: Dict, users: List[Dict]) -> Dict:
        """基于规则生成事理图谱（当LLM不可用时）"""
        nodes = []
        edges = []
        insights = []
        recommendations = []

        total_users = stats["total_users"]
        node_id_counter = 1

        # 创建兴趣节点（Top 5）
        interest_nodes = {}
        for interest, count in sorted(stats["interest_distribution"].items(), key=lambda x: x[1], reverse=True)[:5]:
            node_id = f"E{node_id_counter:03d}"
            node_id_counter += 1
            interest_nodes[interest] = node_id
            nodes.append({
                "id": node_id,
                "type": "兴趣特征",
                "name": interest,
                "description": f"{count}个用户({count/total_users*100:.1f}%)具有此兴趣"
            })

        # 创建品牌节点（Top 5）
        brand_nodes = {}
        for brand, count in sorted(stats["brand_distribution"].items(), key=lambda x: x[1], reverse=True)[:5]:
            node_id = f"E{node_id_counter:03d}"
            node_id_counter += 1
            brand_nodes[brand] = node_id
            nodes.append({
                "id": node_id,
                "type": "品牌偏好",
                "name": f"{brand}偏好",
                "description": f"{count}个用户({count/total_users*100:.1f}%)偏好此品牌"
            })

        # 创建兴趣-品牌关联边
        for interest, brands in stats["interest_brand_correlation"].items():
            if interest not in interest_nodes:
                continue

            for brand, cooccur_count in brands.items():
                if brand not in brand_nodes:
                    continue

                # 计算条件概率和置信度（使用Wilson score interval）
                interest_count = stats["interest_distribution"][interest]
                probability = cooccur_count / interest_count if interest_count > 0 else 0
                confidence = self._wilson_score(cooccur_count, interest_count)

                if probability > 0.1:  # 只保留显著关联
                    edges.append({
                        "from": interest_nodes[interest],
                        "to": brand_nodes[brand],
                        "relation": f"{interest}用户倾向于{brand}",
                        "probability": round(probability, 2),
                        "confidence": round(confidence, 2)
                    })

                    if probability > 0.5:
                        insights.append(
                            f"{interest}兴趣用户中，{probability*100:.0f}%偏好{brand}品牌（置信度{confidence*100:.0f}%）"
                        )

        # 生成推荐
        if edges:
            top_edge = max(edges, key=lambda x: x["probability"])
            recommendations.append(
                f"针对{nodes[int(top_edge['from'][1:])-1]['name']}兴趣用户，重点投放{nodes[int(top_edge['to'][1:])-1]['name']}相关素材"
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "insights": insights if insights else ["数据量不足，无法生成有效洞察"],
            "recommendations": recommendations if recommendations else ["建议收集更多数据以生成精准推荐"]
        }

    def _wilson_score(self, successes: int, total: int, confidence: float = 0.95) -> float:
        """计算Wilson score interval的下界，用于置信度评估"""
        if total == 0:
            return 0.0

        # Z-score for 95% confidence
        z = 1.96 if confidence == 0.95 else 1.645

        p = successes / total
        denominator = 1 + z * z / total
        centre = (p + z * z / (2 * total)) / denominator
        adjustment = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator

        return max(0.0, centre - adjustment)
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
