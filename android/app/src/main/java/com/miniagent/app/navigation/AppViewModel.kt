package com.miniagent.app.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.miniagent.app.core.network.AuthEventBus
import com.miniagent.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AppViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    authEventBus: AuthEventBus,
) : ViewModel() {

    /** null = still resolving, true/false = resolved start state. */
    private val _loggedIn = MutableStateFlow<Boolean?>(null)
    val loggedIn: StateFlow<Boolean?> = _loggedIn.asStateFlow()

    /** Emits when the backend rejected the session (401); the UI routes to login. */
    val forcedLogout: SharedFlow<Unit> = authEventBus.unauthorized

    init {
        viewModelScope.launch {
            _loggedIn.value = authRepository.hasToken()
        }
    }

    fun onForcedLogout() {
        viewModelScope.launch { authRepository.logout() }
    }
}
