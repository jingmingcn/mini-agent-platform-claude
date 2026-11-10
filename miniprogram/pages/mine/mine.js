const { http, clearToken } = require('../../utils/request')
const auth = require('../../utils/auth')

Page({
  data: { user: {}, usage: { conversations: 0, requests_30d: 0, tokens_30d: 0 } },
  async onShow() {
    await auth.ensureLogin()
    const [me, usage] = await Promise.all([http.get('/auth/me'), http.get('/users/me/usage')])
    this.setData({ user: me.profile, usage })
  },
  onNickname(e) {
    const nickname = (e.detail.value || '').trim()
    if (nickname && nickname !== this.data.user.nickname) this.relogin({ nickname })
  },
  onAvatar(e) {
    // TODO: upload avatar to object storage; temp file paths are only valid locally.
    this.setData({ 'user.avatar_url': e.detail.avatarUrl })
  },
  relogin(extra) {
    wx.login({
      success: async (r) => {
        const data = await http.post('/auth/wechat/login', { code: r.code, dev_openid: auth.devOpenid(), ...extra })
        require('../../utils/request').setToken(data.access_token)
        this.setData({ user: data.profile })
        wx.showToast({ title: '已更新', icon: 'none' })
      },
    })
  },
  clearCache() { clearToken(); wx.showToast({ title: '已清除，重新进入将自动登录', icon: 'none' }) },
})
