package com.miniagent.app.core.network

import com.miniagent.app.core.config.SettingsStore
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Adds `Authorization: Bearer <token>` to every request when a token is stored,
 * and publishes a 401 through [AuthEventBus] so the UI can route back to login.
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val settings: SettingsStore,
    private val authEvents: AuthEventBus,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val token = runBlocking { settings.token() }
        val request = if (!token.isNullOrBlank()) {
            chain.request().newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            chain.request()
        }
        val response = chain.proceed(request)
        if (response.code == 401) {
            authEvents.notifyUnauthorized()
        }
        return response
    }
}
