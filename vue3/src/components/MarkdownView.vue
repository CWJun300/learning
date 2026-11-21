<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import 'highlight.js/styles/github.css'

const props = defineProps({
  source: { type: String, default: '' },
})

const md = new MarkdownIt({
  // 关闭原生 HTML：即使有人写 <script>，markdown-it 也会把它当文本转义
  html: false,
  linkify: true,
  breaks: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch {
        /* 高亮失败时退回纯文本 */
      }
    }
    return ''
  },
})

const rendered = computed(() =>
  // 第二道防线：即便 markdown-it 配置被改动，DOMPurify 也会清掉危险标签
  DOMPurify.sanitize(md.render(props.source || '')),
)
</script>

<template>
  <div class="markdown-body" v-html="rendered" />
</template>

<style>
.markdown-body {
  line-height: 1.75;
  word-break: break-word;
  color: #303133;
}
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin: 1em 0 0.5em;
  font-weight: 600;
}
.markdown-body p {
  margin: 0.6em 0;
}
.markdown-body code {
  background: #f5f7fa;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 0.9em;
}
.markdown-body pre {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
.markdown-body pre code {
  background: transparent;
  padding: 0;
}
.markdown-body blockquote {
  margin: 0.8em 0;
  padding-left: 12px;
  border-left: 3px solid #dcdfe6;
  color: #606266;
}
.markdown-body ul,
.markdown-body ol {
  padding-left: 1.5em;
}
.markdown-body img {
  max-width: 100%;
}
</style>
