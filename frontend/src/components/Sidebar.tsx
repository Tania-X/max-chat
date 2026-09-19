import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, LogOut, MessageSquare, Plus, Settings, Trash2 } from 'lucide-react'
import { useAuth, useChat } from '../store'

export default function Sidebar() {
  const { sessions, currentSessionId, selectSession, createSession, deleteSession, renameSession } =
    useChat()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const commitRename = async (id: string) => {
    if (editTitle.trim() && editTitle.trim() !== sessions.find((s) => s.id === id)?.title) {
      try {
        await renameSession(id, editTitle.trim())
      } catch (e) {
        console.error('重命名失败', e)
      }
    }
    setEditingId(null)
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-800 bg-surface-800/60">
      <div className="p-3">
        <button
          onClick={() => createSession()}
          className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2.5 text-sm font-medium text-white shadow-lg shadow-primary/25 transition hover:bg-primary-dark"
        >
          <Plus className="h-4 w-4" /> 新建会话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => selectSession(s.id)}
            className={`group mb-1 flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 ${
              s.id === currentSessionId
                ? 'bg-primary/15 text-gray-100'
                : 'text-gray-400 hover:bg-surface-700 hover:text-gray-200'
            }`}
          >
            <MessageSquare className="h-4 w-4 shrink-0 opacity-60" />
            {editingId === s.id ? (
              <input
                autoFocus
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => commitRename(s.id)}
                onKeyDown={(e) => e.key === 'Enter' && commitRename(s.id)}
                onClick={(e) => e.stopPropagation()}
                className="w-full rounded border border-primary/50 bg-surface-900 px-1.5 py-0.5 text-sm outline-none"
              />
            ) : (
              <span
                className="flex-1 truncate"
                onDoubleClick={(e) => {
                  e.stopPropagation()
                  setEditingId(s.id)
                  setEditTitle(s.title)
                }}
              >
                {s.title}
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                if (window.confirm(`删除会话「${s.title}」？该会话的消息将一并删除。`)) {
                  deleteSession(s.id).catch((err) => console.error('删除会话失败', err))
                }
              }}
              aria-label={`删除会话 ${s.title}`}
              className="cursor-pointer opacity-0 transition group-hover:opacity-60 focus-visible:opacity-100 hover:!opacity-100 hover:text-red-400"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-gray-600">暂无会话，点击上方新建</p>
        )}
      </div>

      <div className="border-t border-gray-800 p-3">
        <div className="mb-2 flex items-center gap-2.5 px-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-indigo-400 text-sm font-semibold text-white">
            {user?.display_name?.[0]?.toUpperCase() || 'U'}
          </div>
          <span className="flex-1 truncate text-sm text-gray-300">{user?.display_name}</span>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => navigate('/usage')}
            title="用量统计"
            className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-gray-400 transition hover:bg-surface-700 hover:text-gray-200"
          >
            <BarChart3 className="h-3.5 w-3.5" /> 用量
          </button>
          <button
            onClick={() => navigate('/settings')}
            title="设置"
            className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-gray-400 transition hover:bg-surface-700 hover:text-gray-200"
          >
            <Settings className="h-3.5 w-3.5" /> 设置
          </button>
          <button
            onClick={logout}
            title="退出登录"
            className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-gray-400 transition hover:bg-surface-700 hover:text-red-400"
          >
            <LogOut className="h-3.5 w-3.5" /> 退出
          </button>
        </div>
      </div>
    </aside>
  )
}
