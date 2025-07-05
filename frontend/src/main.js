import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth' // 引入 auth store

import './assets/main.css'

const app = createApp(App)

// 1. 先 use Pinia
app.use(createPinia())

// 2. 在挂载路由之前，初始化认证状态
// 这会确保在路由守卫执行时，authStore 已经从 localStorage 加载了 token
const authStore = useAuthStore()
authStore.checkAuthOnLoad() // 我们将 checkAuthOnLoad 从 store 内部移到这里显式调用

// 3. 最后 use router
app.use(router)

app.use(naive)

app.mount('#app')