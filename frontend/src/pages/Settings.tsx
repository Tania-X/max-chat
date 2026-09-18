import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Blocks, Brain, Cpu, GraduationCap, Plug } from 'lucide-react'
import CapabilitiesTab from '../components/settings/CapabilitiesTab'
import MemoryTab from '../components/settings/MemoryTab'
import ModelsTab from '../components/settings/ModelsTab'

const TABS = [
  { key: 'models', label: '模型配置', icon: Cpu },
  { key: 'plugin', label: '插件', icon: Blocks },
  { key: 'skill', label: 'Skill', icon: GraduationCap },
  { key: 'mcp', label: 'MCP', icon: Plug },
  { key: 'memory', label: '记忆与画像', icon: Brain },
] as const

type TabKey = (typeof TABS)[number]['key']

export default function Settings() {
  const [tab, setTab] = useState<TabKey>('models')
  const navigate = useNavigate()

  return (
    <div className="flex h-screen bg-surface-900">
      <aside className="flex w-56 flex-col border-r border-gray-800 bg-surface-800/60 p-4">
        <button
          onClick={() => navigate('/')}
          className="mb-6 flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-surface-700 hover:text-gray-200"
        >
          <ArrowLeft className="h-4 w-4" /> 返回聊天
        </button>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`mb-1 flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 ${
              tab === key
                ? 'bg-primary/15 text-gray-100'
                : 'text-gray-400 hover:bg-surface-700 hover:text-gray-200'
            }`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </aside>
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mx-auto max-w-2xl">
          {tab === 'models' && <ModelsTab />}
          {tab === 'plugin' && <CapabilitiesTab type="plugin" />}
          {tab === 'skill' && <CapabilitiesTab type="skill" />}
          {tab === 'mcp' && <CapabilitiesTab type="mcp" />}
          {tab === 'memory' && <MemoryTab />}
        </div>
      </main>
    </div>
  )
}
