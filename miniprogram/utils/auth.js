const { setToken, getToken, request } = require('./request')

let loginPromise = null

function wxLogin() {
  return new Promise((resolve, reject) => wx.login({ success: (r) => (r.code ? resolve(r.code) : reject(new Error('wx.login 无 code'))), fail: reject }))
}

/** Persistent per-install id; the backend only uses it in WECHAT_DEV_LOGIN mode (no AppID configured). */
function devOpenid() {
  let id = wx.getStorageSync('mini_agent_dev_id')
  if (!id) {
    id = 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
    wx.setStorageSync('mini_agent_dev_id', id)
  }
  return id
}

/** wx.login -> POST /auth/wechat/login -> store JWT. Concurrent callers share one login. */
function login() {
  if (loginPromise) return loginPromise
  loginPromise = (async () => {
    const code = await wxLogin()
    const data = await request({ url: '/auth/wechat/login', method: 'POST', data: { code, dev_openid: devOpenid() }, retry: false })
    setToken(data.access_token)
    getApp().globalData.user = data.profile
    return data.profile
  })()
  loginPromise.finally(() => { loginPromise = null })
  return loginPromise
}

async function ensureLogin() {
  if (getToken()) return true
  await login()
  return true
}

module.exports = { login, ensureLogin, devOpenid }
