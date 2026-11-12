package com.miniagent.app.core.network

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.miniagent.app.core.config.SettingsStore
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import javax.inject.Inject
import javax.inject.Singleton

/** Shared JSON configuration used by both REST and SSE parsing. */
val AppJson: Json = Json {
    ignoreUnknownKeys = true
    explicitNulls = false
    coerceInputValues = true
    isLenient = true
}

/**
 * Builds (and caches) a Retrofit [ApiService] for the currently configured base URL.
 * Rebuilds transparently when the user changes 服务环境 at runtime, so repositories
 * can simply call [api] before each request.
 */
@Singleton
class ApiProvider @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val settings: SettingsStore,
) {
    @Volatile
    private var cachedBaseUrl: String? = null

    @Volatile
    private var cachedService: ApiService? = null

    private val converter = AppJson.asConverterFactory("application/json".toMediaType())

    suspend fun api(): ApiService {
        val base = ensureTrailingSlash(settings.baseUrl())
        val current = cachedService
        if (current != null && base == cachedBaseUrl) return current
        return synchronized(this) {
            val again = cachedService
            if (again != null && base == cachedBaseUrl) {
                again
            } else {
                val service = Retrofit.Builder()
                    .baseUrl(base)
                    .client(okHttpClient)
                    .addConverterFactory(converter)
                    .build()
                    .create(ApiService::class.java)
                cachedBaseUrl = base
                cachedService = service
                service
            }
        }
    }

    private fun ensureTrailingSlash(url: String): String = if (url.endsWith("/")) url else "$url/"
}
