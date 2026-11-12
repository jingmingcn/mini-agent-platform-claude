package com.miniagent.app.feature.chat

import com.miniagent.app.data.model.AttachmentDto
import com.miniagent.app.data.model.CitationDto
import com.miniagent.app.data.model.MessageDto

/** A single chat bubble in the UI (user or assistant). */
data class ChatMessage(
    val localId: Long,
    val serverId: Int? = null,
    val role: String, // "user" | "assistant"
    val content: String = "",
    val status: String = "completed", // streaming | completed | interrupted | error
    val messageType: String = "markdown",
    val citations: List<CitationDto> = emptyList(),
    val attachments: List<AttachmentDto> = emptyList(),
    val toolCalls: List<String> = emptyList(),
    val feedback: Int? = null,
) {
    val isUser: Boolean get() = role == "user"
    val isStreaming: Boolean get() = status == "streaming"
    val isError: Boolean get() = status == "error" || messageType == "error"

    companion object {
        fun fromDto(dto: MessageDto): ChatMessage = ChatMessage(
            localId = dto.id.toLong(),
            serverId = dto.id,
            role = dto.role,
            content = dto.content,
            status = dto.status,
            messageType = dto.messageType,
            citations = dto.citations,
            attachments = dto.attachments,
            feedback = dto.feedback,
        )
    }
}

/** A chat attachment that has been uploaded and is ready to attach to the next message. */
data class PendingAttachment(
    val id: Int,
    val filename: String,
    val fileType: String,
    val isImage: Boolean,
    val url: String?,
    val uploading: Boolean = false,
    val localKey: Long = System.nanoTime(),
)
