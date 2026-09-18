import { useEffect, useState } from 'react'
import { Plus, Trash2, Zap } from 'lucide-react'
import { apiFetch } from '../../api/client'
import type { ModelConfig } from '../../types'

const PROVIDERS = ['gemini', 'openai', 'anthropic', 'deepseek', 'openrouter']

const empty = { provider: 'gemini', model_name: '', api_key: '', base_url: '', label: '', is_default: false }

export default function ModelsTab() {
  const [models, setModels] = useState<ModelConfig[]>([])
  const [form, setForm] = useState(empty)
  const [showForm, setShowForm] = useState(false)
  const [testResult, setTestResult] = useState<Record<string, string>>({})

  const load = () =>
    apiFetch<ModelConfig[]>('/api/models').then(setModels).catch((e) => console.error(e))
  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    await apiFetch('/api/models', { method: 'POST', body: JSON.stringify(form) })
    setForm(empty)
    setShowForm(false)
    load()
  }

  const remove = async (id: string) => {
    await apiFetch(`/api/models/${id}`, { method: 'DELETE' })
    load()
  }

  const setDefault = async (m: ModelConfig) => {
    await apiFetch(`/api/models/${m.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        provider: m.provider, model_name: m.model_name, base_url: m.base_url,
        label: m.label, is_default: true,
      }),
    })
    load()
  }

  const test = async (m: ModelConfig) => {
    setTestResult({ ...testResult, [m.id]: '测试中…' })
    const resp = await apiFetch<{ ok: boolean; latency_ms?: number; error?: string }>(
      '/api/models/test',
      { method: 'POST', body: JSON.stringify({ provider: m.provider, model_name: m.model_name }) },
    )
    setTestResult({
      ...testResult,
      [m.id]: resp.ok ? `连通正常 · ${resp.latency_ms}ms` : `失败: ${resp.error?.slice(0, 80)}`,
    })
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-200">模型配置</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs text-white transition hover:bg-primary-dark"
        >
          <Plus className="h-3.5 w-3.5" /> 添加模型
        </button>
      </div>

      {showForm && (
        <div className="mb-4 space-y-3 rounded-xl border border-primary/30 bg-surface-800 p-4">
          <div className="grid grid-cols-2 gap-3">
            <select
              value={form.provider}
              onChange={(e) => setForm({ ...form, provider: e.target.value })}
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            >
              {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <input
              value={form.model_name}
              onChange={(e) => setForm({ ...form, model_name: e.target.value })}
              placeholder="模型名，如 gemini-2.0-flash / gpt-4o"
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            />
            <input
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              placeholder="API Key（加密存储）"
              type="password"
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            />
            <input
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              placeholder="Base URL（可选）"
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
            />
            设为默认模型
          </label>
          <button
            onClick={create}
            disabled={!form.model_name}
            className="cursor-pointer rounded-lg bg-primary px-4 py-2 text-xs text-white transition hover:bg-primary-dark disabled:opacity-40"
          >
            保存
          </button>
        </div>
      )}

      <div className="space-y-2">
        {models.map((m) => (
          <div
            key={m.id}
            className="flex items-center gap-3 rounded-xl border border-gray-800 bg-surface-800/60 px-4 py-3 transition hover:border-gray-700"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2 text-sm text-gray-200">
                {m.label}
                {m.is_default && (
                  <span className="rounded bg-primary/20 px-1.5 py-0.5 text-[10px] text-primary-light">默认</span>
                )}
              </div>
              <div className="mt-0.5 text-xs text-gray-500">
                {m.provider}/{m.model_name} · {m.has_api_key ? '已配置 Key' : '使用环境变量 Key'}
              </div>
              {testResult[m.id] && (
                <div className="mt-1 text-[11px] text-gray-400">{testResult[m.id]}</div>
              )}
            </div>
            <button
              onClick={() => test(m)}
              title="测试连通性"
              className="cursor-pointer rounded-md p-1.5 text-gray-500 transition hover:bg-surface-700 hover:text-emerald-400"
            >
              <Zap className="h-4 w-4" />
            </button>
            {!m.is_default && (
              <button
                onClick={() => setDefault(m)}
                className="cursor-pointer rounded-md px-2 py-1 text-[11px] text-gray-500 transition hover:bg-surface-700 hover:text-primary-light"
              >
                设为默认
              </button>
            )}
            <button
              onClick={() => remove(m.id)}
              className="cursor-pointer rounded-md p-1.5 text-gray-500 transition hover:bg-surface-700 hover:text-red-400"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        {models.length === 0 && (
          <p className="py-8 text-center text-sm text-gray-600">
            暂无模型配置。添加一个，或在后端 .env 中配置 GOOGLE_API_KEY 作为兜底。
          </p>
        )}
      </div>
    </div>
  )
}
