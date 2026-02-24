import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = '/api/v1'

// 全局错误处理拦截器
axios.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.message || error.message || '操作失败，请稍后重试'
    ElMessage.error(message)
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 请求超时设置
axios.defaults.timeout = 30000

export const loadUserData = (params) => {
  return axios.post(`${BASE_URL}/graphs/data/load`, params)
    .then(r => r.data)
}

export const getDataStatus = () => {
  return axios.get(`${BASE_URL}/graphs/data/status`)
    .then(r => r.data)
}

// Mock数据构建接口已移除，请使用 buildKnowledgeGraphFromCSV

export const importSeparatedCSV = () => {
  return axios.post(`${BASE_URL}/csv/import-separated-csv`)
    .then(r => r.data)
}

export const getBuildProgress = () => {
  return axios.get(`${BASE_URL}/graphs/knowledge/progress`)
    .then(r => r.data)
}

export const queryGraph = (entityName = null, entityType = null, depth = 2) => {
  const params = new URLSearchParams()
  if (entityName) params.append('entity_name', entityName)
  if (entityType) params.append('entity_type', entityType)
  params.append('depth', depth)
  return axios.get(`${BASE_URL}/graphs/knowledge/query?${params}`)
    .then(r => r.data)
}

export const searchEntities = (keyword = null, entityType = null, limit = 20) => {
  const params = new URLSearchParams()
  if (keyword) params.append('keyword', keyword)
  if (entityType) params.append('entity_type', entityType)
  params.append('limit', limit)
  return axios.get(`${BASE_URL}/graphs/knowledge/search?${params}`)
    .then(r => r.data)
}

export const expandEntity = (entityId, depth = 2, maxNodes = 50) => {
  return axios.get(`${BASE_URL}/graphs/knowledge/expand/${entityId}`, {
    params: { depth, max_nodes: maxNodes }
  }).then(r => r.data)
}

export const aiGraphQuery = (question, maxDepth = 2, maxNodes = 50) => {
  return axios.post(`${BASE_URL}/graphs/knowledge/ai-query`, {
    question,
    max_depth: maxDepth,
    max_nodes: maxNodes
  }).then(r => r.data)
}

export const getEntityTypes = () => {
  return axios.get(`${BASE_URL}/graphs/knowledge/types`)
    .then(r => r.data)
}

// Mock样本生成接口已移除，请使用CSV导入功能

export const buildEventGraph = (params) => {
  // 事件图谱生成需要更长的超时时间（3分钟）
  return axios.post(`${BASE_URL}/qa/event-graph/generate`, params, {
    timeout: 180000
  }).then(r => r.data)
}

export const askQuestion = (question) => {
  // QA查询也可能需要更长的超时时间（1分钟）
  return axios.post(`${BASE_URL}/qa/query`, { question }, {
    timeout: 60000
  }).then(r => r.data)
}

export const getBrandCorrelation = (brand) => {
  return axios.get(`${BASE_URL}/graphs/brand-correlation`, {
    params: { brand }
  }).then(r => r.data)
}

export const importCSV = (formData) => {
  return axios.post(`${BASE_URL}/samples/import-csv`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)
}

export const importBatchCSV = (formData) => {
  return axios.post(`${BASE_URL}/samples/import-batch`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000  // 60秒超时，因为批量上传可能需要更长时间
  }).then(r => r.data)
}

export const inferUsers = (usersData) => {
  return axios.post(`${BASE_URL}/samples/infer`, usersData)
    .then(r => r.data)
}

export const listSamples = (sampleType = null, page = 1, pageSize = 100) => {
  const params = new URLSearchParams()
  if (sampleType) params.append('sample_type', sampleType)
  params.append('page', page)
  params.append('page_size', pageSize)
  return axios.get(`${BASE_URL}/samples/list?${params}`)
    .then(r => r.data)
}

// ========== 逻辑行为生成相关接口 ==========

export const extractEvents = (userIds = null) => {
  // 逻辑行为生成需要更长的超时时间（3分钟）
  return axios.post(`${BASE_URL}/logical-behaviors/generate/batch`, { user_ids: userIds }, {
    timeout: 180000
  }).then(r => r.data)
}

// 批量生成的别名（兼容旧代码）
export const startBatchExtract = extractEvents

export const extractEventsForUser = (userId) => {
  // 单用户逻辑行为生成也需要更长的超时时间（3分钟）
  return axios.post(`${BASE_URL}/logical-behaviors/generate/${userId}`, {}, {
    timeout: 180000
  }).then(r => r.data)
}

// 获取生成进度
export const getExtractProgress = () => {
  return axios.get(`${BASE_URL}/logical-behaviors/progress`)
    .then(r => r.data)
}

// 流式批量生成（暂不支持，返回错误提示）
export const startBatchExtractStream = () => {
  return Promise.reject(new Error('流式批量生成暂不支持，请使用普通批量生成'))
}

export const listEventSequences = (limit = 100, offset = 0) => {
  return axios.get(`${BASE_URL}/logical-behaviors/sequences`, {
    params: { limit, offset }
  }).then(r => r.data)
}

export const getUserSequence = (userId) => {
  return axios.get(`${BASE_URL}/logical-behaviors/sequences/${userId}`)
    .then(r => r.data)
}

export const getUserDetail = (userId) => {
  return axios.get(`${BASE_URL}/logical-behaviors/users/${userId}/detail`)
    .then(r => r.data)
}

// 获取事件统计（用于序列挖掘页面）
export const getEventStats = () => {
  return axios.get(`${BASE_URL}/mining/event-types`)
    .then(r => r.data)
}

// ========== 序列模式挖掘相关接口 ==========

export const mineFrequentPatterns = (params) => {
  // 序列挖掘可能需要较长时间（特别是PrefixSpan算法）
  return axios.post(`${BASE_URL}/mining/mine`, params, {
    timeout: 300000  // 5分钟超时
  }).then(r => r.data)
}

export const listFrequentPatterns = (limit = 100, offset = 0) => {
  return axios.get(`${BASE_URL}/mining/patterns/saved`, {
    params: { limit, offset }
  }).then(r => r.data)
}

// ========== 事理图谱相关接口 ==========

export const generateCausalGraph = (params) => {
  return axios.post(`${BASE_URL}/causal-graph/generate`, params, {
    timeout: 300000  // 5分钟超时
  }).then(r => r.data)
}

// 流式生成事理图谱
export const generateCausalGraphStream = async (params, onProgress, onContent, onResult, onError) => {
  const response = await fetch(`${BASE_URL}/causal-graph/generate/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(params)
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))

          if (data.type === 'progress' && onProgress) {
            onProgress(data.message)
          } else if (data.type === 'content' && onContent) {
            onContent(data.content)
          } else if (data.type === 'result' && onResult) {
            onResult(data.data)
          } else if (data.type === 'error' && onError) {
            onError(data.message)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export const listCausalGraphs = (limit = 20, offset = 0) => {
  return axios.get(`${BASE_URL}/causal-graph/list`, {
    params: { limit, offset }
  }).then(r => r.data)
}

export const getCausalGraph = (graphId) => {
  return axios.get(`${BASE_URL}/causal-graph/${graphId}`)
    .then(r => r.data)
}

export const deleteCausalGraph = (graphId) => {
  return axios.delete(`${BASE_URL}/causal-graph/${graphId}`)
    .then(r => r.data)
}

export const queryCausalGraph = (graphId, question, userContext = null) => {
  return axios.post(`${BASE_URL}/causal-graph/${graphId}/query`, {
    question,
    user_context: userContext
  }).then(r => r.data)
}

