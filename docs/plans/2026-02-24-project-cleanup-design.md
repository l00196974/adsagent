# Project Cleanup Design

**Date**: 2026-02-24
**Strategy**: Aggressive Cleanup (Plan A)
**Objective**: Remove deprecated code, unused features, generated documentation, and migration scripts to reduce technical debt

---

## Overview

This cleanup targets accumulated technical debt from iterative development:
- 49 generated markdown documentation files (~280KB)
- 14 completed database migration scripts
- 8 frontend debug statements
- 3 unimplemented TODO endpoints

**Preservation**: Core documentation, test files, and future-planned logical_behavior module remain intact.

---

## Part 1: Documentation Cleanup

### Files to Keep (4)
- `README.md` - Project overview
- `CLAUDE.md` - Claude Code guidance
- `QUICK_START.md` - Quick start guide
- `AGENTS.md` - Agent configuration

### Files to Delete (49)

**Root directory (24 files)**:
- `IMPLEMENTATION_SUMMARY.md`
- `OPTIMIZATION_SUMMARY.md`
- `PERFORMANCE_OPTIMIZATION_REPORT.md`
- `LLM_STREAMING_IMPLEMENTATION_COMPLETE.md`
- `SEQUENCE_MINING_FEATURE.md`
- `CAUSAL_GRAPH_IMPLEMENTATION.md`
- `FLEXIBLE_DATA_STRUCTURE_GUIDE.md`
- `VERIFICATION_REPORT.md`
- `VERIFICATION_SUMMARY.md`
- `SYSTEM_VERIFICATION_REPORT.md`
- `VERIFICATION_CHECKLIST.md`
- `DATA_CONVERSION_COMPLETE.md`
- `UNSTRUCTURED_FORMAT_SUMMARY.md`
- `SIMPLIFIED_UNSTRUCTURED_FORMAT.md`
- `BATCH_EXTRACTION_PERFORMANCE_ANALYSIS.md`
- `SEQUENCE_VIEW_PERFORMANCE_FIX.md`
- `USER_DETAIL_PERFORMANCE_FIX.md`
- `CSV_IMPORT_GUIDE.md`
- `CSV_IMPORT_FIX_GUIDE.md`
- `CSV_IMPORT_TEST_REPORT.md`
- `PROJECT_CLEANUP_SUMMARY.md`
- `END_TO_END_TEST_REPORT.md`
- `TEST_RESULTS.md`
- `TASK_PERSISTENCE.md`

**Backend directory (7 files)**:
- `backend/STREAMING_IMPLEMENTATION_REPORT.md`
- `backend/STREAMING_QUICK_REFERENCE.md`
- `backend/LLM_STREAMING_GUIDE.md`
- `backend/MEMORY_OPTIMIZATION.md`
- `backend/MEMORY_ISSUE_ROOT_CAUSE.md`
- `backend/BUGFIX_SEQUENCE_MINING.md`
- `backend/BUGFIX_SEQUENCE_MINING_STATS.md`

**Rationale**: These are implementation reports and summaries generated during development. All information is preserved in git history and CLAUDE.md.

---

## Part 2: Migration Scripts Cleanup

### Files to Delete (14)

**Database migration scripts (7)**:
- `backend/scripts/migrate_to_flexible_schema.py`
- `backend/scripts/migrate_to_unstructured.py`
- `backend/scripts/migrate_add_indexes.py`
- `backend/scripts/add_event_category_column.py`
- `backend/scripts/add_performance_indexes.py`
- `backend/scripts/add_event_failure_fields.py`
- `backend/scripts/cleanup_event_sequences.py`

**Data conversion scripts (2)**:
- `backend/scripts/convert_to_unstructured.py`
- `backend/scripts/convert_profiles_to_unstructured.py`

**Test/generation scripts (5)**:
- `backend/scripts/benchmark_performance.py`
- `backend/scripts/generate_csv_data.py`
- `backend/scripts/generate_csv_templates.py`
- `backend/scripts/generate_realistic_data.py`
- `backend/scripts/test_prompt.py`

**Rationale**: Database has been migrated to final schema. Scripts completed their mission. Can be restored from git history if needed.

---

## Part 3: Frontend Debug Cleanup

### Statements to Remove (8)

**CausalGraphView.vue (7 statements)**:
- Rendering condition console.log
- Container size console.log
- Graph data console.log
- Node ID console.log
- Edge validation console.log
- Self-loop filtering console.log
- Additional debug console.log

**EventExtraction.vue (1 statement)**:
- Batch extraction task recovery console.log

**Approach**: Direct deletion. No conditional wrapping needed.

---

## Part 4: Unimplemented Endpoints Cleanup

### Endpoints to Delete (3)

**File**: `backend/app/api/base_modeling_routes.py`

1. **POST /api/v1/modeling/behavior/add** (Lines 125-135)
   - Purpose: Manual behavior data addition
   - Status: TODO not implemented
   - Reason: System uses CSV import; manual addition not needed

2. **GET /api/v1/modeling/app-tags/status** (Lines 198-210)
   - Purpose: APP tag generation progress query
   - Status: TODO not implemented, returns mock data
   - Reason: APP tagging feature not enabled

3. **GET /api/v1/modeling/media-tags/status** (Lines 272-284)
   - Purpose: Media tag generation progress query
   - Status: TODO not implemented, returns mock data
   - Reason: Media tagging feature not enabled

**Approach**: Remove route functions and their registrations.

---

## Part 5: Preserved Content

### Test Files (14 - KEEP)
All `backend/test_*.py` files remain:
- Unit and integration tests
- Valuable for code quality assurance
- Can be run with manually installed pytest

### Logical Behavior Module (KEEP)
- `backend/app/services/logical_behavior.py`
- `backend/app/api/logical_behavior_routes.py`
- **Reason**: Correct implementation using 4-tuple structure (Agent, Scene, Action, Object)
- **Future**: Will replace event_extraction.py

---

## Expected Outcomes

**Quantitative**:
- Remove ~300KB+ of files
- Delete 28 unused files
- Clean 8 debug statements
- Remove 3 dead endpoints

**Qualitative**:
- Cleaner codebase
- Reduced technical debt
- Easier navigation
- No misleading TODO endpoints

---

## Risk Assessment

**Low Risk**:
- All deleted content preserved in git history
- No active functionality affected
- Test files preserved for quality assurance

**Rollback Plan**:
- If migration scripts needed: `git checkout <commit> -- backend/scripts/`
- If documentation needed: `git checkout <commit> -- <file>.md`

---

## Implementation Notes

1. Create backup branch before cleanup
2. Delete files in batches (docs → scripts → debug → endpoints)
3. Test backend startup after endpoint removal
4. Test frontend after debug removal
5. Commit with descriptive message
6. Verify no broken imports or references

---

## Future Considerations

**Next Phase** (separate task):
- Replace event_extraction.py with logical_behavior.py
- Update frontend to use new 4-tuple structure
- Migrate existing event data to logical behavior format
