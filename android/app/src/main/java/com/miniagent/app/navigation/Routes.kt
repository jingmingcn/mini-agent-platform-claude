package com.miniagent.app.navigation

object Routes {
    const val LOGIN = "login"
    const val AGENTS = "agents"
    const val HISTORY = "history"
    const val PROFILE = "profile"

    // chat?agentId={agentId}&conversationId={conversationId}
    const val CHAT = "chat"
    const val ARG_AGENT_ID = "agentId"
    const val ARG_CONVERSATION_ID = "conversationId"

    fun chatWithAgent(agentId: Int): String = "$CHAT?$ARG_AGENT_ID=$agentId&$ARG_CONVERSATION_ID=-1"
    fun chatWithConversation(conversationId: Int): String =
        "$CHAT?$ARG_AGENT_ID=-1&$ARG_CONVERSATION_ID=$conversationId"
}

/** Bottom navigation tabs. */
enum class TabDestination(val route: String, val label: String) {
    Agents(Routes.AGENTS, "智能体"),
    History(Routes.HISTORY, "会话"),
    Profile(Routes.PROFILE, "我的"),
}
