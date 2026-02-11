from typing import Dict, List, Optional
from app.data.mock_data import get_mock_users

class SampleManager:
    def __init__(self):
        self.default_ratios = {"positive": 1, "churn": 10, "weak": 5, "control": 5}
    
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
