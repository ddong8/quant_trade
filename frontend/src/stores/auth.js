import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'))
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  async function login(credentials) {
    try {
      // 后端API简化了，这里直接模拟成功
      // const { data } = await api.post('/login/access-token', new URLSearchParams(credentials));
      // setToken(data.access_token);
      setToken("fake-jwt-token-for-demo") // 模拟Token
      router.push({ name: 'dashboard' })
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    router.push({ name: 'login' })
  }
  
  // 页面加载时初始化
  const storedToken = localStorage.getItem('token')
  if (storedToken) {
    setToken(storedToken)
  }

  return { token, user, isAuthenticated, login, logout }
})