import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth' // 引入 auth store

import './assets/main.css'

// --- Monaco Editor Worker Manual Setup ---
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') {
      return new jsonWorker()
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return new cssWorker()
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return new htmlWorker()
    }
    if (label === 'typescript' || label === 'javascript') {
      return new tsWorker()
    }
    return new editorWorker()
  },
}
// --- End Monaco Editor Worker Manual Setup ---

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
