/**
 * Minimal Markdown -> blocks renderer for <rich-text>.
 * Returns [{type:'html', html}, {type:'code', lang, code}] so code blocks can get a copy button.
 * All text is HTML-escaped first; only our own tags are emitted (no raw HTML passthrough).
 */
const S = {
  h: ['font-size:36rpx;font-weight:700;margin:20rpx 0 12rpx;', 'font-size:33rpx;font-weight:700;margin:18rpx 0 10rpx;', 'font-size:30rpx;font-weight:600;margin:16rpx 0 8rpx;'],
  p: 'margin:8rpx 0;line-height:1.75;',
  li: 'margin:4rpx 0;line-height:1.7;',
  list: 'padding-left:36rpx;margin:8rpx 0;',
  quote: 'border-left:6rpx solid #c7d2fe;padding:6rpx 18rpx;color:#4b5563;background:#f5f7ff;margin:10rpx 0;',
  code: 'background:#f1f3f7;padding:2rpx 8rpx;border-radius:6rpx;font-family:Menlo,monospace;font-size:24rpx;color:#c7254e;',
  table: 'border-collapse:collapse;width:100%;margin:12rpx 0;font-size:24rpx;',
  th: 'border:1px solid #e5e7eb;padding:8rpx 12rpx;background:#f8fafc;font-weight:600;text-align:left;',
  td: 'border:1px solid #e5e7eb;padding:8rpx 12rpx;',
  hr: 'border:none;border-top:1px solid #e5e7eb;margin:16rpx 0;',
  cite: 'display:inline-block;font-size:20rpx;color:#3b5bfd;background:#eef2ff;border-radius:6rpx;padding:0 8rpx;margin:0 2rpx;vertical-align:super;line-height:1.4;',
  link: 'color:#3b5bfd;text-decoration:underline;',
}

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function inline(text) {
  let s = esc(text)
  const codes = []
  s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000` })
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
  s = s.replace(/~~([^~]+)~~/g, '<del>$1</del>')
  s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, `<span style="${S.link}">$1</span>`)
  s = s.replace(/\[(\d{1,2})\]/g, `<span style="${S.cite}">$1</span>`)
  s = s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code style="${S.code}">${codes[+i]}</code>`)
  return s
}

function splitRow(line) {
  return line.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
}

function render(md) {
  const lines = (md || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let html = ''
  const flush = () => { if (html) { blocks.push({ type: 'html', html }); html = '' } }
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    const fence = line.match(/^\s*```(\w*)/)
    if (fence) {
      const code = []
      i++
      while (i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i++])
      i++ // closing fence (may be missing while streaming)
      flush()
      blocks.push({ type: 'code', lang: fence[1] || '', code: code.join('\n') })
      continue
    }
    if (!line.trim()) { i++; continue }
    const h = line.match(/^(#{1,6})\s+(.*)$/)
    if (h) { html += `<div style="${S.h[Math.min(h[1].length, 3) - 1]}">${inline(h[2])}</div>`; i++; continue }
    if (/^\s*([-*_])\s*\1\s*\1[\s\1]*$/.test(line)) { html += `<hr style="${S.hr}"/>`; i++; continue }
    if (/^\s*>/.test(line)) {
      const q = []
      while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ''))
      html += `<div style="${S.quote}">${q.map(inline).join('<br/>')}</div>`
      continue
    }
    if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const head = splitRow(line)
      i += 2
      let t = `<table style="${S.table}"><tr>${head.map((c) => `<th style="${S.th}">${inline(c)}</th>`).join('')}</tr>`
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        t += `<tr>${splitRow(lines[i++]).map((c) => `<td style="${S.td}">${inline(c)}</td>`).join('')}</tr>`
      }
      html += t + '</table>'
      continue
    }
    const ul = /^\s*[-*+]\s+/
    const ol = /^\s*\d+[.)]\s+/
    if (ul.test(line) || ol.test(line)) {
      const ordered = ol.test(line)
      const re = ordered ? ol : ul
      const items = []
      while (i < lines.length && re.test(lines[i])) items.push(lines[i++].replace(re, ''))
      const tag = ordered ? 'ol' : 'ul'
      html += `<${tag} style="${S.list}">${items.map((it) => `<li style="${S.li}">${inline(it)}</li>`).join('')}</${tag}>`
      continue
    }
    const para = []
    while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|\s*```|\s*>|\s*[-*+]\s+|\s*\d+[.)]\s+)/.test(lines[i])) {
      para.push(lines[i++])
    }
    if (!para.length) para.push(lines[i++])
    html += `<div style="${S.p}">${para.map(inline).join('<br/>')}</div>`
  }
  flush()
  return blocks
}

module.exports = { render, esc }
