from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class SampleType(str, Enum):
    POSITIVE = "positive"
    CHURN = "churn"
    WEAK = "weak"
    CONTROL = "control"

class EntityType(str, Enum):
    USER = "User"
    BRAND = "Brand"
    MODEL = "Model"
    INTEREST = "Interest"
    SCENE = "Scene"
    AUDIENCE = "Audience"

class SampleGenerateRequest(BaseModel):
    industry: str = "汽车"
    category: str = "豪华轿车"
    ratios: Dict[str, int] = {"positive": 1, "churn": 10, "weak": 5, "control": 5}
    total_count: int = 1000

class GraphQueryRequest(BaseModel):
    entity_type: str
    entity_name: Optional[str] = None
    depth: int = 2

class QARequest(BaseModel):
    question: str

class SampleResponse(BaseModel):
    samples: Dict[str, List[Dict]]
    statistics: Dict[str, Dict]

class KnowledgeGraphResponse(BaseModel):
    entities: List[Dict]
    relations: List[Dict]
    stats: Dict

class EventGraphResponse(BaseModel):
    nodes: List[Dict]
    edges: List[Dict]
    insights: List[str]

class QAResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    sources: Dict
