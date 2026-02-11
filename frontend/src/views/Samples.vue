<template>
  <div class="samples">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>样本管理</span>
          <el-button type="primary" @click="handleGenerateSamples" :loading="loading">
            生成样本
          </el-button>
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
    
    <el-card style="margin-top: 20px" v-if="sampleData">
      <template #header>典型案例</template>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="正样本" name="positive">
          <el-table :data="typicalCases.positive || []" size="small">
            <el-table-column prop="user_id" label="用户ID" width="100" />
            <el-table-column prop="profile.age_bucket" label="年龄" width="80" />
            <el-table-column prop="profile.income" label="收入" width="80" />
            <el-table-column prop="profile.city" label="城市" width="80" />
            <el-table-column prop="intent" label="意向" width="60" />
            <el-table-column prop="stage" label="阶段" width="80" />
            <el-table-column label="兴趣" min-width="150">
              <template #default="{ row }">
                <el-tag v-for="i in row.interests" :key="i" size="small" type="info">
                  {{ i }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="流失样本" name="churn">
          <el-table :data="typicalCases.churn || []" size="small">
            <el-table-column prop="user_id" label="用户ID" width="100" />
            <el-table-column prop="profile.age_bucket" label="年龄" width="80" />
            <el-table-column prop="profile.income" label="收入" width="80" />
            <el-table-column prop="brand.primary_brand" label="品牌" width="80" />
            <el-table-column prop="stage" label="阶段" width="80" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="弱兴趣样本" name="weak">
          <el-table :data="typicalCases.weak || []" size="small">
            <el-table-column prop="user_id" label="用户ID" width="100" />
            <el-table-column prop="profile.income" label="收入" width="80" />
            <el-table-column prop="intent" label="意向" width="60" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="空白对照" name="control">
          <el-table :data="typicalCases.control || []" size="small">
            <el-table-column prop="user_id" label="用户ID" width="100" />
            <el-table-column prop="profile.income" label="收入" width="80" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { doGenerateSamples } from '../api'

const formRef = ref(null)
const loading = ref(false)
const sampleData = ref(null)
const sampleStatistics = ref({})
const typicalCases = ref({})
const activeTab = ref('positive')

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

const handleGenerateSamples = async () => {
  if (!formRef.value) return
  
  formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const res = await doGenerateSamples({
        industry: form.industry,
        total_count: form.total_count,
        ratios: form.ratios
      })
      
      sampleData.value = res.data
      
      const samples = res.data  // samples 直接在 data 下
      typicalCases.value = {
        positive: samples.positive?.slice(0, 5) || [],
        churn: samples.churn?.slice(0, 5) || [],
        weak: samples.weak?.slice(0, 5) || [],
        control: samples.control?.slice(0, 5) || []
      }
      
      sampleStatistics.value = res.data.statistics || {}
      
      ElMessage.success('样本生成成功')
    } catch (e) {
      ElMessage.error('生成失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
