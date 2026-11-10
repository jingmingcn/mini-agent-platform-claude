const { API_BASE } = require('../config')

const TOKEN_KEY = 'mini_agent_token'

function getToken() { return wx.getStorageSync(TOKEN_KEY) || '' }
function setToken(t) { wx.setStorageSync(TOKEN_KEY, t) }
function clearToken() { wx.removeStorageSync(TOKEN_KEY) }

/**
 * Promise wrapper for wx.request with unified envelope {code, message, data}.
 * On 401 it re-logins once and retries.
 */
function request({ url, method = 'GET', data, retry = true, silent = false }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: API_BASE + url,
      method,
      data,
      timeout: 60000,
      header: { 'content-type': 'application/json', Authorization: getToken() ? `Bearer ${getToken()}` : '' },
      success: async (res) => {
        const body = res.data || {}
        if (res.statusCode === 401 && retry) {
          clearToken()
          try {
            await require('./auth').login()
            resolve(await request({ url, method, data, retry: false, silent }))
          } catch (e) { reject(e) }
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300 && body.code === 0) return resolve(body.data)
        const err = new Error(body.message || `请求失败(${res.statusCode})`)
        err.statusCode = res.statusCode
        if (!silent) wx.showToast({ title: err.message, icon: 'none' })
        reject(err)
      },
      fail: (e) => {
        if (!silent) wx.showToast({ title: '网络错误，请检查网络', icon: 'none' })
        reject(new Error(e.errMsg || 'network error'))
      },
    })
  })
}

const http = {
  get: (url, data, opts = {}) => request({ url, data, ...opts }),
  post: (url, data, opts = {}) => request({ url, method: 'POST', data, ...opts }),
  put: (url, data, opts = {}) => request({ url, method: 'PUT', data, ...opts }),
  patch: (url, data, opts = {}) => request({ url, method: 'PATCH', data, ...opts }),
  del: (url, opts = {}) => request({ url, method: 'DELETE', ...opts }),
}

function uploadFile(filePath, name) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: API_BASE + '/files/upload',
      filePath,
      name: 'file',
      formData: name ? { filename: name } : {},
      header: { Authorization: `Bearer ${getToken()}` },
      success: (res) => {
        let body = {}
        try { body = JSON.parse(res.data) } catch (e) { /* ignore */ }
        if (res.statusCode === 200 && body.code === 0) resolve(body.data)
        else reject(new Error(body.message || `上传失败(${res.statusCode})`))
      },
      fail: (e) => reject(new Error(e.errMsg || '上传失败')),
    })
  })
}

module.exports = { http, request, uploadFile, getToken, setToken, clearToken, API_BASE }
