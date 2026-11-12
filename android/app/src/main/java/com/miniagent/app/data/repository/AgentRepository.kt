package com.miniagent.app.data.repository

import com.miniagent.app.core.network.ApiProvider
import com.miniagent.app.core.network.apiCall
import com.miniagent.app.data.model.AgentDto
import com.miniagent.app.data.model.AppConfig
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AgentRepository @Inject constructor(
    private val apiProvider: ApiProvider,
) {
    suspend fun appConfig(): AppConfig = apiCall { apiProvider.api().appConfig() }

    suspend fun agents(keyword: String? = null): List<AgentDto> =
        apiCall { apiProvider.api().agents(keyword = keyword?.takeIf { it.isNotBlank() }) }

    suspend fun agent(id: Int): AgentDto = apiCall { apiProvider.api().agent(id) }
}
