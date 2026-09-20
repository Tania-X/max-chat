const TOKEN_KEY = 'max_chat_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

/** 带状态码的 API 错误：调用方需要区分"未登录"与"网络故障"。 */
export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export const isApiError = (err: unknown): err is ApiError => err instanceof ApiError

type UnauthorizedHandler = () => void
let onUnauthorized: UnauthorizedHandler | null = null

/** 注册全局 401 处理（清理登录态并跳转），由 store 在模块初始化时注入。 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler
}

export function notifyUnauthorized() {
  onUnauthorized?.()
}

/** 统一解析错误体：后端契约是 {detail, code}，422 的 detail 可能是数组。 */
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown })?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    if (first?.msg) return first.msg
  }
  return fallback
}

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
    if (resp.status === 401) notifyUnauthorized()
    throw new ApiError(
      errorMessage(body, `请求失败 (${resp.status})`),
      resp.status,
      (body as { code?: string })?.code,
    )
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
    if (resp.status === 401) notifyUnauthorized()
    callbacks.onError(errorMessage(body, `请求失败 (${resp.status})`))
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
