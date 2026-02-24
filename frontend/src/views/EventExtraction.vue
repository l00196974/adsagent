<template>
  <div class="event-extraction">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>事件抽象</span>
          <div>
            <el-button
              type="primary"
              @click="handleBatchExtract"
              :loading="batchLoading"
              :disabled="extractProgress.status === 'running'"
            >
              批量事件抽象
            </el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 进度展示 -->
      <el-card v-if="extractProgress.status === 'running'" class="progress-card" shadow="never">
        <div class="progress-header">
          <span>批量抽象进行中...</span>
          <el-tag type="info">{{ extractProgress.current_batch }}/{{ extractProgress.total_batches }} 批次</el-tag>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 15px;"
        >
          <template #title>
            <span style="font-size: 13px;">任务在后台运行中，您可以切换到其他页面，回来时会自动恢复进度显示</span>
          </template>
        </el-alert>

        <el-progress
          :percentage="extractProgress.progress_percent"
          :format="formatProgress"
        />

        <div class="progress-details">
          <div class="detail-item">
            <span class="label">总用户数：</span>
            <span class="value">{{ extractProgress.total_users }}</span>
          </div>
          <div class="detail-item">
            <span class="label">已处理：</span>
            <span class="value">{{ extractProgress.processed_users }}</span>
          </div>
          <div class="detail-item">
            <span class="label">成功：</span>
            <span class="value success">{{ extractProgress.success_count }}</span>
          </div>
          <div class="detail-item">
            <span class="label">失败：</span>
            <span class="value error">{{ extractProgress.failed_count }}</span>
          </div>
          <div class="detail-item" v-if="extractProgress.estimated_remaining_seconds">
            <span class="label">预计剩余：</span>
            <span class="value">{{ formatTime(extractProgress.estimated_remaining_seconds) }}</span>
          </div>
        </div>

        <div class="current-users" v-if="extractProgress.current_user_ids && extractProgress.current_user_ids.length > 0">
          <span class="label">当前处理：</span>
          <el-tag
            v-for="userId in extractProgress.current_user_ids.slice(0, 5)"
            :key="userId"
            size="small"
            class="user-tag"
          >
            {{ userId }}
          </el-tag>
          <span v-if="extractProgress.current_user_ids.length > 5">
            等 {{ extractProgress.current_user_ids.length }} 个用户
          </span>
        </div>
      </el-card>

      <!-- 完成提示 -->
      <el-alert
        v-if="extractProgress.status === 'completed'"
        type="success"
        title="批量抽象完成"
        :description="`成功: ${extractProgress.success_count}/${extractProgress.total_users}, 失败: ${extractProgress.failed_count}/${extractProgress.total_users}`"
        show-icon
        closable
        @close="resetProgress"
        style="margin-bottom: 20px"
      />

      <!-- 错误提示 -->
      <el-alert
        v-if="extractProgress.status === 'failed'"
        type="error"
        title="批量抽象失败"
        :description="extractProgress.error_message"
        show-icon
        closable
        @close="resetProgress"
        style="margin-bottom: 20px"
      />

      <!-- LLM返回内容展示 -->
      <el-card v-if="llmOutputs.length > 0" class="llm-output-card" style="margin-bottom: 20px">
        <template #header>
          <div class="card-header">
            <span>LLM返回内容 ({{ llmOutputs.length }})</span>
            <el-button text @click="clearLLMOutputs">清空</el-button>
          </div>
        </template>

        <el-scrollbar max-height="400px">
          <el-timeline>
            <el-timeline-item
              v-for="output in llmOutputs"
              :key="output.id"
              :timestamp="output.timestamp"
              :type="output.success ? 'success' : 'danger'"
            >
              <el-card shadow="hover">
                <div class="output-header">
                  <span class="user-id">用户: {{ output.user_id }}</span>
                  <el-tag :type="output.success ? 'success' : 'danger'" size="small">
                    {{ output.success ? '成功' : '失败' }}
                  </el-tag>
                </div>

                <div v-if="output.success" class="events-list">
                  <div class="event-count">抽象出 {{ output.event_count }} 个事件</div>
                  <div v-for="(event, idx) in output.events" :key="idx" class="event-item">
                    <el-tag size="small" type="primary">{{ event.event_type }}</el-tag>
                    <span class="event-desc">{{ event.timestamp }}</span>
                  </div>
                </div>

                <div v-else class="error-message">
                  <el-alert type="error" :closable="false" :title="output.error" />
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-scrollbar>
      </el-card>

      <el-table :data="tableData" style="width: 100%" v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="150" />

        <el-table-column label="行为序列" width="200">
          <template #default="scope">
            <el-link type="primary" @click="showSequenceDetail(scope.row)">
              {{ scope.row.behavior_count }} 条
            </el-link>
          </template>
        </el-table-column>

        <el-table-column label="逻辑行为序列" width="200">
          <template #default="scope">
            <el-link
              v-if="scope.row.has_events"
              type="success"
              @click="showSequenceDetail(scope.row)"
            >
              {{ scope.row.event_count }} 条
            </el-link>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 'success'" type="success">已抽象</el-tag>
            <el-tag v-else-if="scope.row.status === 'failed'" type="danger">失败</el-tag>
            <el-tag v-else type="info">未抽象</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="失败原因" min-width="200">
          <template #default="scope">
            <el-tooltip v-if="scope.row.error_message" :content="scope.row.error_message" placement="top">
              <span style="color: #f56c6c; cursor: pointer;">{{ scope.row.error_message.substring(0, 30) }}...</span>
            </el-tooltip>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button
              v-if="scope.row.has_events && scope.row.status === 'success'"
              size="small"
              @click="showSequenceDetail(scope.row)"
            >
              查看
            </el-button>
            <el-button
              v-else-if="scope.row.status === 'failed'"
              size="small"
              type="warning"
              @click="handleSingleExtract(scope.row.user_id)"
              :loading="extractingUsers[scope.row.user_id]"
            >
              重新生成
            </el-button>
            <el-button
              v-else
              size="small"
              type="primary"
              @click="handleSingleExtract(scope.row.user_id)"
              :loading="extractingUsers[scope.row.user_id]"
            >
              生成
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`用户 ${selectedUser?.user_id} 的详细信息`"
      width="70%"
    >
      <div v-if="selectedUser" v-loading="detailLoading">
        <!-- 用户画像 -->
        <el-divider content-position="left">用户画像</el-divider>
        <div v-if="userProfile" class="profile-section">
          <div style="padding: 15px; background: #f5f7fa; border-radius: 4px;">
            {{ userProfile.profile_text }}
          </div>
        </div>
        <el-empty v-else description="暂无用户画像数据" :image-size="80" />

        <!-- 原始行为序列 -->
        <el-divider content-position="left">原始行为序列</el-divider>
        <el-scrollbar max-height="300px">
          <div v-if="userBehaviors && userBehaviors.length > 0" class="behavior-list">
            <div v-for="(behavior, index) in userBehaviors" :key="index" class="behavior-item">
              <span class="behavior-time">{{ formatTimestamp(behavior.timestamp) }}</span>
              <span class="behavior-detail">{{ behavior.behavior_text }}</span>
            </div>
          </div>
          <div v-else-if="selectedUser.behavior_sequence && selectedUser.behavior_sequence.length > 0">
            <ol>
              <li v-for="(behavior, index) in selectedUser.behavior_sequence" :key="index">
                {{ behavior }}
              </li>
            </ol>
          </div>
          <el-empty v-else description="暂无行为数据" :image-size="80" />
        </el-scrollbar>

        <!-- 逻辑行为序列 -->
        <el-divider content-position="left">逻辑行为序列</el-divider>
        <el-scrollbar max-height="300px">
          <ol v-if="userEvents && userEvents.length > 0" class="event-list">
            <li v-for="(event, index) in userEvents" :key="index" class="event-item">
              {{ event }}
            </li>
          </ol>
          <ol v-else-if="selectedUser.event_sequence && selectedUser.event_sequence.length > 0">
            <li v-for="(event, index) in selectedUser.event_sequence" :key="index">
              {{ event }}
            </li>
          </ol>
          <el-empty v-else description="暂无逻辑行为序列" :image-size="80" />
        </el-scrollbar>
      </div>

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUserDetail, startBatchExtract, getExtractProgress, startBatchExtractStream, extractEventsForUserStream } from '../api/index.js'
import axios from 'axios'
import { startLLMLog, appendLLMLog, completeLLMLog, errorLLMLog } from '../stores/llmLog'

const loading = ref(false)
const batchLoading = ref(false)
const detailLoading = ref(false)
const tableData = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const detailDialogVisible = ref(false)
const selectedUser = ref(null)
const extractingUsers = reactive({})
const userProfile = ref(null)
const userBehaviors = ref([])
const userEvents = ref([])
const progressTimer = ref(null)
const llmOutputs = ref([])
const eventSourceConnection = ref(null)

// 进度状态
const extractProgress = ref({
  status: 'idle',
  total_users: 0,
  processed_users: 0,
  success_count: 0,
  failed_count: 0,
  current_batch: 0,
  total_batches: 0,
  current_user_ids: [],
  progress_percent: 0,
  estimated_remaining_seconds: null,
  error_message: null
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const response = await axios.get('/api/v1/events/sequences', {
      params: {
        limit: pageSize.value,
        offset: offset
      }
    })

    if (response.data.code === 0) {
      tableData.value = response.data.data.items
      total.value = response.data.data.total
    } else {
      ElMessage.error('加载数据失败')
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 批量事件抽象（后台任务+轮询模式）
const handleBatchExtract = async () => {
  try {
    await ElMessageBox.confirm(
      '将对所有未抽象的用户进行事件抽象,此操作可能需要较长时间,是否继续?',
      '批量事件抽象',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    batchLoading.value = true

    // 启动LLM日志记录
    startLLMLog('批量事件抽象')
    appendLLMLog('正在启动后台任务...\n')

    // 重置进度
    resetProgress()

    // 调用后台任务启动接口（不传参数表示处理所有用户）
    const response = await startBatchExtract()

    if (response.code === 0) {
      appendLLMLog('后台任务已启动，开始处理...\n')
      ElMessage.success('批量抽象任务已启动')

      // 启动进度轮询
      startProgressPolling()
    } else {
      throw new Error(response.message || '启动失败')
    }

  } catch (error) {
    if (error !== 'cancel') {
      batchLoading.value = false
      console.error('启动批量抽象失败:', error)
      errorLLMLog(error.response?.data?.detail || error.message)
      ElMessage.error('启动批量抽象失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 开始轮询进度
const startProgressPolling = () => {
  // 清除旧的定时器
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
  }

  // 每 1 秒轮询一次
  progressTimer.value = setInterval(async () => {
    try {
      const response = await getExtractProgress()
      if (response.code === 0) {
        extractProgress.value = response.data

        // 不在LLM日志中显示进度，进度信息已经在进度条中显示

        // 如果完成或失败，停止轮询
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(progressTimer.value)
          progressTimer.value = null
          batchLoading.value = false

          if (response.data.status === 'completed') {
            appendLLMLog(`\n\n✓ 批量抽象完成！`)
            appendLLMLog(`\n总计: ${response.data.total_users} 个用户`)
            appendLLMLog(`\n成功: ${response.data.success_count} 个`)
            appendLLMLog(`\n失败: ${response.data.failed_count} 个\n`)
            completeLLMLog()
            ElMessage.success(`批量抽象完成！成功 ${response.data.success_count}/${response.data.total_users}`)
            await loadData()
          } else {
            appendLLMLog(`\n\n✗ 批量抽象失败: ${response.data.error_message}\n`)
            errorLLMLog(response.data.error_message)
            ElMessage.error(`批量抽象失败: ${response.data.error_message}`)
          }
        }
      }
    } catch (error) {
      console.error('获取进度失败:', error)
    }
  }, 1000)
}

// 重置进度
const resetProgress = () => {
  extractProgress.value = {
    status: 'idle',
    total_users: 0,
    processed_users: 0,
    success_count: 0,
    failed_count: 0,
    current_batch: 0,
    total_batches: 0,
    current_user_ids: [],
    progress_percent: 0,
    estimated_remaining_seconds: null,
    error_message: null
  }
}

// 格式化进度百分比
const formatProgress = (percentage) => {
  return `${percentage.toFixed(1)}%`
}

// 格式化时间
const formatTime = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) {
    return `${seconds} 秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes} 分 ${secs} 秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours} 小时 ${minutes} 分`
  }
}

// 清空LLM输出
const clearLLMOutputs = () => {
  llmOutputs.value = []
}

// 单用户事件抽象
const handleSingleExtract = async (userId) => {
  try {
    extractingUsers[userId] = true

    // 启动LLM日志记录
    startLLMLog(`事件抽象 - ${userId}`)
    appendLLMLog(`正在为用户 ${userId} 抽象事件...\n`)
    appendLLMLog(`\n--- LLM实时响应 ---\n`)

    // 使用流式API
    await extractEventsForUserStream(userId, {
      onProgress: (message) => {
        appendLLMLog(`[进度] ${message}\n`)
      },
      onLLMChunk: (chunk) => {
        // 实时显示LLM返回的每个chunk
        appendLLMLog(chunk)
      },
      onDone: (data) => {
        appendLLMLog(`\n--- 响应结束 ---\n`)
        appendLLMLog(`\n✓ 事件抽象完成\n`)
        completeLLMLog()
        ElMessage.success(`用户 [${userId}] 事件抽象完成`)
        loadData()
      },
      onError: (error) => {
        appendLLMLog(`\n✗ 抽象失败: ${error}\n`)
        errorLLMLog(error)
        ElMessage.error(`用户 [${userId}] 事件抽象失败: ${error}`)
      }
    })

  } catch (error) {
    console.error('单用户事件抽象失败:', error)
    appendLLMLog(`\n✗ 抽象异常: ${error.message}\n`)
    errorLLMLog(error.message)
    ElMessage.error(`用户 [${userId}] 事件抽象失败`)
  } finally {
    extractingUsers[userId] = false
  }
}

// 显示序列详情
const showSequenceDetail = async (row) => {
  selectedUser.value = row
  detailDialogVisible.value = true

  // 加载用户完整信息
  detailLoading.value = true
  try {
    const response = await getUserDetail(row.user_id)
    if (response.code === 0) {
      userProfile.value = response.data.profile
      userBehaviors.value = response.data.behaviors
      userEvents.value = response.data.events
    }
  } catch (error) {
    console.error('加载用户详情失败:', error)
    ElMessage.warning('加载用户详情失败，仅显示基础信息')
  } finally {
    detailLoading.value = false
  }
}

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 获取行为标签类型
const getBehaviorTagType = (action) => {
  const typeMap = {
    'view': 'info',
    'click': 'primary',
    'search': 'warning',
    'purchase': 'success',
    'share': 'success',
    'like': 'danger',
    'comment': 'warning'
  }
  return typeMap[action] || 'info'
}

onMounted(async () => {
  // 加载数据
  loadData()

  // 检查是否有正在运行的任务
  try {
    const response = await getExtractProgress()
    if (response.code === 0 && response.data.status === 'running') {
      // 恢复进度状态
      extractProgress.value = response.data
      // 开始轮询
      startProgressPolling()
    }
  } catch (error) {
    console.error('检查任务状态失败:', error)
  }
})

onBeforeUnmount(() => {
  // 组件销毁时清除定时器
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
  }
  // 关闭流式连接
  if (eventSourceConnection.value && eventSourceConnection.value.close) {
    eventSourceConnection.value.close()
  }
})
</script>

<style scoped>
.event-extraction {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-card {
  margin-bottom: 20px;
  background: #f5f7fa;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  font-weight: 500;
}

.progress-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 15px;
}

.detail-item {
  display: flex;
  align-items: center;
}

.detail-item .label {
  font-weight: 500;
  margin-right: 5px;
  color: #606266;
}

.detail-item .value {
  font-weight: 600;
}

.detail-item .value.success {
  color: #67c23a;
}

.detail-item .value.error {
  color: #f56c6c;
}

.current-users {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #dcdfe6;
}

.current-users .label {
  font-weight: 500;
  margin-right: 10px;
  color: #606266;
}

.user-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

.profile-section {
  margin-bottom: 20px;
}

.behavior-list {
  padding: 10px;
}

.behavior-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  gap: 12px;
}

.behavior-time {
  color: #909399;
  font-size: 12px;
  min-width: 160px;
}

.behavior-detail {
  color: #606266;
  font-size: 13px;
  display: flex;
  gap: 16px;
}

.event-list {
  padding-left: 20px;
  line-height: 2;
}

.event-item {
  margin-bottom: 12px;
  padding: 8px;
  background: #f0f9ff;
  border-left: 3px solid #409eff;
  border-radius: 4px;
}

ol {
  padding-left: 20px;
  line-height: 2;
}

ol li {
  margin-bottom: 8px;
}

.llm-output-card {
  background: #fafafa;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.output-header .user-id {
  font-weight: 500;
  color: #303133;
}

.events-list {
  margin-top: 8px;
}

.event-count {
  color: #606266;
  font-size: 13px;
  margin-bottom: 8px;
}

.events-list .event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  padding: 6px 0;
}

.events-list .event-desc {
  color: #606266;
  font-size: 12px;
}

.error-message {
  margin-top: 8px;
}
</style>
