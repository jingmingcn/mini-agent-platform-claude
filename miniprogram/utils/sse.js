/**
 * Streaming chat over SSE using wx.request({ enableChunked: true }).
 * - Incremental UTF-8 decoding (chunks may split multi-byte characters)
 * - SSE frame parsing (event:/data: lines separated by a blank line)
 * - abort() for "stop generating"; onError distinguishes user abort from network failures
 */
const { API_BASE, getToken } = require('./request')

class Utf8Decoder {
  constructor() { this.pending = [] }
  decode(buffer) {
    const bytes = this.pending.concat(Array.from(new Uint8Array(buffer)))
    let out = ''
    let i = 0
    while (i < bytes.length) {
      const b = bytes[i]
      let need = 0
      let cp = 0
      if (b < 0x80) { out += String.fromCharCode(b); i++; continue }
      else if ((b & 0xe0) === 0xc0) { need = 1; cp = b & 0x1f }
      else if ((b & 0xf0) === 0xe0) { need = 2; cp = b & 0x0f }
      else if ((b & 0xf8) === 0xf0) { need = 3; cp = b & 0x07 }
      else { out += '�'; i++; continue }
      if (i + need >= bytes.length) break // incomplete sequence: keep for next chunk
      for (let k = 1; k <= need; k++) cp = (cp << 6) | (bytes[i + k] & 0x3f)
      out += String.fromCodePoint(cp)
      i += need + 1
    }
    this.pending = bytes.slice(i)
    return out
  }
}

class SSEParser {
  constructor(onEvent) { this.buf = ''; this.onEvent = onEvent }
  feed(text) {
    this.buf += text.replace(/\r\n/g, '\n')
    let idx
    while ((idx = this.buf.indexOf('\n\n')) >= 0) {
      const block = this.buf.slice(0, idx)
      this.buf = this.buf.slice(idx + 2)
      let event = 'message'
      const data = []
      block.split('\n').forEach((line) => {
        if (line.startsWith(':')) return // comment / keep-alive
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''))
      })
      if (!data.length) continue
      let payload = data.join('\n')
      try { payload = JSON.parse(payload) } catch (e) { /* raw text */ }
      this.onEvent(event, payload)
    }
  }
}

/**
 * @param {object} body  {agent_id, conversation_id, content, attachment_ids, regenerate}
 * @param {object} handlers {onEvent(event, data), onDone(), onError(err)}
 * @returns {{abort: Function}}
 */
function streamChat(body, handlers) {
  const decoder = new Utf8Decoder()
  const parser = new SSEParser((ev, data) => handlers.onEvent && handlers.onEvent(ev, data))
  let status = 0
  let rawText = ''
  let aborted = false
  let finished = false
  const finish = (err) => {
    if (finished) return
    finished = true
    if (err) handlers.onError && handlers.onError(err)
    else handlers.onDone && handlers.onDone()
  }

  const task = wx.request({
    url: API_BASE + '/chat/stream',
    method: 'POST',
    data: body,
    enableChunked: true,
    responseType: 'arraybuffer',
    timeout: 300000,
    header: { 'content-type': 'application/json', Accept: 'text/event-stream', Authorization: `Bearer ${getToken()}` },
    success: (res) => {
      status = status || res.statusCode
      if (status !== 200) {
        // Non-stream JSON error (validation / permission). Body may come via chunks or res.data.
        let text = rawText
        if (!text && res.data) text = typeof res.data === 'string' ? res.data : decoder.decode(res.data)
        let msg = `请求失败(${status})`
        try { msg = JSON.parse(text).message || msg } catch (e) { /* ignore */ }
        const err = new Error(msg)
        err.statusCode = status
        return finish(err)
      }
      // Some base libraries deliver the whole body in res.data when chunking isn't supported.
      if (res.data && res.data.byteLength && !rawText) parser.feed(decoder.decode(res.data))
      finish()
    },
    fail: (e) => {
      if (aborted) return finish()
      const err = new Error('连接中断：' + (e.errMsg || ''))
      err.network = true
      finish(err)
    },
  })
  if (task && task.onHeadersReceived) task.onHeadersReceived((h) => { status = h.statusCode || status })
  if (task && task.onChunkReceived) {
    task.onChunkReceived((chunk) => {
      const text = decoder.decode(chunk.data)
      rawText += text
      if (status === 0 || status === 200) parser.feed(text)
    })
  }
  return {
    abort() { aborted = true; try { task.abort() } catch (e) { /* ignore */ } },
  }
}

module.exports = { streamChat, Utf8Decoder, SSEParser }
