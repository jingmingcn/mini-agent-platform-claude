package com.miniagent.app.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Chat
import androidx.compose.material.icons.outlined.Apps
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.miniagent.app.core.ui.LoadingState
import com.miniagent.app.feature.agents.AgentsScreen
import com.miniagent.app.feature.auth.LoginScreen
import com.miniagent.app.feature.chat.ChatScreen
import com.miniagent.app.feature.history.HistoryScreen
import com.miniagent.app.feature.profile.ProfileScreen

@Composable
fun AppRoot(appViewModel: AppViewModel = hiltViewModel()) {
    val loggedIn by appViewModel.loggedIn.collectAsStateWithLifecycle()

    when (loggedIn) {
        null -> LoadingState()
        else -> {
            val navController = rememberNavController()
            LaunchedEffect(navController) {
                appViewModel.forcedLogout.collect {
                    appViewModel.onForcedLogout()
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                        launchSingleTop = true
                    }
                }
            }
            AppScaffold(
                navController = navController,
                start = if (loggedIn == true) Routes.AGENTS else Routes.LOGIN,
            )
        }
    }
}

@Composable
private fun AppScaffold(navController: NavHostController, start: String) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute in TabDestination.entries.map { it.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    TabDestination.entries.forEach { tab ->
                        val selected = backStackEntry?.destination?.hierarchy
                            ?.any { it.route == tab.route } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(tab.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon(), contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = start,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.LOGIN) {
                LoginScreen(
                    onLoggedIn = {
                        navController.navigate(Routes.AGENTS) {
                            popUpTo(Routes.LOGIN) { inclusive = true }
                            launchSingleTop = true
                        }
                    },
                )
            }
            composable(Routes.AGENTS) {
                AgentsScreen(onOpenAgent = { navController.navigate(Routes.chatWithAgent(it)) })
            }
            composable(Routes.HISTORY) {
                HistoryScreen(onOpenConversation = { navController.navigate(Routes.chatWithConversation(it)) })
            }
            composable(Routes.PROFILE) {
                ProfileScreen(
                    onLoggedOut = {
                        navController.navigate(Routes.LOGIN) {
                            popUpTo(0) { inclusive = true }
                            launchSingleTop = true
                        }
                    },
                )
            }
            composable(
                route = "${Routes.CHAT}?${Routes.ARG_AGENT_ID}={${Routes.ARG_AGENT_ID}}&${Routes.ARG_CONVERSATION_ID}={${Routes.ARG_CONVERSATION_ID}}",
                arguments = listOf(
                    navArgument(Routes.ARG_AGENT_ID) {
                        type = NavType.IntType
                        defaultValue = -1
                    },
                    navArgument(Routes.ARG_CONVERSATION_ID) {
                        type = NavType.IntType
                        defaultValue = -1
                    },
                ),
            ) {
                ChatScreen(onBack = { navController.popBackStack() })
            }
        }
    }
}

private fun TabDestination.icon(): ImageVector = when (this) {
    TabDestination.Agents -> Icons.Outlined.Apps
    TabDestination.History -> Icons.AutoMirrored.Outlined.Chat
    TabDestination.Profile -> Icons.Outlined.Person
}
