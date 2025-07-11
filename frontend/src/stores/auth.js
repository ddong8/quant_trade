// frontend/src/stores/auth.js

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null);
  const user = ref(null);

  const isAuthenticated = computed(() => !!token.value);

  function setToken(newToken) {
    token.value = newToken;
    if (newToken) {
      localStorage.setItem('token', newToken);
    } else {
      localStorage.removeItem('token');
    }
  }

  async function login(credentials) {
    try {
      const { data } = await api.login(credentials);
      setToken(data.access_token);
      router.push({ name: 'dashboard' });
    } catch (error) {
      console.error('Login failed:', error);
      logout(); 
      throw error;
    }
  }

  function logout() {
    setToken(null);
    user.value = null;
    router.push({ name: 'login' });
  }

  function checkAuthOnLoad() {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }
  }

  return { token, user, isAuthenticated, login, logout, checkAuthOnLoad };
})
