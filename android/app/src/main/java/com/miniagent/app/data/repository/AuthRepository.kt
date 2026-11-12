package com.miniagent.app.data.repository

import com.miniagent.app.core.config.SettingsStore
import com.miniagent.app.core.network.ApiProvider
import com.miniagent.app.core.network.apiCall
import com.miniagent.app.data.model.UserProfile
import com.miniagent.app.data.model.WechatLoginRequest
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val apiProvider: ApiProvider,
    private val settings: SettingsStore,
) {
    val isLoggedIn: Flow<Boolean> = settings.tokenFlow.map { !it.isNullOrBlank() }

    suspend fun hasToken(): Boolean = !settings.token().isNullOrBlank()

    /**
     * Dev / device login. Uses a stable per-install id as both the login code and
     * dev_openid, which the backend honours when WECHAT_DEV_LOGIN=true. Swap this for
     * a real wx.login code obtained via the WeChat Open SDK in production.
     */
    suspend fun login(nickname: String? = null): UserProfile {
        val deviceId = settings.deviceId()
        val api = apiProvider.api()
        val resp = apiCall {
            api.wechatLogin(
                WechatLoginRequest(
                    code = deviceId,
                    nickname = nickname,
                    devOpenid = deviceId,
                ),
            )
        }
        settings.setToken(resp.accessToken)
        resp.profile?.let { settings.setProfile(it.nickname, it.avatarUrl) }
        return resp.profile ?: UserProfile(id = 0, nickname = nickname)
    }

    suspend fun me(): UserProfile? {
        val api = apiProvider.api()
        val resp = apiCall { api.me() }
        resp.profile?.let { settings.setProfile(it.nickname, it.avatarUrl) }
        return resp.profile
    }

    suspend fun logout() {
        settings.clearSession()
    }
}
