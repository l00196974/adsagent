"""
图谱相关API路由 - 使用依赖注入解决并发安全问题
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional
from pydantic import BaseModel, Field
from app.core.dependencies import get_kg_builder, get_graph_db
from app.services.knowledge_graph import KnowledgeGraphBuilder, GraphQueryEngine
from app.core.graph_db import GraphDatabase
from app.core.exceptions import BusinessException, DataValidationError
from app.core.logger import app_logger

router = APIRouter()


# ========== 请求模型 ==========

class BuildGraphRequest(BaseModel):
    """构建知识图谱请求"""
    user_count: Optional[int] = Field(None, ge=1, le=1000000, description="用户数量")


class QueryGraphRequest(BaseModel):
    """查询图谱请求"""
    entity_name: Optional[str] = Field(None, max_length=100)
    entity_type: Optional[str] = Field(None, max_length=50)
    depth: int = Field(2, ge=1, le=5, description="查询深度")


class SearchRequest(BaseModel):
    """搜索请求"""
    keyword: Optional[str] = Field(None, max_length=100)
    entity_type: Optional[str] = Field(None, max_length=50)
    limit: int = Field(20, ge=1, le=100)


class ExpandRequest(BaseModel):
    """展开实体请求"""
    depth: int = Field(2, ge=1, le=5)
    max_nodes: int = Field(50, ge=1, le=200)


class AIQueryRequest(BaseModel):
    """AI查询请求"""
    question: str = Field(..., min_length=1, max_length=500)
    max_depth: int = Field(2, ge=1, le=5)
    max_nodes: int = Field(50, ge=1, le=200)


class BuildFromCSVRequest(BaseModel):
    """从CSV数据构建图谱请求"""
    users: list = Field(..., min_items=1, description="用户数据列表")


# ========== API端点 ==========

# Mock数据构建接口已移除，请使用 /knowledge/build-from-csv 接口


@router.post("/knowledge/build-from-csv")
async def build_knowledge_graph_from_csv(
    request: BuildFromCSVRequest,
    builder: KnowledgeGraphBuilder = Depends(get_kg_builder)
):
    """从CSV数据构建知识图谱"""
    try:
        users = request.users
        app_logger.info(f"开始从CSV数据构建知识图谱，用户数量: {len(users)}")

        result = builder.build_from_csv_data(users=users)

        app_logger.info(f"知识图谱构建完成: {result.get('stats', {})}")
        return {
            "code": 0,
            "data": result,
            "message": f"成功从 {len(users)} 条数据构建知识图谱"
        }
    except Exception as e:
        app_logger.error(f"从CSV构建知识图谱失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="知识图谱构建失败，请稍后重试")


@router.get("/knowledge/progress")
async def get_build_progress(
    builder: KnowledgeGraphBuilder = Depends(get_kg_builder)
):
    """获取知识图谱构建进度"""
    try:
        progress = builder.get_progress()
        return {"code": 0, "data": progress}
    except Exception:
        return {
            "code": 0,
            "data": {
                "current_step": "未开始",
                "step_progress": 0,
                "total_batches": 0
            }
        }


@router.get("/knowledge/query")
async def query_graph(
    entity_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    depth: int = 2,
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """查询知识图谱"""
    try:
        # 参数验证
        if depth < 1 or depth > 5:
            raise DataValidationError("查询深度必须在1-5之间")

        engine = GraphQueryEngine()

        if entity_name:
            # 验证entity_name不包含特殊字符
            if not entity_name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
                raise DataValidationError("实体名称包含非法字符")
            result = engine.query_by_entity(entity_name, depth)
        else:
            # 返回概览数据
            entities = graph_db.query_entities(limit=100)
            relations = graph_db.query_relations(limit=200)
            result = {"entities": entities, "relations": relations}

        return {"code": 0, "data": result}
    except DataValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"查询图谱失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/brand-correlation")
async def query_brand_correlation(
    brand: str,
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """查询品牌兴趣关联"""
    try:
        # 验证brand参数
        if not brand or len(brand) > 50:
            raise DataValidationError("品牌名称无效")

        engine = GraphQueryEngine()
        result = engine.query_brand_interest_correlation(brand)

        return {"code": 0, "data": result}
    except DataValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"查询品牌关联失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/knowledge/search")
async def search_entities(
    keyword: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 20,
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """搜索实体"""
    try:
        # 参数验证
        if limit < 1 or limit > 100:
            raise DataValidationError("limit必须在1-100之间")

        engine = GraphQueryEngine()
        result = engine.search_entities(keyword, entity_type, limit)

        return {"code": 0, "data": result}
    except DataValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"搜索实体失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索失败，请稍后重试")


@router.get("/knowledge/expand/{entity_id}")
async def expand_entity(
    entity_id: str,
    depth: int = 2,
    max_nodes: int = 50,
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """展开实体的关联关系"""
    try:
        # 参数验证
        if depth < 1 or depth > 5:
            raise DataValidationError("深度必须在1-5之间")
        if max_nodes < 1 or max_nodes > 200:
            raise DataValidationError("max_nodes必须在1-200之间")

        # 检查实体是否存在
        if not graph_db.knowledge_graph.has_node(entity_id):
            raise HTTPException(status_code=404, detail="实体不存在")

        # 收集关联实体和关系
        related_entities = []
        related_relations = []
        visited = set()
        queue = [(entity_id, 0)]

        while queue and len(related_entities) < max_nodes:
            node, d = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            if d > 0:
                data = graph_db.knowledge_graph.nodes.get(node, {})
                related_entities.append({
                    "id": node,
                    "type": data.get("type", "Unknown"),
                    "distance": d,
                    "properties": {k: v for k, v in data.items() if k != "type"}
                })

            if d < depth:
                # 出边
                for neighbor in graph_db.knowledge_graph.successors(node):
                    if neighbor not in visited:
                        edge_data = graph_db.knowledge_graph.get_edge_data(node, neighbor)
                        if edge_data:
                            # MultiDiGraph返回字典，取第一个边
                            first_edge = list(edge_data.values())[0]
                            related_relations.append({
                                "from": node,
                                "to": neighbor,
                                "type": first_edge.get("type", "RELATED"),
                                "weight": first_edge.get("weight", 0.5)
                            })
                        queue.append((neighbor, d + 1))

                # 入边
                for predecessor in graph_db.knowledge_graph.predecessors(node):
                    if predecessor not in visited:
                        edge_data = graph_db.knowledge_graph.get_edge_data(predecessor, node)
                        if edge_data:
                            first_edge = list(edge_data.values())[0]
                            related_relations.append({
                                "from": predecessor,
                                "to": node,
                                "type": first_edge.get("type", "RELATED"),
                                "weight": first_edge.get("weight", 0.5)
                            })
                        queue.append((predecessor, d + 1))

        return {
            "code": 0,
            "data": {
                "central_entity": entity_id,
                "entities": related_entities,
                "relations": related_relations,
                "depth": depth,
                "total_entities": len(related_entities) + 1,
                "total_relations": len(related_relations)
            }
        }
    except DataValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"展开实体失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="展开失败，请稍后重试")


@router.post("/knowledge/ai-query")
async def ai_graph_query(
    request: AIQueryRequest,
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """AI图谱查询 - 基于自然语言生成查询"""
    try:
        from app.services.qa_engine import QAEngine

        # 使用QA引擎解析问题
        engine = QAEngine()
        query_params = engine._parse_question_to_query(request.question)

        # 执行查询
        results = {"entities": [], "relations": [], "query_params": query_params}

        entity_type = query_params.get("entity_type")
        keyword = query_params.get("keyword", "")

        if entity_type == "User":
            users = graph_db.query_entities("User", limit=request.max_nodes * 2)

            # 如果有关键词，进行过滤
            if keyword:
                keyword_lower = keyword.lower()
                filtered_users = []
                for u in users:
                    # 在ID中搜索
                    if keyword_lower in u["id"].lower():
                        filtered_users.append(u)
                        continue
                    # 在属性中搜索
                    props = u.get("properties", {})
                    for key, value in props.items():
                        if isinstance(value, str) and keyword_lower in value.lower():
                            filtered_users.append(u)
                            break
                users = filtered_users[:request.max_nodes]
            else:
                users = users[:request.max_nodes]

            results["entities"] = users

            user_ids = [u["id"] for u in users]
            relations = graph_db.query_relations(limit=request.max_nodes * 3)
            results["relations"] = [
                rel for rel in relations
                if rel["from"] in user_ids or rel["to"] in user_ids
            ]

        elif entity_type == "Brand":
            brands = graph_db.query_entities("Brand", limit=10)
            if keyword:
                brands = [
                    b for b in brands
                    if keyword in b.get("properties", {}).get("name", "")
                ]
            results["entities"] = brands

            brand_ids = [b["id"] for b in brands]
            relations = graph_db.query_relations(limit=50)
            results["relations"] = [
                rel for rel in relations
                if rel["from"] in brand_ids or rel["to"] in brand_ids
            ]

        elif entity_type == "Interest":
            interests = graph_db.query_entities("Interest", limit=20)
            if keyword:
                interests = [
                    i for i in interests
                    if keyword in i.get("properties", {}).get("name", "")
                ]
            results["entities"] = interests

            interest_ids = [i["id"] for i in interests]
            relations = graph_db.query_relations(limit=100)
            results["relations"] = [
                rel for rel in relations
                if rel["from"] in interest_ids or rel["to"] in interest_ids
            ]

        else:
            results["entities"] = graph_db.query_entities(limit=request.max_nodes)
            results["relations"] = graph_db.query_relations(limit=request.max_nodes * 2)

        return {
            "code": 0,
            "data": {
                "question": request.question,
                "parsed_query": query_params,
                "results": results,
                "ai_summary": engine._generate_query_summary(request.question, query_params)
            }
        }
    except Exception as e:
        app_logger.error(f"AI查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI查询失败，请稍后重试")


@router.get("/knowledge/types")
async def get_entity_types(
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """获取所有实体类型"""
    try:
        entities = graph_db.query_entities(limit=1000)
        types = list(set(e["type"] for e in entities))

        return {"code": 0, "data": {"types": types}}
    except Exception as e:
        app_logger.error(f"获取实体类型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取失败，请稍后重试")


@router.get("/knowledge/stats")
async def get_graph_stats(
    graph_db: GraphDatabase = Depends(get_graph_db)
):
    """获取图谱统计信息"""
    try:
        stats = graph_db.get_stats()
        return {"code": 0, "data": stats}
    except Exception as e:
        app_logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取失败，请稍后重试")
