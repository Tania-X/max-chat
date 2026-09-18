const TOKEN_KEY = 'max_chat_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const resp = await fetch(path, { ...options, headers })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `请求失败 (${resp.status})`)
  }
  return resp.json()
}

export interface StreamCallbacks {
  onChunk: (delta: string) => void
  onToolEvent: (ev: Record<string, unknown>) => void
  onDone: (stats: Record<string, unknown>) => void
  onError: (message: string) => void
}

export async function streamChat(
  sessionId: string,
  content: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`/api/chat/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ content }),
    signal,
  })
  if (!resp.ok || !resp.body) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    callbacks.onError(body.detail || `请求失败 (${resp.status})`)
    return
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        const data = line.slice(5).trim()
        if (!data) continue
        try {
          const parsed = JSON.parse(data)
          if (currentEvent === 'chunk') callbacks.onChunk(parsed.delta)
          else if (currentEvent === 'tool_call' || currentEvent === 'tool_result')
            callbacks.onToolEvent(parsed)
          else if (currentEvent === 'done') callbacks.onDone(parsed)
          else if (currentEvent === 'error') callbacks.onError(parsed.message)
        } catch {
          console.error('SSE parse error', data)
        }
      }
    }
  }
}
