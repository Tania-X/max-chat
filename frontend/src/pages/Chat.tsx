import { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { streamChat } from '../api/client'
import Composer from '../components/Composer'
import MessageList from '../components/MessageList'
import Sidebar from '../components/Sidebar'
import TracePanel from '../components/TracePanel'
import { useChat } from '../store'
import type { Message, MessageStats, ToolEvent } from '../types'

export default function Chat() {
  const {
    sessions, currentSessionId, messages, models, generating,
    loadSessions, loadModels, selectSession, createSession,
    setSessionModel, setMessages, setGenerating, beginStream, abortStream,
  } = useChat()
  const [traceId, setTraceId] = useState<string | null>(null)
  const [modelMenuOpen, setModelMenuOpen] = useState(false)
  const modelMenuRef = useRef<HTMLDivElement>(null)

  // 下拉菜单：Esc 与点击外部都要能关闭
  useEffect(() => {
    if (!modelMenuOpen) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModelMenuOpen(false)
    }
    const onMouseDown = (e: MouseEvent) => {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) {
        setModelMenuOpen(false)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('mousedown', onMouseDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('mousedown', onMouseDown)
    }
  }, [modelMenuOpen])

  useEffect(() => {
    loadSessions()
      .then(() => {
        const { sessions: list } = useChat.getState()
        if (list.length > 0 && !useChat.getState().currentSessionId) {
          selectSession(list[0].id).catch((e) => console.error('加载会话失败', e))
        }
      })
      .catch((e) => console.error('加载会话列表失败', e))
    loadModels().catch((e) => console.error('加载模型列表失败', e))
  }, [])

  // 离开聊天页时中止生成，避免连接与额度在后台继续消耗
  useEffect(() => () => useChat.getState().abortStream(), [])

  const currentSession = sessions.find((s) => s.id === currentSessionId)
  const currentModel =
    models.find((m) => m.id === currentSession?.model_config_id) ||
    models.find((m) => m.is_default) ||
    models[0]

  const send = async (text: string) => {
    let sessionId = currentSessionId
    if (!sessionId) sessionId = await createSession()

    const userMsg: Message = {
      id: `u-${Date.now()}`, role: 'user', content: text, tool_events: [],
    }
    const assistantMsg: Message = {
      id: `a-${Date.now()}`, role: 'assistant', content: '', tool_events: [], streaming: true,
    }
    setMessages([...useChat.getState().messages, userMsg, assistantMsg])

    // 句柄由 store 持有：切会话/登出/离开页面时都能统一中止
    const controller = beginStream()

    const patchAssistant = (patch: Partial<Message>) => {
      const list = useChat.getState().messages
      setMessages(list.map((m) => (m.id === assistantMsg.id ? { ...m, ...patch } : m)))
    }

    try {
      await streamChat(sessionId, text, {
        onChunk: (delta) => {
          const m = useChat.getState().messages.find((x) => x.id === assistantMsg.id)
          patchAssistant({ content: (m?.content || '') + delta })
        },
        onToolEvent: (ev) => {
          const m = useChat.getState().messages.find((x) => x.id === assistantMsg.id)
          patchAssistant({ tool_events: [...(m?.tool_events || []), ev as unknown as ToolEvent] })
        },
        onDone: (stats) => {
          patchAssistant({ streaming: false, stats: stats as unknown as MessageStats })
          loadSessions().catch((e) => console.error('刷新会话列表失败', e))
        },
        onError: (message) => {
          const m = useChat.getState().messages.find((x) => x.id === assistantMsg.id)
          patchAssistant({
            streaming: false,
            content: (m?.content || '') + `\n\n> ⚠️ 出错：${message}`,
          })
        },
      }, controller.signal)
    } finally {
      // 无论正常结束、报错还是被中断，都不能把"正在生成"永久挂住
      patchAssistant({ streaming: false })
      setGenerating(false)
    }
  }

  const stop = () => {
    abortStream()
    setGenerating(false)
    const list = useChat.getState().messages
    const last = list[list.length - 1]
    if (last?.streaming) {
      setMessages(list.map((m) => (m.id === last.id ? { ...m, streaming: false } : m)))
    }
  }

  return (
    <div className="flex h-screen bg-surface-900">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
          <h1 className="truncate text-sm font-medium text-gray-200">
            {currentSession?.title || '新会话'}
          </h1>
          <div className="relative" ref={modelMenuRef}>
            <button
              onClick={() => setModelMenuOpen(!modelMenuOpen)}
              aria-haspopup="menu"
              aria-expanded={modelMenuOpen}
              aria-label="切换模型"
              className="flex cursor-pointer items-center gap-2 rounded-lg border border-gray-700 bg-surface-800 px-3 py-1.5 text-xs text-gray-300 transition hover:border-primary/50"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              {currentModel ? currentModel.label : '未配置模型'}
              <ChevronDown className="h-3.5 w-3.5 text-gray-500" />
            </button>
            {modelMenuOpen && (
              <div className="absolute right-0 z-20 mt-2 w-64 rounded-xl border border-gray-700 bg-surface-800 p-1.5 shadow-2xl">
                {models.length === 0 && (
                  <p className="px-3 py-2 text-xs text-gray-500">
                    请先在设置页添加模型配置
                  </p>
                )}
                {models.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      if (currentSessionId) setSessionModel(currentSessionId, m.id)
                      setModelMenuOpen(false)
                    }}
                    className={`flex w-full cursor-pointer flex-col rounded-lg px-3 py-2 text-left transition hover:bg-surface-700 ${
                      m.id === currentModel?.id ? 'bg-primary/10' : ''
                    }`}
                  >
                    <span className="text-xs font-medium text-gray-200">{m.label}</span>
                    <span className="text-[11px] text-gray-500">
                      {m.provider}/{m.model_name}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </header>

        <MessageList messages={messages} onShowTrace={setTraceId} />
        <Composer onSend={send} onStop={stop} generating={generating} />
      </main>
      {traceId && <TracePanel traceId={traceId} onClose={() => setTraceId(null)} />}
    </div>
  )
}
