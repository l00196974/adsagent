<template>
  <div class="event-extraction">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>事件抽象</span>
          <div>
            <el-button type="primary" @click="handleBatchExtract" :loading="batchLoading">
              批量事件抽象
            </el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="tableData" style="width: 100%" v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="150" />

        <el-table-column label="行为序列" width="200">
          <template #default="scope">
            <el-link type="primary" @click="showSequenceDetail(scope.row)">
              {{ scope.row.behavior_count }} 条
            </el-link>
          </template>
        </el-table-column>

        <el-table-column label="事理序列" width="200">
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
            <el-tag v-if="scope.row.has_events" type="success">已抽象</el-tag>
            <el-tag v-else type="info">未抽象</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button
              v-if="scope.row.has_events"
              size="small"
              @click="showSequenceDetail(scope.row)"
            >
              查看
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
      :title="`用户 ${selectedUser?.user_id} 的事件序列`"
      width="60%"
    >
      <div v-if="selectedUser">
        <el-divider content-position="left">原始行为序列</el-divider>
        <el-scrollbar max-height="300px">
          <ol>
            <li v-for="(behavior, index) in selectedUser.behavior_sequence" :key="index">
              {{ behavior }}
            </li>
          </ol>
        </el-scrollbar>

        <el-divider content-position="left">抽象事理序列</el-divider>
        <el-scrollbar max-height="300px">
          <ol v-if="selectedUser.event_sequence.length > 0">
            <li v-for="(event, index) in selectedUser.event_sequence" :key="index">
              {{ event }}
            </li>
          </ol>
          <el-empty v-else description="暂无事理序列" :image-size="100" />
        </el-scrollbar>
      </div>

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const loading = ref(false)
const batchLoading = ref(false)
const tableData = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const detailDialogVisible = ref(false)
const selectedUser = ref(null)
const extractingUsers = reactive({})

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

// 批量事件抽象
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
    const response = await axios.post('/api/v1/events/extract', {
      user_ids: null
    })

    if (response.data.code === 0) {
      const { total_users, success_count, failed_count } = response.data.data
      ElMessage.success(
        `批量事件抽象完成: 成功 ${success_count}/${total_users}, 失败 ${failed_count}/${total_users}`
      )
      await loadData()
    } else {
      ElMessage.error('批量事件抽象失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量事件抽象失败:', error)
      ElMessage.error('批量事件抽象失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    batchLoading.value = false
  }
}

// 单用户事件抽象
const handleSingleExtract = async (userId) => {
  try {
    extractingUsers[userId] = true
    const response = await axios.post(`/api/v1/events/extract/${userId}`)

    if (response.data.code === 0) {
      ElMessage.success(`用户 [${userId}] 事件抽象完成`)
      await loadData()
    } else {
      ElMessage.error(`用户 [${userId}] 事件抽象失败`)
    }
  } catch (error) {
    console.error(`用户 [${userId}] 事件抽象失败:`, error)
    ElMessage.error(`事件抽象失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    extractingUsers[userId] = false
  }
}

// 显示序列详情
const showSequenceDetail = (row) => {
  selectedUser.value = row
  detailDialogVisible.value = true
}

onMounted(() => {
  loadData()
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

ol {
  padding-left: 20px;
  line-height: 2;
}

ol li {
  margin-bottom: 8px;
}
</style>
