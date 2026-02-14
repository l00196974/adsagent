<template>
  <div class="dashboard">
    <el-alert type="info" :closable="false" show-icon style="margin-bottom: 20px">
      <template #title>
        数据概览 - 请先前往"数据导入"页面上传CSV文件
      </template>
    </el-alert>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>用户数据</template>
          <div class="stat-value" :class="{'text-warning': stats.users === 0, 'text-success': stats.users > 0}">
            {{ formatNumber(stats.users) }}
          </div>
          <div class="stat-label">{{ dataStatus }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>实体节点</template>
          <div class="stat-value">{{ formatNumber(stats.entities) }}</div>
          <div class="stat-label">知识图谱</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>关系边</template>
          <div class="stat-value">{{ formatNumber(stats.relations) }}</div>
          <div class="stat-label">知识图谱</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>样本状态</template>
          <div class="stat-value">{{ sampleReady ? '已生成' : '待生成' }}</div>
          <div class="stat-label">正:流失:弱:对照</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>系统状态</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户数据">
          <el-tag :type="stats.users > 0 ? 'success' : 'info'">
            {{ stats.users > 0 ? `已加载 ${formatNumber(stats.users)} 条` : '未加载' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="知识图谱">
          <el-tag :type="stats.entities > 0 ? 'success' : 'info'">
            {{ stats.entities > 0 ? `已构建 ${formatNumber(stats.entities)} 实体` : '未构建' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="样本数据">
          <el-tag :type="sampleReady ? 'success' : 'info'">
            {{ sampleReady ? '已生成' : '未生成' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="事理图谱">
          <el-tag :type="eventGraphReady ? 'success' : 'info'">
            {{ eventGraphReady ? '已生成' : '未生成' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>使用流程</template>
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="导入CSV数据" description="上传用户行为数据文件" />
        <el-step title="构建知识图谱" description="自动识别字段并构建图谱" />
        <el-step title="生成样本" description="生成训练样本数据" />
        <el-step title="智能问答" description="基于图谱回答问题" />
      </el-steps>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>快速开始</template>
          <el-space direction="vertical" style="width: 100%">
            <el-button type="primary" @click="goToImport" size="large" style="width: 100%">
              前往数据导入
            </el-button>
            <el-button @click="goToGraph" :disabled="stats.entities === 0" size="large" style="width: 100%">
              查看知识图谱
            </el-button>
            <el-button @click="goToQA" :disabled="stats.entities === 0" size="large" style="width: 100%">
              智能问答
            </el-button>
          </el-space>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>示例问题</template>
          <el-tag
            v-for="(q, i) in exampleQuestions"
            :key="i"
            @click="goToQA(q)"
            class="example-tag"
            type="info"
            effect="plain"
            :disabled="stats.entities === 0"
          >
            {{ q }}
          </el-tag>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDataStatus } from '../api'

const router = useRouter()
const stats = reactive({ users: 0, entities: 0, relations: 0 })
const sampleReady = ref(false)
const eventGraphReady = ref(false)
const exampleQuestions = [
  '喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？',
  '高收入人群对豪华轿车的品牌偏好是什么？',
  '什么样的用户容易流失？',
  '针对商务人士应该投放哪些素材？'
]

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

const formatNumber = (num) => {
  return num.toLocaleString()
}

const goToImport = () => router.push('/import')
const goToGraph = () => router.push('/graph')
const goToQA = (q) => {
  if (stats.entities === 0) {
    ElMessage.warning('请先导入数据并构建知识图谱')
    return
  }
  router.push({ path: '/qa', query: q ? { q } : {} })
}

onMounted(async () => {
  // 数据状态API已移除，统计信息通过图谱查询获取
})
</script>

<style scoped>
.stat-value {
  font-size: 32px;
  font-weight: bold;
  text-align: center;
  margin: 20px 0;
}
.stat-value.text-warning { color: #E6A23C; }
.stat-value.text-success { color: #67C23A; }
.stat-label {
  color: #909399;
  text-align: center;
  font-size: 14px;
}
.example-tag {
  margin: 5px;
  cursor: pointer;
  transition: all 0.3s;
}
.example-tag:not(.is-disabled):hover {
  transform: scale(1.05);
}
.example-tag.is-disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
