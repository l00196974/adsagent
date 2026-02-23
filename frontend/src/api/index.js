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

// ========== 事件抽象相关接口 ==========

export const startBatchExtract = (userIds = null) => {
  return axios.post(`${BASE_URL}/events/extract/start`, { user_ids: userIds })
    .then(r => r.data)
}

export const getExtractProgress = () => {
  return axios.get(`${BASE_URL}/events/extract/progress`)
    .then(r => r.data)
}

export const extractEvents = (userIds = null) => {
  // 事件抽象需要更长的超时时间（3分钟）
  return axios.post(`${BASE_URL}/events/extract`, { user_ids: userIds }, {
    timeout: 180000
  }).then(r => r.data)
}

export const extractEventsForUser = (userId) => {
  // 单用户事件抽象也需要更长的超时时间（3分钟）
  return axios.post(`${BASE_URL}/events/extract/${userId}`, {}, {
    timeout: 180000
  }).then(r => r.data)
}

/**
 * 单用户事件抽象（LLM流式响应）
 * @param {string} userId - 用户ID
 * @param {Object} callbacks - 回调函数
 * @param {Function} callbacks.onLLMChunk - LLM实时响应回调
 * @param {Function} callbacks.onProgress - 进度回调
 * @param {Function} callbacks.onDone - 完成回调
 * @param {Function} callbacks.onError - 错误回调
 */
export const extractEventsForUserStream = (userId, callbacks = {}) => {
  const url = `${BASE_URL}/events/extract/${userId}/llm-stream`

  return new Promise((resolve, reject) => {
    // 使用fetch来发起POST请求（EventSource只支持GET）
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      const readStream = () => {
        reader.read().then(({ done, value }) => {
          if (done) {
            return
          }

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6))

                switch (data.type) {
                  case 'start':
                    if (callbacks.onProgress) callbacks.onProgress(data.message)
                    break
                  case 'progress':
                    if (callbacks.onProgress) callbacks.onProgress(data.message)
                    break
                  case 'llm_chunk':
                    if (callbacks.onLLMChunk) callbacks.onLLMChunk(data.content)
                    break
                  case 'done':
                    if (callbacks.onDone) callbacks.onDone(data)
                    resolve(data)
                    return
                  case 'error':
                    if (callbacks.onError) callbacks.onError(data.message)
                    reject(new Error(data.message))
                    return
                }
              } catch (e) {
                console.error('解析SSE数据失败:', e, line)
              }
            }
          }

          readStream()
        }).catch(error => {
          if (callbacks.onError) callbacks.onError(error.message)
          reject(error)
        })
      }

      readStream()
    }).catch(error => {
      if (callbacks.onError) callbacks.onError(error.message)
      reject(error)
    })
  })
}

export const listEventSequences = (limit = 100, offset = 0) => {
  return axios.get(`${BASE_URL}/events/sequences`, {
    params: { limit, offset }
  }).then(r => r.data)
}

export const getUserSequence = (userId) => {
  return axios.get(`${BASE_URL}/events/sequences/${userId}`)
    .then(r => r.data)
}

export const getUserDetail = (userId) => {
  return axios.get(`${BASE_URL}/events/users/${userId}/detail`)
    .then(r => r.data)
}

/**
 * 启动批量事件抽象（流式）
 * @param {Object} config - 配置参数 { user_ids?: string[] }
 * @param {Object} callbacks - 回调函数集合
 * @param {Function} callbacks.onProgress - 进度回调
 * @param {Function} callbacks.onUserResult - 用户结果回调
 * @param {Function} callbacks.onComplete - 完成回调
 * @param {Function} callbacks.onError - 错误回调
 * @param {Function} callbacks.onLLMChunk - LLM流式内容回调（可选）
 * @returns {EventSource} EventSource 实例，可用于关闭连接
 */
export const startBatchExtractStream = (config, callbacks) => {
  const { onProgress, onUserResult, onComplete, onError, onLLMChunk } = callbacks

  // 构建查询参数
  const params = new URLSearchParams()
  if (config.user_ids && config.user_ids.length > 0) {
    params.append('user_ids', JSON.stringify(config.user_ids))
  }

  // 创建 EventSource 连接
  const url = `${BASE_URL}/events/extract/start/stream${params.toString() ? '?' + params.toString() : ''}`

  // 使用 fetch 发送 POST 请求并处理 SSE 流
  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(config)
  }).then(response => {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const processStream = () => {
      reader.read().then(({ done, value }) => {
        if (done) {
          return
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // 保留最后一个不完整的行

        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const data = JSON.parse(line.substring(5).trim())

              // 根据数据内容调用相应的回调
              if (data.status === 'processing') {
                onProgress && onProgress(data)
              } else if (data.user_id) {
                // 用户结果
                onUserResult && onUserResult(data)
                if (data.progress) {
                  onProgress && onProgress(data.progress)
                }
              } else if (data.status === 'completed') {
                onComplete && onComplete(data)
                return
              } else if (data.error) {
                onError && onError(data)
                return
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e, line)
            }
          }
        }

        processStream()
      }).catch(error => {
        onError && onError({ error: error.message })
      })
    }

    processStream()
  }).catch(error => {
    onError && onError({ error: error.message })
  })

  // 返回一个可以关闭连接的对象
  return {
    close: () => {
      // fetch 的 reader 会在组件卸载时自动关闭
    }
  }
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

