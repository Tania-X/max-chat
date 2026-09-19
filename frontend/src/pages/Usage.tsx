import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Coins, Gauge, Timer, Zap } from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { apiFetch } from '../api/client'
import type { UsageSummary } from '../types'

const COLORS = ['#6366F1', '#818CF8', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

export default function Usage() {
  const [days, setDays] = useState(30)
  const [data, setData] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    apiFetch<UsageSummary>(`/api/usage/summary?days=${days}`)
      .then((result) => {
        if (cancelled) return // 快速切换区间时丢弃过期响应
        setData(result)
        setError('')
      })
      .catch((e) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : '加载失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [days])

  const cards = data
    ? [
        { label: '总调用次数', value: data.total_calls, icon: Zap, color: 'text-primary-light' },
        { label: '总 Token', value: (data.total_prompt_tokens + data.total_completion_tokens).toLocaleString(), icon: Gauge, color: 'text-emerald-400' },
        { label: '估算总成本', value: `$${data.total_cost_usd.toFixed(4)}`, icon: Coins, color: 'text-amber-400' },
        { label: '平均首 token 延迟', value: `${data.avg_ttft_ms} ms`, icon: Timer, color: 'text-indigo-300' },
        { label: '平均生成速率', value: `${data.avg_tokens_per_second} tok/s`, icon: Gauge, color: 'text-sky-400' },
      ]
    : []

  return (
    <div className="min-h-screen bg-surface-900 p-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-surface-700 hover:text-gray-200"
          >
            <ArrowLeft className="h-4 w-4" /> 返回聊天
          </button>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-gray-700 bg-surface-800 px-3 py-1.5 text-xs text-gray-300 outline-none focus:border-primary"
          >
            <option value={7}>近 7 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
        </div>

        <h1 className="mb-6 text-xl font-semibold text-gray-100">用量与成本观测</h1>

        {error && (
          <p role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            加载用量数据失败：{error}
          </p>
        )}
        {loading && !data && <p className="text-sm text-gray-500">加载中…</p>}
        {data && (
          <>
            <div className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-5">
              {cards.map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="glass rounded-xl p-4 transition hover:border-primary/40">
                  <Icon className={`mb-2 h-5 w-5 ${color}`} />
                  <div className="text-lg font-semibold text-gray-100">{value}</div>
                  <div className="mt-0.5 text-[11px] text-gray-500">{label}</div>
                </div>
              ))}
            </div>

            <div className="mb-8 grid gap-6 md:grid-cols-2">
              <div className="glass rounded-xl p-5">
                <h3 className="mb-4 text-sm font-medium text-gray-300">每日 Token 消耗</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={data.by_day}>
                    <defs>
                      <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366F1" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                    />
                    <Area type="monotone" dataKey="tokens" stroke="#6366F1" fill="url(#tokenGrad)" name="tokens" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="glass rounded-xl p-5">
                <h3 className="mb-4 text-sm font-medium text-gray-300">每日成本 (USD)</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.by_day}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                    />
                    <Bar dataKey="cost_usd" fill="#F59E0B" radius={[4, 4, 0, 0]} name="成本" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="glass rounded-xl p-5">
                <h3 className="mb-4 text-sm font-medium text-gray-300">按模型的成本占比</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={data.by_model}
                      dataKey="cost_usd"
                      nameKey="model_name"
                      innerRadius={50}
                      outerRadius={85}
                      paddingAngle={3}
                    >
                      {data.by_model.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="glass rounded-xl p-5">
                <h3 className="mb-4 text-sm font-medium text-gray-300">模型调用明细</h3>
                <div className="space-y-2">
                  {data.by_model.map((m) => (
                    <div key={m.model_name} className="rounded-lg bg-surface-900/60 px-3 py-2.5">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-200">{m.model_name}</span>
                        <span className="text-amber-400">${m.cost_usd.toFixed(5)}</span>
                      </div>
                      <div className="mt-1 flex justify-between text-[11px] text-gray-500">
                        <span>{m.provider} · {m.calls} 次调用</span>
                        <span>{(m.prompt_tokens + m.completion_tokens).toLocaleString()} tokens</span>
                      </div>
                    </div>
                  ))}
                  {data.by_model.length === 0 && (
                    <p className="py-6 text-center text-sm text-gray-600">暂无调用记录</p>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
