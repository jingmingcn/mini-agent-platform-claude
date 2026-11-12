package com.miniagent.app.feature.history

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ChatBubbleOutline
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
import com.miniagent.app.data.model.ConversationDto

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun HistoryScreen(
    onOpenConversation: (Int) -> Unit,
    viewModel: HistoryViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    var pendingDelete by remember { mutableStateOf<ConversationDto?>(null) }

    // Refresh whenever this tab becomes active again (e.g. returning from chat).
    LaunchedEffect(Unit) { viewModel.load(refresh = true) }

    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            Text("历史会话", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(
                value = state.keyword,
                onValueChange = viewModel::onKeywordChange,
                leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null) },
                placeholder = { Text("搜索会话") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                keyboardActions = androidx.compose.foundation.text.KeyboardActions(
                    onSearch = { viewModel.search() },
                ),
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    imeAction = androidx.compose.ui.text.input.ImeAction.Search,
                ),
            )
        }

        when {
            state.loading -> LoadingState()
            state.error != null && state.conversations.isEmpty() ->
                ErrorState(message = state.error!!, onRetry = { viewModel.load() })
            else -> PullToRefreshBox(
                isRefreshing = state.refreshing,
                onRefresh = { viewModel.load(refresh = true) },
                modifier = Modifier.fillMaxSize(),
            ) {
                if (state.conversations.isEmpty()) {
                    EmptyState(text = "还没有会话，去首页选择一个智能体开始对话吧", icon = Icons.Outlined.ChatBubbleOutline)
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(
                            start = 16.dp, end = 16.dp, bottom = 16.dp,
                        ),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(state.conversations, key = { it.id }) { conv ->
                            ConversationCard(
                                conv = conv,
                                onClick = { onOpenConversation(conv.id) },
                                onLongClick = { pendingDelete = conv },
                            )
                        }
                    }
                }
            }
        }
    }

    pendingDelete?.let { conv ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text("删除会话") },
            text = { Text("确定删除「${conv.title.ifBlank { conv.agentName ?: "会话" }}」吗？此操作不可撤销。") },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.delete(conv)
                    pendingDelete = null
                }) { Text("删除", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) { Text("取消") }
            },
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ConversationCard(
    conv: ConversationDto,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .combinedClickable(onClick = onClick, onLongClick = onLongClick),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RemoteAvatar(url = conv.agentAvatar, name = conv.agentName, size = 44.dp)
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text(
                    text = conv.title.ifBlank { conv.agentName ?: "新对话" },
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = "${conv.agentName ?: ""} · ${conv.messageCount} 条消息",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
    }
}
