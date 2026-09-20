import { useEffect, useState } from 'react'
import { Activity, Brain, Trash2, UserCog } from 'lucide-react'
import { apiFetch } from '../../api/client'
import type { ExtractionStats, MemoryItem } from '../../types'

const CATEGORY_LABEL: Record<string, string> = {
  preference: '偏好',
  fact: '事实',
  habit: '习惯',
  general: '通用',
}

// 抽取失败原因：区分"没配 Key"和"模型不听话"，排查方向完全不同
const OUTCOME_LABEL: Record<string, string> = {
  ok: '成功',
  no_json: '模型未返回 JSON',
  bad_schema: 'JSON 结构不符',
  call_failed: '调用失败',
  skipped_no_key: '未配置抽取模型 Key',
}

/**
 * 单行画像。编辑期间只改本地 state，失焦/回车才写回服务端。
 * 此前是 onChange 直接 PUT —— 每敲一个字发一次请求，且响应乱序时会互相覆盖。
 */
function ProfileRow({
  name,
  value,
  onSave,
  onDelete,
}: {
  name: string
  value: string
  onSave: (value: string) => void
  onDelete: () => void
}) {
  const [draft, setDraft] = useState(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  const commit = () => {
    if (draft !== value) onSave(draft)
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-gray-800 bg-surface-800/60 px-3 py-2">
      <span className="w-28 shrink-0 text-xs font-medium text-primary-light">{name}</span>
      <input
        value={draft}
        aria-label={`画像 ${name}`}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur()
        }}
        className="flex-1 bg-transparent text-sm text-gray-200 outline-none"
      />
      <button
        onClick={onDelete}
        aria-label={`删除画像 ${name}`}
        className="cursor-pointer text-gray-600 transition hover:text-red-400"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export default function MemoryTab() {
  const [memories, setMemories] = useState<MemoryItem[]>([])
  const [profile, setProfile] = useState<Record<string, string>>({})
  const [stats, setStats] = useState<ExtractionStats | null>(null)
  const [newKey, setNewKey] = useState('')
  const [newValue, setNewValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const [memoryList, profileResp, extraction] = await Promise.all([
        apiFetch<MemoryItem[]>('/api/memory'),
        apiFetch<{ data: Record<string, string> }>('/api/profile'),
        apiFetch<ExtractionStats>('/api/memory/extraction/stats?days=30'),
      ])
      setMemories(memoryList)
      setProfile(profileResp.data)
      setStats(extraction)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const deleteMemory = async (id: string) => {
    try {
      await apiFetch(`/api/memory/${id}`, { method: 'DELETE' })
      setMemories((prev) => prev.filter((m) => m.id !== id))
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    }
  }

  const saveProfile = async (data: Record<string, string>) => {
    const previous = profile
    setProfile(data)
    try {
      await apiFetch('/api/profile', { method: 'PUT', body: JSON.stringify({ data }) })
      setError('')
    } catch (e) {
      setProfile(previous) // 失败回滚，避免界面显示与服务端不一致
      setError(e instanceof Error ? e.message : '保存失败')
    }
  }

  return (
    <div className="space-y-8">
      {error && (
        <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          {error}
        </p>
      )}

      <section>
        <h3 className="mb-1 flex items-center gap-2 text-sm font-medium text-gray-200">
          <UserCog className="h-4 w-4 text-primary-light" /> 用户画像
        </h3>
        <p className="mb-3 text-xs text-gray-500">
          AI 会从对话中自动沉淀你的画像，也可以手动补充，对话时将作为背景信息注入。
        </p>
        <div className="space-y-2">
          {Object.entries(profile).map(([k, v]) => (
            <ProfileRow
              key={k}
              name={k}
              value={v}
              onSave={(next) => saveProfile({ ...profile, [k]: next })}
              onDelete={() => {
                const next = { ...profile }
                delete next[k]
                saveProfile(next)
              }}
            />
          ))}
          <div className="flex items-center gap-2">
            <input
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="键，如 职业"
              aria-label="新画像的键"
              className="w-28 rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-xs outline-none focus:border-primary"
            />
            <input
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              placeholder="值，如 后端工程师"
              aria-label="新画像的值"
              className="flex-1 rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-xs outline-none focus:border-primary"
            />
            <button
              onClick={() => {
                if (newKey.trim()) {
                  saveProfile({ ...profile, [newKey.trim()]: newValue })
                  setNewKey('')
                  setNewValue('')
                }
              }}
              className="cursor-pointer rounded-lg bg-primary px-3 py-2 text-xs text-white transition hover:bg-primary-dark"
            >
              添加
            </button>
          </div>
        </div>
      </section>

      <section>
        <h3 className="mb-1 flex items-center gap-2 text-sm font-medium text-gray-200">
          <Brain className="h-4 w-4 text-primary-light" /> 长期记忆
        </h3>
        <p className="mb-3 text-xs text-gray-500">
          每轮对话后自动抽取的事实与偏好，相关记忆会在后续对话中注入上下文。
        </p>
        <div className="space-y-2">
          {memories.map((m) => (
            <div
              key={m.id}
              className="flex items-start gap-3 rounded-lg border border-gray-800 bg-surface-800/60 px-4 py-3"
            >
              <span className="mt-0.5 shrink-0 rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary-light">
                {CATEGORY_LABEL[m.category] || m.category}
              </span>
              <span className="flex-1 text-sm text-gray-300">{m.content}</span>
              <button
                onClick={() => deleteMemory(m.id)}
                aria-label="删除该条记忆"
                className="cursor-pointer text-gray-600 transition hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          {loading && <p className="py-6 text-center text-sm text-gray-600">加载中…</p>}
          {!loading && memories.length === 0 && (
            <p className="py-6 text-center text-sm text-gray-600">暂无记忆，聊几轮后会自动沉淀</p>
          )}
        </div>
      </section>

      {stats && stats.total > 0 && (
        <section>
          <h3 className="mb-1 flex items-center gap-2 text-sm font-medium text-gray-200">
            <Activity className="h-4 w-4 text-primary-light" /> 抽取健康度（近 {stats.days} 天）
          </h3>
          <p className="mb-3 text-xs text-gray-500">
            抽取在后台异步执行，这里可以看到它到底有没有在工作、失败时是什么原因。
          </p>

          <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              { label: '抽取次数', value: String(stats.total) },
              {
                label: '失败率',
                value: `${(stats.failure_rate * 100).toFixed(1)}%`,
                warn: stats.failure_rate > 0,
              },
              { label: '平均耗时', value: `${stats.avg_latency_ms} ms` },
              {
                label: '累计成本',
                value: `$${stats.total_cost_usd.toFixed(6)}`,
              },
            ].map(({ label, value, warn }) => (
              <div key={label} className="glass rounded-xl p-3">
                <div className={`text-base font-semibold ${warn ? 'text-amber-400' : 'text-gray-100'}`}>
                  {value}
                </div>
                <div className="mt-0.5 text-[11px] text-gray-500">{label}</div>
              </div>
            ))}
          </div>

          <p className="mb-3 text-xs text-gray-500">
            写入 {stats.memories_written} 条，跳过重复 {stats.duplicates_skipped} 条
          </p>

          {Object.keys(stats.by_outcome).some((o) => o !== 'ok') && (
            <div className="mb-3 flex flex-wrap gap-2">
              {Object.entries(stats.by_outcome)
                .filter(([outcome]) => outcome !== 'ok')
                .map(([outcome, count]) => (
                  <span
                    key={outcome}
                    className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-300"
                  >
                    {OUTCOME_LABEL[outcome] || outcome} × {count}
                  </span>
                ))}
            </div>
          )}

          {stats.recent_failures.length > 0 && (
            <details className="rounded-lg border border-gray-800 bg-surface-800/60 px-3 py-2">
              <summary className="cursor-pointer text-xs text-gray-400">
                最近 {stats.recent_failures.length} 次失败详情
              </summary>
              <ul className="mt-2 space-y-2">
                {stats.recent_failures.map((f, i) => (
                  <li key={i} className="text-[11px] text-gray-500">
                    <span className="text-amber-300/90">{OUTCOME_LABEL[f.outcome] || f.outcome}</span>
                    <span className="ml-2">{f.created_at.replace('T', ' ').slice(0, 19)}</span>
                    <div className="mt-0.5 break-all text-gray-400">{f.error}</div>
                    {f.raw_snippet && (
                      <pre className="mt-1 max-h-24 overflow-auto rounded bg-surface-900 px-2 py-1 text-[10px] text-gray-500">
                        {f.raw_snippet}
                      </pre>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
    </div>
  )
}
