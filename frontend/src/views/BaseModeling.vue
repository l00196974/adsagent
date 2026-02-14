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
              <el-table-column prop="action" label="动作" width="100" />
              <el-table-column prop="timestamp" label="时间戳" width="180" />
              <el-table-column prop="item_id" label="商品ID" width="120" />
              <el-table-column prop="app_id" label="APP ID" width="120" />
              <el-table-column prop="media_id" label="媒体ID" width="120" />
              <el-table-column prop="poi_id" label="POI ID" width="120" />
              <el-table-column prop="duration" label="时长(秒)" width="100" />
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
              <el-table-column prop="age" label="年龄" width="80" />
              <el-table-column prop="gender" label="性别" width="80" />
              <el-table-column prop="city" label="城市" width="120" />
              <el-table-column prop="occupation" label="职业" width="150" />
              <el-table-column label="其他属性" min-width="200">
                <template #default="scope">
                  <el-tag
                    v-for="(value, key) in scope.row.properties"
                    :key="key"
                    size="small"
                    style="margin-right: 5px"
                  >
                    {{ key }}: {{ value }}
                  </el-tag>
                </template>
              </el-table-column>
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
import { Upload, Refresh } from '@element-plus/icons-vue'
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
  ElMessage.error('上传失败,请检查文件格式')
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
