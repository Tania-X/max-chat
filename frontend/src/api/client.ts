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

function isAbort(err: unknown): boolean {
  return err instanceof DOMException ? err.name === 'AbortError' : (err as { name?: string })?.name === 'AbortError'
}

function errText(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

export async function streamChat(
  sessionId: string,
  content: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  // 本函数不抛出：所有失败都通过 callbacks.onError 上报，
  // 用户主动停止（abort）不算错误，静默返回。
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let resp: Response
  try {
    resp = await fetch(`/api/chat/${sessionId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ content }),
      signal,
    })
  } catch (err) {
    if (isAbort(err)) return
    callbacks.onError(`网络请求失败：${errText(err)}`)
    return
  }

  if (!resp.ok || !resp.body) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    callbacks.onError(body.detail || `请求失败 (${resp.status})`)
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''
  // 后端异常中断时流会直接结束且不带 done/error，必须让 UI 知道，
  // 否则"正在生成"状态会一直挂着
  let terminal = false
  try {
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
            else if (currentEvent === 'done') {
              terminal = true
              callbacks.onDone(parsed)
            } else if (currentEvent === 'error') {
              terminal = true
              callbacks.onError(parsed.message)
            }
          } catch {
            console.error('SSE parse error', data)
          }
        }
      }
    }
  } catch (err) {
    if (isAbort(err)) return
    callbacks.onError(`连接中断：${errText(err)}`)
    return
  } finally {
    reader.releaseLock()
  }

  if (!terminal && !signal?.aborted) {
    callbacks.onError('连接意外结束，回复可能不完整')
  }
}
