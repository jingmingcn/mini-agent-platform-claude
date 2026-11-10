function fmtTime(s) {
  if (!s) return ''
  const d = new Date(/Z|\+/.test(s) ? s : s + 'Z')
  const now = new Date()
  const p = (n) => (n < 10 ? '0' + n : '' + n)
  if (d.toDateString() === now.toDateString()) return `${p(d.getHours())}:${p(d.getMinutes())}`
  return `${d.getMonth() + 1}-${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function throttle(fn, wait) {
  let last = 0
  let timer = null
  return function (...args) {
    const now = Date.now()
    const remaining = wait - (now - last)
    clearTimeout(timer)
    if (remaining <= 0) { last = now; fn.apply(this, args) }
    else timer = setTimeout(() => { last = Date.now(); fn.apply(this, args) }, remaining)
  }
}

/** Convert a server message to the unified client message protocol. */
function normalizeMessage(m) {
  return {
    id: m.id,
    role: m.role,
    type: m.message_type || (m.role === 'assistant' ? 'markdown' : 'text'),
    content: m.content || '',
    attachments: m.attachments || [],
    citations: m.citations || [],
    status: m.status || 'completed',
    feedback: m.feedback || 0,
  }
}

module.exports = { fmtTime, throttle, normalizeMessage }
