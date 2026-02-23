import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/modeling'
  },
  {
    path: '/modeling',
    name: 'BaseModeling',
    component: () => import('../views/BaseModeling.vue')
  },
  {
    path: '/events',
    name: 'EventExtraction',
    component: () => import('../views/EventExtraction.vue')
  },
  {
    path: '/mining',
    name: 'SequenceMining',
    component: () => import('../views/SequenceMining.vue')
  },
  {
    path: '/causal-graph/generate',
    name: 'CausalGraphGeneration',
    component: () => import('../views/CausalGraphGeneration.vue')
  },
  {
    path: '/causal-graph/view/:graphId?',
    name: 'CausalGraphView',
    component: () => import('../views/CausalGraphView.vue')
  },
  {
    path: '/qa',
    name: 'QAChat',
    component: () => import('../views/QAChat.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
