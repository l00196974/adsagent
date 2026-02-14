from typing import Dict, List, Optional
import random
from app.data.mock_data import get_mock_users

class SampleManager:
    def __init__(self):
        self.default_ratios = {"positive": 1, "churn": 10, "weak": 5, "control": 5}
        self._cached_samples = None
    
    def generate_samples(
        self,
        industry: str = "汽车",
        ratios: Optional[Dict[str, int]] = None,
        total_count: int = 1000
    ) -> Dict[str, List[Dict]]:
        ratios = ratios or self.default_ratios
        total_ratio = sum(ratios.values())
        
        users = get_mock_users(total_count * 2)
        
        samples = {"positive": [], "churn": [], "weak": [], "control": []}
        
        for user in users:
            intent = user.get("purchase_intent", "无")
            stage = user.get("lifecycle_stage", "空白")
            
            if intent == "高" and stage in ["意向", "转化"]:
                if len(samples["positive"]) < total_count * ratios["positive"] // total_ratio:
                    samples["positive"].append(self._compress_user(user))
            elif stage == "流失":
                if len(samples["churn"]) < total_count * ratios["churn"] // total_ratio:
                    samples["churn"].append(self._compress_user(user))
            elif intent == "中":
                if len(samples["weak"]) < total_count * ratios["weak"] // total_ratio:
                    samples["weak"].append(self._compress_user(user))
            else:
                if len(samples["control"]) < total_count * ratios["control"] // total_ratio:
                    samples["control"].append(self._compress_user(user))
        
        return samples
    
    def compute_statistics(self, samples: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        stats = {}
        
        for sample_type, users in samples.items():
            if not users:
                stats[sample_type] = {"count": 0}
                continue
            
            incomes = [u["profile"]["income"] for u in users]
            income_dist = {}
            for inc in incomes:
                income_dist[inc] = income_dist.get(inc, 0) + 1
            
            interests = []
            for u in users:
                interests.extend(u.get("interests", []))
            interest_freq = {}
            for interest in interests:
                interest_freq[interest] = interest_freq.get(interest, 0) + 1
            
            brands = [u["brand"]["primary_brand"] for u in users]
            brand_dist = {}
            for b in brands:
                brand_dist[b] = brand_dist.get(b, 0) + 1
            
            stats[sample_type] = {
                "count": len(users),
                "income_distribution": income_dist,
                "top_interests": sorted(interest_freq.items(), key=lambda x: x[1], reverse=True)[:10],
                "brand_distribution": brand_dist
            }
        
        return stats
    
    def extract_typical_cases(self, samples: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        typical = {}
        for sample_type, users in samples.items():
            n = min(5, len(users))
            typical[sample_type] = users[:n]
        return typical
    
    def _compress_user(self, user: Dict) -> Dict:
        return {
            "user_id": user["user_id"],
            "profile": {
                "age_bucket": user["demographics"]["age_bucket"],
                "income": user["demographics"]["income_level"],
                "city": user["demographics"]["city_tier"]
            },
            "interests": user["interests"][:5],
            "brand": user["brand_affinity"],
            "intent": user["purchase_intent"],
            "stage": user["lifecycle_stage"]
        }
    
    def process_csv_import(self, users_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Process imported CSV data and categorize into sample types"""
        samples = {"positive": [], "churn": [], "weak": [], "control": []}
        
        for user in users_data:
            normalized = self._normalize_csv_user(user)
            
            # Categorize based on purchase intent and lifecycle stage
            intent = normalized.get("purchase_intent", "无")
            stage = normalized.get("lifecycle_stage", "空白")
            
            if intent == "高" and stage in ["意向", "转化"]:
                samples["positive"].append(normalized)
            elif stage == "流失":
                samples["churn"].append(normalized)
            elif intent == "中":
                samples["weak"].append(normalized)
            else:
                samples["control"].append(normalized)
        
        return samples
    
    def _normalize_csv_user(self, user_data: Dict) -> Dict:
        """Normalize CSV user data to internal format"""
        return {
            "user_id": user_data.get("user_id", f"U{len(user_data):06d}"),
            "demographics": {
                "age": user_data.get("age", 30),
                "age_bucket": user_data.get("age_bucket", "30-35"),
                "gender": user_data.get("gender", "男"),
                "income_level": user_data.get("income_level", "中等收入"),
                "city_tier": user_data.get("city_tier", "一线"),
                "occupation": user_data.get("occupation", "技术专家")
            },
            "interests": user_data.get("interests", "").split(",") if isinstance(user_data.get("interests"), str) else user_data.get("interests", []),
            "behaviors": user_data.get("behaviors", []),
            "brand_affinity": {
                "primary_brand": user_data.get("primary_brand", "宝马"),
                "primary_model": user_data.get("primary_model", "5系"),
                "brand_score": float(user_data.get("brand_score", 0.5))
            },
            "purchase_intent": user_data.get("purchase_intent", "无"),
            "intent_score": float(user_data.get("intent_score", 0.0)),
            "lifecycle_stage": user_data.get("lifecycle_stage", "空白")
        }
    
    def infer_user(self, user_data: Dict) -> Dict:
        """Perform inference on user data to calculate scores"""
        normalized = self._normalize_csv_user(user_data)
        
        # Calculate churn probability based on behaviors and lifecycle stage
        stage = normalized.get("lifecycle_stage", "空白")
        behaviors = normalized.get("behaviors", [])
        
        churn_prob = 0.0
        if stage == "流失":
            churn_prob = 0.9
        elif stage == "空白":
            churn_prob = 0.3
        elif stage == "认知":
            churn_prob = 0.2
        elif stage == "意向":
            churn_prob = 0.1
        elif stage == "转化":
            churn_prob = 0.05
        
        # Adjust based on behavior frequency
        if len(behaviors) < 2:
            churn_prob += 0.1
        elif len(behaviors) > 10:
            churn_prob -= 0.1
        
        churn_prob = min(1.0, max(0.0, churn_prob))
        
        # Calculate purchase intent score
        intent_map = {"无": 0.0, "低": 0.25, "中": 0.5, "高": 1.0}
        intent_score = normalized.get("intent_score", intent_map.get(normalized.get("purchase_intent", "无"), 0.0))
        
        # Calculate brand affinity
        brand = normalized.get("brand_affinity", {})
        brand_score = brand.get("brand_score", 0.5)
        
        # Generate recommendations
        recommendations = []
        if intent_score > 0.7:
            recommendations.append("高意向用户，建议优先转化")
        elif intent_score > 0.4:
            recommendations.append("中等意向，建议培育")
        else:
            recommendations.append("低意向用户，建议认知培育")
        
        if churn_prob > 0.5:
            recommendations.append("流失风险高，建议召回")
        
        interests = normalized.get("interests", [])
        if "高尔夫" in interests:
            recommendations.append("兴趣偏向高端运动，可推送豪华车型")
        if "科技" in interests:
            recommendations.append("关注科技，可推送新能源车型")
        
        return {
            "user_id": normalized["user_id"],
            "churn_probability": round(churn_prob, 3),
            "intent_score": round(intent_score, 3),
            "brand_affinity_score": round(brand_score, 3),
            "recommendations": recommendations,
            "normalized_data": normalized
        }
    
    def get_all_samples(self) -> Dict[str, List[Dict]]:
        """Get all cached samples"""
        if self._cached_samples is None:
            # Generate default samples if not cached
            self._cached_samples = self.generate_samples(
                industry="汽车",
                ratios=self.default_ratios,
                total_count=1000
            )
        return self._cached_samples
    
    def cache_samples(self, samples: Dict[str, List[Dict]]):
        """Cache generated samples"""
        self._cached_samples = samples
