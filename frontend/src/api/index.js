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
  return axios.post(`${BASE_URL}/qa/event-graph/generate`, params)
    .then(r => r.data)
}

export const askQuestion = (question) => {
  return axios.post(`${BASE_URL}/qa/query`, { question })
    .then(r => r.data)
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
