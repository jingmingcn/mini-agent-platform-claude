package com.miniagent.app.feature.agents

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.miniagent.app.core.ui.EmptyState
import com.miniagent.app.core.ui.ErrorState
import com.miniagent.app.core.ui.LoadingState
import com.miniagent.app.core.ui.RemoteAvatar
import com.miniagent.app.data.model.AgentDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentsScreen(
    onOpenAgent: (Int) -> Unit,
    viewModel: AgentsViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            Text(
                text = state.platformName,
                style = MaterialTheme.typography.headlineSmall,
            )
            if (state.welcomeText.isNotBlank()) {
                Text(
                    text = state.welcomeText,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
            OutlinedTextField(
                value = state.keyword,
                onValueChange = viewModel::onKeywordChange,
                leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null) },
                placeholder = { Text("搜索智能体") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
            )
        }

        if (state.categories.isNotEmpty()) {
            LazyRow(
                modifier = Modifier.fillMaxWidth().padding(bottom = 4.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item {
                    FilterChip(
                        selected = state.selectedCategory == null,
                        onClick = { viewModel.onCategorySelected(null) },
                        label = { Text("全部") },
                    )
                }
                items(state.categories) { category ->
                    FilterChip(
                        selected = state.selectedCategory == category,
                        onClick = { viewModel.onCategorySelected(category) },
                        label = { Text(category) },
                    )
                }
            }
        }

        when {
            state.loading -> LoadingState()
            state.error != null && state.allAgents.isEmpty() ->
                ErrorState(message = state.error!!, onRetry = { viewModel.load() })
            else -> PullToRefreshBox(
                isRefreshing = state.refreshing,
                onRefresh = { viewModel.load(refresh = true) },
                modifier = Modifier.fillMaxSize(),
            ) {
                val agents = state.visibleAgents
                if (agents.isEmpty()) {
                    EmptyState(text = "没有找到智能体")
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(
                            start = 16.dp, end = 16.dp, top = 4.dp, bottom = 16.dp,
                        ),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(agents, key = { it.id }) { agent ->
                            AgentCard(agent = agent, onClick = { onOpenAgent(agent.id) })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AgentCard(agent: AgentDto, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RemoteAvatar(url = agent.avatar, name = agent.name, size = 48.dp)
            Column(
                modifier = Modifier.weight(1f).padding(start = 12.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = agent.name,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false),
                    )
                    if (agent.isFeatured) {
                        Text(
                            text = "精选",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(start = 6.dp),
                        )
                    }
                }
                val subtitle = agent.description ?: agent.category ?: "点击开始对话"
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 3.dp),
                )
            }
        }
    }
}
