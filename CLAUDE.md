# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Advertising Knowledge Graph System - A dual-graph system (knowledge graph + event graph) for automotive advertising decision support, combining user behavior analysis with LLM-powered causal reasoning.

**Tech Stack**: FastAPI + Vue 3 + NetworkX + SQLite + Anthropic API

## Development Commands

### Backend (FastAPI)

```bash
# Start backend server
cd backend
python main.py
# Runs on http://localhost:8000
# API docs: http://localhost:8000/docs

# Install dependencies
pip install -r requirements.txt

# Required environment setup
cp .env.example .env
# Edit .env to add ANTHROPIC_API_KEY
```

### Frontend (Vue 3 + Vite)

```bash
# Start dev server
cd frontend
npm run dev
# Runs on http://localhost:5173

# Install dependencies
npm install

# Build for production
npm run build
```

### Testing

```bash
# Backend tests (if available)
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Architecture Overview

### Dual-Layer Data Architecture

**In-Memory Layer** (NetworkX):
- `knowledge_graph`: MultiDiGraph for entity-relationship queries
- `event_graph`: DiGraph for causal event chains

**Persistent Layer** (SQLite at `data/graph.db`):
- Auto-syncs on every write operation
- Auto-loads on startup
- Tables: `entities`, `relations`, `event_nodes`, `event_edges`

**Critical Pattern**: All graph operations go through [backend/app/core/graph_db.py](backend/app/core/graph_db.py) which maintains both layers.

### Request Flow Pattern

```
Frontend → FastAPI Router → Dependency Injection → Service Layer → GraphDatabase → Persistence
```

**Key Files**:
- Routes: [backend/app/api/graph_routes.py](backend/app/api/graph_routes.py), [backend/app/api/qa_routes.py](backend/app/api/qa_routes.py)
- Services: [backend/app/services/knowledge_graph.py](backend/app/services/knowledge_graph.py), [backend/app/services/event_graph.py](backend/app/services/event_graph.py)
- Core: [backend/app/core/graph_db.py](backend/app/core/graph_db.py), [backend/app/core/persistence.py](backend/app/core/persistence.py)

### Dependency Injection System

**CRITICAL**: This system uses FastAPI dependency injection to ensure concurrent safety. Never use global variables for stateful services.

```python
# Correct pattern (from graph_routes.py)
@router.post("/knowledge/build")
async def build_knowledge_graph(
    request: BuildGraphRequest,
    builder: KnowledgeGraphBuilder = Depends(get_kg_builder)
):
    # Each request gets independent instance
```

Dependencies defined in [backend/app/core/dependencies.py](backend/app/core/dependencies.py):
- `get_kg_builder()`: Knowledge graph builder (per-request)
- `get_graph_db()`: Graph database (singleton)
- `get_llm_client()`: LLM client (per-request)
- `get_qa_engine()`: QA engine (per-request)

### Batch Processing Pattern

Knowledge graph construction uses batch processing (5000 entities/batch) to handle large datasets:

```python
# From knowledge_graph.py:117-206
def _extract_batch(self, users: List[Dict]) -> Dict:
    entities_to_create = []
    relations_to_create = []

    # Collect all entities and relations
    for user in users:
        entities_to_create.append({...})
        relations_to_create.append({...})

    # Batch create (10x+ faster than individual creates)
    entity_count = graph_db.batch_create_entities(entities_to_create)
    relation_count = graph_db.batch_create_relations(relations_to_create)
```

**When modifying graph operations**: Always use `batch_create_entities()` and `batch_create_relations()` instead of individual `create_entity()` calls.

## Core Services

### KnowledgeGraphBuilder ([backend/app/services/knowledge_graph.py](backend/app/services/knowledge_graph.py))

Constructs knowledge graphs from user behavior data.

**Entity Types**:
- `User`: User profiles with demographics
- `Interest`: User interests (golf, tech, etc.)
- `Brand`: Automotive brands (BMW, Mercedes, etc.)
- `Model`: Car models (7 Series, S-Class, etc.)

**Relationship Types**:
- `HAS_INTEREST`: User → Interest (weight: 0.8)
- `PREFERS`: User → Brand (weight: brand_score)
- `INTERESTED_IN`: User → Model (weight: brand_score * 0.9)

**Key Methods**:
- `build(user_count)`: Main entry point, returns graph data + stats
- `_extract_batch(users)`: Batch process users into entities/relations
- `get_progress()`: Returns current build progress

### EventGraphBuilder ([backend/app/services/event_graph.py](backend/app/services/event_graph.py))

Generates causal event graphs using LLM analysis.

**Workflow**:
1. Generate samples (1:10:5:5 ratio via SampleManager)
2. Compute statistics (conversion rates, churn rates)
3. Extract typical cases
4. Call LLM for causal analysis
5. Return event graph with probability/confidence scores

**Sample Ratio**: 1 positive : 10 high-potential : 5 weak-interest : 5 control

### QAEngine ([backend/app/services/qa_engine.py](backend/app/services/qa_engine.py))

Natural language question answering over knowledge graphs.

**Intent Types**:
- `comparison`: Compare brands/models
- `recommendation`: Suggest targeting strategies
- `churn_analysis`: Identify churn patterns
- `segment_analysis`: Analyze user segments

**Fallback Behavior**: Returns mock answers when LLM unavailable (graceful degradation).

## Error Handling & Logging

### Unified Exception System

All exceptions go through [backend/app/core/exceptions.py](backend/app/core/exceptions.py):

```python
# Custom exceptions
BusinessException       # Base for business logic errors
DataValidationError    # Invalid input data
ResourceNotFoundError  # Entity not found
DatabaseError          # Persistence failures
LLMServiceError        # LLM API failures
```

**Exception handlers registered in [backend/main.py](backend/main.py:20-23)**:
- Users see friendly messages
- Full stack traces logged to `logs/adsagent_error.log`

### Logging System

Configured in [backend/app/core/logger.py](backend/app/core/logger.py):
- Application log: `logs/adsagent.log` (INFO+)
- Error log: `logs/adsagent_error.log` (ERROR+)
- Rotating files: 10MB max, 5 backups

**Usage**:
```python
from app.core.logger import app_logger

app_logger.info("Operation started")
app_logger.error("Operation failed", exc_info=True)  # Include stack trace
```

## Security & Validation

### Request Validation

All API endpoints use Pydantic models for validation:

```python
class BuildGraphRequest(BaseModel):
    user_count: Optional[int] = Field(None, ge=1, le=1000000)

class QueryGraphRequest(BaseModel):
    entity_name: Optional[str] = Field(None, max_length=100)
    depth: int = Field(2, ge=1, le=5)  # Prevents DoS via deep recursion
```

### Input Sanitization

Entity names are sanitized in [backend/app/api/graph_routes.py](backend/app/api/graph_routes.py:111-112):

```python
if not entity_name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
    raise DataValidationError("实体名称包含非法字符")
```

### Known Security Issues (P1 Priority)

1. **CSV Upload Vulnerability** ([backend/app/api/sample_routes.py](backend/app/api/sample_routes.py)):
   - Only checks file extension (can be bypassed)
   - No file size limit
   - `pd.read_csv()` can execute formulas
   - **Fix**: Validate MIME type, limit size, disable formula execution

## Performance Considerations

### Batch Operations

**Always use batch methods** when creating multiple entities/relations:

```python
# Good (10x+ faster)
graph_db.batch_create_entities(entities)
graph_db.batch_create_relations(relations)

# Bad (slow, causes N+1 persistence calls)
for entity in entities:
    graph_db.create_entity(entity["id"], entity["type"], entity["properties"])
```

### N+1 Query Problem

**Known issue** in [backend/app/services/knowledge_graph.py:254-269](backend/app/services/knowledge_graph.py#L254-L269):

```python
# Current (inefficient)
for rel in relations:
    entity = graph_db.query_entities()  # Queries all entities repeatedly

# Better approach
all_entities = {e["id"]: e for e in graph_db.query_entities()}  # Query once
for rel in relations:
    entity = all_entities.get(rel["to"])  # Dictionary lookup
```

## Configuration

### Backend Config ([backend/app/core/config.py](backend/app/core/config.py))

Environment variables (set in `.env`):
- `ANTHROPIC_API_KEY`: Required for LLM features
- `APP_HOST`: Server bind address (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 8000)
- `PRIMARY_MODEL`: LLM model (default: glm-4.6-flash)
- `REASONING_MODEL`: Reasoning model (default: qwen3-32b)
- `MAX_TOKENS_PER_REQUEST`: Token limit (default: 30000)

### Frontend API Client ([frontend/src/api/index.js](frontend/src/api/index.js))

Base URL: `/api/v1` (proxied to backend via Vite config)

**Key endpoints**:
- `buildKnowledgeGraph(userCount)`: POST `/graphs/knowledge/build`
- `queryKnowledgeGraph(params)`: GET `/graphs/knowledge/query`
- `generateSamples(config)`: POST `/samples/generate`
- `generateEventGraph()`: POST `/qa/event-graph/generate`
- `queryQA(question)`: POST `/qa/query`

## Data Persistence

### Database Location

**IMPORTANT**: Database uses relative path `data/graph.db`, which resolves to:
- Project root: `./data/graph.db` (when running from root)
- Backend dir: `./backend/data/graph.db` (when running from backend/)

**Recommendation**: Use absolute paths in production to avoid confusion.

### Schema

**Entities table**:
```sql
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    properties TEXT NOT NULL,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Relations table**:
```sql
CREATE TABLE relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    type TEXT NOT NULL,
    properties TEXT NOT NULL,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Extension Points

The system is designed for future enhancements:

1. **Graph Database**: Replace NetworkX + SQLite with Neo4j
   - Config already prepared in [backend/app/core/config.py](backend/app/core/config.py)
   - Update [backend/app/core/graph_db.py](backend/app/core/graph_db.py) to use Neo4j driver

2. **Data Source**: Replace mock data with ClickHouse
   - Modify [backend/app/data/mock_data.py](backend/app/data/mock_data.py)
   - Add ClickHouse client in `backend/app/core/`

3. **LLM Provider**: Switch between providers
   - Update [backend/app/core/anthropic_client.py](backend/app/core/anthropic_client.py)
   - Add new client classes for other providers

4. **Caching**: Add Redis for query caching
   - Create `backend/app/core/cache.py`
   - Wrap frequently accessed queries

## Common Pitfalls

1. **Don't use global variables for stateful services** - Use dependency injection
2. **Don't forget to use batch operations** - Individual creates are 10x+ slower
3. **Don't skip input validation** - All user input must be validated via Pydantic
4. **Don't return raw exceptions to clients** - Use unified exception handlers
5. **Don't assume database path** - Check working directory when debugging persistence issues

## Verification

After making changes, verify the system:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Build knowledge graph
curl -X POST http://localhost:8000/api/v1/graphs/knowledge/build \
  -H "Content-Type: application/json" \
  -d '{"user_count": 100}'

# 3. Check logs
tail -f backend/logs/adsagent.log

# 4. Verify persistence
python -c "import sqlite3; conn = sqlite3.connect('data/graph.db'); \
  cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM entities'); \
  print(f'Entities: {cursor.fetchone()[0]}'); conn.close()"
```
