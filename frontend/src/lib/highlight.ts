/**
 * 按需注册 highlight.js 语言。
 *
 * 直接 `import hljs from 'highlight.js'` 会把全部 ~190 种语言打进主包
 * （构建产物里能搜到 fortran / haskell / erlang / matlab 等），是 bundle 膨胀的
 * 主要原因。这里只注册常见语言，其余语言退化为不高亮。
 */

import hljs from 'highlight.js/lib/core'

import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import csharp from 'highlight.js/lib/languages/csharp'
import css from 'highlight.js/lib/languages/css'
import diff from 'highlight.js/lib/languages/diff'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import go from 'highlight.js/lib/languages/go'
import ini from 'highlight.js/lib/languages/ini'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import kotlin from 'highlight.js/lib/languages/kotlin'
import markdown from 'highlight.js/lib/languages/markdown'
import php from 'highlight.js/lib/languages/php'
import python from 'highlight.js/lib/languages/python'
import ruby from 'highlight.js/lib/languages/ruby'
import rust from 'highlight.js/lib/languages/rust'
import sql from 'highlight.js/lib/languages/sql'
import swift from 'highlight.js/lib/languages/swift'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

const LANGUAGES = {
  bash,
  c,
  cpp,
  csharp,
  css,
  diff,
  dockerfile,
  go,
  ini,
  java,
  javascript,
  json,
  kotlin,
  markdown,
  php,
  python,
  ruby,
  rust,
  sql,
  swift,
  typescript,
  xml,
  yaml,
}

for (const [name, definition] of Object.entries(LANGUAGES)) {
  hljs.registerLanguage(name, definition)
}

// 常见别名，让 ```js / ```ts / ```yml / ```sh 之类也能命中
const ALIASES: Record<string, string> = {
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  zsh: 'bash',
  yml: 'yaml',
  html: 'xml',
  vue: 'xml',
  'c++': 'cpp',
  cs: 'csharp',
  kt: 'kotlin',
  rb: 'ruby',
  golang: 'go',
  toml: 'ini',
  conf: 'ini',
  md: 'markdown',
}

export function resolveLanguage(language: string): string | null {
  const key = language.trim().toLowerCase()
  if (!key) return null
  if (hljs.getLanguage(key)) return key
  const alias = ALIASES[key]
  return alias && hljs.getLanguage(alias) ? alias : null
}

export default hljs
