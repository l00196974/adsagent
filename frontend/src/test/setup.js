import { createTestingPinia } from '@pinia/testing'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import { vi } from 'vitest'

// 全局测试设置
beforeAll(() => {
  // Mock console用于测试
  vi.spyOn(console, 'log').mockImplementation(() => {})
  vi.spyOn(console, 'warn').mockImplementation(() => {})
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterAll(() => {
  vi.restoreAllMocks()
})

// 测试工具函数
export const createTestRouter = () => {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'Home', component: { template: '<div>Home</div>' } },
      { path: '/dashboard', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
      { path: '/graph', name: 'Graph', component: { template: '<div>Graph</div>' } },
      { path: '/samples', name: 'Samples', component: { template: '<div>Samples</div>' } },
      { path: '/qa', name: 'QA', component: { template: '<div>QA</div>' } }
    ]
  })
}

export const mountWithPlugins = (component, options = {}) => {
  const router = createTestRouter()
  
  return mount(component, {
    global: {
      plugins: [
        ElementPlus,
        createTestingPinia(),
        router
      ],
      stubs: ['router-link', 'router-view']
    },
    ...options
  })
}

// Mock API函数
export const mockAPI = {
  loadUserData: vi.fn().mockResolvedValue({ code: 0, data: { loaded_count: 50000 } }),
  getDataStatus: vi.fn().mockResolvedValue({ code: 0, data: { loaded_count: 50000, status: '已加载' } }),
  buildKnowledgeGraph: vi.fn().mockResolvedValue({ 
    code: 0, 
    data: { 
      stats: { total_entities: 1000, total_relations: 5000 },
      entities: [],
      relations: []
    } 
  }),
  getBuildProgress: vi.fn().mockResolvedValue({ 
    code: 0, 
    data: { 
      current_step: '构建完成',
      step_progress: 1,
      entities_created: 1000,
      relations_created: 5000
    } 
  }),
  generateSamples: vi.fn().mockResolvedValue({ 
    code: 0, 
    data: { 
      samples: {
        positive: Array(50).fill({}),
        churn: Array(500).fill({}),
        weak: Array(250).fill({}),
        control: Array(250).fill({})
      }
    } 
  }),
  askQuestion: vi.fn().mockResolvedValue({ 
    code: 0, 
    data: { 
      answer: '根据分析，喜欢高尔夫的用户更倾向于宝马7系，高意向率达到42%。',
      confidence: 0.85,
      reasoning: '高尔夫与宝马品牌有0.75的关联度'
    } 
  })
}
