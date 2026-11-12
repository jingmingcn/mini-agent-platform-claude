package com.miniagent.app.data.repository

import com.miniagent.app.core.network.ApiProvider
import com.miniagent.app.core.network.ChatEvent
import com.miniagent.app.core.network.SseChatClient
import com.miniagent.app.core.network.apiCall
import com.miniagent.app.data.model.ChatRequest
import com.miniagent.app.data.model.StopRequest
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val sseClient: SseChatClient,
    private val apiProvider: ApiProvider,
) {
    fun stream(
        agentId: Int?,
        conversationId: Int?,
        content: String,
        attachmentIds: List<Int> = emptyList(),
        regenerate: Boolean = false,
    ): Flow<ChatEvent> = sseClient.stream(
        ChatRequest(
            agentId = agentId,
            conversationId = conversationId,
            content = content,
            attachmentIds = attachmentIds,
            regenerate = regenerate,
        ),
    )

    /** Ask the backend to stop generating a streaming assistant message. */
    suspend fun stop(messageId: Int) {
        runCatching { apiCall { apiProvider.api().stop(StopRequest(messageId)) } }
    }
}
