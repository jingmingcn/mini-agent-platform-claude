package com.miniagent.app.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.miniagent.app.core.config.SettingsStore
import com.miniagent.app.core.network.userMessage
import com.miniagent.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val baseUrl: String = "",
    val nickname: String = "",
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val settings: SettingsStore,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    private val _loginSuccess = Channel<Unit>(Channel.BUFFERED)
    val loginSuccess = _loginSuccess.receiveAsFlow()

    init {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(baseUrl = settings.baseUrl())
        }
    }

    fun onNicknameChange(value: String) {
        _uiState.value = _uiState.value.copy(nickname = value)
    }

    fun onBaseUrlChange(value: String) {
        _uiState.value = _uiState.value.copy(baseUrl = value)
    }

    fun login() {
        if (_uiState.value.loading) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            settings.setBaseUrl(_uiState.value.baseUrl)
            val result = runCatching {
                authRepository.login(nickname = _uiState.value.nickname.trim().ifBlank { null })
            }
            result.onSuccess {
                _uiState.value = _uiState.value.copy(loading = false)
                _loginSuccess.trySend(Unit)
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(loading = false, error = e.userMessage())
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
