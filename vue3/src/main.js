import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import axios from 'axios'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 统一请求客户端：所有接口都在 /api 下，开发期由 vite proxy 转发到 8000
const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const message = err.response?.data?.message || err.message || '请求失败'
    return Promise.reject(new Error(message))
  },
)

app.config.globalProperties.$http = http
app.provide('http', http)

app.use(ElementPlus, { size: 'small', zIndex: 3000 })
app.use(createPinia())
app.use(router)
app.mount('#app')
