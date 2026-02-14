<template>
  <div class="data-import-container">
    <el-card class="header-card">
      <h2>数据导入</h2>
      <p>上传CSV文件导入真实用户行为数据，系统将自动识别字段并构建知识图谱</p>
    </el-card>

    <el-card class="upload-card">
      <h3>快速导入测试数据（100用户）</h3>
      <el-alert
        title="使用预生成的测试数据"
        type="info"
        description="点击下方按钮直接导入100个用户的完整测试数据，包含所有11种关系类型"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-button
        type="success"
        size="large"
        @click="handleImportSeparatedCSV"
        :loading="importingSeparated"
        style="width: 100%"
      >
        <el-icon><Upload /></el-icon>
        导入测试数据（100用户 + 891关系）
      </el-button>
    </el-card>

    <el-card class="upload-card" style="margin-top: 20px">
      <h3>上传自定义CSV文件</h3>
      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="fileList"
        multiple
        accept=".csv"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持上传多个CSV文件，每个文件最大10MB，单次最多20个文件
          </div>
        </template>
      </el-upload>

      <div class="upload-actions">
        <el-button type="primary" @click="handleUpload" :loading="uploading" :disabled="fileList.length === 0">
          开始导入
        </el-button>
        <el-button @click="handleClear" :disabled="fileList.length === 0">
          清空列表
        </el-button>
      </div>
    </el-card>

    <el-card v-if="importResult" class="result-card">
      <h3>导入结果</h3>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="上传文件数">{{ importResult.total_files }}</el-descriptions-item>
        <el-descriptions-item label="成功文件数">{{ importResult.successful_files }}</el-descriptions-item>
        <el-descriptions-item label="总记录数">{{ importResult.total_records }}</el-descriptions-item>
        <el-descriptions-item label="去重后记录数">{{ importResult.unique_records }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <h4>文件处理详情</h4>
      <el-table :data="importResult.file_results" style="width: 100%">
        <el-table-column prop="filename" label="文件名" width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">
              {{ scope.row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="record_count" label="记录数" width="100" />
        <el-table-column label="字段识别">
          <template #default="scope">
            <el-popover v-if="scope.row.field_statistics" placement="top" width="400" trigger="hover">
              <template #reference>
                <el-button size="small" type="text">
                  识别 {{ scope.row.field_statistics.recognized_fields }}/{{ scope.row.field_statistics.total_fields }} 个字段
                </el-button>
              </template>
              <div>
                <p><strong>字段映射:</strong></p>
                <ul>
                  <li v-for="(target, source) in scope.row.field_mapping" :key="source">
                    {{ source }} → {{ target }}
                  </li>
                </ul>
              </div>
            </el-popover>
            <span v-else-if="scope.row.error">{{ scope.row.error }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <div class="action-buttons">
        <el-button type="primary" @click="handleBuildGraph" :loading="building">
          构建知识图谱
        </el-button>
        <el-button type="success" @click="handleBuildEventGraph" :loading="buildingEvent">
          生成事理图谱
        </el-button>
      </div>
    </el-card>

    <el-card v-if="graphResult" class="graph-result-card">
      <h3>知识图谱构建结果</h3>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="实体数量">{{ graphResult.stats.total_entities }}</el-descriptions-item>
        <el-descriptions-item label="关系数量">{{ graphResult.stats.total_relations }}</el-descriptions-item>
        <el-descriptions-item label="处理批次">{{ graphResult.progress.total_batches }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 20px">
        <el-button type="primary" @click="$router.push('/graph')">查看图谱</el-button>
      </div>
    </el-card>

    <el-card v-if="eventGraphResult" class="event-graph-result-card">
      <h3>事理图谱生成结果</h3>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="节点数量">{{ eventGraphResult.nodes.length }}</el-descriptions-item>
        <el-descriptions-item label="关系数量">{{ eventGraphResult.edges.length }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <h4>关键洞察</h4>
      <ul>
        <li v-for="(insight, index) in eventGraphResult.insights" :key="index">{{ insight }}</li>
      </ul>

      <h4>投放建议</h4>
      <ul>
        <li v-for="(rec, index) in eventGraphResult.recommendations" :key="index">{{ rec }}</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Upload } from '@element-plus/icons-vue'
import { importBatchCSV, importSeparatedCSV, buildKnowledgeGraph, buildEventGraph } from '../api'
import { useRouter } from 'vue-router'

const router = useRouter()
const uploadRef = ref()
const fileList = ref([])
const uploading = ref(false)
const importingSeparated = ref(false)
const building = ref(false)
const buildingEvent = ref(false)
const importResult = ref(null)
const graphResult = ref(null)
const eventGraphResult = ref(null)
const importedUsers = ref([])

const handleFileChange = (file, files) => {
  fileList.value = files
}

const handleClear = () => {
  fileList.value = []
  uploadRef.value.clearFiles()
  importResult.value = null
  graphResult.value = null
  eventGraphResult.value = null
  importedUsers.value = []
}

const handleImportSeparatedCSV = async () => {
  importingSeparated.value = true
  try {
    const result = await importSeparatedCSV()

    if (result.code === 0) {
      ElMessage.success(result.data.message || '导入成功')

      // 显示导入结果
      graphResult.value = {
        stats: result.data.stats,
        progress: {
          total_batches: 1
        }
      }

      // 自动跳转到图谱页面
      setTimeout(() => {
        router.push('/graph')
      }, 2000)
    } else {
      ElMessage.error(result.message || '导入失败')
    }
  } catch (error) {
    console.error('导入分离CSV失败:', error)
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  } finally {
    importingSeparated.value = false
  }
}

const handleUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  if (fileList.value.length > 20) {
    ElMessage.warning('单次最多上传20个文件')
    return
  }

  uploading.value = true
  const formData = new FormData()

  fileList.value.forEach(file => {
    formData.append('files', file.raw)
  })

  try {
    const result = await importBatchCSV(formData)
    importResult.value = result.data
    importedUsers.value = result.data.users
    ElMessage.success(result.message || '导入成功')
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
}

const handleBuildGraph = async () => {
  if (!importedUsers.value || importedUsers.value.length === 0) {
    ElMessage.warning('没有可用的用户数据')
    return
  }

  building.value = true
  try {
    // 调用构建知识图谱API（需要添加新的API端点）
    const response = await fetch('/api/v1/graphs/knowledge/build-from-csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ users: importedUsers.value })
    })
    const result = await response.json()

    if (result.code === 0) {
      graphResult.value = result.data
      ElMessage.success('知识图谱构建成功')
    } else {
      ElMessage.error(result.message || '构建失败')
    }
  } catch (error) {
    console.error('构建知识图谱失败:', error)
    ElMessage.error('构建失败，请稍后重试')
  } finally {
    building.value = false
  }
}

const handleBuildEventGraph = async () => {
  if (!importedUsers.value || importedUsers.value.length === 0) {
    ElMessage.warning('没有可用的用户数据')
    return
  }

  buildingEvent.value = true
  try {
    // 调用生成事理图谱API（需要添加新的API端点）
    const response = await fetch('/api/v1/qa/event-graph/build-from-csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ users: importedUsers.value })
    })
    const result = await response.json()

    if (result.code === 0) {
      eventGraphResult.value = result.data
      ElMessage.success('事理图谱生成成功')
    } else {
      ElMessage.error(result.message || '生成失败')
    }
  } catch (error) {
    console.error('生成事理图谱失败:', error)
    ElMessage.error('生成失败，请稍后重试')
  } finally {
    buildingEvent.value = false
  }
}
</script>

<style scoped>
.data-import-container {
  padding: 20px;
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
  color: #606266;
}

.upload-card {
  margin-bottom: 20px;
}

.upload-card h3 {
  margin: 0 0 20px 0;
}

.upload-demo {
  margin-bottom: 20px;
}

.upload-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.result-card,
.graph-result-card,
.event-graph-result-card {
  margin-bottom: 20px;
}

.result-card h3,
.graph-result-card h3,
.event-graph-result-card h3 {
  margin: 0 0 20px 0;
}

.result-card h4,
.event-graph-result-card h4 {
  margin: 20px 0 10px 0;
  color: #606266;
}

.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.event-graph-result-card ul {
  padding-left: 20px;
}

.event-graph-result-card li {
  margin: 8px 0;
  color: #606266;
}
</style>
