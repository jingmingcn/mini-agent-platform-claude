const { http } = require('../../utils/request')

Component({
  properties: {
    messageId: Number,
    content: String,
    value: { type: Number, value: 0 },
    canRegenerate: { type: Boolean, value: false },
  },
  methods: {
    copy() { wx.setClipboardData({ data: this.data.content || '' }) },
    regenerate() { this.triggerEvent('regenerate') },
    async rate(e) {
      const v = e.currentTarget.dataset.v
      const next = this.data.value === v ? 0 : v
      await http.post(`/messages/${this.data.messageId}/feedback`, { rating: next })
      this.setData({ value: next })
      if (next) wx.showToast({ title: '感谢反馈', icon: 'none' })
    },
  },
})
