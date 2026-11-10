const { http } = require('../../utils/request')
const auth = require('../../utils/auth')

Page({
  data: { list: [], total: 0, page: 1, agents: [], agentNames: ['全部智能体'], filterIndex: 0 },
  onShow() { this.init() },
  async init() {
    await auth.ensureLogin()
    const agents = await http.get('/agents')
    this.setData({ agents, agentNames: ['全部智能体'].concat(agents.map((a) => a.name)) })
    this.reload()
  },
  onPullDownRefresh() { this.reload().finally(() => wx.stopPullDownRefresh()) },
  onReachBottom() { if (this.data.list.length < this.data.total) this.load(this.data.page + 1) },
  onFilter(e) { this.setData({ filterIndex: Number(e.detail.value) }); this.reload() },
  reload() { return this.load(1) },
  async load(page) {
    const idx = this.data.filterIndex
    const params = { page, page_size: 20 }
    if (idx > 0) params.agent_id = this.data.agents[idx - 1].id
    const res = await http.get('/conversations', params)
    this.setData({ page, total: res.total, list: page === 1 ? res.items : this.data.list.concat(res.items) })
  },
})
