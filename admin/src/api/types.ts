export interface ApiEnvelope<T> { code: number; message: string; data: T }
export interface PageResult<T> { items: T[]; total: number; page: number; page_size: number }

export interface AdminProfile {
  id: number; username: string; display_name: string | null; role: 'super_admin' | 'admin' | 'viewer'
  is_active: boolean; last_login_at: string | null; created_at: string
}

export interface LLMConfig {
  id: number; name: string; provider: string; base_url: string; api_key_masked: string
  chat_model: string | null; embedding_model: string | null; temperature: number; max_tokens: number | null
  timeout_seconds: number | null; max_retries: number | null; enabled: boolean; is_default: boolean
  last_test_status: string | null; last_test_message: string | null; created_at: string; updated_at: string
}
export interface ProviderPreset { provider: string; label: string; base_url: string; chat_model: string | null; embedding_model: string | null }

export interface Agent {
  id: number; name: string; description: string | null; avatar: string | null; category: string | null
  system_prompt: string; welcome_message: string | null; suggested_questions: string[] | null
  llm_config_id: number | null; llm_config_name?: string | null; temperature: number | null; max_tokens: number | null
  knowledge_base_ids: number[]; enable_rag: boolean; rag_top_k: number; rag_score_threshold: number
  rag_no_result_policy: 'fallback' | 'strict'; rag_refuse_message: string | null
  enable_memory: boolean; memory_max_messages: number; memory_max_tokens: number
  enable_tools: boolean; tools: string[] | null; status: 'draft' | 'published' | 'offline'
  access_level: 'public' | 'restricted'; sort_order: number; is_featured: boolean; created_at: string; updated_at: string
}

export interface KnowledgeBase {
  id: number; name: string; description: string | null; category: string | null
  embedding_llm_config_id: number | null; embedding_model: string | null; embedding_dim: number | null
  vector_store: string; collection_name: string | null; chunk_size: number; chunk_overlap: number
  top_k: number; score_threshold: number; status: string; document_count: number; chunk_count: number
  created_at: string; updated_at: string; needs_rebuild?: boolean
}

export interface DocumentItem {
  id: number; knowledge_base_id: number; filename: string; file_type: string; file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'; progress: number; stage: string | null
  error_message: string | null; chunk_count: number; char_count: number; task_id: string | null
  created_at: string; updated_at: string
}

export interface Chunk {
  id: number; chunk_id: string; document_id: number; chunk_index: number; content: string; char_count: number
  page_number: number | null
}

export interface Citation {
  index: number; chunk_id: string; document_id: number; document_name: string; knowledge_base_id: number
  knowledge_base_name: string; content: string; snippet: string; score: number; page_number: number | null
}

export interface Prompt {
  id: number; agent_id: number | null; name: string; description: string | null; content: string
  version: number; kind: string; created_at: string; updated_at: string
}

export interface Conversation {
  id: number; user_id: number; agent_id: number; agent_name: string | null; title: string; message_count: number
  last_message_at: string | null; created_at: string; user_nickname?: string | null
}

export interface Message {
  id: number; conversation_id: number; role: string; content: string; message_type: string; status: string
  attachments: any[] | null; citations: Citation[] | null; token_usage: Record<string, number> | null
  model: string | null; feedback: number | null; latency_ms: number | null; created_at: string
}

export interface EndUser {
  id: number; nickname: string | null; avatar_url: string | null; status: string; created_at: string
  last_login_at: string | null; conversation_count: number; total_tokens: number
}

export interface ApiLog {
  id: number; llm_config_id: number | null; agent_id: number | null; user_id: number | null; call_type: string
  provider: string | null; model: string | null; prompt_tokens: number; completion_tokens: number
  total_tokens: number; latency_ms: number; status: string; error_message: string | null; created_at: string
}

export interface AuditLog {
  id: number; admin_username: string | null; action: string; resource_type: string; resource_id: string | null
  detail: Record<string, unknown> | null; ip: string | null; created_at: string
}

export interface Overview {
  agents: number; published_agents: number; models: number; knowledge_bases: number; documents: number
  users: number; conversations: number; today_calls: number; today_tokens: number; total_tokens: number
  likes: number; dislikes: number; trend: { date: string; requests: number; tokens: number }[]
  top_agents: { id: number; name: string; requests: number }[]; recent_logs: ApiLog[]
}

export interface ToolInfo { name: string; description: string; parameters: Record<string, unknown> }
export interface SystemSettings { platform_name: string; welcome_text: string; quick_questions: string[]; featured_agent_ids: number[] }
