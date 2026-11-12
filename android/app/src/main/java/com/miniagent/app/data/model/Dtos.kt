package com.miniagent.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ----------------------------------------------------------------------------
// Auth
// ----------------------------------------------------------------------------

@Serializable
data class WechatLoginRequest(
    val code: String,
    val nickname: String? = null,
    @SerialName("avatar_url") val avatarUrl: String? = null,
    @SerialName("dev_openid") val devOpenid: String? = null,
)

@Serializable
data class LoginResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Int = 0,
    @SerialName("principal_type") val principalType: String = "user",
    val profile: UserProfile? = null,
)

@Serializable
data class MeResponse(
    @SerialName("principal_type") val principalType: String,
    val profile: UserProfile? = null,
)

@Serializable
data class UserProfile(
    val id: Int,
    val nickname: String? = null,
    @SerialName("avatar_url") val avatarUrl: String? = null,
    val status: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("last_login_at") val lastLoginAt: String? = null,
)

// ----------------------------------------------------------------------------
// App config / agents
// ----------------------------------------------------------------------------

@Serializable
data class AppConfig(
    @SerialName("platform_name") val platformName: String? = null,
    @SerialName("welcome_text") val welcomeText: String? = null,
    @SerialName("quick_questions") val quickQuestions: List<String> = emptyList(),
    @SerialName("featured_agent_ids") val featuredAgentIds: List<Int> = emptyList(),
)

@Serializable
data class AgentDto(
    val id: Int,
    val name: String,
    val description: String? = null,
    val avatar: String? = null,
    val category: String? = null,
    @SerialName("welcome_message") val welcomeMessage: String? = null,
    @SerialName("suggested_questions") val suggestedQuestions: List<String> = emptyList(),
    @SerialName("enable_rag") val enableRag: Boolean = false,
    @SerialName("is_featured") val isFeatured: Boolean = false,
)

// ----------------------------------------------------------------------------
// Conversations / messages
// ----------------------------------------------------------------------------

@Serializable
data class ConversationPage(
    val items: List<ConversationDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 20,
)

@Serializable
data class ConversationDto(
    val id: Int,
    @SerialName("user_id") val userId: Int = 0,
    @SerialName("agent_id") val agentId: Int,
    @SerialName("agent_name") val agentName: String? = null,
    @SerialName("agent_avatar") val agentAvatar: String? = null,
    val title: String = "",
    @SerialName("message_count") val messageCount: Int = 0,
    @SerialName("last_message_at") val lastMessageAt: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class MessagesResponse(
    val conversation: ConversationDto? = null,
    val items: List<MessageDto> = emptyList(),
)

@Serializable
data class MessageDto(
    val id: Int,
    @SerialName("conversation_id") val conversationId: Int,
    val role: String,
    val content: String = "",
    @SerialName("message_type") val messageType: String = "text",
    val status: String = "completed",
    val attachments: List<AttachmentDto> = emptyList(),
    val citations: List<CitationDto> = emptyList(),
    val model: String? = null,
    val feedback: Int? = null,
    @SerialName("latency_ms") val latencyMs: Int? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class AttachmentDto(
    @SerialName("file_id") val fileId: Int? = null,
    val name: String? = null,
    val type: String? = null, // "image" | "file"
    @SerialName("file_type") val fileType: String? = null,
    val size: Long? = null,
    val url: String? = null,
)

@Serializable
data class CitationDto(
    val index: Int = 0,
    @SerialName("document_name") val documentName: String? = null,
    @SerialName("knowledge_base_name") val knowledgeBaseName: String? = null,
    val snippet: String? = null,
    val content: String? = null,
    val score: Double? = null,
    @SerialName("page_number") val pageNumber: Int? = null,
)

// ----------------------------------------------------------------------------
// Files / chat control
// ----------------------------------------------------------------------------

@Serializable
data class UploadedFileDto(
    val id: Int,
    val filename: String,
    @SerialName("file_type") val fileType: String,
    @SerialName("file_size") val fileSize: Long,
    val url: String? = null,
    @SerialName("has_text") val hasText: Boolean = false,
)

@Serializable
data class FeedbackRequest(
    val rating: Int, // 1 | -1 | 0
    val comment: String? = null,
)

@Serializable
data class RenameRequest(val title: String)

@Serializable
data class StopRequest(@SerialName("message_id") val messageId: Int)

@Serializable
data class ChatRequest(
    @SerialName("agent_id") val agentId: Int? = null,
    @SerialName("conversation_id") val conversationId: Int? = null,
    val content: String = "",
    @SerialName("attachment_ids") val attachmentIds: List<Int> = emptyList(),
    val regenerate: Boolean = false,
)
