package com.miniagent.app.data.repository

import com.miniagent.app.core.network.ApiProvider
import com.miniagent.app.core.network.apiCall
import com.miniagent.app.data.model.ConversationPage
import com.miniagent.app.data.model.FeedbackRequest
import com.miniagent.app.data.model.MessagesResponse
import com.miniagent.app.data.model.RenameRequest
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ConversationRepository @Inject constructor(
    private val apiProvider: ApiProvider,
) {
    suspend fun list(
        keyword: String? = null,
        page: Int = 1,
        pageSize: Int = 20,
    ): ConversationPage = apiCall {
        apiProvider.api().conversations(
            keyword = keyword?.takeIf { it.isNotBlank() },
            page = page,
            pageSize = pageSize,
        )
    }

    suspend fun messages(conversationId: Int): MessagesResponse =
        apiCall { apiProvider.api().messages(conversationId) }

    suspend fun rename(conversationId: Int, title: String) {
        apiCall { apiProvider.api().renameConversation(conversationId, RenameRequest(title)) }
    }

    suspend fun delete(conversationId: Int) {
        apiCall { apiProvider.api().deleteConversation(conversationId) }
    }

    suspend fun feedback(messageId: Int, rating: Int, comment: String? = null) {
        apiCall { apiProvider.api().feedback(messageId, FeedbackRequest(rating, comment)) }
    }
}
