import axios from 'axios'

/**
 * 全局唯一的 HTTP 客户端。
 * baseURL 设为 /api：开发期走 vite proxy，生产期由 FastAPI 托管前端，同源。
 */
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

export default http
