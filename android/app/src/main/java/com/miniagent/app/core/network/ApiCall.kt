package com.miniagent.app.core.network

import kotlinx.coroutines.CancellationException
import retrofit2.HttpException
import java.io.IOException

/**
 * Runs a Retrofit call that returns an [ApiEnvelope], unwraps it, and normalizes
 * failures into [ApiException] with a human-readable Chinese message.
 */
suspend fun <T> apiCall(block: suspend () -> ApiEnvelope<T>): T {
    try {
        return block().unwrap()
    } catch (ce: CancellationException) {
        throw ce
    } catch (e: ApiException) {
        throw e
    } catch (e: HttpException) {
        val message = runCatching {
            e.response()?.errorBody()?.string()?.let { body ->
                AppJson.decodeFromString<ApiEnvelope<kotlinx.serialization.json.JsonElement>>(body).message
            }
        }.getOrNull()?.takeIf { it.isNotBlank() } ?: defaultHttpMessage(e.code())
        throw ApiException(httpStatus = e.code(), businessCode = null, message = message)
    } catch (e: IOException) {
        throw ApiException(httpStatus = 0, businessCode = null, message = "网络连接失败，请检查网络或服务地址")
    }
}

private fun defaultHttpMessage(code: Int): String = when (code) {
    401 -> "登录已过期，请重新登录"
    403 -> "没有访问权限"
    404 -> "资源不存在"
    429 -> "请求过于频繁，请稍后再试"
    in 500..599 -> "服务器开小差了（$code）"
    else -> "请求失败（$code）"
}

/** Best-effort user-facing message for any throwable. */
fun Throwable.userMessage(): String = when (this) {
    is ApiException -> message
    else -> message ?: "操作失败，请稍后再试"
}
