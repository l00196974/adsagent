import axios from 'axios'

const BASE_URL = '/api/v1'

export const loadUserData = (params) => {
  return axios.post(`${BASE_URL}/data/load`, params)
    .then(r => r.data)
}

export const getDataStatus = () => {
  return axios.get(`${BASE_URL}/data/status`)
    .then(r => r.data)
}

export const buildKnowledgeGraph = (userCount = null) => {
  const url = userCount ? `${BASE_URL}/graphs/knowledge/build?user_count=${userCount}` : `${BASE_URL}/graphs/knowledge/build`
  return axios.post(url)
    .then(r => r.data)
}

export const getBuildProgress = () => {
  return axios.get(`${BASE_URL}/graphs/knowledge/progress`)
    .then(r => r.data)
}

export const queryGraph = (entityName = null, entityType = null) => {
  const params = new URLSearchParams()
  if (entityName) params.append('entity_name', entityName)
  if (entityType) params.append('entity_type', entityType)
  return axios.get(`${BASE_URL}/graphs/knowledge/query?${params}`)
    .then(r => r.data)
}

export const generateSamples = (params) => {
  return axios.post(`${BASE_URL}/samples/generate`, params)
    .then(r => r.data)
}

export const doGenerateSamples = (params) => {
  return axios.post(`${BASE_URL}/samples/generate`, params)
    .then(r => r.data)
}

export const buildEventGraph = (params) => {
  return axios.post(`${BASE_URL}/qa/event-graph/generate`, params)
    .then(r => r.data)
}

export const askQuestion = (question) => {
  return axios.post(`${BASE_URL}/qa/query`, { question })
    .then(r => r.data)
}

export const getBrandCorrelation = (brand) => {
  return axios.get(`${BASE_URL}/graphs/brand-correlation?brand=${brand}`)
    .then(r => r.data)
}
