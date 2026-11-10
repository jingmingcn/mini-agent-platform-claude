import { http } from './http'
import type {
  AdminProfile, Agent, ApiLog, AuditLog, Chunk, Citation, Conversation, DocumentItem, EndUser, KnowledgeBase,
  LLMConfig, Message, Overview, PageResult, Prompt, ProviderPreset, SystemSettings, ToolInfo,
} from './types'

export const authApi = {
  login: (username: string, password: string) =>
    http.post<{ access_token: string; profile: AdminProfile }>('/auth/admin/login', { username, password }),
  me: () => http.get<{ principal_type: string; profile: AdminProfile }>('/auth/me'),
}

export const modelApi = {
  providers: () => http.get<ProviderPreset[]>('/models/providers'),
  list: () => http.get<LLMConfig[]>('/models'),
  create: (data: Record<string, unknown>) => http.post<LLMConfig>('/models', data),
  update: (id: number, data: Record<string, unknown>) => http.put<LLMConfig>(`/models/${id}`, data),
  remove: (id: number) => http.delete<null>(`/models/${id}`),
  test: (id: number) => http.post<Record<string, any>>(`/models/${id}/test`),
  setDefault: (id: number) => http.post<LLMConfig>(`/models/${id}/default`),
}

export const agentApi = {
  list: (params?: { keyword?: string; status?: string }) => http.get<Agent[]>('/agents', params),
  get: (id: number) => http.get<Agent>(`/agents/${id}`),
  create: (data: Partial<Agent>) => http.post<Agent>('/agents', data),
  update: (id: number, data: Partial<Agent>) => http.put<Agent>(`/agents/${id}`, data),
  remove: (id: number) => http.delete<null>(`/agents/${id}`),
  publish: (id: number) => http.post<Agent>(`/agents/${id}/publish`),
  offline: (id: number) => http.post<Agent>(`/agents/${id}/offline`),
  permissions: (id: number) => http.get<{ id: number; nickname: string | null }[]>(`/agents/${id}/permissions`),
  setPermissions: (id: number, user_ids: number[]) => http.put<unknown>(`/agents/${id}/permissions`, { user_ids }),
}

export const kbApi = {
  list: (keyword?: string) => http.get<KnowledgeBase[]>('/knowledge-bases', { keyword }),
  get: (id: number) => http.get<KnowledgeBase>(`/knowledge-bases/${id}`),
  create: (data: Partial<KnowledgeBase>) => http.post<KnowledgeBase>('/knowledge-bases', data),
  update: (id: number, data: Partial<KnowledgeBase>) => http.put<KnowledgeBase>(`/knowledge-bases/${id}`, data),
  remove: (id: number) => http.delete<null>(`/knowledge-bases/${id}`),
  rebuild: (id: number) => http.post<{ documents: number }>(`/knowledge-bases/${id}/rebuild`),
  documents: (id: number, params: { page: number; page_size: number; status?: string; keyword?: string }) =>
    http.get<PageResult<DocumentItem>>(`/knowledge-bases/${id}/documents`, params),
  upload: (id: number, files: File[], onProgress?: (pct: number) => void) => {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    return http.post<DocumentItem[]>(`/knowledge-bases/${id}/documents`, fd, {
      onUploadProgress: (e) => onProgress && e.total && onProgress(Math.round((e.loaded / e.total) * 100)),
    })
  },
  search: (id: number, query: string, top_k?: number, score_threshold?: number) =>
    http.post<Citation[]>(`/knowledge-bases/${id}/search`, { query, top_k, score_threshold }),
}

export const docApi = {
  get: (id: number) => http.get<DocumentItem>(`/documents/${id}`),
  chunks: (id: number, page: number, page_size = 20) => http.get<PageResult<Chunk>>(`/documents/${id}/chunks`, { page, page_size }),
  reparse: (id: number) => http.post<DocumentItem>(`/documents/${id}/reparse`),
  deleteVectors: (id: number) => http.delete<DocumentItem>(`/documents/${id}/vectors`),
  remove: (id: number) => http.delete<null>(`/documents/${id}`),
}

export const promptApi = {
  list: (agent_id?: number) => http.get<Prompt[]>('/prompts', { agent_id }),
  create: (data: Partial<Prompt>) => http.post<Prompt>('/prompts', data),
  update: (id: number, data: Partial<Prompt>) => http.put<Prompt>(`/prompts/${id}`, data),
  remove: (id: number) => http.delete<null>(`/prompts/${id}`),
}

export const conversationApi = {
  list: (params: Record<string, unknown>) => http.get<PageResult<Conversation>>('/conversations', params),
  messages: (id: number) => http.get<{ conversation: Conversation; items: Message[] }>(`/conversations/${id}/messages`),
  remove: (id: number) => http.delete<null>(`/conversations/${id}`),
}

export const userApi = {
  list: (params: Record<string, unknown>) => http.get<PageResult<EndUser>>('/users', params),
  setStatus: (id: number, status: string) => http.put<EndUser>(`/users/${id}/status`, { status }),
  admins: () => http.get<AdminProfile[]>('/admin-users'),
  createAdmin: (data: Record<string, unknown>) => http.post<AdminProfile>('/admin-users', data),
  updateAdmin: (id: number, data: Record<string, unknown>) => http.put<AdminProfile>(`/admin-users/${id}`, data),
}

export const logApi = {
  api: (params: Record<string, unknown>) => http.get<PageResult<ApiLog>>('/logs/api', params),
  audit: (params: Record<string, unknown>) => http.get<PageResult<AuditLog>>('/logs/audit', params),
  overview: () => http.get<Overview>('/stats/overview'),
}

export const systemApi = {
  settings: () => http.get<SystemSettings>('/settings'),
  saveSettings: (data: Partial<SystemSettings>) => http.put<SystemSettings>('/settings', data),
  tools: () => http.get<ToolInfo[]>('/tools'),
}
