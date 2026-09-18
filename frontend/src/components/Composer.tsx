import { useEffect, useRef, useState } from 'react'
import { Send, Square } from 'lucide-react'

export default function Composer({
  onSend,
  onStop,
  generating,
}: {
  onSend: (text: string) => void
  onStop: () => void
  generating: boolean
}) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    }
  }, [text])

  const submit = () => {
    const value = text.trim()
    if (!value || generating) return
    setText('')
    onSend(value)
  }

  return (
    <div className="border-t border-gray-800 bg-surface-900/80 p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-gray-700 bg-surface-800 p-2 shadow-xl transition focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/20">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          rows={1}
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-gray-100 outline-none placeholder:text-gray-600"
        />
        {generating ? (
          <button
            onClick={onStop}
            title="停止生成"
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl bg-red-500/90 text-white transition hover:bg-red-500"
          >
            <Square className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!text.trim()}
            title="发送"
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl bg-primary text-white shadow-lg shadow-primary/25 transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>
      <p className="mt-2 text-center text-[11px] text-gray-600">
        内容由 AI 生成，请注意甄别 · 支持 Markdown 输出
      </p>
    </div>
  )
}
