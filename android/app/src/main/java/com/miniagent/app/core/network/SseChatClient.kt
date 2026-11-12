package com.miniagent.app.core.network

import com.miniagent.app.core.config.SettingsStore
import com.miniagent.app.data.model.ChatRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.isActive
import kotlinx.coroutines.job
import kotlinx.serialization.encodeToString
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

/**
 * Streams a chat turn from `POST /chat/stream` as a cold [Flow] of [ChatEvent].
 *
 * Cancelling collection (e.g. the user taps 停止生成) cancels the underlying HTTP
 * call; the backend treats the client disconnect as an interrupt and persists the
 * partial answer as `interrupted`.
 */
@Singleton
class SseChatClient @Inject constructor(
    @Named("sse") private val client: OkHttpClient,
    private val settings: SettingsStore,
) {
    fun stream(request: ChatRequest): Flow<ChatEvent> = flow {
        val base = settings.baseUrl().trimEnd('/')
        val token = settings.token()
        val json = AppJson.encodeToString(request)
        val httpRequest = Request.Builder()
            .url("$base/chat/stream")
            .post(json.toRequestBody(JSON_MEDIA))
            .header("Accept", "text/event-stream")
            .apply { if (!token.isNullOrBlank()) header("Authorization", "Bearer $token") }
            .build()

        val call = client.newCall(httpRequest)
        // Cancel the socket when the coroutine is cancelled so reads unblock promptly.
        currentCoroutineContext().job.invokeOnCompletion { call.cancel() }

        val response = call.execute()
        try {
            if (!response.isSuccessful) {
                val bodyText = response.body?.string().orEmpty()
                val message = runCatching { AppJson.decodeFromString<ErrorPayload>(bodyText).message }
                    .getOrNull()?.takeIf { it.isNotBlank() }
                    ?: "请求失败(${response.code})"
                emit(ChatEvent.Error(code = response.code, message = message, messageId = null))
                return@flow
            }

            val source = response.body?.source() ?: return@flow
            val frame = StringBuilder()
            while (true) {
                currentCoroutineContext().ensureActive()
                val line = try {
                    source.readUtf8Line()
                } catch (io: IOException) {
                    // Expected when the call is cancelled (stop generating).
                    if (!currentCoroutineContext().isActive) return@flow
                    throw io
                } ?: break

                if (line.isEmpty()) {
                    parseFrame(frame.toString())?.let { emit(it) }
                    frame.setLength(0)
                } else {
                    frame.append(line).append('\n')
                }
            }
            parseFrame(frame.toString())?.let { emit(it) }
        } finally {
            response.close()
        }
    }.flowOn(Dispatchers.IO)

    /** Parse one SSE frame (event:/data: lines). Unknown or malformed frames are ignored. */
    private fun parseFrame(block: String): ChatEvent? {
        if (block.isBlank()) return null
        var event = "message"
        val data = StringBuilder()
        for (raw in block.split('\n')) {
            val line = raw.trimEnd('\r')
            when {
                line.startsWith(":") -> Unit // keep-alive comment
                line.startsWith("event:") -> event = line.removePrefix("event:").trim()
                line.startsWith("data:") -> {
                    if (data.isNotEmpty()) data.append('\n')
                    data.append(line.removePrefix("data:").removePrefix(" "))
                }
            }
        }
        val payload = data.toString()
        if (payload.isEmpty()) return null
        return runCatching {
            when (event) {
                "meta" -> AppJson.decodeFromString<MetaPayload>(payload).let {
                    ChatEvent.Meta(
                        it.conversationId, it.userMessageId, it.assistantMessageId,
                        it.agentId, it.model, it.title,
                    )
                }
                "citations" -> ChatEvent.Citations(
                    AppJson.decodeFromString<CitationsPayload>(payload).items,
                )
                "tool" -> AppJson.decodeFromString<ToolPayload>(payload).let {
                    ChatEvent.Tool(it.name, it.arguments?.toString(), it.result, it.error)
                }
                "delta" -> ChatEvent.Delta(AppJson.decodeFromString<DeltaPayload>(payload).content)
                "done" -> AppJson.decodeFromString<DonePayload>(payload).let {
                    ChatEvent.Done(it.messageId, it.status, it.finishReason)
                }
                "error" -> AppJson.decodeFromString<ErrorPayload>(payload).let {
                    ChatEvent.Error(it.code, it.message, it.messageId)
                }
                else -> null
            }
        }.getOrNull()
    }

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()

        /** A client tuned for long-lived streaming responses (no read timeout). */
        fun buildClient(base: OkHttpClient): OkHttpClient = base.newBuilder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .connectTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(false)
            .build()
    }
}
