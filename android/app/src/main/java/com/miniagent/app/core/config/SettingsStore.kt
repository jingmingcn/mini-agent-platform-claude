package com.miniagent.app.core.config

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.miniagent.app.BuildConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "mini_agent_prefs")

/**
 * Persistent app settings backed by Jetpack DataStore:
 *  - JWT access token (end-user principal)
 *  - configurable backend base URL (服务环境)
 *  - a stable per-install device id used for dev login (dev_openid)
 *  - lightweight cached profile for the 个人中心 header
 *
 * Note on token storage: DataStore is app-private. For production hardening you can
 * additionally wrap the token with EncryptedSharedPreferences / Jetpack Security; the
 * surface here is intentionally small so that swap is a one-file change.
 */
@Singleton
class SettingsStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private object Keys {
        val TOKEN = stringPreferencesKey("access_token")
        val BASE_URL = stringPreferencesKey("base_url")
        val DEVICE_ID = stringPreferencesKey("device_id")
        val NICKNAME = stringPreferencesKey("nickname")
        val AVATAR = stringPreferencesKey("avatar_url")
    }

    val tokenFlow: Flow<String?> = context.dataStore.data.map { it[Keys.TOKEN] }
    val baseUrlFlow: Flow<String> =
        context.dataStore.data.map { it[Keys.BASE_URL] ?: BuildConfig.DEFAULT_BASE_URL }

    suspend fun token(): String? = tokenFlow.first()

    suspend fun baseUrl(): String = baseUrlFlow.first()

    suspend fun setToken(token: String?) {
        context.dataStore.edit { prefs ->
            if (token.isNullOrBlank()) prefs.remove(Keys.TOKEN) else prefs[Keys.TOKEN] = token
        }
    }

    suspend fun setBaseUrl(url: String) {
        context.dataStore.edit { it[Keys.BASE_URL] = normalizeBaseUrl(url) }
    }

    suspend fun resetBaseUrl() {
        context.dataStore.edit { it.remove(Keys.BASE_URL) }
    }

    /** Stable id generated once per install; used as dev_openid for dev login. */
    suspend fun deviceId(): String {
        val existing = context.dataStore.data.map { it[Keys.DEVICE_ID] }.first()
        if (existing != null) return existing
        val generated = "and_" + UUID.randomUUID().toString().replace("-", "").take(24)
        context.dataStore.edit { it[Keys.DEVICE_ID] = generated }
        return generated
    }

    val profileFlow: Flow<CachedProfile> = context.dataStore.data.map {
        CachedProfile(nickname = it[Keys.NICKNAME], avatarUrl = it[Keys.AVATAR])
    }

    suspend fun setProfile(nickname: String?, avatarUrl: String?) {
        context.dataStore.edit { prefs ->
            if (nickname != null) prefs[Keys.NICKNAME] = nickname
            if (avatarUrl != null) prefs[Keys.AVATAR] = avatarUrl
        }
    }

    suspend fun clearSession() {
        context.dataStore.edit { prefs ->
            prefs.remove(Keys.TOKEN)
            prefs.remove(Keys.NICKNAME)
            prefs.remove(Keys.AVATAR)
        }
    }

    companion object {
        fun normalizeBaseUrl(raw: String): String {
            var url = raw.trim()
            if (url.isEmpty()) return BuildConfig.DEFAULT_BASE_URL
            if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
            return url.trimEnd('/')
        }
    }
}

data class CachedProfile(val nickname: String?, val avatarUrl: String?)
