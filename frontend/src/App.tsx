import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import Usage from './pages/Usage'

function Protected({ children }: { children: JSX.Element }) {
  const { user, ready } = useAuth()
  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface-900">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const init = useAuth((s) => s.init)
  useEffect(() => {
    init()
  }, [init])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Protected><Chat /></Protected>} />
        <Route path="/settings" element={<Protected><Settings /></Protected>} />
        <Route path="/usage" element={<Protected><Usage /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
