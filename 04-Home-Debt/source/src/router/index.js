import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/current' },
  { path: '/current', name: 'current', component: () => import('../views/CurrentDebt.vue') },
  { path: '/past', name: 'past', component: () => import('../views/PastDebt.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
