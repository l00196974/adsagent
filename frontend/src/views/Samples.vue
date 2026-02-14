<template>
  <div class="samples">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>样本管理</span>
          <div class="header-actions">
            <el-button type="success" @click="showImportDialog = true" :loading="importing">
              导入CSV
            </el-button>
            <el-button type="primary" @click="handleGenerateSamples" :loading="loading">
              生成样本
            </el-button>
          </div>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="行业" prop="industry">
              <el-select v-model="form.industry" placeholder="选择行业">
                <el-option label="汽车" value="汽车" />
                <el-option label="美妆" value="美妆" />
                <el-option label="电商" value="电商" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="样本数量" prop="total_count">
              <el-input-number v-model="form.total_count" :min="100" :max="10000" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-divider content-position="left">样本比例配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="正样本">
              <el-input-number v-model="form.ratios.positive" :min="1" :max="10" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="流失样本">
              <el-input-number v-model="form.ratios.churn" :min="1" :max="50" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="弱兴趣样本">
              <el-input-number v-model="form.ratios.weak" :min="1" :max="50" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="空白对照">
              <el-input-number v-model="form.ratios.control" :min="1" :max="50" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item>
          <el-tag type="info">
            当前比例: 正:{{ form.ratios.positive }} : 
            流失:{{ form.ratios.churn }} : 
            弱兴趣:{{ form.ratios.weak }} : 
            对照:{{ form.ratios.control }}
            (总计: {{ totalRatio }})
          </el-tag>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-row :gutter="20" style="margin-top: 20px" v-if="sampleData">
      <el-col :span="12">
        <el-card>
          <template #header>样本分布</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="正样本">
              {{ sampleStatistics.positive?.count || 0 }} 人
            </el-descriptions-item>
            <el-descriptions-item label="流失样本">
              {{ sampleStatistics.churn?.count || 0 }} 人
            </el-descriptions-item>
            <el-descriptions-item label="弱兴趣样本">
              {{ sampleStatistics.weak?.count || 0 }} 人
            </el-descriptions-item>
            <el-descriptions-item label="空白对照">
              {{ sampleStatistics.control?.count || 0 }} 人
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>正样本收入分布</template>
          <div v-if="sampleStatistics.positive?.income_distribution">
            <div v-for="(count, income) in sampleStatistics.positive.income_distribution" :key="income">
              <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                <span>{{ income }}</span>
                <span>{{ count }} 人 ({{ (count / sampleStatistics.positive.count * 100).toFixed(1) }}%)</span>
              </div>
              <el-progress :percentage="count / sampleStatistics.positive.count * 100" :show-text="false" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 全量样本表格 -->
    <el-card style="margin-top: 20px" v-if="sampleData">
      <template #header>
        <div class="card-header">
          <span>全量样本数据</span>
          <div class="header-actions">
            <el-select v-model="viewType" placeholder="选择查看类型" style="width: 150px" @change="currentPage = 1">
              <el-option label="正样本" value="positive" />
              <el-option label="流失样本" value="churn" />
              <el-option label="弱兴趣样本" value="weak" />
              <el-option label="空白对照" value="control" />
              <el-option label="全部" value="all" />
            </el-select>
            <el-button type="primary" size="small" @click="exportSamples">导出CSV</el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="paginatedSamples" 
        v-loading="loading"
        stripe
        border
        max-height="500"
        style="width: 100%"
      >
        <el-table-column prop="user_id" label="用户ID" width="100" fixed />
        <el-table-column label="人口属性" min-width="200">
          <template #default="{ row }">
            <span>{{ row.profile?.age_bucket || row.demographics?.age_bucket || '-' }}</span> /
            <span>{{ row.profile?.income || row.demographics?.income_level || '-' }}</span> /
            <span>{{ row.profile?.city || row.demographics?.city_tier || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="品牌偏好" min-width="150">
          <template #default="{ row }">
            <el-tag size="small" type="warning">{{ row.brand?.primary_brand || row.brand_affinity?.primary_brand || '-' }}</el-tag>
            <span style="margin-left: 8px;">{{ ((row.brand?.brand_score || row.brand_affinity?.brand_score || 0) * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="兴趣标签" min-width="200">
          <template #default="{ row }">
            <el-tag 
              v-for="interest in (row.interests || []).slice(0, 4)" 
              :key="interest" 
              size="small" 
              type="info"
              style="margin-right: 4px;"
            >
              {{ interest }}
            </el-tag>
            <el-tag v-if="(row.interests || []).length > 4" size="small" type="info">
              +{{ (row.interests || []).length - 4 }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="intent" label="购买意向" width="100">
          <template #default="{ row }">
            <el-tag :type="getIntentType(row.intent || row.purchase_intent)">
              {{ row.intent || row.purchase_intent || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stage" label="生命周期" width="100">
          <template #default="{ row }">
            <el-tag :type="getStageType(row.stage || row.lifecycle_stage)">
              {{ row.stage || row.lifecycle_stage || '-' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container" v-if="currentSamples.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="currentSamples.length"
          layout="total, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
        <span class="pagination-info">
          显示 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, currentSamples.length) }} 条，
          共 {{ currentSamples.length }} 条
        </span>
      </div>
    </el-card>
    
    <!-- CSV导入对话框 -->
    <el-dialog v-model="showImportDialog" title="导入用户数据" width="500px">
      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".csv"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽CSV文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            <p>支持字段: user_id, age, age_bucket, gender, income_level, city_tier, occupation, interests, primary_brand, brand_score, purchase_intent, lifecycle_stage</p>
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleImportCSV" :loading="importing" :disabled="!selectedFile">
          导入并分析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { generateSamples, importCSV, inferUsers } from '../api'

const formRef = ref(null)
const uploadRef = ref(null)
const loading = ref(false)
const importing = ref(false)
const sampleData = ref(null)
const sampleStatistics = ref({})
const showImportDialog = ref(false)
const selectedFile = ref(null)
const viewType = ref('positive')
const currentPage = ref(1)
const pageSize = ref(50)
const inferenceResults = ref({})

const form = reactive({
  industry: '汽车',
  total_count: 1000,
  ratios: {
    positive: 1,
    churn: 10,
    weak: 5,
    control: 5
  }
})

const rules = {
  industry: [{ required: true, message: '请选择行业', trigger: 'change' }],
  total_count: [{ required: true, message: '请输入样本数量', trigger: 'blur' }]
}

const totalRatio = computed(() => {
  return form.ratios.positive + form.ratios.churn + form.ratios.weak + form.ratios.control
})

// 获取当前视图的样本数据
const currentSamples = computed(() => {
  if (!sampleData.value) return []
  
  if (viewType.value === 'all') {
    return [
      ...(sampleData.value.positive || []),
      ...(sampleData.value.churn || []),
      ...(sampleData.value.weak || []),
      ...(sampleData.value.control || [])
    ]
  }
  
  return sampleData.value[viewType.value] || []
})

// 分页数据
const paginatedSamples = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return currentSamples.value.slice(start, end)
})

const handleGenerateSamples = async () => {
  if (!formRef.value) return
  
  formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const res = await generateSamples({
        industry: form.industry,
        total_count: form.total_count,
        ratios: form.ratios
      })
      
      sampleData.value = res.data
      
      // 计算统计信息
      const stats = {}
      for (const type of ['positive', 'churn', 'weak', 'control']) {
        const data = res.data[type] || []
        stats[type] = computeTypeStats(data)
      }
      sampleStatistics.value = stats
      
      // 重置分页
      currentPage.value = 1
      viewType.value = 'positive'
      
      ElMessage.success(`样本生成成功，共 ${dataSummary(res.data)} 条`)
    } catch (e) {
      ElMessage.error('生成失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      loading.value = false
    }
  })
}

const computeTypeStats = (data) => {
  if (!data.length) return { count: 0 }
  
  const incomes = data.map(u => u.profile?.income || u.demographics?.income_level).filter(Boolean)
  const incomeDist = {}
  incomes.forEach(i => incomeDist[i] = (incomeDist[i] || 0) + 1)
  
  const interests = data.flatMap(u => u.interests || []).filter(Boolean)
  const interestFreq = {}
  interests.forEach(i => interestFreq[i] = (interestFreq[i] || 0) + 1)
  
  const brands = data.map(u => u.brand?.primary_brand || u.brand_affinity?.primary_brand).filter(Boolean)
  const brandDist = {}
  brands.forEach(b => brandDist[b] = (brandDist[b] || 0) + 1)
  
  return {
    count: data.length,
    income_distribution: incomeDist,
    top_interests: Object.entries(interestFreq).sort((a, b) => b[1] - a[1]),
    brand_distribution: brandDist
  }
}

const dataSummary = (data) => {
  return (data.positive?.length || 0) + 
         (data.churn?.length || 0) + 
         (data.weak?.length || 0) + 
         (data.control?.length || 0)
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleImportCSV = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择CSV文件')
    return
  }
  
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const res = await importCSV(formData)
    
    if (res.code === 0) {
      // 存储样本数据
      sampleData.value = res.data.samples
      sampleStatistics.value = res.data.statistics
      
      // 执行推理
      const allUsers = [
        ...(res.data.samples.positive || []),
        ...(res.data.samples.churn || []),
        ...(res.data.samples.weak || []),
        ...(res.data.samples.control || [])
      ]
      
      const inferRes = await inferUsers({ users: allUsers })
      if (inferRes.code === 0) {
        inferenceResults.value = {}
        inferRes.data.results.forEach(r => {
          inferenceResults.value[r.user_id] = r
        })
      }
      
      showImportDialog.value = false
      currentPage.value = 1
      viewType.value = 'positive'
      
      ElMessage.success(`导入成功，共 ${res.data.total_count} 条用户数据`)
    }
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    importing.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
}

const getIntentType = (intent) => {
  const map = { '高': 'success', '中': 'warning', '无': 'info' }
  return map[intent] || 'info'
}

const getStageType = (stage) => {
  const map = { '转化': 'success', '意向': 'warning', '流失': 'danger', '空白': 'info' }
  return map[stage] || 'info'
}

const exportSamples = () => {
  const data = currentSamples.value
  if (!data.length) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  
  const headers = ['user_id', '年龄', '收入', '城市', '品牌', '兴趣', '意向', '阶段']
  const rows = data.map(u => [
    u.user_id,
    u.profile?.age_bucket || u.demographics?.age_bucket || '',
    u.profile?.income || u.demographics?.income_level || '',
    u.profile?.city || u.demographics?.city_tier || '',
    u.brand?.primary_brand || u.brand_affinity?.primary_brand || '',
    (u.interests || []).join(';'),
    u.intent || u.purchase_intent || '',
    u.stage || u.lifecycle_stage || ''
  ])
  
  const csvContent = [headers, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `samples_${viewType.value}_${Date.now()}.csv`
  link.click()
  
  ElMessage.success('导出成功')
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
