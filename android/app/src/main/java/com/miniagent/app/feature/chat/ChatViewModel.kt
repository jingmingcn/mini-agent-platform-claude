package com.miniagent.app.feature.chat

import android.net.Uri
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.miniagent.app.core.network.ChatEvent
import com.miniagent.app.core.network.userMessage
import com.miniagent.app.data.model.AttachmentDto
import com.miniagent.app.data.repository.AgentRepository
import com.miniagent.app.data.repository.ChatRepository
import com.miniagent.app.data.repository.ConversationRepository
import com.miniagent.app.data.repository.FileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicLong
import javax.inject.Inject

data class ChatUiState(
    val loading: Boolean = true,
    val headerTitle: String = "对话",
    val headerAvatar: String? = null,
    val welcomeMessage: String? = null,
    val suggestedQuestions: List<String> = emptyList(),
    val messages: List<ChatMessage> = emptyList(),
    val input: String = "",
    val pendingAttachments: List<PendingAttachment> = emptyList(),
    val streaming: Boolean = false,
    val conversationId: Int? = null,
    val agentId: Int? = null,
    val error: String? = null,
) {
    val canRegenerate: Boolean
        get() = !streaming && messages.lastOrNull()?.role == "assistant" && conversationId != null

    val canSend: Boolean
        get() = !streaming &&
            (input.isNotBlank() || pendingAttachments.any { !it.uploading }) &&
            pendingAttachments.none { it.uploading }
}

@HiltViewModel
class ChatViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val agentRepository: AgentRepository,
    private val conversationRepository: ConversationRepository,
    private val chatRepository: ChatRepository,
    private val fileRepository: FileRepository,
) : ViewModel() {

    private val argAgentId: Int = savedStateHandle.get<Int>("agentId")?.takeIf { it > 0 } ?: -1
    private val argConversationId: Int =
        savedStateHandle.get<Int>("conversationId")?.takeIf { it > 0 } ?: -1

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private val localIdSeq = AtomicLong(1)
    private var streamJob: Job? = null
    private var currentAssistantLocalId: Long = -1
    private var currentAssistantServerId: Int? = null

    init {
        when {
            argConversationId > 0 -> loadConversation(argConversationId)
            argAgentId > 0 -> loadAgent(argAgentId)
            else -> _uiState.update { it.copy(loading = false, error = "缺少智能体或会话参数") }
        }
    }

    private fun loadAgent(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true) }
            runCatching { agentRepository.agent(id) }
                .onSuccess { agent ->
                    _uiState.update {
                        it.copy(
                            loading = false,
                            agentId = agent.id,
                            headerTitle = agent.name,
                            headerAvatar = agent.avatar,
                            welcomeMessage = agent.welcomeMessage?.takeIf(String::isNotBlank),
                            suggestedQuestions = agent.suggestedQuestions,
                        )
                    }
                }
                .onFailure { e -> _uiState.update { it.copy(loading = false, error = e.userMessage()) } }
        }
    }

    private fun loadConversation(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true) }
            runCatching { conversationRepository.messages(id) }
                .onSuccess { resp ->
                    val conv = resp.conversation
                    _uiState.update {
                        it.copy(
                            loading = false,
                            conversationId = id,
                            agentId = conv?.agentId,
                            headerTitle = conv?.agentName ?: conv?.title ?: "对话",
                            headerAvatar = conv?.agentAvatar,
                            messages = resp.items.map(ChatMessage::fromDto),
                        )
                    }
                }
                .onFailure { e -> _uiState.update { it.copy(loading = false, error = e.userMessage()) } }
        }
    }

    fun onInputChange(value: String) = _uiState.update { it.copy(input = value) }

    fun useSuggestion(text: String) {
        _uiState.update { it.copy(input = text) }
    }

    fun consumeError() = _uiState.update { it.copy(error = null) }

    // ------------------------------------------------------------------ attachments
    fun addAttachment(uri: Uri) {
        val placeholderKey = System.nanoTime()
        _uiState.update {
            it.copy(
                pendingAttachments = it.pendingAttachments + PendingAttachment(
                    id = -1, filename = "上传中…", fileType = "", isImage = false,
                    url = null, uploading = true, localKey = placeholderKey,
                ),
            )
        }
        viewModelScope.launch {
            runCatching { fileRepository.upload(uri) }
                .onSuccess { dto ->
                    _uiState.update { state ->
                        state.copy(
                            pendingAttachments = state.pendingAttachments.map { pa ->
                                if (pa.localKey == placeholderKey) {
                                    PendingAttachment(
                                        id = dto.id,
                                        filename = dto.filename,
                                        fileType = dto.fileType,
                                        isImage = dto.fileType in IMAGE_TYPES,
                                        url = dto.url,
                                        uploading = false,
                                        localKey = placeholderKey,
                                    )
                                } else {
                                    pa
                                }
                            },
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { state ->
                        state.copy(
                            pendingAttachments = state.pendingAttachments
                                .filterNot { it.localKey == placeholderKey },
                            error = e.userMessage(),
                        )
                    }
                }
        }
    }

    fun removeAttachment(key: Long) {
        _uiState.update { it.copy(pendingAttachments = it.pendingAttachments.filterNot { a -> a.localKey == key }) }
    }

    // ------------------------------------------------------------------ sending
    fun send() {
        val state = _uiState.value
        if (!state.canSend) return
        val content = state.input.trim()
        val attachments = state.pendingAttachments.filter { !it.uploading }
        val attachmentIds = attachments.map { it.id }

        val userMsg = ChatMessage(
            localId = localIdSeq.getAndIncrement(),
            role = "user",
            content = content,
            status = "completed",
            messageType = "text",
            attachments = attachments.map {
                AttachmentDto(
                    fileId = it.id, name = it.filename,
                    type = if (it.isImage) "image" else "file",
                    fileType = it.fileType, url = it.url,
                )
            },
        )
        _uiState.update {
            it.copy(
                messages = it.messages + userMsg,
                input = "",
                pendingAttachments = emptyList(),
            )
        }
        startStream(content = content, attachmentIds = attachmentIds, regenerate = false)
    }

    fun regenerate() {
        val state = _uiState.value
        if (state.streaming || state.conversationId == null) return
        // Drop the trailing assistant message visually; backend will recreate it.
        _uiState.update {
            val trimmed = it.messages.toMutableList()
            if (trimmed.lastOrNull()?.role == "assistant") trimmed.removeAt(trimmed.lastIndex)
            it.copy(messages = trimmed)
        }
        startStream(content = "", attachmentIds = emptyList(), regenerate = true)
    }

    private fun startStream(content: String, attachmentIds: List<Int>, regenerate: Boolean) {
        val assistant = ChatMessage(
            localId = localIdSeq.getAndIncrement(),
            role = "assistant",
            content = "",
            status = "streaming",
            messageType = "markdown",
        )
        currentAssistantLocalId = assistant.localId
        currentAssistantServerId = null
        _uiState.update { it.copy(messages = it.messages + assistant, streaming = true, error = null) }

        streamJob = viewModelScope.launch {
            try {
                chatRepository.stream(
                    agentId = _uiState.value.agentId,
                    conversationId = _uiState.value.conversationId,
                    content = content,
                    attachmentIds = attachmentIds,
                    regenerate = regenerate,
                ).collect { event -> handleEvent(event) }
            } catch (ce: CancellationException) {
                markStreamingInterrupted()
                throw ce
            } catch (e: Exception) {
                updateAssistant { it.copy(content = it.content.ifBlank { e.userMessage() }, status = "error", messageType = "error") }
            } finally {
                _uiState.update { it.copy(streaming = false) }
            }
        }
    }

    private fun handleEvent(event: ChatEvent) {
        when (event) {
            is ChatEvent.Meta -> {
                currentAssistantServerId = event.assistantMessageId
                _uiState.update { st ->
                    st.copy(
                        conversationId = event.conversationId,
                        messages = st.messages.map { m ->
                            if (m.localId == currentAssistantLocalId) m.copy(serverId = event.assistantMessageId)
                            else m
                        },
                    )
                }
            }
            is ChatEvent.Citations -> updateAssistant { it.copy(citations = event.items) }
            is ChatEvent.Delta -> updateAssistant { it.copy(content = it.content + event.content) }
            is ChatEvent.Tool -> {
                val label = buildString {
                    append("🔧 ").append(event.name)
                    event.error?.let { append(" · 失败") }
                }
                updateAssistant { it.copy(toolCalls = it.toolCalls + label) }
            }
            is ChatEvent.Done -> updateAssistant {
                it.copy(status = if (it.status == "error") "error" else event.status)
            }
            is ChatEvent.Error -> updateAssistant {
                it.copy(
                    content = it.content.ifBlank { event.message },
                    status = "error",
                    messageType = "error",
                )
            }
        }
    }

    fun stopGeneration() {
        val serverId = currentAssistantServerId
        streamJob?.cancel()
        if (serverId != null) {
            viewModelScope.launch { chatRepository.stop(serverId) }
        }
    }

    private fun markStreamingInterrupted() {
        updateAssistant { if (it.status == "streaming") it.copy(status = "interrupted") else it }
    }

    private inline fun updateAssistant(crossinline transform: (ChatMessage) -> ChatMessage) {
        _uiState.update { st ->
            st.copy(
                messages = st.messages.map { m ->
                    if (m.localId == currentAssistantLocalId) transform(m) else m
                },
            )
        }
    }

    // ------------------------------------------------------------------ feedback
    fun sendFeedback(message: ChatMessage, rating: Int) {
        val serverId = message.serverId ?: return
        val newRating = if (message.feedback == rating) 0 else rating
        _uiState.update { st ->
            st.copy(messages = st.messages.map { if (it.localId == message.localId) it.copy(feedback = newRating.takeIf { r -> r != 0 }) else it })
        }
        viewModelScope.launch {
            runCatching { conversationRepository.feedback(serverId, newRating) }
        }
    }

    companion object {
        private val IMAGE_TYPES = setOf("png", "jpg", "jpeg", "gif", "webp")
    }
}
