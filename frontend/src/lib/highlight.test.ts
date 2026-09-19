import { describe, expect, it } from 'vitest'

import hljs, { resolveLanguage } from './highlight'

describe('highlight.js 按需注册', () => {
  it('注册了常用语言', () => {
    for (const lang of ['python', 'typescript', 'javascript', 'go', 'rust', 'sql', 'yaml', 'bash']) {
      expect(hljs.getLanguage(lang), `缺少语言 ${lang}`).toBeTruthy()
    }
  })

  it('不再打包全量语言', () => {
    // 直接 import 'highlight.js' 会带来 ~190 种语言，这里只保留白名单
    for (const lang of ['fortran', 'haskell', 'erlang', 'matlab', 'cobol', 'lisp']) {
      expect(hljs.getLanguage(lang), `不应注册 ${lang}`).toBeFalsy()
    }
  })

  it('常见别名可解析且真的能用于高亮', () => {
    // 注：hljs 自身也内置了一部分别名，因此解析结果可能是别名本身而非规范名，
    // 这里断言的是"能拿来高亮"这一实际契约。
    for (const alias of ['js', 'jsx', 'ts', 'tsx', 'py', 'sh', 'yml', 'C++', 'html', 'cs', 'kt']) {
      const resolved = resolveLanguage(alias)
      expect(resolved, `别名 ${alias} 未解析`).toBeTruthy()
      expect(hljs.getLanguage(resolved!)).toBeTruthy()
      expect(() => hljs.highlight('x = 1', { language: resolved! })).not.toThrow()
    }
  })

  it('规范化调用形式（大小写与空白）', () => {
    expect(resolveLanguage('  Python  ')).toBe('python')
    expect(resolveLanguage('PYTHON')).toBe('python')
  })

  it('未注册语言返回 null，由调用方决定降级策略', () => {
    expect(resolveLanguage('brainfuck')).toBeNull()
    expect(resolveLanguage('')).toBeNull()
  })

  it('高亮结果被转义，不会把代码里的标签注入 DOM', () => {
    const html = hljs.highlight('<img src=x onerror=alert(1)>', { language: 'xml' }).value
    expect(html).not.toContain('<img')
  })
})
