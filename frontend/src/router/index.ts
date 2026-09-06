import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
    },
    {
      path: '/terms',
      name: 'terms',
      component: () => import('@/views/TermsView.vue'),
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('@/views/PrivacyView.vue'),
    },
    {
      path: '/home',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
    },
    {
      path: '/chat/:id',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      props: true,
    },
  ],
})

router.beforeEach((to) => {
  const userStore = useUserStore()
  if (!userStore.token &&
      to.name !== 'login' && to.name !== 'register' &&
      to.name !== 'terms' && to.name !== 'privacy') {
    return '/login'
  }
})

export default router
