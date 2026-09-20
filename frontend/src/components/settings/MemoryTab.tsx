import { useEffect, useState } from 'react'
import { Brain, Trash2, UserCog } from 'lucide-react'
import { apiFetch } from '../../api/client'
import type { MemoryItem } from '../../types'

const CATEGORY_LABEL: Record<string, string> = {
  preference: '偏好',
  fact: '事实',
  habit: '习惯',
  general: '通用',
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
  const [newKey, setNewKey] = useState('')
  const [newValue, setNewValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const [memoryList, profileResp] = await Promise.all([
        apiFetch<MemoryItem[]>('/api/memory'),
        apiFetch<{ data: Record<string, string> }>('/api/profile'),
      ])
      setMemories(memoryList)
      setProfile(profileResp.data)
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
    </div>
  )
}
