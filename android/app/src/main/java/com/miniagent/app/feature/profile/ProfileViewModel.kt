package com.miniagent.app.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.miniagent.app.core.config.SettingsStore
import com.miniagent.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val nickname: String = "用户",
    val avatarUrl: String? = null,
    val userId: Int? = null,
    val baseUrl: String = "",
    val message: String? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val settings: SettingsStore,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    private val _loggedOut = Channel<Unit>(Channel.BUFFERED)
    val loggedOut = _loggedOut.receiveAsFlow()

    init {
        viewModelScope.launch {
            val cached = settings.profileFlow
            _uiState.update { it.copy(baseUrl = settings.baseUrl()) }
            cached.collect { profile ->
                _uiState.update {
                    it.copy(
                        nickname = profile.nickname ?: it.nickname,
                        avatarUrl = profile.avatarUrl ?: it.avatarUrl,
                    )
                }
            }
        }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            runCatching { authRepository.me() }.onSuccess { profile ->
                if (profile != null) {
                    _uiState.update {
                        it.copy(
                            nickname = profile.nickname ?: it.nickname,
                            avatarUrl = profile.avatarUrl ?: it.avatarUrl,
                            userId = profile.id,
                        )
                    }
                }
            }
        }
    }

    fun updateBaseUrl(url: String) {
        viewModelScope.launch {
            settings.setBaseUrl(url)
            _uiState.update { it.copy(baseUrl = settings.baseUrl(), message = "服务地址已更新，重新登录后生效") }
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _loggedOut.trySend(Unit)
        }
    }

    fun consumeMessage() = _uiState.update { it.copy(message = null) }
}
