import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/graph',
    name: 'GraphVisual',
    component: () => import('../views/GraphVisual.vue')
  },
  {
    path: '/samples',
    name: 'Samples',
    component: () => import('../views/Samples.vue')
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
