export interface User {
  id: string
  username: string
  display_name: string
}

export interface ChatSession {
  id: string
  title: string
  model_config_id: string | null
  updated_at?: string
}

export interface ToolEvent {
  type: 'tool_call' | 'tool_result'
  name: string
  args?: Record<string, unknown>
  response?: unknown
  ts_ms?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  tool_events: ToolEvent[]
  trace_id?: string | null
  created_at?: string
  streaming?: boolean
  stats?: MessageStats
}

export interface MessageStats {
  message_id: string
  trace_id?: string
  ttft_ms?: number
  duration_ms?: number
  prompt_tokens?: number
  completion_tokens?: number
  tokens_per_second?: number
}

export interface ModelConfig {
  id: string
  provider: string
  model_name: string
  label: string
  base_url: string
  has_api_key: boolean
  is_default: boolean
}

export interface Capability {
  id: string
  type: 'plugin' | 'skill' | 'mcp'
  name: string
  description: string
  enabled: boolean
  config: Record<string, unknown>
}

export interface MemoryItem {
  id: string
  content: string
  category: string
  created_at: string
}

export interface Trace {
  id: string
  session_id: string
  provider: string
  model_name: string
  prompt_tokens: number
  completion_tokens: number
  ttft_ms: number | null
  duration_ms: number
  tokens_per_second: number
  cost_usd: number
  tool_spans: ToolEvent[]
  error: string
  created_at: string
}

export interface UsageSummary {
  days: number
  total_calls: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_cost_usd: number
  avg_ttft_ms: number
  avg_tokens_per_second: number
  by_model: {
    model_name: string
    provider: string
    calls: number
    prompt_tokens: number
    completion_tokens: number
    cost_usd: number
  }[]
  by_day: { date: string; calls: number; tokens: number; cost_usd: number }[]
}
