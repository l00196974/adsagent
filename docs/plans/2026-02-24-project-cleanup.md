# Project Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove technical debt by deleting 49 generated MD files, 14 migration scripts, 8 debug statements, and 3 TODO endpoints.

**Architecture:** Sequential cleanup in 4 phases (docs → scripts → debug → endpoints) with verification after each phase.

**Tech Stack:** Bash, Git, Vue 3, FastAPI

---

## Task 1: Create Backup Branch

**Files:**
- None (git operation only)

**Step 1: Create backup branch**

```bash
cd /home/linxiankun/adsagent
git checkout -b backup-before-cleanup
```

Expected: `Switched to a new branch 'backup-before-cleanup'`

**Step 2: Push backup branch**

```bash
git push -u origin backup-before-cleanup
```

Expected: Branch pushed to remote (or skip if no remote)

**Step 3: Return to master**

```bash
git checkout master
```

Expected: `Switched to branch 'master'`

**Step 4: Commit (no changes yet)**

Skip - no changes to commit

---

## Task 2: Delete Generated Documentation (Root Level - Part 1)

**Files:**
- Delete: `/home/linxiankun/adsagent/IMPLEMENTATION_SUMMARY.md`
- Delete: `/home/linxiankun/adsagent/OPTIMIZATION_SUMMARY.md`
- Delete: `/home/linxiankun/adsagent/PERFORMANCE_OPTIMIZATION_REPORT.md`
- Delete: `/home/linxiankun/adsagent/LLM_STREAMING_IMPLEMENTATION_COMPLETE.md`
- Delete: `/home/linxiankun/adsagent/SEQUENCE_MINING_FEATURE.md`
- Delete: `/home/linxiankun/adsagent/CAUSAL_GRAPH_IMPLEMENTATION.md`
- Delete: `/home/linxiankun/adsagent/FLEXIBLE_DATA_STRUCTURE_GUIDE.md`
- Delete: `/home/linxiankun/adsagent/VERIFICATION_REPORT.md`

**Step 1: Delete first batch of MD files**

```bash
cd /home/linxiankun/adsagent
rm -f IMPLEMENTATION_SUMMARY.md \
      OPTIMIZATION_SUMMARY.md \
      PERFORMANCE_OPTIMIZATION_REPORT.md \
      LLM_STREAMING_IMPLEMENTATION_COMPLETE.md \
      SEQUENCE_MINING_FEATURE.md \
      CAUSAL_GRAPH_IMPLEMENTATION.md \
      FLEXIBLE_DATA_STRUCTURE_GUIDE.md \
      VERIFICATION_REPORT.md
```

Expected: Files deleted silently

**Step 2: Verify deletion**

```bash
ls -la *.md | grep -E "(IMPLEMENTATION|OPTIMIZATION|PERFORMANCE|LLM_STREAMING|SEQUENCE_MINING|CAUSAL_GRAPH|FLEXIBLE|VERIFICATION_REPORT)"
```

Expected: No output (files not found)

**Step 3: Verify core docs still exist**

```bash
ls -la README.md CLAUDE.md QUICK_START.md AGENTS.md
```

Expected: All 4 files exist

**Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove generated documentation (batch 1/3)

Remove implementation reports and feature guides:
- IMPLEMENTATION_SUMMARY.md
- OPTIMIZATION_SUMMARY.md
- PERFORMANCE_OPTIMIZATION_REPORT.md
- LLM_STREAMING_IMPLEMENTATION_COMPLETE.md
- SEQUENCE_MINING_FEATURE.md
- CAUSAL_GRAPH_IMPLEMENTATION.md
- FLEXIBLE_DATA_STRUCTURE_GUIDE.md
- VERIFICATION_REPORT.md

All information preserved in git history and CLAUDE.md.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 8 deletions

---

## Task 3: Delete Generated Documentation (Root Level - Part 2)

**Files:**
- Delete: `/home/linxiankun/adsagent/VERIFICATION_SUMMARY.md`
- Delete: `/home/linxiankun/adsagent/SYSTEM_VERIFICATION_REPORT.md`
- Delete: `/home/linxiankun/adsagent/VERIFICATION_CHECKLIST.md`
- Delete: `/home/linxiankun/adsagent/DATA_CONVERSION_COMPLETE.md`
- Delete: `/home/linxiankun/adsagent/UNSTRUCTURED_FORMAT_SUMMARY.md`
- Delete: `/home/linxiankun/adsagent/SIMPLIFIED_UNSTRUCTURED_FORMAT.md`
- Delete: `/home/linxiankun/adsagent/BATCH_EXTRACTION_PERFORMANCE_ANALYSIS.md`
- Delete: `/home/linxiankun/adsagent/SEQUENCE_VIEW_PERFORMANCE_FIX.md`

**Step 1: Delete second batch of MD files**

```bash
cd /home/linxiankun/adsagent
rm -f VERIFICATION_SUMMARY.md \
      SYSTEM_VERIFICATION_REPORT.md \
      VERIFICATION_CHECKLIST.md \
      DATA_CONVERSION_COMPLETE.md \
      UNSTRUCTURED_FORMAT_SUMMARY.md \
      SIMPLIFIED_UNSTRUCTURED_FORMAT.md \
      BATCH_EXTRACTION_PERFORMANCE_ANALYSIS.md \
      SEQUENCE_VIEW_PERFORMANCE_FIX.md
```

Expected: Files deleted silently

**Step 2: Verify deletion**

```bash
ls -la *.md | grep -E "(VERIFICATION|DATA_CONVERSION|UNSTRUCTURED|BATCH_EXTRACTION|SEQUENCE_VIEW)"
```

Expected: No output (files not found)

**Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove generated documentation (batch 2/3)

Remove verification reports and data conversion docs:
- VERIFICATION_SUMMARY.md
- SYSTEM_VERIFICATION_REPORT.md
- VERIFICATION_CHECKLIST.md
- DATA_CONVERSION_COMPLETE.md
- UNSTRUCTURED_FORMAT_SUMMARY.md
- SIMPLIFIED_UNSTRUCTURED_FORMAT.md
- BATCH_EXTRACTION_PERFORMANCE_ANALYSIS.md
- SEQUENCE_VIEW_PERFORMANCE_FIX.md

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 8 deletions

---

## Task 4: Delete Generated Documentation (Root Level - Part 3)

**Files:**
- Delete: `/home/linxiankun/adsagent/USER_DETAIL_PERFORMANCE_FIX.md`
- Delete: `/home/linxiankun/adsagent/CSV_IMPORT_GUIDE.md`
- Delete: `/home/linxiankun/adsagent/CSV_IMPORT_FIX_GUIDE.md`
- Delete: `/home/linxiankun/adsagent/CSV_IMPORT_TEST_REPORT.md`
- Delete: `/home/linxiankun/adsagent/PROJECT_CLEANUP_SUMMARY.md`
- Delete: `/home/linxiankun/adsagent/END_TO_END_TEST_REPORT.md`
- Delete: `/home/linxiankun/adsagent/TEST_RESULTS.md`
- Delete: `/home/linxiankun/adsagent/TASK_PERSISTENCE.md`

**Step 1: Delete third batch of MD files**

```bash
cd /home/linxiankun/adsagent
rm -f USER_DETAIL_PERFORMANCE_FIX.md \
      CSV_IMPORT_GUIDE.md \
      CSV_IMPORT_FIX_GUIDE.md \
      CSV_IMPORT_TEST_REPORT.md \
      PROJECT_CLEANUP_SUMMARY.md \
      END_TO_END_TEST_REPORT.md \
      TEST_RESULTS.md \
      TASK_PERSISTENCE.md
```

Expected: Files deleted silently

**Step 2: Verify deletion**

```bash
ls -la *.md | grep -E "(USER_DETAIL|CSV_IMPORT|PROJECT_CLEANUP|END_TO_END|TEST_RESULTS|TASK_PERSISTENCE)"
```

Expected: No output (files not found)

**Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove generated documentation (batch 3/3)

Remove performance fixes, CSV guides, and test reports:
- USER_DETAIL_PERFORMANCE_FIX.md
- CSV_IMPORT_GUIDE.md
- CSV_IMPORT_FIX_GUIDE.md
- CSV_IMPORT_TEST_REPORT.md
- PROJECT_CLEANUP_SUMMARY.md
- END_TO_END_TEST_REPORT.md
- TEST_RESULTS.md
- TASK_PERSISTENCE.md

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 8 deletions

---

## Task 5: Delete Backend Documentation

**Files:**
- Delete: `/home/linxiankun/adsagent/backend/STREAMING_IMPLEMENTATION_REPORT.md`
- Delete: `/home/linxiankun/adsagent/backend/STREAMING_QUICK_REFERENCE.md`
- Delete: `/home/linxiankun/adsagent/backend/LLM_STREAMING_GUIDE.md`
- Delete: `/home/linxiankun/adsagent/backend/MEMORY_OPTIMIZATION.md`
- Delete: `/home/linxiankun/adsagent/backend/MEMORY_ISSUE_ROOT_CAUSE.md`
- Delete: `/home/linxiankun/adsagent/backend/BUGFIX_SEQUENCE_MINING.md`
- Delete: `/home/linxiankun/adsagent/backend/BUGFIX_SEQUENCE_MINING_STATS.md`

**Step 1: Delete backend MD files**

```bash
cd /home/linxiankun/adsagent/backend
rm -f STREAMING_IMPLEMENTATION_REPORT.md \
      STREAMING_QUICK_REFERENCE.md \
      LLM_STREAMING_GUIDE.md \
      MEMORY_OPTIMIZATION.md \
      MEMORY_ISSUE_ROOT_CAUSE.md \
      BUGFIX_SEQUENCE_MINING.md \
      BUGFIX_SEQUENCE_MINING_STATS.md
```

Expected: Files deleted silently

**Step 2: Verify deletion**

```bash
ls -la backend/*.md
```

Expected: `ls: cannot access 'backend/*.md': No such file or directory`

**Step 3: Commit**

```bash
cd /home/linxiankun/adsagent
git add -A
git commit -m "$(cat <<'EOF'
chore: remove backend generated documentation

Remove streaming guides, memory optimization, and bugfix reports:
- backend/STREAMING_IMPLEMENTATION_REPORT.md
- backend/STREAMING_QUICK_REFERENCE.md
- backend/LLM_STREAMING_GUIDE.md
- backend/MEMORY_OPTIMIZATION.md
- backend/MEMORY_ISSUE_ROOT_CAUSE.md
- backend/BUGFIX_SEQUENCE_MINING.md
- backend/BUGFIX_SEQUENCE_MINING_STATS.md

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 7 deletions

---

## Task 6: Delete Migration Scripts (Part 1)

**Files:**
- Delete: `/home/linxiankun/adsagent/backend/scripts/migrate_to_flexible_schema.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/migrate_to_unstructured.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/migrate_add_indexes.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/add_event_category_column.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/add_performance_indexes.py`

**Step 1: Delete migration scripts batch 1**

```bash
cd /home/linxiankun/adsagent/backend/scripts
rm -f migrate_to_flexible_schema.py \
      migrate_to_unstructured.py \
      migrate_add_indexes.py \
      add_event_category_column.py \
      add_performance_indexes.py
```

Expected: Files deleted silently

**Step 2: Verify deletion**

```bash
ls -la backend/scripts/migrate*.py backend/scripts/add*.py 2>&1 | grep -E "(migrate|add_event|add_performance)"
```

Expected: "No such file or directory" messages

**Step 3: Commit**

```bash
cd /home/linxiankun/adsagent
git add -A
git commit -m "$(cat <<'EOF'
chore: remove database migration scripts (batch 1/3)

Remove completed migration scripts:
- migrate_to_flexible_schema.py
- migrate_to_unstructured.py
- migrate_add_indexes.py
- add_event_category_column.py
- add_performance_indexes.py

Database already migrated. Scripts can be restored from git history if needed.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 5 deletions

---

## Task 7: Delete Migration Scripts (Part 2)

**Files:**
- Delete: `/home/linxiankun/adsagent/backend/scripts/add_event_failure_fields.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/cleanup_event_sequences.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/convert_to_unstructured.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/convert_profiles_to_unstructured.py`

**Step 1: Delete migration scripts batch 2**

```bash
cd /home/linxiankun/adsagent/backend/scripts
rm -f add_event_failure_fields.py \
      cleanup_event_sequences.py \
      convert_to_unstructured.py \
      convert_profiles_to_unstructured.py
```

Expected: Files deleted silently

**Step 2: Verify deletion**

```bash
ls -la backend/scripts/*.py 2>&1 | grep -E "(add_event_failure|cleanup_event|convert)"
```

Expected: "No such file or directory" or no matching files

**Step 3: Commit**

```bash
cd /home/linxiankun/adsagent
git add -A
git commit -m "$(cat <<'EOF'
chore: remove database migration scripts (batch 2/3)

Remove conversion and cleanup scripts:
- add_event_failure_fields.py
- cleanup_event_sequences.py
- convert_to_unstructured.py
- convert_profiles_to_unstructured.py

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 4 deletions

---

## Task 8: Delete Test/Generation Scripts

**Files:**
- Delete: `/home/linxiankun/adsagent/backend/scripts/benchmark_performance.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/generate_csv_data.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/generate_csv_templates.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/generate_realistic_data.py`
- Delete: `/home/linxiankun/adsagent/backend/scripts/test_prompt.py`

**Step 1: Delete test/generation scripts**

```bash
cd /home/linxiankun/adsagent/backend/scripts
rm -f benchmark_performance.py \
      generate_csv_data.py \
      generate_csv_templates.py \
      generate_realistic_data.py \
      test_prompt.py
```

Expected: Files deleted silently

**Step 2: Verify scripts directory is empty or minimal**

```bash
ls -la backend/scripts/
```

Expected: Directory empty or only contains __init__.py

**Step 3: Commit**

```bash
cd /home/linxiankun/adsagent
git add -A
git commit -m "$(cat <<'EOF'
chore: remove test and generation scripts (batch 3/3)

Remove benchmark, CSV generation, and test scripts:
- benchmark_performance.py
- generate_csv_data.py
- generate_csv_templates.py
- generate_realistic_data.py
- test_prompt.py

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with 5 deletions

---

## Task 9: Remove Frontend Debug Statements (CausalGraphView.vue)

**Files:**
- Modify: `/home/linxiankun/adsagent/frontend/src/views/CausalGraphView.vue`

**Step 1: Read file to locate console.log statements**

```bash
cd /home/linxiankun/adsagent
grep -n "console.log" frontend/src/views/CausalGraphView.vue
```

Expected: 7 lines with console.log statements

**Step 2: Remove all console.log statements**

Use the Edit tool to remove each console.log line. The exact lines will vary, but search for patterns like:
- `console.log('渲染条件'`
- `console.log('容器尺寸'`
- `console.log('图数据'`
- `console.log('节点ID'`
- `console.log('边验证'`
- `console.log('自环过滤'`

Remove entire lines containing these console.log statements.

**Step 3: Verify removal**

```bash
grep -n "console.log" frontend/src/views/CausalGraphView.vue
```

Expected: No output (no console.log found)

**Step 4: Test frontend builds**

```bash
cd /home/linxiankun/adsagent/frontend
npm run build
```

Expected: Build succeeds with no errors

**Step 5: Commit**

```bash
cd /home/linxiankun/adsagent
git add frontend/src/views/CausalGraphView.vue
git commit -m "$(cat <<'EOF'
chore: remove debug console.log from CausalGraphView

Remove 7 console.log statements used for debugging:
- Rendering conditions
- Container size
- Graph data
- Node IDs
- Edge validation
- Self-loop filtering

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with modifications to CausalGraphView.vue

---

## Task 10: Remove Frontend Debug Statements (EventExtraction.vue)

**Files:**
- Modify: `/home/linxiankun/adsagent/frontend/src/views/EventExtraction.vue`

**Step 1: Read file to locate console.log statement**

```bash
cd /home/linxiankun/adsagent
grep -n "console.log" frontend/src/views/EventExtraction.vue
```

Expected: 1 line with console.log statement (batch extraction task recovery)

**Step 2: Remove console.log statement**

Use the Edit tool to remove the console.log line related to batch extraction task recovery.

**Step 3: Verify removal**

```bash
grep -n "console.log" frontend/src/views/EventExtraction.vue
```

Expected: No output (no console.log found)

**Step 4: Verify no other debug statements in frontend**

```bash
cd /home/linxiankun/adsagent/frontend/src
grep -r "console.log\|debugger" --include="*.vue" --include="*.js"
```

Expected: No output or only intentional logging (like error handlers)

**Step 5: Commit**

```bash
cd /home/linxiankun/adsagent
git add frontend/src/views/EventExtraction.vue
git commit -m "$(cat <<'EOF'
chore: remove debug console.log from EventExtraction

Remove console.log for batch extraction task recovery debugging.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with modifications to EventExtraction.vue

---

## Task 11: Remove TODO Endpoint 1 (behavior/add)

**Files:**
- Modify: `/home/linxiankun/adsagent/backend/app/api/base_modeling_routes.py`

**Step 1: Read the endpoint definition**

```bash
cd /home/linxiankun/adsagent
sed -n '125,135p' backend/app/api/base_modeling_routes.py
```

Expected: Shows the POST /behavior/add endpoint with TODO comment

**Step 2: Remove the endpoint function**

Use the Edit tool to remove lines 125-135 (the entire `add_behavior_data` function including the @router.post decorator).

**Step 3: Verify removal**

```bash
grep -n "add_behavior_data\|/behavior/add" backend/app/api/base_modeling_routes.py
```

Expected: No output (function removed)

**Step 4: Test backend starts without errors**

```bash
cd /home/linxiankun/adsagent/backend
python -c "from app.api.base_modeling_routes import router; print('Import successful')"
```

Expected: "Import successful" (no syntax errors)

**Step 5: Commit**

```bash
cd /home/linxiankun/adsagent
git add backend/app/api/base_modeling_routes.py
git commit -m "$(cat <<'EOF'
chore: remove unimplemented behavior/add endpoint

Remove POST /api/v1/modeling/behavior/add endpoint (TODO not implemented).
System uses CSV import; manual addition not needed.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with modifications to base_modeling_routes.py

---

## Task 12: Remove TODO Endpoint 2 (app-tags/status)

**Files:**
- Modify: `/home/linxiankun/adsagent/backend/app/api/base_modeling_routes.py`

**Step 1: Read the endpoint definition**

```bash
cd /home/linxiankun/adsagent
sed -n '198,210p' backend/app/api/base_modeling_routes.py
```

Expected: Shows the GET /app-tags/status endpoint with TODO comment

**Step 2: Remove the endpoint function**

Use the Edit tool to remove lines 198-210 (the entire `get_app_tags_status` function including the @router.get decorator).

**Step 3: Verify removal**

```bash
grep -n "get_app_tags_status\|/app-tags/status" backend/app/api/base_modeling_routes.py
```

Expected: No output (function removed)

**Step 4: Test backend starts without errors**

```bash
cd /home/linxiankun/adsagent/backend
python -c "from app.api.base_modeling_routes import router; print('Import successful')"
```

Expected: "Import successful"

**Step 5: Commit**

```bash
cd /home/linxiankun/adsagent
git add backend/app/api/base_modeling_routes.py
git commit -m "$(cat <<'EOF'
chore: remove unimplemented app-tags/status endpoint

Remove GET /api/v1/modeling/app-tags/status endpoint (TODO not implemented).
APP tagging feature not enabled.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with modifications to base_modeling_routes.py

---

## Task 13: Remove TODO Endpoint 3 (media-tags/status)

**Files:**
- Modify: `/home/linxiankun/adsagent/backend/app/api/base_modeling_routes.py`

**Step 1: Read the endpoint definition**

```bash
cd /home/linxiankun/adsagent
sed -n '272,284p' backend/app/api/base_modeling_routes.py
```

Expected: Shows the GET /media-tags/status endpoint with TODO comment

**Step 2: Remove the endpoint function**

Use the Edit tool to remove lines 272-284 (the entire `get_media_tags_status` function including the @router.get decorator).

**Step 3: Verify removal**

```bash
grep -n "get_media_tags_status\|/media-tags/status" backend/app/api/base_modeling_routes.py
```

Expected: No output (function removed)

**Step 4: Test backend starts without errors**

```bash
cd /home/linxiankun/adsagent/backend
python -c "from app.api.base_modeling_routes import router; print('Import successful')"
```

Expected: "Import successful"

**Step 5: Commit**

```bash
cd /home/linxiankun/adsagent
git add backend/app/api/base_modeling_routes.py
git commit -m "$(cat <<'EOF'
chore: remove unimplemented media-tags/status endpoint

Remove GET /api/v1/modeling/media-tags/status endpoint (TODO not implemented).
Media tagging feature not enabled.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created with modifications to base_modeling_routes.py

---

## Task 14: Final Verification and Summary

**Files:**
- None (verification only)

**Step 1: Verify backend starts successfully**

```bash
cd /home/linxiankun/adsagent/backend
timeout 10 python main.py &
sleep 5
curl -s http://localhost:8000/health
pkill -f "python main.py"
```

Expected: `{"status":"ok","message":"广告知识图谱系统运行中"}`

**Step 2: Verify frontend builds successfully**

```bash
cd /home/linxiankun/adsagent/frontend
npm run build
```

Expected: Build completes with no errors

**Step 3: Count deleted files**

```bash
cd /home/linxiankun/adsagent
git log --oneline --since="1 hour ago" | wc -l
```

Expected: 13 commits (1 backup + 12 cleanup commits)

**Step 4: Generate cleanup summary**

```bash
cd /home/linxiankun/adsagent
echo "=== Cleanup Summary ==="
echo "Deleted MD files: 49"
echo "Deleted migration scripts: 14"
echo "Removed debug statements: 8"
echo "Removed TODO endpoints: 3"
echo ""
echo "Total commits: $(git log --oneline --since='1 hour ago' | wc -l)"
echo "Preserved test files: $(ls backend/test_*.py 2>/dev/null | wc -l)"
echo "Preserved logical_behavior module: $(ls backend/app/services/logical_behavior.py backend/app/api/logical_behavior_routes.py 2>/dev/null | wc -l) files"
```

Expected: Summary showing all cleanup metrics

**Step 5: No commit needed**

This is verification only - no changes to commit.

---

## Completion Checklist

- [ ] Backup branch created
- [ ] 49 MD files deleted (4 batches)
- [ ] 14 migration scripts deleted (3 batches)
- [ ] 8 frontend debug statements removed (2 files)
- [ ] 3 TODO endpoints removed (base_modeling_routes.py)
- [ ] Backend starts successfully
- [ ] Frontend builds successfully
- [ ] 13 commits created
- [ ] Test files preserved (14 files)
- [ ] logical_behavior module preserved (2 files)

---

## Rollback Instructions

If issues arise, rollback to backup branch:

```bash
cd /home/linxiankun/adsagent
git checkout backup-before-cleanup
git branch -D master
git checkout -b master
git push -f origin master
```

Or restore specific files from git history:

```bash
# Restore all deleted MD files
git checkout HEAD~13 -- "*.md"

# Restore migration scripts
git checkout HEAD~13 -- backend/scripts/

# Restore specific endpoint
git checkout HEAD~3 -- backend/app/api/base_modeling_routes.py
```
