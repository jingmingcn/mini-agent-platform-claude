package com.miniagent.app.feature.agents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.miniagent.app.core.network.userMessage
import com.miniagent.app.data.model.AgentDto
import com.miniagent.app.data.repository.AgentRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AgentsUiState(
    val loading: Boolean = true,
    val refreshing: Boolean = false,
    val error: String? = null,
    val platformName: String = "Mini-Agent",
    val welcomeText: String = "",
    val allAgents: List<AgentDto> = emptyList(),
    val categories: List<String> = emptyList(),
    val selectedCategory: String? = null,
    val keyword: String = "",
) {
    val visibleAgents: List<AgentDto>
        get() = allAgents.filter { agent ->
            (selectedCategory == null || agent.category == selectedCategory) &&
                (keyword.isBlank() ||
                    agent.name.contains(keyword, ignoreCase = true) ||
                    agent.description?.contains(keyword, ignoreCase = true) == true)
        }
}

@HiltViewModel
class AgentsViewModel @Inject constructor(
    private val agentRepository: AgentRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AgentsUiState())
    val uiState: StateFlow<AgentsUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load(refresh: Boolean = false) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                loading = !refresh && _uiState.value.allAgents.isEmpty(),
                refreshing = refresh,
                error = if (refresh) _uiState.value.error else null,
            )
            val config = runCatching { agentRepository.appConfig() }.getOrNull()
            runCatching { agentRepository.agents() }
                .onSuccess { agents ->
                    val categories = agents.mapNotNull { it.category?.takeIf(String::isNotBlank) }
                        .distinct()
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        refreshing = false,
                        error = null,
                        allAgents = agents.sortedByDescending { it.isFeatured },
                        categories = categories,
                        platformName = config?.platformName ?: _uiState.value.platformName,
                        welcomeText = config?.welcomeText ?: _uiState.value.welcomeText,
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        refreshing = false,
                        error = e.userMessage(),
                    )
                }
        }
    }

    fun onKeywordChange(value: String) {
        _uiState.value = _uiState.value.copy(keyword = value)
    }

    fun onCategorySelected(category: String?) {
        _uiState.value = _uiState.value.copy(selectedCategory = category)
    }
}
