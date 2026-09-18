import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { ChevronDown, ChevronRight, Copy, User, Wrench } from 'lucide-react'
import { useState } from 'react'
import type { Message, ToolEvent } from '../types'

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false)
  const highlighted = language && hljs.getLanguage(language)
    ? hljs.highlight(code, { language }).value
    : hljs.highlightAuto(code).value
  return (
    <div className="group relative my-2">
      <button
        onClick={() => {
          navigator.clipboard.writeText(code)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        }}
        className="absolute right-2 top-2 z-10 flex cursor-pointer items-center gap-1 rounded bg-surface-700/90 px-2 py-1 text-xs text-gray-400 opacity-0 transition group-hover:opacity-100 hover:text-gray-200"
      >
        <Copy className="h-3 w-3" /> {copied ? '已复制' : '复制'}
      </button>
      <pre>
        <code dangerouslySetInnerHTML={{ __html: highlighted }} />
      </pre>
    </div>
  )
}

function ToolCard({ ev }: { ev: ToolEvent }) {
  const [open, setOpen] = useState(false)
  const isCall = ev.type === 'tool_call'
  return (
    <div className="my-2 rounded-lg border border-amber-500/25 bg-amber-500/5 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-amber-300/90 transition hover:bg-amber-500/10"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Wrench className="h-3.5 w-3.5" />
        <span className="font-medium">{ev.name}</span>
        <span className="text-amber-400/60">{isCall ? '调用中' : '返回结果'}</span>
      </button>
      {open && (
        <pre className="max-h-48 overflow-auto border-t border-amber-500/20 px-3 py-2 text-gray-400">
          {JSON.stringify(isCall ? ev.args : ev.response, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default function MessageList({
  messages,
  onShowTrace,
}: {
  messages: Message[]
  onShowTrace: (traceId: string) => void
}) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-dark shadow-xl shadow-primary/25">
          <span className="text-2xl">✦</span>
        </div>
        <h2 className="text-xl font-semibold text-gray-200">有什么可以帮你的？</h2>
        <p className="mt-2 max-w-sm text-sm text-gray-500">
          支持多模型切换、长期记忆、插件工具调用，每条回复都可查看 token 与延迟详情
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-5 overflow-y-auto px-6 py-6">
      {messages.map((m) => (
        <div key={m.id} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
          {m.role === 'assistant' && (
            <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-dark text-xs text-white">
              ✦
            </div>
          )}
          <div
            className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              m.role === 'user'
                ? 'bg-primary text-white shadow-lg shadow-primary/20'
                : 'glass text-gray-200'
            }`}
          >
            {m.tool_events?.map((ev, i) => <ToolCard key={i} ev={ev} />)}
            {m.role === 'assistant' ? (
              <div className="markdown-body">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '')
                      const codeStr = String(children).replace(/\n$/, '')
                      return match ? (
                        <CodeBlock language={match[1]} code={codeStr} />
                      ) : (
                        <code className="rounded bg-surface-700 px-1.5 py-0.5 text-primary-light" {...props}>
                          {children}
                        </code>
                      )
                    },
                  }}
                >
                  {m.content}
                </ReactMarkdown>
                {m.streaming && (
                  <span className="ml-1 inline-block h-4 w-2 animate-pulse-slow rounded-sm bg-primary align-middle" />
                )}
              </div>
            ) : (
              <span className="whitespace-pre-wrap">{m.content}</span>
            )}
            {m.role === 'assistant' && m.stats && (
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-gray-700/50 pt-2 text-[11px] text-gray-500">
                <span>首 token {m.stats.ttft_ms ?? '-'}ms</span>
                <span>{m.stats.tokens_per_second ?? '-'} tok/s</span>
                <span>
                  {(m.stats.prompt_tokens ?? 0) + (m.stats.completion_tokens ?? 0)} tokens
                </span>
                {m.stats.trace_id && (
                  <button
                    onClick={() => onShowTrace(m.stats!.trace_id!)}
                    className="cursor-pointer text-primary-light transition hover:text-primary"
                  >
                    查看 Trace →
                  </button>
                )}
              </div>
            )}
          </div>
          {m.role === 'user' && (
            <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-700 text-gray-400">
              <User className="h-4 w-4" />
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
