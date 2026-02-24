<template>
  <div class="causal-graph-generation">
    <el-card class="header-card">
      <h2>事理图谱生成</h2>
      <p>基于高频子序列模式生成事理图谱，用于分析用户行为因果关系</p>
    </el-card>

    <!-- 模式选择区域 -->
    <el-card class="pattern-selection-card">
      <template #header>
        <div class="card-header">
          <span>选择高频模式</span>
          <div>
            <el-button size="small" @click="selectAll">全选</el-button>
            <el-button size="small" @click="clearSelection">清空</el-button>
            <el-button type="primary" size="small" @click="loadPatterns">刷新</el-button>
          </div>
        </div>
      </template>

      <div v-loading="loadingPatterns" class="patterns-container">
        <el-empty v-if="patterns.length === 0" description="暂无高频模式数据" />

        <el-checkbox-group v-else v-model="selectedPatternIds" class="pattern-list">
          <el-checkbox
            v-for="pattern in patterns"
            :key="pattern.id"
            :value="pattern.id"
            class="pattern-item"
          >
            <div class="pattern-content">
              <div class="pattern-sequence">
                <el-tag
                  v-for="(event, index) in pattern.pattern"
                  :key="index"
                  size="small"
                  style="margin-right: 5px"
                >
                  {{ event }}
                </el-tag>
              </div>
              <div class="pattern-stats">
                <el-tag size="small" type="info">支持度: {{ pattern.support }}</el-tag>
                <el-tag size="small" type="warning">支持率: {{ pattern.frequency.toFixed(2) }}%</el-tag>
                <el-tag size="small" type="success">用户数: {{ pattern.user_count }}</el-tag>
              </div>
            </div>
          </el-checkbox>
        </el-checkbox-group>
      </div>
    </el-card>

    <!-- 生成配置区域 -->
    <el-card class="config-card">
      <template #header>
        <span>生成配置</span>
      </template>

      <el-form :model="config" label-width="120px">
        <el-form-item label="图谱名称">
          <el-input
            v-model="config.graphName"
            placeholder="留空则自动生成"
            clearable
          />
        </el-form-item>

        <el-form-item label="分析重点">
          <el-select v-model="config.analysisFocus" placeholder="请选择分析重点">
            <el-option label="综合分析" value="comprehensive" />
            <el-option label="转化路径分析" value="conversion" />
            <el-option label="流失原因分析" value="churn" />
            <el-option label="用户画像分析" value="profile" />
          </el-select>
        </el-form-item>

        <el-form-item label="使用模式">
          <el-radio-group v-model="config.useAllPatterns">
            <el-radio :value="true">使用所有模式</el-radio>
            <el-radio :value="false">使用选中的 {{ selectedPatternIds.length }} 个模式</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 生成按钮 -->
    <div class="action-buttons">
      <el-button
        type="primary"
        size="large"
        :loading="generating"
        :disabled="!config.useAllPatterns && selectedPatternIds.length === 0"
        @click="generateGraph"
      >
        {{ generating ? '生成中...' : '生成事理图谱' }}
      </el-button>
    </div>

    <!-- 生成进度 -->
    <el-card v-if="generating || generationResult" class="progress-card">
      <template #header>
        <span>{{ generating ? '生成进度' : '生成结果' }}</span>
      </template>

      <div v-if="generating" class="progress-content">
        <el-progress :percentage="progress" :status="progressStatus" />
        <p class="progress-text">{{ progressText }}</p>
      </div>

      <div v-else-if="generationResult" class="result-content">
        <el-result icon="success" title="事理图谱生成成功">
          <template #sub-title>
            <div class="result-stats">
              <p>图谱名称: {{ generationResult.graph_name }}</p>
              <p>节点数量: {{ generationResult.nodes_count }}</p>
              <p>边数量: {{ generationResult.edges_count }}</p>
            </div>
          </template>
          <template #extra>
            <div class="insights-section">
              <h4>关键洞察</h4>
              <ul class="insights-list">
                <li v-for="(insight, index) in generationResult.insights" :key="index">
                  {{ insight }}
                </li>
              </ul>
            </div>
            <div class="result-actions">
              <el-button type="primary" @click="viewGraph">查看详情</el-button>
              <el-button @click="resetForm">继续生成</el-button>
            </div>
          </template>
        </el-result>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listFrequentPatterns, generateCausalGraphStream } from '@/api'
import { startLLMLog, appendLLMLog, completeLLMLog, errorLLMLog } from '@/stores/llmLog'

const router = useRouter()

// 数据
const patterns = ref([])
const selectedPatternIds = ref([])
const loadingPatterns = ref(false)
const generating = ref(false)
const progress = ref(0)
const progressStatus = ref('')
const progressText = ref('')
const generationResult = ref(null)

const config = ref({
  graphName: '',
  analysisFocus: 'comprehensive',
  useAllPatterns: true
})

// 加载高频模式
const loadPatterns = async () => {
  loadingPatterns.value = true
  try {
    const response = await listFrequentPatterns(100, 0)
    if (response.code === 0) {
      patterns.value = response.data.patterns || []
      ElMessage.success(`加载了 ${patterns.value.length} 个高频模式`)
    }
  } catch (error) {
    console.error('加载高频模式失败:', error)
  } finally {
    loadingPatterns.value = false
  }
}

// 全选
const selectAll = () => {
  selectedPatternIds.value = patterns.value.map(p => p.id)
}

// 清空选择
const clearSelection = () => {
  selectedPatternIds.value = []
}

// 生成事理图谱（流式）
const generateGraph = async () => {
  generating.value = true
  progress.value = 0
  progressStatus.value = ''
  progressText.value = '准备生成...'
  generationResult.value = null

  // 启动LLM日志记录
  startLLMLog('生成事理图谱')

  try {
    const params = {
      pattern_ids: config.value.useAllPatterns ? null : selectedPatternIds.value,
      analysis_focus: config.value.analysisFocus,
      graph_name: config.value.graphName || null
    }

    await generateCausalGraphStream(
      params,
      // onProgress
      (message) => {
        progressText.value = message
        // 根据进度消息更新进度条
        if (message.includes('加载')) {
          progress.value = 20
        } else if (message.includes('提取')) {
          progress.value = 40
        } else if (message.includes('构建')) {
          progress.value = 50
        } else if (message.includes('调用')) {
          progress.value = 60
        } else if (message.includes('解析')) {
          progress.value = 90
        } else if (message.includes('保存')) {
          progress.value = 95
        }
      },
      // onContent
      (content) => {
        // 将LLM输出添加到全局日志
        appendLLMLog(content)
      },
      // onResult
      (data) => {
        progress.value = 100
        progressStatus.value = 'success'
        progressText.value = '生成完成！'
        generationResult.value = data
        completeLLMLog()
        ElMessage.success('事理图谱生成成功')
      },
      // onError
      (error) => {
        progress.value = 100
        progressStatus.value = 'exception'
        progressText.value = '生成失败'
        errorLLMLog(error)
        ElMessage.error(`生成失败: ${error}`)
      }
    )
  } catch (error) {
    progress.value = 100
    progressStatus.value = 'exception'
    progressText.value = '生成失败'
    console.error('生成事理图谱失败:', error)
    errorLLMLog(error.message)
    ElMessage.error(`生成失败: ${error.message}`)
  } finally {
    generating.value = false
  }
}

// 查看图谱详情
const viewGraph = () => {
  if (generationResult.value) {
    router.push({
      name: 'CausalGraphView',
      params: { graphId: generationResult.value.graph_id }
    })
  }
}

// 重置表单
const resetForm = () => {
  generationResult.value = null
  progress.value = 0
  progressStatus.value = ''
  progressText.value = ''
}

onMounted(() => {
  loadPatterns()
})
</script>

<style scoped>
.causal-graph-generation {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-card h2 {
  margin: 0 0 10px 0;
  color: #303133;
}

.header-card p {
  margin: 0;
  color: #909399;
}

.pattern-selection-card,
.config-card,
.progress-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.patterns-container {
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
}

.pattern-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pattern-item {
  width: 100%;
  padding: 10px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  transition: all 0.3s;
}

.pattern-item:hover {
  background-color: #F5F7FA;
  border-color: #409EFF;
}

.pattern-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.pattern-sequence {
  flex: 1;
  font-weight: 500;
  color: #303133;
}

.pattern-stats {
  display: flex;
  gap: 10px;
}

.action-buttons {
  text-align: center;
  margin: 30px 0;
}

.progress-content {
  padding: 20px;
}

.progress-text {
  text-align: center;
  margin-top: 10px;
  color: #606266;
}

.result-content {
  padding: 20px;
}

.result-stats {
  text-align: left;
  margin: 20px 0;
}

.result-stats p {
  margin: 5px 0;
  color: #606266;
}

.insights-section {
  margin: 20px 0;
  text-align: left;
}

.insights-section h4 {
  margin-bottom: 10px;
  color: #303133;
}

.insights-list {
  list-style: none;
  padding: 0;
}

.insights-list li {
  padding: 8px 0;
  border-bottom: 1px solid #EBEEF5;
  color: #606266;
}

.insights-list li:last-child {
  border-bottom: none;
}

.result-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
  justify-content: center;
}
</style>
