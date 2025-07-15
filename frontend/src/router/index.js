// frontend/src/router/index.js

import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import MainLayout from '@/layouts/MainLayout.vue';
import LoginView from '@/views/LoginView.vue';
import DashboardView from '@/views/DashboardView.vue';
import StrategiesView from '@/views/StrategiesView.vue';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: DashboardView,
      },
      {
        path: 'strategies',
        name: 'strategies',
        component: StrategiesView,
      },
      // 如果有其他页面，在这里添加
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 全局导航守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const isAuthenticated = !!authStore.token;

  if (to.name !== 'login' && !isAuthenticated) {
    // 如果用户未登录且访问的不是登录页，则重定向到登录页
    next({ name: 'login' });
  } else if (to.name === 'login' && isAuthenticated) {
    // 如果用户已登录且试图访问登录页，则重定向到仪表盘
    next({ name: 'dashboard' });
  } else {
    // 其他情况，正常放行
    next();
  }
});

export default router;