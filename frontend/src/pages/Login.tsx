import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { useAuth } from '../store'

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') await login(username, password)
      else await register(username, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-surface-900">
      <div className="pointer-events-none absolute -top-40 left-1/4 h-96 w-96 rounded-full bg-primary/20 blur-[120px]" />
      <div className="pointer-events-none absolute bottom-0 right-1/4 h-80 w-80 rounded-full bg-indigo-500/10 blur-[100px]" />

      <div className="glass relative z-10 w-full max-w-md rounded-2xl p-8 shadow-2xl">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-dark shadow-lg shadow-primary/30">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-2xl font-semibold text-gray-50">MAX Chat</h1>
          <p className="mt-1 text-sm text-gray-400">多模型 · 记忆 · 插件 · 可观测的 AI 助手</p>
        </div>

        <div className="mb-6 flex rounded-lg bg-surface-800 p-1">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 cursor-pointer rounded-md py-2 text-sm transition-all duration-200 ${
                mode === m ? 'bg-primary text-white shadow' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {m === 'login' ? '登录' : '注册'}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">用户名</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-surface-800 px-3.5 py-2.5 text-sm text-gray-100 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
              placeholder="请输入用户名"
              required
              minLength={2}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-surface-800 px-3.5 py-2.5 text-sm text-gray-100 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
              placeholder="至少 6 位"
              required
              minLength={6}
            />
          </div>
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full cursor-pointer rounded-lg bg-gradient-to-r from-primary to-primary-dark py-2.5 text-sm font-medium text-white shadow-lg shadow-primary/25 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? '请稍候…' : mode === 'login' ? '登 录' : '注册并登录'}
          </button>
        </form>
      </div>
    </div>
  )
}
