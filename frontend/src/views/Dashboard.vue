<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>用户规模</template>
          <div class="stat-value" :class="{'text-warning': stats.users === 0, 'text-success': stats.users > 0}">
            {{ stats.users | formatNumber }}
          </div>
          <div class="stat-label">{{ dataStatus }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>知识图谱</template>
          <div class="stat-value">{{ stats.entities | formatNumber }}</div>
          <div class="stat-label">实体节点</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>知识图谱</template>
          <div class="stat-value">{{ stats.relations | formatNumber }}</div>
          <div class="stat-label">关系边</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>样本状态</template>
          <div class="stat-value">{{ sampleReady ? '已生成' : '待生成' }}</div>
          <div class="stat-label">1:10:5:5</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>Step 1: 加载用户数据</span>
          <el-tag :type="stats.users > 0 ? 'success' : 'info'">
            {{ stats.users > 0 ? '已加载' : '未加载' }}
          </el-tag>
        </div>
      </template>
      
      <el-form :model="loadForm" label-width="120px">
        <el-form-item label="加载用户数量">
          <el-input-number v-model="loadForm.count" :min="1000" :max="500000" :step="1000" />
          <span class="form-tip">最大支持50万用户</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadUserData" :loading="loadingData" size="large">
            {{ loadingData ? '加载中...' : '加载用户数据' }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="stats.users > 0" type="success" :closable="false" show-icon>
        <template #title>✓ 用户数据加载成功！共 {{ stats.users | formatNumber }} 用户已就绪</template>
      </el-alert>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>Step 2: 构建知识图谱</span>
          <el-tag :type="stats.entities > 0 ? 'success' : 'info'">
            {{ stats.entities > 0 ? '已构建' : '未构建' }}
          </el-tag>
        </div>
      </template>
      
      <el-alert v-if="stats.users === 0" type="warning" show-icon style="margin-bottom: 20px">
        请先加载用户数据后再构建知识图谱
      </el-alert>

      <div v-if="stats.users > 0">
        <el-form label-width="120px">
          <el-form-item label="构建用户数量">
            <el-input :value="stats.users | formatNumber" disabled />
            <span class="form-tip">将使用已加载的 {{ stats.users | formatNumber }} 用户构建图谱</span>
          </el-form-item>
          <el-form-item label="批次大小">
            <el-input-number v-model="buildForm.batchSize" :min="1000" :max="10000" :step="1000" />
            <span class="form-tip">每批处理的用户数</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="startBuild" :loading="building" size="large" :disabled="stats.users === 0">
              {{ building ? '构建中...' : '开始构建知识图谱' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div v-if="building || progress.current_step" class="progress-section">
          <el-divider content-position="left">构建进度</el-divider>
          <div class="step-info">
            <span class="step-name">{{ progress.step_name || progress.current_step }}</span>
            <span class="step-progress">{{ (progress.step_progress * 100).toFixed(1) }}%</span>
          </div>
          <el-progress :percentage="progress.step_progress * 100" :status="progress.step_progress >= 1 ? 'success' : ''" :stroke-width="20" />
          
          <div v-if="progress.total_batches > 0" class="batch-info">
            <div class="batch-header">
              <span>批次处理: {{ progress.current_batch || 0 }} / {{ progress.total_batches }}</span>
              <el-tag size="small" type="info">{{ progress.batch_info || '' }}</el-tag>
            </div>
            <el-progress :percentage="(progress.current_batch / progress.total_batches) * 100" :stroke-width="12" :show-text="false" />
            <div class="batches-completed">
              <span>已完成批次:</span>
              <el-tag v-for="batch in progress.batches_completed" :key="batch" size="small" type="success" class="batch-tag">{{ batch }}</el-tag>
              <span v-if="!progress.batches_completed.length" class="no-batches">暂无</span>
            </div>
          </div>
          
          <div class="stats-info">
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-num">{{ progress.entities_created | formatNumber }}</div>
                  <div class="stat-label">已创建实体</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-num">{{ progress.relations_created | formatNumber }}</div>
                  <div class="stat-label">已创建关系</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-num">{{ progress.total_batches }}</div>
                  <div class="stat-label">总批次数</div>
                </div>
              </el-col>
            </el-row>
          </div>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>示例问题</template>
          <el-tag v-for="(q, i) in exampleQuestions" :key="i" @click="goToQA(q)" class="example-tag" type="info" effect="plain">{{ q }}</el-tag>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>系统状态</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户数据">
              <el-tag :type="stats.users > 0 ? 'success' : 'info'">{{ stats.users > 0 ? '已加载' : '未加载' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="知识图谱">
              <el-tag :type="stats.entities > 0 ? 'success' : 'info'">{{ stats.entities > 0 ? '已构建' : '未构建' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="样本数据">
              <el-tag :type="sampleReady ? 'success' : 'info'">{{ sampleReady ? '已生成' : '未生成' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="事理图谱">
              <el-tag :type="eventGraphReady ? 'success' : 'info'">{{ eventGraphReady ? '已生成' : '未生成' }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>使用流程</template>
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="加载用户数据" description="从数据源加载用户数据" />
        <el-step title="构建知识图谱" description="分批处理构建图谱" />
        <el-step title="生成样本" description="生成训练样本" />
        <el-step title="智能问答" description="基于图谱回答问题" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { buildKnowledgeGraph, doGenerateSamples, buildEventGraph, getBuildProgress, loadUserData as apiLoadUserData, getDataStatus } from '../api'

const router = useRouter()
const stats = reactive({ users: 0, entities: 0, relations: 0 })
const sampleReady = ref(false)
const eventGraphReady = ref(false)
const loadingData = ref(false)
const building = ref(false)
const buildForm = reactive({ batchSize: 5000 })
const loadForm = reactive({ count: 50000 })
const progress = reactive({ current_step: '', step_progress: 0, step_name: '', total_batches: 0, current_batch: 0, batch_info: '', batches_completed: [], entities_created: 0, relations_created: 0 })
const exampleQuestions = ['喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？', '高收入人群对豪华轿车的品牌偏好是什么？', '什么样的用户容易流失？', '针对商务人士应该投放哪些素材？']
let progressTimer = null

const currentStep = computed(() => {
  if (stats.users === 0) return 0
  if (stats.entities === 0) return 1
  if (!sampleReady.value) return 2
  return 3
})

const dataStatus = computed(() => {
  if (stats.users === 0) return '未加载'
  return `${(stats.users / 10000).toFixed(0)}万用户`
})

const loadUserData = async () => {
  loadingData.value = true
  try {
    const res = await apiLoadUserData({ count: loadForm.count })
    stats.users = res.data.loaded_count
    ElMessage.success(`成功加载 ${stats.users.toLocaleString()} 用户数据`)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally { loadingData.value = false }
}

const startBuild = async () => {
  if (stats.users === 0) {
    ElMessage.warning('请先加载用户数据')
    return
  }
  building.value = true
  progress.current_step = '准备中...'
  progress.step_progress = 0
  progress.total_batches = Math.ceil(stats.users / buildForm.batchSize)
  progress.current_batch = 0
  progress.batches_completed = []
  progress.entities_created = 0
  progress.relations_created = 0
  progressTimer = setInterval(fetchProgress, 500)
  try {
    const res = await buildKnowledgeGraph(stats.users)
    if (progressTimer) { clearInterval(progressTimer); progressTimer = null }
    stats.entities = res.data.stats.total_entities
    stats.relations = res.data.stats.total_relations
    progress.step_progress = 1
    progress.step_name = '构建完成'
    ElMessage.success(`知识图谱构建成功！`)
    ElMessage.info(`实体: ${stats.entities.toLocaleString()}, 关系: ${stats.relations.toLocaleString()}`)
  } catch (e) {
    if (progressTimer) { clearInterval(progressTimer); progressTimer = null }
    ElMessage.error('构建失败: ' + (e.response?.data?.detail || e.message))
  } finally { building.value = false }
}

const fetchProgress = async () => {
  try {
    const res = await getBuildProgress()
    if (res.code === 0 && res.data) {
      progress.current_step = res.data.current_step || ''
      progress.step_progress = res.data.step_progress || 0
      progress.step_name = res.data.step_name || ''
      progress.total_batches = res.data.total_batches || 0
      progress.current_batch = res.data.current_batch || 0
      progress.batch_info = res.data.batch_info || ''
      progress.batches_completed = res.data.batches_completed || []
      progress.entities_created = res.data.entities_created || 0
      progress.relations_created = res.data.relations_created || 0
    }
  } catch (e) { console.error('获取进度失败', e) }
}

const goToQA = (q) => router.push({ path: '/qa', query: { q } })
onMounted(async () => {
  try {
    const res = await getDataStatus()
    if (res.code === 0 && res.data) { stats.users = res.data.loaded_count || 0 }
  } catch (e) { console.error('获取数据状态失败', e) }
})
onUnmounted(() => { if (progressTimer) clearInterval(progressTimer) })
</script>

<style scoped>
.stat-value { font-size: 28px; font-weight: bold; text-align: center; }
.stat-value.text-warning { color: #E6A23C; }
.stat-value.text-success { color: #67C23A; }
.stat-label { color: #909399; text-align: center; margin-top: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.form-tip { margin-left: 10px; color: #909399; font-size: 12px; }
.progress-section { margin-top: 20px; padding: 20px; background: #f5f7fa; border-radius: 8px; }
.step-info { display: flex; justify-content: space-between; margin-bottom: 10px; }
.step-name { font-size: 16px; font-weight: bold; color: #303133; }
.step-progress { font-size: 16px; font-weight: bold; color: #409EFF; }
.batch-info { margin-top: 20px; padding: 15px; background: white; border-radius: 6px; }
.batch-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.batches-completed { margin-top: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 5px; }
.batch-tag { margin: 2px; }
.no-batches { color: #909399; font-size: 12px; margin-left: 10px; }
.stats-info { margin-top: 20px; padding: 15px; background: white; border-radius: 6px; }
.stat-item { text-align: center; }
.stat-num { font-size: 24px; font-weight: bold; color: #67C23A; }
.example-tag { margin: 5px; cursor: pointer; transition: all 0.3s; }
.example-tag:hover { transform: scale(1.05); }
</style>
