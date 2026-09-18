import { useEffect, useState } from 'react'
import { Activity, X, Zap } from 'lucide-react'
import { apiFetch } from '../api/client'
import type { Trace } from '../types'

interface Span {
  label: string
  start: number
  end: number
  color: string
  detail?: string
}

export default function TracePanel({
  traceId,
  onClose,
}: {
  traceId: string
  onClose: () => void
}) {
  const [trace, setTrace] = useState<Trace | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch<Trace>(`/api/traces/${traceId}`)
      .then(setTrace)
      .catch((e) => {
        setError(e.message)
        console.error(e)
      })
  }, [traceId])

  const spans: Span[] = []
  if (trace) {
    const total = Math.max(trace.duration_ms, 1)
    if (trace.ttft_ms != null) {
      spans.push({ label: '排队 + 首 token', start: 0, end: trace.ttft_ms, color: 'bg-amber-400' })
      spans.push({
        label: '流式生成',
        start: trace.ttft_ms,
        end: total,
        color: 'bg-primary',
      })
    } else {
      spans.push({ label: 'LLM 调用', start: 0, end: total, color: 'bg-primary' })
    }
    for (const ev of trace.tool_spans || []) {
      if (ev.type === 'tool_call') {
        spans.push({
          label: `工具: ${ev.name}`,
          start: ev.ts_ms ?? 0,
          end: Math.min((ev.ts_ms ?? 0) + 60, total),
          color: 'bg-emerald-400',
          detail: JSON.stringify(ev.args),
        })
      }
    }
  }

  return (
    <div className="flex h-full w-96 flex-col border-l border-gray-800 bg-surface-800/80">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-200">
          <Activity className="h-4 w-4 text-primary-light" /> 调用链路 Trace
        </div>
        <button
          onClick={onClose}
          className="cursor-pointer rounded p-1 text-gray-500 transition hover:bg-surface-700 hover:text-gray-300"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!trace && !error && <p className="text-sm text-gray-500">加载中…</p>}
        {trace && (
          <>
            <div className="mb-4 grid grid-cols-2 gap-2">
              {[
                { label: '模型', value: trace.model_name },
                { label: '总耗时', value: `${trace.duration_ms} ms` },
                { label: '首 token 延迟', value: trace.ttft_ms != null ? `${trace.ttft_ms} ms` : '-' },
                { label: '生成速率', value: `${trace.tokens_per_second} tok/s` },
                { label: '输入 tokens', value: String(trace.prompt_tokens) },
                { label: '输出 tokens', value: String(trace.completion_tokens) },
                { label: '估算成本', value: `$${trace.cost_usd.toFixed(6)}` },
                { label: '时间', value: new Date(trace.created_at + 'Z').toLocaleString() },
              ].map((item) => (
                <div key={item.label} className="rounded-lg bg-surface-900/60 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-gray-500">{item.label}</div>
                  <div className="mt-0.5 truncate text-sm text-gray-200">{item.value}</div>
                </div>
              ))}
            </div>

            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-gray-400">
              <Zap className="h-3.5 w-3.5" /> 时间线
            </h4>
            <div className="space-y-2">
              {spans.map((span, i) => {
                const total = Math.max(trace.duration_ms, 1)
                const left = Math.min((span.start / total) * 100, 100)
                const width = Math.max(((span.end - span.start) / total) * 100, 2)
                return (
                  <div key={i} title={span.detail || span.label}>
                    <div className="mb-1 flex justify-between text-[11px] text-gray-500">
                      <span className="truncate">{span.label}</span>
                      <span>{span.end - span.start} ms</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-surface-900">
                      <div
                        className={`h-full rounded-full ${span.color} transition-all duration-300`}
                        style={{ marginLeft: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            {trace.tool_spans?.length > 0 && (
              <>
                <h4 className="mb-2 mt-5 text-xs font-medium text-gray-400">工具调用明细</h4>
                <div className="space-y-2">
                  {trace.tool_spans.map((ev, i) => (
                    <div key={i} className="rounded-lg border border-gray-700/60 bg-surface-900/60 p-2.5">
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="font-medium text-emerald-300">{ev.name}</span>
                        <span className="text-gray-500">{ev.ts_ms ?? 0} ms</span>
                      </div>
                      <pre className="max-h-32 overflow-auto text-[11px] text-gray-500">
                        {JSON.stringify(ev.type === 'tool_call' ? ev.args : ev.response, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </>
            )}
            {trace.error && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
                {trace.error}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
