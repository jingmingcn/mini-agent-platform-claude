package com.miniagent.app.feature.chat

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.Send
import androidx.compose.material.icons.outlined.AttachFile
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.miniagent.app.core.ui.LoadingState
import com.miniagent.app.core.ui.RemoteAvatar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onBack: () -> Unit,
    viewModel: ChatViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val snackbarHost = remember { SnackbarHostState() }
    val copy = rememberCopyAction()

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent(),
    ) { uri -> if (uri != null) viewModel.addAttachment(uri) }

    // Auto-scroll to the newest content as it streams in.
    val lastContentLength = state.messages.lastOrNull()?.content?.length ?: 0
    LaunchedEffect(state.messages.size, lastContentLength) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.size - 1)
        }
    }

    LaunchedEffect(state.error) {
        state.error?.let {
            snackbarHost.showSnackbar(it)
            viewModel.consumeError()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHost) },
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RemoteAvatar(url = state.headerAvatar, name = state.headerTitle, size = 30.dp)
                        Text(
                            text = state.headerTitle,
                            style = MaterialTheme.typography.titleMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(start = 8.dp),
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "返回")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .imePadding(),
        ) {
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                when {
                    state.loading -> LoadingState()
                    else -> LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(
                            horizontal = 12.dp, vertical = 8.dp,
                        ),
                    ) {
                        if (state.messages.isEmpty()) {
                            item {
                                WelcomeBlock(
                                    title = state.headerTitle,
                                    avatar = state.headerAvatar,
                                    welcome = state.welcomeMessage,
                                    suggestions = state.suggestedQuestions,
                                    onSuggestion = viewModel::useSuggestion,
                                )
                            }
                        }
                        items(state.messages, key = { it.localId }) { message ->
                            val isLastAssistant = message.role == "assistant" &&
                                message.localId == state.messages.lastOrNull()?.localId
                            ChatBubble(
                                message = message,
                                agentName = state.headerTitle,
                                agentAvatar = state.headerAvatar,
                                isLastAssistant = isLastAssistant,
                                streaming = state.streaming,
                                onCopy = copy,
                                onFeedback = viewModel::sendFeedback,
                                onRegenerate = viewModel::regenerate,
                            )
                        }
                    }
                }
            }

            Composer(
                state = state,
                onInputChange = viewModel::onInputChange,
                onSend = viewModel::send,
                onStop = viewModel::stopGeneration,
                onAttach = { picker.launch("*/*") },
                onRemoveAttachment = viewModel::removeAttachment,
            )
        }
    }
}

@Composable
private fun WelcomeBlock(
    title: String,
    avatar: String?,
    welcome: String?,
    suggestions: List<String>,
    onSuggestion: (String) -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 24.dp, bottom = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        RemoteAvatar(url = avatar, name = title, size = 64.dp)
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.padding(top = 12.dp),
        )
        if (!welcome.isNullOrBlank()) {
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.padding(top = 12.dp, start = 24.dp, end = 24.dp),
            ) {
                Text(
                    text = welcome,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(14.dp),
                )
            }
        }
        if (suggestions.isNotEmpty()) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp, start = 24.dp, end = 24.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                suggestions.forEach { q ->
                    SuggestionChip(
                        onClick = { onSuggestion(q) },
                        label = { Text(q) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun Composer(
    state: ChatUiState,
    onInputChange: (String) -> Unit,
    onSend: () -> Unit,
    onStop: () -> Unit,
    onAttach: () -> Unit,
    onRemoveAttachment: (Long) -> Unit,
) {
    Surface(tonalElevation = 3.dp, color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxWidth().padding(8.dp)) {
            if (state.pendingAttachments.isNotEmpty()) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    state.pendingAttachments.forEach { att ->
                        Surface(
                            color = MaterialTheme.colorScheme.surfaceVariant,
                            shape = RoundedCornerShape(10.dp),
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.padding(start = 10.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
                            ) {
                                Text(
                                    text = if (att.uploading) "上传中…" else att.filename,
                                    style = MaterialTheme.typography.labelMedium,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.widthIn(max = 160.dp),
                                )
                                IconButton(
                                    onClick = { onRemoveAttachment(att.localKey) },
                                    modifier = Modifier.size(24.dp),
                                ) {
                                    Icon(
                                        Icons.Outlined.Close,
                                        contentDescription = "移除",
                                        modifier = Modifier.size(14.dp),
                                    )
                                }
                            }
                        }
                    }
                }
            }

            Row(verticalAlignment = Alignment.Bottom) {
                IconButton(onClick = onAttach, enabled = !state.streaming) {
                    Icon(Icons.Outlined.AttachFile, contentDescription = "添加附件")
                }
                TextField(
                    value = state.input,
                    onValueChange = onInputChange,
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("发消息…") },
                    maxLines = 5,
                    shape = RoundedCornerShape(20.dp),
                    colors = TextFieldDefaults.colors(
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent,
                        focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                    ),
                )
                Box(modifier = Modifier.padding(start = 6.dp)) {
                    if (state.streaming) {
                        FilledCircleButton(
                            icon = Icons.Outlined.Stop,
                            desc = "停止生成",
                            container = MaterialTheme.colorScheme.error,
                            onClick = onStop,
                        )
                    } else {
                        FilledCircleButton(
                            icon = Icons.AutoMirrored.Outlined.Send,
                            desc = "发送",
                            container = MaterialTheme.colorScheme.primary,
                            enabled = state.canSend,
                            onClick = onSend,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun FilledCircleButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    desc: String,
    container: Color,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    Surface(
        shape = CircleShape,
        color = if (enabled) container else MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.size(44.dp),
    ) {
        IconButton(onClick = onClick, enabled = enabled) {
            Icon(
                icon,
                contentDescription = desc,
                tint = if (enabled) Color.White else MaterialTheme.colorScheme.outline,
            )
        }
    }
}

