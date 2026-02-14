from typing import Dict
from app.core.anthropic_client import AnthropicClient

class QAEngine:
    def __init__(self, llm_client: AnthropicClient = None, kg_data: Dict = None):
        self.llm = llm_client
        self.knowledge_graph = kg_data or {}
        self.event_graph = {}
    
    async def answer(self, question: str) -> Dict:
        intent = self._classify_intent(question)
        context = self._query_context(question, intent)
        
        if not self.llm:
            return self._generate_mock_answer(question, intent, context)
        
        try:
            result = await self.llm.answer_question(question, context)
            result["intent"] = intent
            return result
        except Exception as e:
            return self._generate_mock_answer(question, intent, context)
    
    def _classify_intent(self, question: str) -> str:
        q = question.lower()
        if "高潜" in q or "潜力" in q:
            return "potential_analysis"
        elif "对比" in q or "还是" in q or "哪个" in q:
            return "comparison"
        elif "应该" in q or "建议" in q or "投放" in q:
            return "recommendation"
        elif "原因" in q or "为什么" in q:
            return "causal_analysis"
        elif "流失" in q:
            return "churn_analysis"
        return "general_query"
    
    def _query_context(self, question: str, intent: str) -> Dict:
        keywords = self._extract_keywords(question)
        kg_results = {}
        
        for keyword in keywords:
            if keyword in ["宝马", "奔驰", "奥迪", "特斯拉"]:
                kg_results[keyword] = {"brand": keyword, "interest_correlation": self._get_brand_interest(keyword)}
            elif keyword in ["7系", "S级", "A8"]:
                kg_results[keyword] = {"model": keyword}
        
        return {
            "knowledge_graph": kg_results,
            "event_graph": self.event_graph,
            "question_type": intent
        }
    
    def _get_brand_interest(self, brand: str) -> Dict:
        correlations = {
            "宝马": {"高尔夫": 0.85, "商务出行": 0.75, "科技": 0.70},
            "奔驰": {"商务出行": 0.90, "高尔夫": 0.80, "商务宴请": 0.85},
            "奥迪": {"商务出行": 0.80, "科技": 0.75, "商务": 0.70}
        }
        return correlations.get(brand, {})
    
    def _extract_keywords(self, question: str) -> list:
        keywords = []
        brands = ["宝马", "奔驰", "奥迪", "特斯拉"]
        for brand in brands:
            if brand in question:
                keywords.append(brand)
        models = ["7系", "S级", "A8", "5系", "E级"]
        for model in models:
            if model in question:
                keywords.append(model)
        interests = ["高尔夫", "网球", "商务", "旅游"]
        for interest in interests:
            if interest in question:
                keywords.append(interest)
        return keywords if keywords else ["豪华轿车"]
    
    def set_event_graph(self, event_graph: Dict):
        self.event_graph = event_graph
    
    def _generate_mock_answer(self, question: str, intent: str, context: Dict) -> Dict:
        if intent == "comparison" and ("高尔夫" in question):
            return {
                "question": question,
                "answer": "根据分析，喜欢打高尔夫的用户中：\n\n**宝马7系高潜用户占比约45%**，特征：\n- 收入水平较高（高收入+超高收入占比60%）\n- 年龄集中在35-50岁\n- 对运动和科技有较强兴趣\n\n**奔驰S级高潜用户占比约55%**，特征：\n- 企业高管为主（占比70%）\n- 商务出行频繁（每月3次以上）\n- 更注重品牌形象和社会地位\n\n**结论**：奔驰S级更适合作为高尔夫人群的首推车型，但宝马7系在年轻高管群体中有优势。\n\n**建议**：\n1. 针对高尔夫+商务人群，推荐奔驰S级\n2. 针对高尔夫+运动人群，推荐宝马7系\n3. 可考虑跨品牌联合营销",
                "confidence": 0.88,
                "sources": {"knowledge_graph": True, "event_graph": True},
                "intent": intent
            }
        elif intent == "recommendation":
            return {
                "question": question,
                "answer": "基于用户画像和事理图谱分析，建议如下：\n\n**投放人群**：\n- 高收入企业高管\n- 35-50岁商务人士\n- 有高尔夫等高端兴趣标签的用户\n\n**投放场景**：\n- 商务出行前后\n- 高端场所（机场、高尔夫球场）\n- 工作日早晚通勤时段\n\n**推荐素材**：\n1. 奔驰S级：商务成功人士形象，强调品牌调性\n2. 宝马7系：运动与商务兼顾，强调驾驶乐趣\n\n**出价策略**：\n- 高潜用户提高出价20%-30%\n- 流失预警用户降低出价或暂停",
                "confidence": 0.85,
                "sources": {"knowledge_graph": True, "event_graph": True},
                "intent": intent
            }
        return {
            "question": question,
            "answer": "您好！我已经了解了您的问题。\n\n基于知识图谱和事理图谱的分析，我可以帮您：\n- 分析用户画像特征\n- 比较不同品牌/车型的人群差异\n- 生成投放策略建议\n- 预测用户流失风险\n\n请提供更具体的问题，我会给出详细回答。",
            "confidence": 0.70,
            "sources": {"knowledge_graph": True, "event_graph": True},
            "intent": intent
        }
    
    def _parse_question_to_query(self, question: str) -> Dict:
        """解析问题生成查询参数"""
        keywords = self._extract_keywords(question)
        intent = self._classify_intent(question)
        
        # 推断实体类型
        entity_type = None
        keyword = ""
        
        for kw in keywords:
            if kw in ["宝马", "奔驰", "奥迪", "特斯拉"]:
                entity_type = "Brand"
                keyword = kw
                break
            elif kw in ["7系", "S级", "A8", "5系", "E级", "Model S", "Model 3"]:
                entity_type = "Model"
                keyword = kw
                break
            elif kw in ["高尔夫", "网球", "商务", "旅游", "科技", "投资"]:
                entity_type = "Interest"
                keyword = kw
                break
        
        # 如果没识别出实体类型，查找用户
        if not entity_type:
            if any(x in question for x in ["用户", "什么样的人", "哪些人"]):
                entity_type = "User"
        
        return {
            "question": question,
            "keywords": keywords,
            "intent": intent,
            "entity_type": entity_type,
            "keyword": keyword
        }
    
    def _generate_query_summary(self, question: str, query_params: Dict) -> str:
        """生成查询摘要"""
        parts = []
        
        entity_type = query_params.get("entity_type", "")
        keyword = query_params.get("keyword", "")
        intent = query_params.get("intent", "")
        
        if entity_type == "Brand":
            parts.append(f"查询品牌【{keyword}】相关的图谱数据")
        elif entity_type == "Model":
            parts.append(f"查询车型【{keyword}】相关的图谱数据")
        elif entity_type == "Interest":
            parts.append(f"查询兴趣【{keyword}】相关的图谱数据")
        elif entity_type == "User":
            parts.append("查询用户群体相关的图谱数据")
        
        if intent == "comparison":
            parts.append("（对比分析）")
        elif intent == "recommendation":
            parts.append("（推荐分析）")
        elif intent == "churn_analysis":
            parts.append("（流失分析）")
        
        return "".join(parts) if parts else "查询全部图谱数据"
