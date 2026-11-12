package com.miniagent.app.core.network

import kotlinx.serialization.Serializable

/** Unified backend response envelope: {"code":0,"message":"ok","data":...}. */
@Serializable
data class ApiEnvelope<T>(
    val code: Int = 0,
    val message: String = "ok",
    val data: T? = null,
)

/** Thrown when an HTTP call fails or the envelope reports a non-zero code. */
class ApiException(
    val httpStatus: Int,
    val businessCode: Int?,
    override val message: String,
) : Exception(message) {
    val isUnauthorized: Boolean get() = httpStatus == 401
}

/** Returns [ApiEnvelope.data] or throws [ApiException] when code != 0. */
fun <T> ApiEnvelope<T>.unwrap(): T {
    if (code != 0) throw ApiException(httpStatus = 200, businessCode = code, message = message)
    @Suppress("UNCHECKED_CAST")
    return (data ?: Unit) as T
}
