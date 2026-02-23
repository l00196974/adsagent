/**
 * LLM日志全局状态管理
 * 用于在所有页面显示最近一次LLM调用的实时响应
 */
import { ref } from 'vue'

// 全局LLM日志状态
export const llmLog = ref({
  isActive: false,        // 是否有活跃的LLM调用
  content: '',            // 当前LLM响应内容
  timestamp: null,        // 开始时间
  taskName: '',           // 任务名称（如"事件抽象"、"生成事理图谱"等）
  status: 'idle'          // idle | streaming | completed | error
})

// 开始新的LLM调用
export function startLLMLog(taskName) {
  llmLog.value = {
    isActive: true,
    content: '',
    timestamp: new Date(),
    taskName: taskName,
    status: 'streaming'
  }
}

// 追加LLM响应内容
export function appendLLMLog(chunk) {
  if (llmLog.value.isActive) {
    llmLog.value.content += chunk
  }
}

// 完成LLM调用
export function completeLLMLog() {
  if (llmLog.value.isActive) {
    llmLog.value.status = 'completed'
    llmLog.value.isActive = false
  }
}

// 标记LLM调用失败
export function errorLLMLog(errorMessage) {
  if (llmLog.value.isActive) {
    llmLog.value.status = 'error'
    llmLog.value.content += `\n\n[错误] ${errorMessage}`
    llmLog.value.isActive = false
  }
}

// 清空日志
export function clearLLMLog() {
  llmLog.value = {
    isActive: false,
    content: '',
    timestamp: null,
    taskName: '',
    status: 'idle'
  }
}
