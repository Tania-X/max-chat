import { Suspense, lazy, useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store'

// 路由级代码分割：图表（recharts）与设置页此前被无条件打进主包
const Login = lazy(() => import('./pages/Login'))
const Chat = lazy(() => import('./pages/Chat'))
const Settings = lazy(() => import('./pages/Settings'))
const Usage = lazy(() => import('./pages/Usage'))

function FullscreenSpinner() {
  return (
    <div className="flex h-screen items-center justify-center bg-surface-900">
      <div
        role="status"
        aria-label="加载中"
        className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
      />
    </div>
  )
}

function Protected({ children }: { children: JSX.Element }) {
  const { user, ready } = useAuth()
  if (!ready) return <FullscreenSpinner />
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const init = useAuth((s) => s.init)
  useEffect(() => {
    init()
  }, [init])

  return (
    <BrowserRouter>
      <Suspense fallback={<FullscreenSpinner />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <Protected>
                <Chat />
              </Protected>
            }
          />
          <Route
            path="/settings"
            element={
              <Protected>
                <Settings />
              </Protected>
            }
          />
          <Route
            path="/usage"
            element={
              <Protected>
                <Usage />
              </Protected>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
