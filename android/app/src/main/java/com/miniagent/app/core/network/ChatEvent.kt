package com.miniagent.app.core.network

import com.miniagent.app.data.model.CitationDto
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/** Decoded Server-Sent Events from `/chat/stream`. */
sealed interface ChatEvent {
    data class Meta(
        val conversationId: Int,
        val userMessageId: Int,
        val assistantMessageId: Int,
        val agentId: Int,
        val model: String?,
        val title: String?,
    ) : ChatEvent

    data class Citations(val items: List<CitationDto>) : ChatEvent

    data class Tool(
        val name: String,
        val arguments: String?,
        val result: String?,
        val error: String?,
    ) : ChatEvent

    data class Delta(val content: String) : ChatEvent

    data class Done(
        val messageId: Int,
        val status: String,
        val finishReason: String?,
    ) : ChatEvent

    data class Error(val code: Int, val message: String, val messageId: Int?) : ChatEvent
}

// ---- wire payloads (matching backend runtime.py event schemas) ----

@Serializable
internal data class MetaPayload(
    @SerialName("conversation_id") val conversationId: Int = 0,
    @SerialName("user_message_id") val userMessageId: Int = 0,
    @SerialName("assistant_message_id") val assistantMessageId: Int = 0,
    @SerialName("agent_id") val agentId: Int = 0,
    val model: String? = null,
    val title: String? = null,
)

@Serializable
internal data class CitationsPayload(val items: List<CitationDto> = emptyList())

@Serializable
internal data class ToolPayload(
    val name: String = "",
    // `arguments` may arrive as a JSON object or a string depending on the provider.
    val arguments: JsonElement? = null,
    val result: String? = null,
    val error: String? = null,
)

@Serializable
internal data class DeltaPayload(val content: String = "")

@Serializable
internal data class DonePayload(
    @SerialName("message_id") val messageId: Int = 0,
    val status: String = "completed",
    @SerialName("finish_reason") val finishReason: String? = null,
)

@Serializable
internal data class ErrorPayload(
    val code: Int = 0,
    val message: String = "",
    @SerialName("message_id") val messageId: Int? = null,
)
