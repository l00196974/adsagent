# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Advertising Knowledge Graph System - A dual-graph system (knowledge graph + event graph) for automotive advertising decision support, combining user behavior analysis with LLM-powered causal reasoning.

**Tech Stack**: FastAPI + Vue 3 + NetworkX + SQLite + OpenAI-compatible LLM API (MiniMax/OpenAI)

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
# Edit .env to add OPENAI_API_KEY and OPENAI_BASE_URL
# Default config uses MiniMax API (OpenAI-compatible)
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
# Backend tests
cd backend
pytest  # Note: pytest must be installed first (not in requirements.txt)

# Run specific test file
pytest tests/test_streaming_implementation.py -v

# Frontend tests
cd frontend
npm test  # Note: No test files currently exist

# Clear Python cache after code changes
find backend -name "*.pyc" -delete
find backend -name "__pycache__" -type d -exec rm -rf {} +
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

### EventExtractor ([backend/app/services/event_extraction.py](backend/app/services/event_extraction.py))

Extracts high-level events from user behavior sequences using LLM.

**Key Methods**:
- `extract_events_for_user(user_id)`: Extract events for single user
- `extract_events_batch(user_ids)`: Batch process multiple users (dynamic batch sizing)
- `_process_single_batch()`: Internal batch processing with parallel execution

**Database Tables**:
- `extracted_events`: Stores extracted events (event_id, user_id, event_type, timestamp, context)
- `event_sequences`: Tracks extraction status and sequences per user (status: 'success', 'failed', 'pending')

**Batch Processing Pattern**:
- Dynamic batch sizing based on token estimation (max 25000 tokens/batch)
- Parallel execution with configurable workers (default: 4 concurrent workers)
- Real-time progress updates after each batch completes
- **Progress tracking**: Uses `_update_progress()` with nonlocal variables for immediate updates

**Query Pattern for Re-extraction**:
```python
# Only process users that haven't succeeded
SELECT DISTINCT user_id FROM behavior_data
WHERE user_id NOT IN (
    SELECT user_id FROM event_sequences WHERE status = 'success'
)
```
This ensures failed users are included in batch re-extraction.

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

### LLM Integration Pattern ([backend/app/core/openai_client.py](backend/app/core/openai_client.py))

**CRITICAL**: The system uses a unified LLM client that supports multiple providers (OpenAI, MiniMax, etc.). **All LLM calls use streaming mode exclusively.**

**Key Methods**:
- `chat_completion(prompt, max_tokens, temperature)`: Unified LLM call interface (async generator, always streaming)
- `abstract_events_batch(user_behaviors, user_profiles)`: Batch event extraction from behaviors
- `_stream_chat()`: Internal streaming implementation with hardcoded `stream=True`
- `_collect_stream_response()`: Helper to collect full response from stream

**Streaming Architecture**:
- **100% streaming usage**: All 13 LLM call points use streaming mode
- **No stream parameter**: The `stream` parameter has been removed from `chat_completion()`
- **Async generator pattern**: `chat_completion()` is an async generator that yields chunks
- **Usage pattern**:
  ```python
  # Correct - get async generator and collect response
  stream_generator = self.chat_completion(prompt, max_tokens=8000)
  response = await self._collect_stream_response(stream_generator)

  # Wrong - don't await chat_completion directly
  response = await self.chat_completion(prompt)  # ❌ Returns coroutine, not string
  ```

**Output Format Pattern**:
- **Text-based format preferred over JSON**: Use pipe-delimited text (`user_id|event_type|timestamp|context`) instead of JSON for LLM outputs
- **Reason**: JSON parsing is fragile with LLM responses (incomplete JSON, formatting errors, token limits)
- **Example**:
  ```
  user_001|看车|2026-01-15 10:00|4S店,宝马,停留2小时
  user_001|浏览车型|2026-01-15 12:30|汽车之家,宝马7系,奔驰S级
  ```

**Timeout Configuration**:
- Batch operations: 300s (5 minutes)
- Large outputs (>8000 tokens): 300s
- Medium outputs (>2000 tokens): 180s
- Small outputs: 60s

**Response Handling**:
- Always remove `<think>` tags from MiniMax responses
- Remove markdown code blocks (```text, ```json)
- Parse line-by-line for text format
- Return both parsed events AND raw LLM response for debugging

**Frontend Integration**:
- Frontend timeout must be >= backend timeout (use 180s for single user extraction)
- Display LLM raw responses in UI for transparency
- Use global LLM log panel ([frontend/src/stores/llmLog.js](frontend/src/stores/llmLog.js)) for real-time feedback
- **Progress display**: Show progress in progress bars, not in LLM log panel

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

1. **CSV Upload Vulnerability** ([backend/app/api/flexible_import_routes.py:28-32](backend/app/api/flexible_import_routes.py#L28-L32)):
   - Only checks file extension (can be bypassed)
   - No file size limit
   - Writes to `/tmp/` without sanitization
   - `pd.read_csv()` can execute formulas
   - **Fix**: Validate MIME type, limit size (e.g., 100MB), disable formula execution with `engine='python'`

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
- `OPENAI_API_KEY`: Required for LLM features (supports MiniMax and other OpenAI-compatible APIs)
- `OPENAI_BASE_URL`: LLM API base URL (default: https://api.minimaxi.com/v1)
- `APP_HOST`: Server bind address (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 8000)
- `PRIMARY_MODEL`: LLM model for general tasks (default: glm-4.6-flash)
- `REASONING_MODEL`: LLM model for complex reasoning (default: qwen3-32b)
- `MAX_TOKENS_PER_REQUEST`: Token limit per request (default: 30000)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j config (optional, not currently used)

### Frontend API Client ([frontend/src/api/index.js](frontend/src/api/index.js))

Base URL: `/api/v1` (proxied to backend via Vite config)

**Global Timeout**: 30 seconds (line 18) - **IMPORTANT**: Individual API calls requiring longer execution must override this

**Key endpoints**:
- `buildKnowledgeGraph(userCount)`: POST `/graphs/knowledge/build`
- `queryKnowledgeGraph(params)`: GET `/graphs/knowledge/query`
- `generateSamples(config)`: POST `/samples/generate`
- `generateEventGraph()`: POST `/qa/event-graph/generate`
- `queryQA(question)`: POST `/qa/query`
- `extractEventsForUser(userId)`: POST `/events/extract/{userId}` (timeout: 180s)

**Timeout Override Pattern**:
```javascript
// Correct - override timeout for long-running operations
axios.post(url, data, { timeout: 180000 })

// Wrong - uses global 30s timeout
axios.post(url, data)
```

## Data Persistence

### Database Location

**IMPORTANT**: The backend always runs from `/home/linxiankun/adsagent/backend` directory, so all code uses relative path `data/graph.db`, which resolves to:
- **Active database**: `/home/linxiankun/adsagent/backend/data/graph.db` ✓
- **Old/unused**: `/home/linxiankun/adsagent/data/graph.db` (已备份为 graph.db.backup_old)

**Critical**:
- Backend must be started from the `backend/` directory: `cd backend && python main.py`
- All services use relative path `"data/graph.db"` which resolves correctly when running from `backend/`
- Do NOT run backend from project root, as it will create/use wrong database path

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
5. **Don't run backend from wrong directory** - Always run from `backend/` directory, not project root
6. **Don't use JSON for LLM outputs** - Prefer text-based formats (pipe-delimited) to avoid parsing failures
7. **Don't use default axios timeout for LLM calls** - Frontend must set explicit timeout (180s+) for event extraction
8. **Don't modify LLM client without testing** - Python caches .pyc files; clear `__pycache__` after changes
9. **Don't await chat_completion() directly** - It's an async generator; use `_collect_stream_response()` or iterate with `async for`
10. **Don't add stream parameter to LLM calls** - All calls are streaming by default; the parameter has been removed
11. **Don't update progress only after all batches complete** - Use nonlocal variables to update progress after each batch in parallel processing

## Critical Implementation Patterns

### LLM Streaming Pattern

**All LLM calls must use streaming**. The system has been refactored to remove non-streaming branches:

```python
# Correct pattern
async def some_llm_operation(self):
    stream_generator = self.llm_client.chat_completion(
        prompt="...",
        max_tokens=8000
    )
    full_response = await self.llm_client._collect_stream_response(stream_generator)
    return full_response

# Also correct - iterate chunks
async def stream_to_frontend(self):
    async for chunk in self.llm_client.chat_completion(prompt="...", max_tokens=8000):
        yield chunk  # Send to SSE endpoint
```

**Never**:
- Add `stream=True` parameter (removed from signature)
- Use `await` on `chat_completion()` directly
- Expect non-streaming responses

### Batch Progress Tracking Pattern

When implementing parallel batch processing with real-time progress updates:

```python
async def process_batches_parallel(self, batches):
    success_count = 0
    failed_count = 0

    async def process_with_progress(batch):
        nonlocal success_count, failed_count  # Critical for real-time updates

        result = await self._process_single_batch(batch)

        # Update immediately after each batch
        success_count += result["success_count"]
        failed_count += result["failed_count"]

        self._update_progress(
            processed_users=success_count + failed_count,
            success_count=success_count,
            failed_count=failed_count
        )

        return result

    # Parallel execution with semaphore
    tasks = [process_with_progress(batch) for batch in batches]
    results = await asyncio.gather(*tasks)
```

**Key points**:
- Use `nonlocal` to share counters across async tasks
- Update progress inside the task, not after `gather()`
- This ensures frontend sees real-time progress, not 0% until completion

## Verification

After making changes, verify the system:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Build knowledge graph
curl -X POST http://localhost:8000/api/v1/graphs/knowledge/build \
  -H "Content-Type: application/json" \
  -d '{"user_count": 100}'

# 3. Test event extraction (should complete in ~60-90s)
curl -X POST http://localhost:8000/api/v1/events/extract/user_0001 \
  -H "Content-Type: application/json"

# 4. Check logs
tail -f backend/logs/adsagent.log

# 5. Verify persistence
python -c "import sqlite3; conn = sqlite3.connect('data/graph.db'); \
  cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM entities'); \
  print(f'Entities: {cursor.fetchone()[0]}'); conn.close()"

# 6. Clear Python cache after code changes
find backend -name "*.pyc" -delete
find backend -name "__pycache__" -type d -exec rm -rf {} +
```

## Debugging LLM Integration Issues

**Common Issues**:

1. **"LLM返回空结果" (LLM returns empty result)**
   - Check logs for actual LLM response length
   - Verify `<think>` tag removal is working
   - Ensure text parsing finds pipe-delimited lines
   - Check if `max_tokens` is sufficient (use 8000 for batch operations)

2. **Frontend timeout (30s exceeded)**
   - Verify API call uses explicit timeout override
   - Check backend logs to see if LLM call completed
   - Ensure frontend displays LLM response for debugging

3. **TypeError: 'async for' requires an object with __aiter__ method, got coroutine**
   - This means you're awaiting `chat_completion()` when you shouldn't
   - `chat_completion()` is an async generator - don't await it
   - Use `_collect_stream_response()` or iterate with `async for`

4. **AttributeError in openai_client.py**
   - Class uses `self.primary_model` not `self.model`
   - Clear `__pycache__` and restart backend

5. **JSON parsing failures**
   - Switch to text-based format (pipe-delimited)
   - LLM often returns incomplete JSON due to token limits
   - Text format is more robust and easier to parse

6. **Progress stuck at 0% during batch extraction**
   - Check if progress updates are inside or outside `asyncio.gather()`
   - Progress must be updated inside each task using `nonlocal` variables
   - Verify `_update_progress()` is called after each batch, not after all batches

## Recent Major Changes (2026-02-23)

### LLM Streaming Unification
- **Removed all non-streaming code paths** from `chat_completion()`
- **Removed `stream` parameter** from method signature
- **Hardcoded `stream=True`** in OpenAI API calls
- All 13 LLM call points now use streaming exclusively
- Compatible with models that only support streaming

### Batch Extraction Progress Fix
- **Fixed progress tracking** in parallel batch processing
- Progress now updates after each batch completes (not after all 90 batches)
- Uses `nonlocal` variables to share state across async tasks
- Frontend sees real-time progress updates every 1-2 seconds

### Frontend LLM Log Optimization
- **Removed progress display** from LLM log panel
- Progress information only shown in progress bars
- LLM log panel reserved for actual LLM response content
- Improves user experience and reduces log noise

## Known Issues & Bugs

### Critical Issues (P1)

1. **LLM Conversion Event Recognition Failure**
   - LLM over-abstracts events (e.g., "购买长城_WEY VV7" → "使用APP")
   - Fails to identify purchase/add_cart actions despite explicit prompts
   - All events incorrectly classified as "engagement" instead of "conversion"
   - **Impact**: Target-oriented sequence mining feature unusable
   - **Workaround**: Implement rule-based post-processing for conversion events

2. **Async Generator Attribute Error** ([backend/logs/adsagent_error.log](backend/logs/adsagent_error.log))
   ```python
   AttributeError: 'async_generator' object has no attribute 'send_progress'
   ```
   - Occurs in streaming event extraction endpoint
   - Attempting to add attributes to async generator objects
   - **Fix**: Use separate progress tracking mechanism, not generator attributes

3. **Batch Processing Incomplete Results**
   ```
   User batch not found in batch results
   ```
   - Batch extraction returns incomplete results
   - Missing error handling for partial batch failures
   - **Fix**: Add proper error handling and result validation in batch processing

### Medium Priority Issues (P2)

4. **Incomplete Implementations in base_modeling_routes.py**
   - Line 131: `# TODO: 实现添加逻辑` (Add logic not implemented)
   - Line 202: `# TODO: 实现进度查询逻辑` (Progress query not implemented)
   - Line 276: `# TODO: 实现进度查询逻辑` (Progress query not implemented)

5. **Debug Statements in Production Code**
   - 8 console.log/debugger statements in frontend
   - Should be removed or wrapped in `if (import.meta.env.DEV)` checks

6. **Frontend Bundle Size Warning**
   - Main bundle: 1.01MB (335KB gzipped)
   - Exceeds 500KB threshold
   - **Recommendation**: Use dynamic imports for route-level code splitting

### Low Priority Issues (P3)

7. **Missing Test Coverage**
   - Backend: 17 test files exist but pytest not in requirements.txt
   - Frontend: 0 test files found
   - No automated testing in CI/CD

8. **Excessive Documentation Files**
   - 402 markdown files in project
   - Many are implementation summaries/reports
   - Should consolidate or archive to `docs/archive/`
