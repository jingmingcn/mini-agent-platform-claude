package com.miniagent.app.core.network

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import javax.inject.Inject
import javax.inject.Singleton

/** App-wide signal that the session is no longer valid (HTTP 401). */
@Singleton
class AuthEventBus @Inject constructor() {
    private val _unauthorized = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val unauthorized: SharedFlow<Unit> = _unauthorized.asSharedFlow()

    fun notifyUnauthorized() {
        _unauthorized.tryEmit(Unit)
    }
}
