const { http } = require('../../utils/request')
const auth = require('../../utils/auth')

Page({
  data: { config: { quick_questions: [] }, agents: [], featured: [], recent: [] },
  onShow() { this.load() },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()) },
  async load() {
    try {
      await auth.ensureLogin()
      const [config, agents, convs] = await Promise.all([
        http.get('/app/config'), http.get('/agents'), http.get('/conversations', { page: 1, page_size: 3 }),
      ])
      getApp().globalData.config = config
      this.setData({ config, agents, featured: agents.filter((a) => a.is_featured), recent: convs.items })
    } catch (e) { console.warn(e) }
  },
  openAgent(e) { this.go(e.currentTarget.dataset.agent) },
  onSelect(e) { this.go(e.detail.agent) },
  go(agent, q) {
    let url = `/pages/chat/chat?agentId=${agent.id}`
    if (q) url += `&q=${encodeURIComponent(q)}`
    wx.navigateTo({ url })
  },
  quickAsk(e) {
    const q = e.currentTarget.dataset.q
    const agents = this.data.agents
    if (!agents.length) return wx.showToast({ title: '暂无可用智能体', icon: 'none' })
    if (agents.length === 1) return this.go(agents[0], q)
    wx.showActionSheet({
      itemList: agents.slice(0, 6).map((a) => a.name),
      success: (r) => this.go(agents[r.tapIndex], q),
    })
  },
  goHistory() { wx.switchTab({ url: '/pages/history/history' }) },
})
