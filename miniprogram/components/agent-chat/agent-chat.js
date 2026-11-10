/**
 * AgentChat: the full chat experience for one agent / conversation.
 * Streams answers over SSE, supports stop / regenerate / attachments, and recovers after disconnects
 * by reloading the server copy (partial answers are persisted as "interrupted").
 */
const { http } = require('../../utils/request')
const { streamChat } = require('../../utils/sse')
const { normalizeMessage, throttle } = require('../../utils/util')

let keySeq = 0
const nextKey = () => `k${Date.now()}_${++keySeq}`

Component({
  properties: {
    agentId: { type: Number, value: 0 },
    conversationId: { type: Number, value: 0 },
  },
  data: {
    agent: {}, messages: [], input: '', busy: false, canSend: false, banner: '',
    attachmentIds: [], attachmentFiles: [], uploading: false, keyboardHeight: 0, safeBottom: 0,
  },
  lifetimes: {
    attached() {
      const info = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
      this.setData({ safeBottom: info.safeArea ? Math.max(0, info.screenHeight - info.safeArea.bottom) : 0 })
      this.flushDelta = throttle(() => this._flush(), 60)
    },
    detached() { if (this.task) this.task.abort() },
  },
  observers: {
    'agentId, conversationId'(agentId, conversationId) {
      if (agentId || conversationId) this.init()
    },
  },
  methods: {
    async init() {
      if (this._inited) return
      this._inited = true
      this.convId = this.data.conversationId || 0
      try {
        if (this.convId) await this.reloadMessages()
        const agentId = this.data.agentId || (this.data.agent && this.data.agent.id)
        if (agentId) {
          const agent = await http.get(`/agents/${agentId}`)
          this.setData({ agent })
          this.triggerEvent('agent', { agent })
        }
      } catch (e) {
        this.setData({ banner: e.message || '加载失败' })
      }
    },

    async reloadMessages() {
      const res = await http.get(`/conversations/${this.convId}/messages`)
      const messages = res.items.map((m) => ({ ...normalizeMessage(m), key: 'm' + m.id }))
      this.setData({ messages })
      if (!this.data.agentId && res.conversation) this.setData({ agentId: res.conversation.agent_id })
    },

    onInput(e) { this.setData({ input: e.detail.value }, () => this.updateCanSend()) },
    onKeyboard(e) { this.setData({ keyboardHeight: e.detail.height || 0 }) },
    onFiles(e) {
      this.setData({ attachmentIds: e.detail.ids, attachmentFiles: e.detail.files, uploading: e.detail.uploading }, () => this.updateCanSend())
    },
    updateCanSend() {
      const d = this.data
      this.setData({ canSend: !d.busy && !d.uploading && (!!d.input.trim() || d.attachmentIds.length > 0) })
    },
    onAsk(e) { this.send(null, e.detail.content) },

    send(_e, preset) {
      const content = (preset || this.data.input).trim()
      if (this.data.busy) return
      if (this.data.uploading) return wx.showToast({ title: '附件上传中', icon: 'none' })
      if (!content && !this.data.attachmentIds.length) return
      const userMsg = { key: nextKey(), id: 0, role: 'user', type: 'text', content, attachments: this.data.attachmentFiles,
        citations: [], status: 'completed', feedback: 0 }
      const body = { agent_id: this.data.agentId || undefined, conversation_id: this.convId || undefined,
        content, attachment_ids: this.data.attachmentIds }
      this.setData({ input: '', attachmentIds: [], attachmentFiles: [] })
      const up = this.selectComponent('#uploader')
      if (up) up.clear()
      this.startStream(body, userMsg)
    },

    regenerate() {
      if (this.data.busy || !this.convId) return
      const messages = this.data.messages.slice()
      while (messages.length && messages[messages.length - 1].role !== 'user') messages.pop()
      this.setData({ messages })
      this.startStream({ conversation_id: this.convId, regenerate: true }, null)
    },

    startStream(body, userMsg) {
      const assistant = { key: nextKey(), id: 0, role: 'assistant', type: 'markdown', content: '', attachments: [],
        citations: [], status: 'streaming', feedback: 0, phase: '思考中' }
      const messages = this.data.messages.concat(userMsg ? [userMsg, assistant] : [assistant])
      this.aIndex = messages.length - 1
      this.uIndex = userMsg ? messages.length - 2 : -1
      this.buffer = ''
      this.assistantId = 0
      this.setData({ messages, busy: true, banner: '' }, () => this.updateCanSend())

      this.task = streamChat(body, {
        onEvent: (ev, data) => this.onEvent(ev, data),
        onDone: () => this.finish(),
        onError: (err) => this.onStreamError(err),
      })
    },

    onEvent(ev, data) {
      const i = this.aIndex
      if (ev === 'meta') {
        const isNew = !this.convId
        this.convId = data.conversation_id
        this.assistantId = data.assistant_message_id
        const patch = { [`messages[${i}].id`]: data.assistant_message_id }
        if (this.uIndex >= 0) patch[`messages[${this.uIndex}].id`] = data.user_message_id
        this.setData(patch)
        if (isNew) this.triggerEvent('conversation', { id: data.conversation_id, title: data.title })
      } else if (ev === 'citations') {
        this.setData({ [`messages[${i}].citations`]: data.items || [], [`messages[${i}].phase`]: (data.items || []).length ? '已检索知识库，正在生成' : '正在生成' })
      } else if (ev === 'tool') {
        this.setData({ [`messages[${i}].phase`]: `调用工具 ${data.name}…` })
      } else if (ev === 'delta') {
        this.buffer += data.content || ''
        this.flushDelta()
      } else if (ev === 'error') {
        this.errorMessage = data.message
      } else if (ev === 'done') {
        this._flush()
        const status = data.status || 'completed'
        const patch = { [`messages[${i}].status`]: status }
        if (status === 'error') {
          patch[`messages[${i}].type`] = 'error'
          patch[`messages[${i}].content`] = this.buffer || this.errorMessage || '生成失败'
        }
        this.setData(patch)
      }
    },

    _flush() {
      if (this.aIndex == null) return
      this.setData({ [`messages[${this.aIndex}].content`]: this.buffer })
    },

    finish() {
      const i = this.aIndex
      const m = this.data.messages[i]
      if (m && m.status === 'streaming') this.setData({ [`messages[${i}].status`]: 'completed' })
      this.task = null
      this.errorMessage = ''
      this.setData({ busy: false }, () => this.updateCanSend())
    },

    async onStreamError(err) {
      const i = this.aIndex
      this.task = null
      if (err.network && this.convId) {
        // Connection dropped mid-stream: server has saved the partial answer. Reconnect by reloading.
        this.setData({ banner: '网络中断，正在恢复会话…' })
        setTimeout(async () => {
          try { await this.reloadMessages(); this.setData({ banner: '' }) } catch (e) { this.setData({ banner: '恢复失败，请下拉重试' }) }
          this.setData({ busy: false }, () => this.updateCanSend())
        }, 1200)
        return
      }
      this.setData({
        [`messages[${i}].type`]: 'error', [`messages[${i}].content`]: err.message || '请求失败',
        [`messages[${i}].status`]: 'error', busy: false,
      }, () => this.updateCanSend())
    },

    stop() {
      if (!this.task) return
      const id = this.assistantId
      this.task.abort()
      this._flush()
      if (id) http.post('/chat/stop', { message_id: id }, { silent: true }).catch(() => {})
      this.setData({ [`messages[${this.aIndex}].status`]: 'interrupted' })
      this.finish()
    },
  },
})
