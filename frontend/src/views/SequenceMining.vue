<template>
  <div class="sequence-mining">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>高频子序列挖掘</span>
          <el-tag type="info">基于逻辑行为序列</el-tag>
        </div>
      </template>

      <el-alert
        title="使用说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <p>1. 选择挖掘算法和参数</p>
        <p>2. 点击"开始挖掘"按钮</p>
        <p>3. 查看挖掘结果，选择感兴趣的模式保存</p>
        <p style="color: #E6A23C; margin-top: 10px">注意：需要先在"事件抽象"页面生成逻辑行为序列</p>
        <p style="color: #67C23A; margin-top: 5px">✓ 内存优化已启用：最大序列长度限制为5，最多处理50,000条序列</p>
      </el-alert>

      <el-form :model="miningForm" label-width="140px" style="margin-bottom: 20px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="挖掘算法">
              <el-select v-model="miningForm.algorithm" placeholder="请选择算法">
                <el-option label="PrefixSpan（经典序列模式挖掘）" value="prefixspan">
                  <div>
                    <div style="font-weight: bold">PrefixSpan</div>
                    <div style="font-size: 12px; color: #999">经典的序列模式挖掘算法，适合发现频繁出现的子序列</div>
                  </div>
                </el-option>
                <el-option label="Attention权重（基于共现频率）" value="attention">
                  <div>
                    <div style="font-weight: bold">Attention权重</div>
                    <div style="font-size: 12px; color: #999">基于事件共现频率的权重方法，适合发现关联性强的事件序列</div>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="最小支持度">
              <el-input-number
                v-model="miningForm.min_support"
                :min="1"
                :max="100"
                placeholder="最小支持度"
              />
              <el-popover
                placement="top"
                :width="300"
                trigger="hover"
              >
                <template #reference>
                  <el-icon style="margin-left: 10px; cursor: help; color: #409EFF"><QuestionFilled /></el-icon>
                </template>
                <div style="line-height: 1.6">
                  <p style="font-weight: bold; margin-bottom: 8px">什么是支持度？</p>
                  <p style="margin-bottom: 8px">支持度是指某个事件序列模式在所有用户中出现的次数。</p>
                  <p style="margin-bottom: 8px"><strong>例如：</strong>支持度=5 表示有5个用户的行为序列中包含该模式。</p>
                  <p style="color: #E6A23C">值越大，找到的模式越少但越可靠。建议设置为2-5。</p>
                </div>
              </el-popover>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大序列长度">
              <el-input-number
                v-model="miningForm.max_length"
                :min="2"
                :max="5"
                placeholder="最大序列长度"
              />
              <el-tooltip content="挖掘的子序列的最大长度（为控制内存使用，限制为5）" placement="top">
                <el-icon style="margin-left: 10px; cursor: help"><QuestionFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="返回模式数量">
              <el-input-number
                v-model="miningForm.top_k"
                :min="1"
                :max="100"
                placeholder="返回前K个模式"
              />
              <el-tooltip content="返回的最高频模式数量" placement="top">
                <el-icon style="margin-left: 10px; cursor: help"><QuestionFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button
            type="primary"
            @click="startMining"
            :loading="mining"
            :disabled="!hasEventData"
          >
            {{ mining ? '挖掘中...' : '开始挖掘' }}
          </el-button>
          <el-button @click="resetForm">重置参数</el-button>
          <el-button @click="loadSavedPatterns">查看已保存模式</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!hasEventData"
        title="提示：未检测到逻辑行为序列数据"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      >
        请先在"事件抽象"页面进行事件提取，生成逻辑行为序列后再进行序列挖掘
      </el-alert>

      <div v-if="miningProgress.show" style="margin-bottom: 20px">
        <el-card shadow="never">
          <div style="margin-bottom: 10px">
            <el-progress
              :percentage="miningProgress.percentage"
              :status="miningProgress.status"
            />
          </div>
          <div style="color: #606266; font-size: 14px">
            <p v-if="miningProgress.step">{{ miningProgress.step }}</p>
            <p v-if="miningProgress.detail">{{ miningProgress.detail }}</p>
          </div>
        </el-card>
      </div>

      <div v-if="statistics" style="margin-bottom: 20px">
        <el-card shadow="never">
          <template #header>
            <span>挖掘统计信息</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="总用户数" :value="statistics.total_users" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="事件类型数" :value="statistics.unique_event_types" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="平均序列长度" :value="statistics.avg_sequence_length" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="发现模式数" :value="statistics.patterns_found" />
            </el-col>
          </el-row>
        </el-card>
      </div>

      <div v-if="patterns.length > 0">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>挖掘结果 (共 {{ patterns.length }} 个模式)</span>
              <el-button
                type="success"
                size="small"
                @click="saveSelectedPatterns"
                :disabled="selectedPatterns.length === 0"
              >
                保存选中模式 ({{ selectedPatterns.length }})
              </el-button>
            </div>
          </template>

          <el-table
            :data="patterns"
            style="width: 100%"
            @selection-change="handleSelectionChange"
            v-loading="mining"
          >
            <el-table-column type="selection" width="55" />

            <el-table-column label="排名" width="70" align="center">
              <template #default="scope">
                <el-tag :type="getRankType(scope.$index + 1)">
                  {{ scope.$index + 1 }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="事件序列" min-width="300">
              <template #default="scope">
                <div style="display: flex; align-items: center; gap: 5px; flex-wrap: wrap">
                  <el-tag
                    v-for="(event, index) in scope.row.pattern"
                    :key="index"
                    size="small"
                    :type="getEventTagType(event)"
                  >
                    {{ event }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="支持度" width="120" align="center">
              <template #header>
                <span>支持度</span>
                <el-popover
                  placement="top"
                  :width="280"
                  trigger="hover"
                >
                  <template #reference>
                    <el-icon style="margin-left: 5px; cursor: help; color: #409EFF"><QuestionFilled /></el-icon>
                  </template>
                  <div style="line-height: 1.6">
                    <p style="font-weight: bold; margin-bottom: 8px">支持度 (Support)</p>
                    <p>该模式在所有用户中出现的次数。</p>
                    <p style="margin-top: 8px"><strong>例如：</strong>支持度=10 表示有10个用户的行为序列包含该模式。</p>
                  </div>
                </el-popover>
              </template>
              <template #default="scope">
                <el-tag type="success">{{ scope.row.support }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column label="支持率" width="120" align="center">
              <template #header>
                <span>支持率</span>
                <el-popover
                  placement="top"
                  :width="280"
                  trigger="hover"
                >
                  <template #reference>
                    <el-icon style="margin-left: 5px; cursor: help; color: #409EFF"><QuestionFilled /></el-icon>
                  </template>
                  <div style="line-height: 1.6">
                    <p style="font-weight: bold; margin-bottom: 8px">支持率 (Support Rate)</p>
                    <p>该模式在所有用户中的占比。</p>
                    <p style="margin-top: 8px"><strong>计算公式：</strong>支持率 = 支持度 / 总用户数 × 100%</p>
                    <p style="margin-top: 8px"><strong>例如：</strong>10个用户中有3个包含该模式，则支持率=30%。</p>
                  </div>
                </el-popover>
              </template>
              <template #default="scope">
                {{ scope.row.support_rate ? scope.row.support_rate.toFixed(1) + '%' : 'N/A' }}
              </template>
            </el-table-column>

            <el-table-column label="用户数" width="120" align="center">
              <template #header>
                <span>用户数</span>
                <el-popover
                  placement="top"
                  :width="280"
                  trigger="hover"
                >
                  <template #reference>
                    <el-icon style="margin-left: 5px; cursor: help; color: #409EFF"><QuestionFilled /></el-icon>
                  </template>
                  <div style="line-height: 1.6">
                    <p style="font-weight: bold; margin-bottom: 8px">用户数</p>
                    <p>包含该模式的用户数量，等同于支持度。</p>
                    <p style="margin-top: 8px">这个指标帮助你了解有多少用户展现了这种行为模式。</p>
                  </div>
                </el-popover>
              </template>
              <template #default="scope">
                {{ scope.row.user_count || scope.row.support || 0 }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button
                  size="small"
                  @click="viewExamples(scope.row)"
                  link
                >
                  查看示例
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <div v-if="savedPatterns.length > 0" style="margin-top: 20px">
        <el-card shadow="never">
          <template #header>
            <span>已保存的模式 (共 {{ savedPatterns.length }} 个)</span>
          </template>

          <el-table :data="savedPatterns" style="width: 100%">
            <el-table-column label="事件序列" min-width="300">
              <template #default="scope">
                <div style="display: flex; align-items: center; gap: 5px; flex-wrap: wrap">
                  <el-tag
                    v-for="(event, index) in (scope.row.pattern || parsePattern(scope.row.pattern_sequence))"
                    :key="index"
                    size="small"
                    :type="getEventTagType(event)"
                  >
                    {{ event }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="支持度" width="100" align="center">
              <template #default="scope">
                <el-tag type="success">{{ scope.row.support || 0 }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column label="支持率" width="100" align="center">
              <template #default="scope">
                {{ scope.row.frequency ? (scope.row.frequency * 100).toFixed(1) + '%' : '-' }}
              </template>
            </el-table-column>

            <el-table-column label="用户数" width="100" align="center">
              <template #default="scope">
                {{ scope.row.user_count || scope.row.support || 0 }}
              </template>
            </el-table-column>

            <el-table-column label="算法" width="120" align="center">
              <template #default="scope">
                {{ scope.row.algorithm || '-' }}
              </template>
            </el-table-column>

            <el-table-column label="保存时间" width="180" align="center">
              <template #default="scope">
                {{ scope.row.created_at }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="100" align="center">
              <template #default="scope">
                <el-button
                  size="small"
                  type="danger"
                  @click="deletePattern(scope.row)"
                  link
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="examplesDialogVisible" title="模式示例" width="60%">
      <div v-if="currentExamples">
        <el-alert
          :title="`模式: ${currentExamples.pattern.join(' → ')}`"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        />

        <el-table :data="currentExamples.examples" style="width: 100%">
          <el-table-column label="用户ID" width="150">
            <template #default="scope">
              {{ scope.row.user_id }}
            </template>
          </el-table-column>

          <el-table-column label="完整事件序列" min-width="400">
            <template #default="scope">
              <div style="display: flex; align-items: center; gap: 5px; flex-wrap: wrap">
                <el-tag
                  v-for="(event, index) in scope.row.sequence"
                  :key="index"
                  size="small"
                  :type="currentExamples.pattern.includes(event) ? 'success' : 'info'"
                >
                  {{ event }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import { mineFrequentPatterns } from '@/api/index.js'

const miningForm = ref({
  algorithm: 'prefixspan',
  min_support: 2,
  max_length: 5,
  top_k: 20
})

const mining = ref(false)
const hasEventData = ref(true)
const patterns = ref([])
const selectedPatterns = ref([])
const statistics = ref(null)
const savedPatterns = ref([])

const miningProgress = ref({
  show: false,
  percentage: 0,
  status: '',
  step: '',
  detail: ''
})

const examplesDialogVisible = ref(false)
const currentExamples = ref(null)

const startMining = async () => {
  try {
    mining.value = true
    patterns.value = []
    statistics.value = null
    selectedPatterns.value = []

    miningProgress.value = {
      show: true,
      percentage: 20,
      status: '',
      step: '正在加载事件序列数据...',
      detail: '从数据库读取用户事件序列'
    }

    await new Promise(resolve => setTimeout(resolve, 500))

    miningProgress.value.percentage = 40
    miningProgress.value.step = '正在执行挖掘算法...'
    miningProgress.value.detail = `使用 ${miningForm.value.algorithm} 算法进行模式挖掘`

    const res = await mineFrequentPatterns(miningForm.value)

    if (res.code === 0) {
      miningProgress.value.percentage = 80
      miningProgress.value.step = '正在格式化结果...'
      miningProgress.value.detail = `发现 ${res.data.frequent_patterns.length} 个高频模式`

      await new Promise(resolve => setTimeout(resolve, 300))

      miningProgress.value.percentage = 100
      miningProgress.value.status = 'success'
      miningProgress.value.step = '挖掘完成！'
      miningProgress.value.detail = ''

      patterns.value = res.data.frequent_patterns
      statistics.value = res.data.statistics

      ElMessage.success(`挖掘完成！发现 ${patterns.value.length} 个高频模式`)

      setTimeout(() => {
        miningProgress.value.show = false
      }, 2000)
    } else {
      throw new Error(res.message || '挖掘失败')
    }
  } catch (error) {
    console.error('挖掘失败:', error)
    miningProgress.value.status = 'exception'
    miningProgress.value.step = '挖掘失败'

    let errorMessage = '挖掘失败，请稍后重试'
    if (error.response) {
      if (error.response.data && error.response.data.detail) {
        // 处理422验证错误（detail是数组）
        if (Array.isArray(error.response.data.detail)) {
          const errors = error.response.data.detail.map(err => {
            const field = err.loc ? err.loc[err.loc.length - 1] : '参数'
            return `${field}: ${err.msg}`
          }).join('; ')
          errorMessage = `参数验证失败: ${errors}`
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = `挖掘失败: ${error.response.data.detail}`
        } else {
          errorMessage = `挖掘失败: ${JSON.stringify(error.response.data.detail)}`
        }
      } else if (error.response.status === 400) {
        errorMessage = '参数错误，请检查输入参数'
      } else if (error.response.status === 422) {
        errorMessage = '参数验证失败，请检查输入参数是否符合要求'
      } else if (error.response.status === 500) {
        errorMessage = '服务器处理失败，请查看后端日志'
      }
    } else if (error.message) {
      errorMessage = `挖掘失败: ${error.message}`
    }

    ElMessage.error(errorMessage)
  } finally {
    mining.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedPatterns.value = selection
}

const saveSelectedPatterns = async () => {
  if (selectedPatterns.value.length === 0) {
    ElMessage.warning('请先选择要保存的模式')
    return
  }

  try {
    const res = await axios.post('/api/v1/mining/patterns/save', {
      patterns: selectedPatterns.value,
      algorithm: miningForm.value.algorithm,
      min_support: miningForm.value.min_support
    })

    if (res.data.code === 0) {
      ElMessage.success(res.data.message)
      selectedPatterns.value = []
      loadSavedPatterns()
    } else {
      throw new Error(res.data.message || '保存失败')
    }
  } catch (error) {
    console.error('保存失败:', error)
    let errorMessage = '保存失败，请稍后重试'
    if (error.response && error.response.data && error.response.data.detail) {
      errorMessage = `保存失败: ${error.response.data.detail}`
    }
    ElMessage.error(errorMessage)
  }
}

const loadSavedPatterns = async () => {
  try {
    const res = await axios.get('/api/v1/mining/patterns/saved')

    if (res.data.code === 0) {
      savedPatterns.value = res.data.data.patterns || []
    }
  } catch (error) {
    console.error('加载已保存模式失败:', error)
  }
}

const deletePattern = async (pattern) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个模式吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await axios.delete(`/api/v1/mining/patterns/${pattern.id}`)

    if (res.data.code === 0) {
      ElMessage.success('删除成功')
      loadSavedPatterns()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const viewExamples = async (pattern) => {
  try {
    const patternId = pattern.pattern.join(',')
    const res = await axios.post(`/api/v1/mining/patterns/${patternId}/examples?limit=5`)

    if (res.data.code === 0) {
      currentExamples.value = res.data.data
      examplesDialogVisible.value = true
    }
  } catch (error) {
    console.error('加载示例失败:', error)
    ElMessage.error('加载示例失败')
  }
}

const resetForm = () => {
  miningForm.value = {
    algorithm: 'prefixspan',
    min_support: 2,
    max_length: 5,
    top_k: 20
  }
  patterns.value = []
  statistics.value = null
  selectedPatterns.value = []
  miningProgress.value.show = false
}

const getRankType = (rank) => {
  if (rank === 1) return 'danger'
  if (rank === 2) return 'warning'
  if (rank === 3) return 'success'
  return 'info'
}

const getEventTagType = (event) => {
  const eventTypes = {
    '浏览': 'primary',
    '点击': 'success',
    '搜索': 'warning',
    '购买': 'danger',
    '加购': 'info'
  }
  return eventTypes[event] || 'info'
}

const parsePattern = (patternStr) => {
  try {
    return JSON.parse(patternStr)
  } catch {
    return patternStr ? patternStr.split(',') : []
  }
}

const checkEventData = async () => {
  try {
    const res = await axios.get('/api/v1/events/stats')
    hasEventData.value = res.data.data && res.data.data.users_with_events > 0
  } catch (error) {
    hasEventData.value = false
  }
}

onMounted(() => {
  loadSavedPatterns()
  checkEventData()
})
</script>

<style scoped>
.sequence-mining {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-alert p {
  margin: 5px 0;
  line-height: 1.6;
}
</style>
