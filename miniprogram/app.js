const auth = require('./utils/auth')

App({
  globalData: { user: null, config: null },
  onLaunch() {
    auth.ensureLogin().catch((e) => console.warn('login failed', e))
  },
})
