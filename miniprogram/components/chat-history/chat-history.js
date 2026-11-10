const { http } = require('../../utils/request')
const { fmtTime } = require('../../utils/util')

Component({
  properties: {
    conversations: { type: Array, value: [] },
    deletable: { type: Boolean, value: true },
    emptyText: { type: String, value: '还没有会话，去首页选择一个智能体吧' },
  },
  data: { items: [] },
  observers: {
    conversations(v) { this.setData({ items: (v || []).map((c) => ({ ...c, time: fmtTime(c.last_message_at || c.created_at) })) }) },
  },
  methods: {
    open(e) {
      const c = e.currentTarget.dataset.item
      wx.navigateTo({ url: `/pages/chat/chat?agentId=${c.agent_id}&conversationId=${c.id}` })
    },
    remove(e) {
      const c = e.currentTarget.dataset.item
      wx.showModal({
        title: '删除会话', content: `确定删除「${c.title}」？`,
        success: async (r) => {
          if (!r.confirm) return
          await http.del(`/conversations/${c.id}`)
          this.triggerEvent('removed', { id: c.id })
        },
      })
    },
    more(e) {
      const c = this.data.items[e.currentTarget.dataset.index]
      wx.showActionSheet({
        itemList: ['重命名'],
        success: () => wx.showModal({
          title: '重命名', editable: true, placeholderText: c.title,
          success: async (r) => {
            if (!r.confirm || !r.content) return
            await http.patch(`/conversations/${c.id}`, { title: r.content })
            this.triggerEvent('removed', { id: null })
          },
        }),
      })
    },
  },
})
