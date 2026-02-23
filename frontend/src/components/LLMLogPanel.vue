<template>
  <div class="llm-log-panel" :class="{ 'collapsed': isCollapsed }">
    <div class="panel-header" @click="toggleCollapse">
      <div class="header-left">
        <el-icon class="icon-ai">
          <ChatDotRound />
        </el-icon>
        <span class="title">LLM响应日志</span>
        <el-tag v-if="llmLog.isActive" type="warning" size="small" effect="dark">
          <el-icon class="is-loading"><Loading /></el-icon>
          生成中
        </el-tag>
        <el-tag v-else-if="llmLog.status === 'completed'" type="success" size="small">
          已完成
        </el-tag>
        <el-tag v-else-if="llmLog.status === 'error'" type="danger" size="small">
          失败
        </el-tag>
      </div>
      <div class="header-right">
        <span v-if="llmLog.taskName" class="task-name">{{ llmLog.taskName }}</span>
        <el-button text @click.stop="clearLog" v-if="!llmLog.isActive">
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-icon class="collapse-icon">
          <ArrowDown v-if="!isCollapsed" />
          <ArrowUp v-else />
        </el-icon>
      </div>
    </div>

    <div class="panel-content" v-show="!isCollapsed">
      <div class="log-info" v-if="llmLog.timestamp">
        <span>开始时间: {{ formatTime(llmLog.timestamp) }}</span>
        <span v-if="llmLog.content">字符数: {{ llmLog.content.length }}</span>
      </div>

      <el-scrollbar class="log-scrollbar" ref="scrollbarRef">
        <div class="log-content">
          <pre v-if="llmLog.content">{{ llmLog.content }}</pre>
          <el-empty v-else description="暂无LLM调用" :image-size="60" />
        </div>
      </el-scrollbar>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { ChatDotRound, Loading, Delete, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { llmLog, clearLLMLog } from '../stores/llmLog'

const isCollapsed = ref(false)
const scrollbarRef = ref(null)

// 切换折叠状态
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// 清空日志
const clearLog = () => {
  clearLLMLog()
}

// 格式化时间
const formatTime = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 监听内容变化，自动滚动到底部
watch(() => llmLog.value.content, () => {
  nextTick(() => {
    if (scrollbarRef.value) {
      const scrollElement = scrollbarRef.value.$refs.wrap
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight
      }
    }
  })
})

// 当有新的LLM调用时，自动展开面板
watch(() => llmLog.value.isActive, (newVal) => {
  if (newVal) {
    isCollapsed.value = false
  }
})
</script>

<style scoped>
.llm-log-panel {
  position: fixed;
  bottom: 0;
  right: 20px;
  width: 600px;
  max-height: 400px;
  background: #ffffff;
  border: 1px solid #dcdfe6;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.1);
  z-index: 2000;
  transition: all 0.3s ease;
}

.llm-log-panel.collapsed {
  max-height: 48px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  user-select: none;
  border-radius: 8px 8px 0 0;
}

.panel-header:hover {
  opacity: 0.95;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-ai {
  font-size: 18px;
}

.title {
  font-weight: 500;
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-name {
  font-size: 13px;
  opacity: 0.9;
}

.collapse-icon {
  font-size: 16px;
  transition: transform 0.3s;
}

.panel-content {
  display: flex;
  flex-direction: column;
  height: 352px;
  background: #fafafa;
}

.log-info {
  display: flex;
  justify-content: space-between;
  padding: 8px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}

.log-scrollbar {
  flex: 1;
  height: 100%;
}

.log-content {
  padding: 16px;
  min-height: 100%;
}

.log-content pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .llm-log-panel {
    right: 10px;
    width: calc(100vw - 20px);
    max-width: 600px;
  }
}
</style>
