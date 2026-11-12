package com.miniagent.app.feature.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.miniagent.app.core.network.userMessage
import com.miniagent.app.data.model.ConversationDto
import com.miniagent.app.data.repository.ConversationRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HistoryUiState(
    val loading: Boolean = true,
    val refreshing: Boolean = false,
    val error: String? = null,
    val conversations: List<ConversationDto> = emptyList(),
    val keyword: String = "",
)

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val conversationRepository: ConversationRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(HistoryUiState())
    val uiState: StateFlow<HistoryUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load(refresh: Boolean = false) {
        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    loading = !refresh && it.conversations.isEmpty(),
                    refreshing = refresh,
                )
            }
            runCatching { conversationRepository.list(keyword = _uiState.value.keyword) }
                .onSuccess { page ->
                    _uiState.update {
                        it.copy(loading = false, refreshing = false, error = null, conversations = page.items)
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(loading = false, refreshing = false, error = e.userMessage()) }
                }
        }
    }

    fun onKeywordChange(value: String) {
        _uiState.update { it.copy(keyword = value) }
    }

    fun search() = load()

    fun delete(conversation: ConversationDto) {
        _uiState.update { it.copy(conversations = it.conversations.filterNot { c -> c.id == conversation.id }) }
        viewModelScope.launch {
            runCatching { conversationRepository.delete(conversation.id) }
                .onFailure { e ->
                    // Re-add on failure.
                    _uiState.update {
                        it.copy(
                            conversations = (it.conversations + conversation).sortedByDescending { c -> c.id },
                            error = e.userMessage(),
                        )
                    }
                }
        }
    }

    fun rename(conversation: ConversationDto, title: String) {
        val trimmed = title.trim()
        if (trimmed.isBlank()) return
        _uiState.update {
            it.copy(conversations = it.conversations.map { c -> if (c.id == conversation.id) c.copy(title = trimmed) else c })
        }
        viewModelScope.launch {
            runCatching { conversationRepository.rename(conversation.id, trimmed) }
                .onFailure { e -> _uiState.update { it.copy(error = e.userMessage()) } }
        }
    }

    fun consumeError() = _uiState.update { it.copy(error = null) }
}
