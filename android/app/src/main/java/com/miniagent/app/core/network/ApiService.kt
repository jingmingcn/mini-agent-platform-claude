package com.miniagent.app.core.network

import com.miniagent.app.data.model.AgentDto
import com.miniagent.app.data.model.AppConfig
import com.miniagent.app.data.model.ConversationPage
import com.miniagent.app.data.model.FeedbackRequest
import com.miniagent.app.data.model.LoginResponse
import com.miniagent.app.data.model.MeResponse
import com.miniagent.app.data.model.MessagesResponse
import com.miniagent.app.data.model.RenameRequest
import com.miniagent.app.data.model.StopRequest
import com.miniagent.app.data.model.UploadedFileDto
import com.miniagent.app.data.model.WechatLoginRequest
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Non-streaming REST endpoints. Base URL is `<server>/api/v1/`.
 * Streaming chat (`/chat/stream`) is handled separately in [SseChatClient].
 */
interface ApiService {

    @POST("auth/wechat/login")
    suspend fun wechatLogin(@Body body: WechatLoginRequest): ApiEnvelope<LoginResponse>

    @GET("auth/me")
    suspend fun me(): ApiEnvelope<MeResponse>

    @GET("app/config")
    suspend fun appConfig(): ApiEnvelope<AppConfig>

    @GET("agents")
    suspend fun agents(
        @Query("keyword") keyword: String? = null,
        @Query("status") status: String? = null,
    ): ApiEnvelope<List<AgentDto>>

    @GET("agents/{id}")
    suspend fun agent(@Path("id") id: Int): ApiEnvelope<AgentDto>

    @GET("conversations")
    suspend fun conversations(
        @Query("agent_id") agentId: Int? = null,
        @Query("keyword") keyword: String? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
    ): ApiEnvelope<ConversationPage>

    @GET("conversations/{id}/messages")
    suspend fun messages(@Path("id") id: Int): ApiEnvelope<MessagesResponse>

    @PATCH("conversations/{id}")
    suspend fun renameConversation(
        @Path("id") id: Int,
        @Body body: RenameRequest,
    ): ApiEnvelope<Unit>

    @DELETE("conversations/{id}")
    suspend fun deleteConversation(@Path("id") id: Int): ApiEnvelope<Unit>

    @POST("messages/{id}/feedback")
    suspend fun feedback(
        @Path("id") messageId: Int,
        @Body body: FeedbackRequest,
    ): ApiEnvelope<Unit>

    @POST("chat/stop")
    suspend fun stop(@Body body: StopRequest): ApiEnvelope<Unit>

    @Multipart
    @POST("files/upload")
    suspend fun upload(@Part file: MultipartBody.Part): ApiEnvelope<UploadedFileDto>
}
