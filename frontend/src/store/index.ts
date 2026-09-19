import { create } from 'zustand'
import {
  ApiError,
  apiFetch,
  clearToken,
  getToken,
  isApiError,
  setToken,
  setUnauthorizedHandler,
} from '../api/client'
import type { ChatSession, Message, ModelConfig, User } from '../types'

interface AuthState {
  user: User | null
  ready: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string) => Promise<void>
  logout: () => void
  init: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  ready: false,
  init: async () => {
    if (!getToken()) {
      set({ ready: true })
      return
    }
    try {
      const user = await apiFetch<User>('/api/auth/me')
      set({ user, ready: true })
    } catch (err) {
      // 只有确认是鉴权失败才清 token；后端未启动/网络抖动不应把用户踢下线
      if (isApiError(err) && err.status === 401) clearToken()
      set({ user: null, ready: true })
    }
  },
  login: async (username, password) => {
    const resp = await apiFetch<{ token: string; user: User }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setToken(resp.token)
    set({ user: resp.user })
  },
  register: async (username, password) => {
    const resp = await apiFetch<{ token: string; user: User }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setToken(resp.token)
    set({ user: resp.user })
  },
  logout: () => {
    clearToken()
    set({ user: null })
    // 会话与消息是跨用户敏感数据，换号登录前必须清干净
    useChat.getState().reset()
  },
}))

interface ChatState {
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: Message[]
  models: ModelConfig[]
  generating: boolean
  streamController: AbortController | null
  reset: () => void
  beginStream: () => AbortController
  abortStream: () => void
  loadSessions: () => Promise<void>
  loadModels: () => Promise<void>
  selectSession: (id: string) => Promise<void>
  createSession: () => Promise<string>
  deleteSession: (id: string) => Promise<void>
  renameSession: (id: string, title: string) => Promise<void>
  setSessionModel: (id: string, modelConfigId: string | null) => Promise<void>
  setMessages: (messages: Message[]) => void
  setGenerating: (v: boolean) => void
}

// 会话切换的请求序号：只有最后一次选择的结果允许写入，避免快速点击导致串台
let sessionRequestSeq = 0

export const useChat = create<ChatState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  models: [],
  generating: false,
  streamController: null,

  reset: () => {
    sessionRequestSeq += 1 // 使仍在飞行中的会话加载失效
    get().abortStream()
    set({
      sessions: [],
      currentSessionId: null,
      messages: [],
      models: [],
      generating: false,
    })
  },

  beginStream: () => {
    get().abortStream()
    const controller = new AbortController()
    set({ streamController: controller, generating: true })
    return controller
  },

  abortStream: () => {
    const controller = get().streamController
    if (controller) {
      controller.abort()
      set({ streamController: null })
    }
  },

  loadSessions: async () => {
    const sessions = await apiFetch<ChatSession[]>('/api/sessions')
    set({ sessions })
  },

  loadModels: async () => {
    const models = await apiFetch<ModelConfig[]>('/api/models')
    set({ models })
  },

  selectSession: async (id) => {
    // 切走时中止仍在进行的生成：既不浪费额度，也避免增量写进错误的会话视图
    get().abortStream()
    set({ generating: false })

    const seq = ++sessionRequestSeq
    set({ currentSessionId: id })
    const messages = await apiFetch<Message[]>(`/api/sessions/${id}/messages`)
    if (seq !== sessionRequestSeq) return // 期间又切了会话，丢弃过期响应
    set({ messages })
  },

  createSession: async () => {
    const session = await apiFetch<ChatSession>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: '新会话' }),
    })
    sessionRequestSeq += 1
    set({ sessions: [session, ...get().sessions], currentSessionId: session.id, messages: [] })
    return session.id
  },

  deleteSession: async (id) => {
    await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' })
    const sessions = get().sessions.filter((s) => s.id !== id)
    const isCurrent = get().currentSessionId === id
    if (isCurrent) {
      sessionRequestSeq += 1
      get().abortStream()
    }
    set({
      sessions,
      currentSessionId: isCurrent ? null : get().currentSessionId,
      messages: isCurrent ? [] : get().messages,
      generating: isCurrent ? false : get().generating,
    })
  },

  renameSession: async (id, title) => {
    await apiFetch(`/api/sessions/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) })
    set({ sessions: get().sessions.map((s) => (s.id === id ? { ...s, title } : s)) })
  },

  setSessionModel: async (id, modelConfigId) => {
    await apiFetch(`/api/sessions/${id}/model`, {
      method: 'PUT',
      body: JSON.stringify({ model_config_id: modelConfigId }),
    })
    set({
      sessions: get().sessions.map((s) =>
        s.id === id ? { ...s, model_config_id: modelConfigId } : s,
      ),
    })
  },

  setMessages: (messages) => set({ messages }),
  setGenerating: (generating) => set({ generating }),
}))

// 任一请求返回 401（token 过期/被吊销）时统一登出，而不是让每个页面各自失败
setUnauthorizedHandler(() => {
  clearToken()
  useAuth.setState({ user: null, ready: true })
  useChat.getState().reset()
})

export { ApiError }
