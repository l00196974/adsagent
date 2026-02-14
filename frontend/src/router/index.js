import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/import',
    name: 'DataImport',
    component: () => import('../views/DataImport.vue')
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
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
    path: '/graph',
    name: 'GraphVisual',
    component: () => import('../views/GraphVisual.vue')
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
