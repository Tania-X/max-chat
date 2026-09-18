import { create } from 'zustand'
import { apiFetch, clearToken, getToken, setToken } from '../api/client'
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
    } catch {
      clearToken()
      set({ ready: true })
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
  },
}))

interface ChatState {
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: Message[]
  models: ModelConfig[]
  generating: boolean
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

export const useChat = create<ChatState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  models: [],
  generating: false,
  loadSessions: async () => {
    const sessions = await apiFetch<ChatSession[]>('/api/sessions')
    set({ sessions })
  },
  loadModels: async () => {
    const models = await apiFetch<ModelConfig[]>('/api/models')
    set({ models })
  },
  selectSession: async (id) => {
    set({ currentSessionId: id })
    const messages = await apiFetch<Message[]>(`/api/sessions/${id}/messages`)
    set({ messages })
  },
  createSession: async () => {
    const session = await apiFetch<ChatSession>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: '新会话' }),
    })
    set({ sessions: [session, ...get().sessions], currentSessionId: session.id, messages: [] })
    return session.id
  },
  deleteSession: async (id) => {
    await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' })
    const sessions = get().sessions.filter((s) => s.id !== id)
    set({
      sessions,
      currentSessionId: get().currentSessionId === id ? null : get().currentSessionId,
      messages: get().currentSessionId === id ? [] : get().messages,
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
