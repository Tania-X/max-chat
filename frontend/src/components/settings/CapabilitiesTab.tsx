import { useEffect, useState } from 'react'
import { Plus, Settings2, X } from 'lucide-react'
import { apiFetch } from '../../api/client'
import type { Capability } from '../../types'

const TYPE_LABEL: Record<string, string> = { plugin: '插件', skill: 'Skill', mcp: 'MCP Server' }

export default function CapabilitiesTab({ type }: { type: 'plugin' | 'skill' | 'mcp' }) {
  const [items, setItems] = useState<Capability[]>([])
  const [editing, setEditing] = useState<Capability | null>(null)
  const [configText, setConfigText] = useState('')
  const [configError, setConfigError] = useState('')
  const [showMcpForm, setShowMcpForm] = useState(false)
  const [mcpForm, setMcpForm] = useState({
    name: '', description: '', transport: 'stdio', command: '', args: '', url: '',
  })

  const load = () =>
    apiFetch<Capability[]>('/api/capabilities').then(setItems).catch((e) => console.error(e))
  useEffect(() => {
    load()
  }, [])

  const toggle = async (cap: Capability) => {
    await apiFetch(`/api/capabilities/${cap.id}/enabled`, {
      method: 'PUT',
      body: JSON.stringify({ enabled: !cap.enabled }),
    })
    load()
  }

  const saveConfig = async () => {
    if (!editing) return
    try {
      const config = configText.trim() ? JSON.parse(configText) : {}
      await apiFetch(`/api/capabilities/${editing.id}/config`, {
        method: 'PUT',
        body: JSON.stringify({ config }),
      })
      setEditing(null)
      load()
    } catch {
      setConfigError('JSON 格式错误，请检查')
    }
  }

  const addMcp = async () => {
    const config =
      mcpForm.transport === 'stdio'
        ? {
            transport: 'stdio',
            command: mcpForm.command,
            args: mcpForm.args.split(' ').filter(Boolean),
          }
        : { transport: 'sse', url: mcpForm.url }
    await apiFetch('/api/capabilities/mcp', {
      method: 'POST',
      body: JSON.stringify({ name: mcpForm.name, description: mcpForm.description, config }),
    })
    setShowMcpForm(false)
    setMcpForm({ name: '', description: '', transport: 'stdio', command: '', args: '', url: '' })
    load()
  }

  const filtered = items.filter((c) => c.type === type)

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-200">{TYPE_LABEL[type]}管理</h3>
        {type === 'mcp' && (
          <button
            onClick={() => setShowMcpForm(!showMcpForm)}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs text-white transition hover:bg-primary-dark"
          >
            <Plus className="h-3.5 w-3.5" /> 添加 MCP Server
          </button>
        )}
      </div>

      {showMcpForm && type === 'mcp' && (
        <div className="mb-4 space-y-3 rounded-xl border border-primary/30 bg-surface-800 p-4">
          <div className="grid grid-cols-2 gap-3">
            <input
              value={mcpForm.name}
              onChange={(e) => setMcpForm({ ...mcpForm, name: e.target.value })}
              placeholder="名称，如 filesystem"
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            />
            <input
              value={mcpForm.description}
              onChange={(e) => setMcpForm({ ...mcpForm, description: e.target.value })}
              placeholder="描述（可选）"
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            />
            <select
              value={mcpForm.transport}
              onChange={(e) => setMcpForm({ ...mcpForm, transport: e.target.value })}
              className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
            >
              <option value="stdio">stdio（本地命令）</option>
              <option value="sse">sse（远程 URL）</option>
            </select>
            {mcpForm.transport === 'stdio' ? (
              <>
                <input
                  value={mcpForm.command}
                  onChange={(e) => setMcpForm({ ...mcpForm, command: e.target.value })}
                  placeholder="命令，如 npx"
                  className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
                />
                <input
                  value={mcpForm.args}
                  onChange={(e) => setMcpForm({ ...mcpForm, args: e.target.value })}
                  placeholder="参数，空格分隔，如 -y @modelcontextprotocol/server-filesystem D:\docs"
                  className="col-span-2 rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
                />
              </>
            ) : (
              <input
                value={mcpForm.url}
                onChange={(e) => setMcpForm({ ...mcpForm, url: e.target.value })}
                placeholder="SSE URL，如 http://127.0.0.1:3001/sse"
                className="rounded-lg border border-gray-700 bg-surface-900 px-3 py-2 text-sm outline-none focus:border-primary"
              />
            )}
          </div>
          <button
            onClick={addMcp}
            disabled={!mcpForm.name || (mcpForm.transport === 'stdio' ? !mcpForm.command : !mcpForm.url)}
            className="cursor-pointer rounded-lg bg-primary px-4 py-2 text-xs text-white transition hover:bg-primary-dark disabled:opacity-40"
          >
            保存
          </button>
        </div>
      )}

      <div className="space-y-2">
        {filtered.map((cap) => (
          <div
            key={cap.id}
            className="flex items-center gap-3 rounded-xl border border-gray-800 bg-surface-800/60 px-4 py-3 transition hover:border-gray-700"
          >
            <button
              onClick={() => toggle(cap)}
              className={`relative h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${
                cap.enabled ? 'bg-primary' : 'bg-gray-700'
              }`}
            >
              <span
                className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all duration-200 ${
                  cap.enabled ? 'left-[18px]' : 'left-0.5'
                }`}
              />
            </button>
            <div className="flex-1">
              <div className="text-sm text-gray-200">{cap.name}</div>
              <div className="mt-0.5 text-xs text-gray-500">{cap.description || '暂无描述'}</div>
            </div>
            <button
              onClick={() => {
                setEditing(cap)
                setConfigText(JSON.stringify(cap.config, null, 2))
                setConfigError('')
              }}
              className="cursor-pointer rounded-md p-1.5 text-gray-500 transition hover:bg-surface-700 hover:text-primary-light"
              title="配置"
            >
              <Settings2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="py-8 text-center text-sm text-gray-600">
            {type === 'mcp'
              ? '尚未添加 MCP Server'
              : `未发现${TYPE_LABEL[type]}，可在 backend/${type === 'plugin' ? 'plugins' : 'skills'}/ 目录下添加`}
          </p>
        )}
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="glass w-full max-w-lg rounded-2xl p-5">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-200">配置：{editing.name}</h4>
              <button
                onClick={() => setEditing(null)}
                className="cursor-pointer text-gray-500 transition hover:text-gray-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea
              value={configText}
              onChange={(e) => {
                setConfigText(e.target.value)
                setConfigError('')
              }}
              rows={10}
              className="w-full rounded-lg border border-gray-700 bg-surface-900 p-3 font-mono text-xs text-gray-200 outline-none focus:border-primary"
              placeholder="{ }"
            />
            {configError && <p className="mt-1 text-xs text-red-400">{configError}</p>}
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => setEditing(null)}
                className="cursor-pointer rounded-lg px-4 py-2 text-xs text-gray-400 transition hover:bg-surface-700"
              >
                取消
              </button>
              <button
                onClick={saveConfig}
                className="cursor-pointer rounded-lg bg-primary px-4 py-2 text-xs text-white transition hover:bg-primary-dark"
              >
                保存配置
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
