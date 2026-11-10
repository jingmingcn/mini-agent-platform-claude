import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope } from './types'

export const TOKEN_KEY = 'mini_agent_admin_token'
export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

const instance = axios.create({ baseURL: API_BASE, timeout: 120_000 })

instance.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

instance.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError<ApiEnvelope<unknown>>) => {
    const status = error.response?.status
    const msg = error.response?.data?.message || error.message || '网络错误'
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (!location.pathname.startsWith('/login')) location.href = '/login?redirect=' + encodeURIComponent(location.pathname)
    } else {
      const detail = error.response?.data?.data
      ElMessage.error(Array.isArray(detail) && detail.length ? `${msg}: ${detail.map((d: any) => `${d.loc} ${d.msg}`).join('; ')}` : msg)
    }
    return Promise.reject(error)
  },
)

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const resp = await instance.request<ApiEnvelope<T>>(config)
  return resp.data.data
}

export const http = {
  get: <T>(url: string, params?: object) => request<T>({ method: 'get', url, params }),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) => request<T>({ method: 'post', url, data, ...config }),
  put: <T>(url: string, data?: unknown) => request<T>({ method: 'put', url, data }),
  patch: <T>(url: string, data?: unknown) => request<T>({ method: 'patch', url, data }),
  delete: <T>(url: string) => request<T>({ method: 'delete', url }),
}
