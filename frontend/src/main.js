// frontend/src/main.js

import { createApp } from 'vue';
import App from './App.vue';
import router from './router'; // 导入 router
import pinia from './stores';   // 导入 pinia

import './assets/main.css';

const app = createApp(App);

app.use(pinia);   // 先安装 Pinia，因为路由守卫会用到 store
app.use(router); // 再安装 Router

app.mount('#app');