<template>
  <div class="base-modeling">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>基础建模</span>
          <el-tag type="info">数据导入与管理</el-tag>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card">
        <!-- Tab 1: 行为数据 -->
        <el-tab-pane label="行为数据" name="behavior">
          <div class="tab-content">
            <div class="action-bar">
              <el-button type="success" :icon="Download" @click="downloadBehaviorTemplate">下载模板</el-button>
              <el-upload
                :action="uploadUrl + '/modeling/behavior/import'"
                :on-success="handleBehaviorUploadSuccess"
                :on-error="handleUploadError"
                :show-file-list="false"
                accept=".csv"
              >
                <el-button type="primary" :icon="Upload">导入CSV</el-button>
              </el-upload>
              <el-button @click="refreshBehaviorData" :icon="Refresh">刷新</el-button>
            </div>

            <el-table :data="behaviorData" style="width: 100%; margin-top: 20px" v-loading="behaviorLoading">
              <el-table-column prop="user_id" label="用户ID" width="120" />
              <el-table-column prop="timestamp" label="时间戳" width="180" />
              <el-table-column prop="behavior_text" label="行为描述" min-width="300" show-overflow-tooltip />
            </el-table>

            <el-pagination
              v-model:current-page="behaviorPage"
              v-model:page-size="behaviorPageSize"
              :total="behaviorTotal"
              @current-change="loadBehaviorData"
              layout="total, prev, pager, next"
              style="margin-top: 20px; justify-content: center"
            />
          </div>
        </el-tab-pane>

        <!-- Tab 2: APP标签 -->
        <el-tab-pane label="APP标签" name="app">
          <div class="tab-content">
            <div class="action-bar">
              <el-button type="success" :icon="Download" @click="downloadAppTemplate">下载模板</el-button>
              <el-upload
                :action="uploadUrl + '/modeling/app-tags/import'"
                :on-success="handleAppUploadSuccess"
                :on-error="handleUploadError"
                :show-file-list="false"
                accept=".csv"
              >
                <el-button type="primary" :icon="Upload">导入APP列表</el-button>
              </el-upload>
              <el-button @click="refreshAppTags" :icon="Refresh">刷新</el-button>
              <el-tag v-if="appTaggingStatus !== 'idle'" :type="getStatusType(appTaggingStatus)">
                {{ getStatusText(appTaggingStatus) }}
              </el-tag>
            </div>

            <el-table :data="appTagsData" style="width: 100%; margin-top: 20px" v-loading="appLoading">
              <el-table-column prop="app_id" label="APP ID" width="150" />
              <el-table-column prop="app_name" label="APP名称" width="200" />
              <el-table-column prop="category" label="分类" width="150" />
              <el-table-column label="标签" min-width="200">
                <template #default="scope">
                  <el-tag
                    v-for="tag in scope.row.tags"
                    :key="tag"
                    size="small"
                    style="margin-right: 5px"
                  >
                    {{ tag }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="LLM生成" width="100">
                <template #default="scope">
                  <el-tag :type="scope.row.llm_generated ? 'success' : 'info'" size="small">
                    {{ scope.row.llm_generated ? '是' : '否' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>

            <el-pagination
              v-model:current-page="appPage"
              v-model:page-size="appPageSize"
              :total="appTotal"
              @current-change="loadAppTags"
              layout="total, prev, pager, next"
              style="margin-top: 20px; justify-content: center"
            />
          </div>
        </el-tab-pane>

        <!-- Tab 3: 媒体标签 -->
        <el-tab-pane label="媒体标签" name="media">
          <div class="tab-content">
            <div class="action-bar">
              <el-button type="success" :icon="Download" @click="downloadMediaTemplate">下载模板</el-button>
              <el-upload
                :action="uploadUrl + '/modeling/media-tags/import'"
                :on-success="handleMediaUploadSuccess"
                :on-error="handleUploadError"
                :show-file-list="false"
                accept=".csv"
              >
                <el-button type="primary" :icon="Upload">导入媒体列表</el-button>
              </el-upload>
              <el-button @click="refreshMediaTags" :icon="Refresh">刷新</el-button>
              <el-tag v-if="mediaTaggingStatus !== 'idle'" :type="getStatusType(mediaTaggingStatus)">
                {{ getStatusText(mediaTaggingStatus) }}
              </el-tag>
            </div>

            <el-table :data="mediaTagsData" style="width: 100%; margin-top: 20px" v-loading="mediaLoading">
              <el-table-column prop="media_id" label="媒体ID" width="150" />
              <el-table-column prop="media_name" label="媒体名称" width="200" />
              <el-table-column prop="media_type" label="类型" width="150" />
              <el-table-column label="标签" min-width="200">
                <template #default="scope">
                  <el-tag
                    v-for="tag in scope.row.tags"
                    :key="tag"
                    size="small"
                    style="margin-right: 5px"
                  >
                    {{ tag }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="LLM生成" width="100">
                <template #default="scope">
                  <el-tag :type="scope.row.llm_generated ? 'success' : 'info'" size="small">
                    {{ scope.row.llm_generated ? '是' : '否' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>

            <el-pagination
              v-model:current-page="mediaPage"
              v-model:page-size="mediaPageSize"
              :total="mediaTotal"
              @current-change="loadMediaTags"
              layout="total, prev, pager, next"
              style="margin-top: 20px; justify-content: center"
            />
          </div>
        </el-tab-pane>

        <!-- Tab 4: 用户画像 -->
        <el-tab-pane label="用户画像" name="profile">
          <div class="tab-content">
            <div class="action-bar">
              <el-button type="success" :icon="Download" @click="downloadProfileTemplate">下载模板</el-button>
              <el-upload
                :action="uploadUrl + '/modeling/profiles/import'"
                :on-success="handleProfileUploadSuccess"
                :on-error="handleUploadError"
                :show-file-list="false"
                accept=".csv"
              >
                <el-button type="primary" :icon="Upload">导入用户画像</el-button>
              </el-upload>
              <el-button @click="refreshProfiles" :icon="Refresh">刷新</el-button>
            </div>

            <el-table :data="profilesData" style="width: 100%; margin-top: 20px" v-loading="profileLoading">
              <el-table-column prop="user_id" label="用户ID" width="120" />
              <el-table-column prop="profile_text" label="用户画像" min-width="400" show-overflow-tooltip />
            </el-table>

            <el-pagination
              v-model:current-page="profilePage"
              v-model:page-size="profilePageSize"
              :total="profileTotal"
              @current-change="loadProfiles"
              layout="total, prev, pager, next"
              style="margin-top: 20px; justify-content: center"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Refresh, Download } from '@element-plus/icons-vue'
import axios from 'axios'

const uploadUrl = '/api/v1'
const activeTab = ref('behavior')

// 行为数据
const behaviorData = ref([])
const behaviorLoading = ref(false)
const behaviorPage = ref(1)
const behaviorPageSize = ref(20)
const behaviorTotal = ref(0)

// APP标签
const appTagsData = ref([])
const appLoading = ref(false)
const appPage = ref(1)
const appPageSize = ref(20)
const appTotal = ref(0)
const appTaggingStatus = ref('idle')

// 媒体标签
const mediaTagsData = ref([])
const mediaLoading = ref(false)
const mediaPage = ref(1)
const mediaPageSize = ref(20)
const mediaTotal = ref(0)
const mediaTaggingStatus = ref('idle')

// 用户画像
const profilesData = ref([])
const profileLoading = ref(false)
const profilePage = ref(1)
const profilePageSize = ref(20)
const profileTotal = ref(0)

// 加载行为数据
const loadBehaviorData = async () => {
  behaviorLoading.value = true
  try {
    const offset = (behaviorPage.value - 1) * behaviorPageSize.value
    const res = await axios.get('/api/v1/modeling/behavior/list', {
      params: { limit: behaviorPageSize.value, offset }
    })
    if (res.data.code === 0) {
      behaviorData.value = res.data.data.items
      behaviorTotal.value = res.data.data.total
    }
  } catch (e) {
    console.error('加载行为数据失败', e)
  } finally {
    behaviorLoading.value = false
  }
}

// 加载APP标签
const loadAppTags = async () => {
  appLoading.value = true
  try {
    const offset = (appPage.value - 1) * appPageSize.value
    const res = await axios.get('/api/v1/modeling/app-tags/list', {
      params: { limit: appPageSize.value, offset }
    })
    if (res.data.code === 0) {
      appTagsData.value = res.data.data.items
      appTotal.value = res.data.data.total
    }
  } catch (e) {
    console.error('加载APP标签失败', e)
  } finally {
    appLoading.value = false
  }
}

// 加载媒体标签
const loadMediaTags = async () => {
  mediaLoading.value = true
  try {
    const offset = (mediaPage.value - 1) * mediaPageSize.value
    const res = await axios.get('/api/v1/modeling/media-tags/list', {
      params: { limit: mediaPageSize.value, offset }
    })
    if (res.data.code === 0) {
      mediaTagsData.value = res.data.data.items
      mediaTotal.value = res.data.data.total
    }
  } catch (e) {
    console.error('加载媒体标签失败', e)
  } finally {
    mediaLoading.value = false
  }
}

// 加载用户画像
const loadProfiles = async () => {
  profileLoading.value = true
  try {
    const offset = (profilePage.value - 1) * profilePageSize.value
    const res = await axios.get('/api/v1/modeling/profiles/list', {
      params: { limit: profilePageSize.value, offset }
    })
    if (res.data.code === 0) {
      profilesData.value = res.data.data.items
      profileTotal.value = res.data.data.total
    }
  } catch (e) {
    console.error('加载用户画像失败', e)
  } finally {
    profileLoading.value = false
  }
}

// 上传成功处理
const handleBehaviorUploadSuccess = (response) => {
  if (response.code === 0) {
    ElMessage.success(response.message)
    loadBehaviorData()
  } else {
    ElMessage.error(response.message || '导入失败')
  }
}

const handleAppUploadSuccess = (response) => {
  if (response.code === 0) {
    ElMessage.success(response.message)
    loadAppTags()
    appTaggingStatus.value = response.data.tagging_status || 'idle'
  } else {
    ElMessage.error(response.message || '导入失败')
  }
}

const handleMediaUploadSuccess = (response) => {
  if (response.code === 0) {
    ElMessage.success(response.message)
    loadMediaTags()
    mediaTaggingStatus.value = response.data.tagging_status || 'idle'
  } else {
    ElMessage.error(response.message || '导入失败')
  }
}

const handleProfileUploadSuccess = (response) => {
  if (response.code === 0) {
    ElMessage.success(response.message)
    loadProfiles()
  } else {
    ElMessage.error(response.message || '导入失败')
  }
}

const handleUploadError = (error) => {
  console.error('上传失败', error)
  
  let errorMessage = '上传失败,请检查文件格式'
  
  if (error.response) {
    const response = error.response
    if (response.data && response.data.detail) {
      errorMessage = `上传失败: ${response.data.detail}`
    } else if (response.status === 422) {
      errorMessage = '文件格式错误，请确保上传CSV文件'
    } else if (response.status === 500) {
      errorMessage = '服务器处理失败，请查看后端日志'
    } else if (response.status === 0) {
      errorMessage = '无法连接到服务器，请检查后端是否启动'
    }
  } else if (error.message) {
    errorMessage = `上传失败: ${error.message}`
  }
  
  ElMessage.error(errorMessage)
}

// 刷新数据
const refreshBehaviorData = () => loadBehaviorData()
const refreshAppTags = () => loadAppTags()
const refreshMediaTags = () => loadMediaTags()
const refreshProfiles = () => loadProfiles()

// 状态显示
const getStatusType = (status) => {
  const map = {
    idle: 'info',
    pending: 'warning',
    in_progress: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    idle: '空闲',
    pending: '待处理',
    in_progress: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

// 下载模板
const downloadBehaviorTemplate = () => {
  const csvContent = `user_id,timestamp,behavior_text
user_001,2026-01-01 10:00:00,在微信上浏览了BMW 7系的广告，停留了5分钟
user_001,2026-01-01 10:30:00,在汽车之家APP搜索"豪华轿车"
user_001,2026-01-02 14:00:00,在4S店停留了2小时，试驾了BMW 7系
user_002,2026-01-01 11:00:00,在抖音上观看了奔驰S级的视频广告
user_002,2026-01-01 15:30:00,在懂车帝APP上对比了BMW 7系和奔驰S级
user_003,2026-01-03 09:00:00,在高德地图上搜索附近的BMW 4S店
user_003,2026-01-03 10:30:00,在BMW官网配置了一台7系，总价120万`
  downloadCSV(csvContent, 'behavior_template.csv')
}

const downloadAppTemplate = () => {
  const csvContent = `app_id,app_name,category
app_001,微信,社交
app_002,抖音,短视频
app_003,淘宝,电商
app_004,高德地图,导航
app_005,美团,生活服务`
  downloadCSV(csvContent, 'app_template.csv')
}

const downloadMediaTemplate = () => {
  const csvContent = `media_id,media_name,media_type
media_001,今日头条,新闻资讯
media_002,腾讯视频,视频平台
media_003,网易云音乐,音乐平台
media_004,知乎,问答社区
media_005,小红书,社交电商`
  downloadCSV(csvContent, 'media_template.csv')
}

const downloadProfileTemplate = () => {
  const csvContent = `user_id,profile_text
user_001,28岁男性，北京工程师，年收入50万，本科学历，喜欢高尔夫和科技产品，关注BMW和奔驰
user_002,35岁女性，上海设计师，年收入30万，硕士学历，喜欢艺术和旅游，偏好奥迪和沃尔沃
user_003,42岁男性，深圳企业高管，年收入100万+，本科学历，经常出差，关注豪华商务车型
user_004,25岁女性，广州在读研究生，无固定收入，喜欢时尚和音乐，关注入门级豪华车
user_005,38岁男性，杭州创业者，年收入80万，硕士学历，科技爱好者，关注新能源豪华车`
  downloadCSV(csvContent, 'profile_template.csv')
}

const downloadCSV = (content, filename) => {
  const blob = new Blob(['\ufeff' + content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success(`模板 ${filename} 下载成功`)
}

onMounted(() => {
  loadBehaviorData()
  loadAppTags()
  loadMediaTags()
  loadProfiles()
})
</script>

<style scoped>
.base-modeling {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tab-content {
  padding: 20px;
}

.action-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
