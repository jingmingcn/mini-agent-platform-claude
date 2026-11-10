const auth = require('../../utils/auth')

Page({
  data: { agentId: 0, conversationId: 0 },
  async onLoad(q) {
    await auth.ensureLogin()
    this.pendingQuestion = q.q ? decodeURIComponent(q.q) : ''
    this.setData({ agentId: Number(q.agentId || 0), conversationId: Number(q.conversationId || 0) })
  },
  onAgent(e) {
    wx.setNavigationBarTitle({ title: e.detail.agent.name })
    if (this.pendingQuestion) {
      const chat = this.selectComponent('#chat')
      chat.send(null, this.pendingQuestion)
      this.pendingQuestion = ''
    }
  },
  onConversation() { /* new conversation created; history list refreshes on show */ },
  onShareAppMessage() { return { title: 'Mini-Agent 智能体', path: `/pages/chat/chat?agentId=${this.data.agentId}` } },
})
