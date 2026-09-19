import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch } from '../api/client'
import type { Message } from '../types'
import { useAuth, useChat } from './index'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const message = (id: string, content: string): Message => ({
  id,
  role: 'user',
  content,
  tool_events: [],
})

beforeEach(() => {
  localStorage.clear()
  useAuth.setState({ user: null, ready: false })
  useChat.setState({
    sessions: [],
    currentSessionId: null,
    messages: [],
    models: [],
    generating: false,
    streamController: null,
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('登出与鉴权失效', () => {
  it('登出会清空会话与消息，避免换号后看到上一个用户的数据', () => {
    localStorage.setItem('max_chat_token', 'tok')
    useAuth.setState({ user: { id: 'u1', username: 'alice', display_name: 'alice' } })
    useChat.setState({
      sessions: [{ id: 's1', title: 'alice 的会话', model_config_id: null }],
      currentSessionId: 's1',
      messages: [message('m1', 'alice 的私密内容')],
    })

    useAuth.getState().logout()

    expect(localStorage.getItem('max_chat_token')).toBeNull()
    expect(useAuth.getState().user).toBeNull()
    expect(useChat.getState().sessions).toEqual([])
    expect(useChat.getState().messages).toEqual([])
    expect(useChat.getState().currentSessionId).toBeNull()
  })

  it('任意请求返回 401 时统一清理登录态与会话数据', async () => {
    localStorage.setItem('max_chat_token', 'expired')
    useAuth.setState({ user: { id: 'u1', username: 'alice', display_name: 'alice' } })
    useChat.setState({ currentSessionId: 's1', messages: [message('m1', '内容')] })
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(jsonResponse({ detail: '登录状态无效或已过期', code: 'unauthorized' }, 401)),
      ),
    )

    await expect(apiFetch('/api/sessions')).rejects.toBeInstanceOf(ApiError)

    expect(localStorage.getItem('max_chat_token')).toBeNull()
    expect(useAuth.getState().user).toBeNull()
    expect(useChat.getState().currentSessionId).toBeNull()
  })

  it('网络故障不应把用户踢下线（只有 401 才清 token）', async () => {
    localStorage.setItem('max_chat_token', 'still-valid')
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))))

    await useAuth.getState().init()

    expect(localStorage.getItem('max_chat_token')).toBe('still-valid')
    expect(useAuth.getState().ready).toBe(true)
  })

  it('422 的 detail 数组不会渲染成 [object Object]', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(jsonResponse({ detail: [{ msg: '密码长度不足' }] }, 422)),
      ),
    )

    await expect(apiFetch('/api/auth/login', { method: 'POST' })).rejects.toThrow('密码长度不足')
  })
})

describe('会话切换', () => {
  it('快速切换时，先发出的过期响应不得覆盖后选的会话', async () => {
    let releaseA: (value: Response) => void = () => {}
    const pendingA = new Promise<Response>((resolve) => {
      releaseA = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url === '/api/sessions/A/messages'
          ? pendingA
          : Promise.resolve(jsonResponse([message('mb', 'B 的消息')])),
      ),
    )

    const requestA = useChat.getState().selectSession('A')
    const requestB = useChat.getState().selectSession('B')
    await requestB
    releaseA(jsonResponse([message('ma', 'A 的消息')]))
    await requestA

    expect(useChat.getState().currentSessionId).toBe('B')
    expect(useChat.getState().messages.map((m) => m.content)).toEqual(['B 的消息'])
  })

  it('切换会话会中止在途生成，避免增量写进错误的会话或继续消耗额度', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse([]))))
    const controller = useChat.getState().beginStream()
    expect(controller.signal.aborted).toBe(false)
    expect(useChat.getState().generating).toBe(true)

    await useChat.getState().selectSession('other')

    expect(controller.signal.aborted).toBe(true)
    expect(useChat.getState().generating).toBe(false)
  })
})

describe('生成句柄', () => {
  it('开始新生成会中止上一次，reset 会中止当前生成', () => {
    const first = useChat.getState().beginStream()
    const second = useChat.getState().beginStream()

    expect(first.signal.aborted).toBe(true)
    expect(second.signal.aborted).toBe(false)

    useChat.getState().reset()

    expect(second.signal.aborted).toBe(true)
    expect(useChat.getState().streamController).toBeNull()
  })
})
