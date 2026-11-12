package com.miniagent.app.feature.chat

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.InsertDriveFile
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.ThumbDown
import androidx.compose.material.icons.outlined.ThumbUp
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.miniagent.app.core.designsystem.UserBubbleDark
import com.miniagent.app.core.designsystem.UserBubbleLight
import com.miniagent.app.core.ui.RemoteAvatar
import com.miniagent.app.data.model.AttachmentDto
import com.miniagent.app.data.model.CitationDto
import dev.jeziellago.compose.markdowntext.MarkdownText

@Composable
fun ChatBubble(
    message: ChatMessage,
    agentName: String?,
    agentAvatar: String?,
    isLastAssistant: Boolean,
    streaming: Boolean,
    onCopy: (String) -> Unit,
    onFeedback: (ChatMessage, Int) -> Unit,
    onRegenerate: () -> Unit,
) {
    if (message.isUser) {
        UserBubble(message)
    } else {
        AssistantBubble(
            message = message,
            agentName = agentName,
            agentAvatar = agentAvatar,
            isLastAssistant = isLastAssistant,
            streaming = streaming,
            onCopy = onCopy,
            onFeedback = onFeedback,
            onRegenerate = onRegenerate,
        )
    }
}

@Composable
private fun UserBubble(message: ChatMessage) {
    val dark = androidx.compose.foundation.isSystemInDarkTheme()
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.End,
    ) {
        Column(horizontalAlignment = Alignment.End, modifier = Modifier.widthIn(max = 300.dp)) {
            if (message.attachments.isNotEmpty()) {
                AttachmentPreviews(message.attachments)
            }
            if (message.content.isNotBlank()) {
                Surface(
                    color = if (dark) UserBubbleDark else UserBubbleLight,
                    shape = RoundedCornerShape(16.dp, 4.dp, 16.dp, 16.dp),
                ) {
                    Text(
                        text = message.content,
                        color = Color.White,
                        style = MaterialTheme.typography.bodyLarge,
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun AssistantBubble(
    message: ChatMessage,
    agentName: String?,
    agentAvatar: String?,
    isLastAssistant: Boolean,
    streaming: Boolean,
    onCopy: (String) -> Unit,
    onFeedback: (ChatMessage, Int) -> Unit,
    onRegenerate: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.Start,
        verticalAlignment = Alignment.Top,
    ) {
        RemoteAvatar(url = agentAvatar, name = agentName, size = 32.dp)
        Column(modifier = Modifier.padding(start = 8.dp).widthIn(max = 320.dp)) {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shape = RoundedCornerShape(4.dp, 16.dp, 16.dp, 16.dp),
                tonalElevation = 1.dp,
            ) {
                Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                    if (message.toolCalls.isNotEmpty()) {
                        message.toolCalls.forEach { tc ->
                            Text(
                                text = tc,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(bottom = 4.dp),
                            )
                        }
                    }
                    when {
                        message.content.isBlank() && message.isStreaming ->
                            TypingIndicator()
                        message.isError ->
                            Text(
                                text = message.content.ifBlank { "生成失败" },
                                color = MaterialTheme.colorScheme.error,
                                style = MaterialTheme.typography.bodyMedium,
                            )
                        else ->
                            MarkdownText(
                                markdown = message.content,
                                style = MaterialTheme.typography.bodyLarge.copy(
                                    color = MaterialTheme.colorScheme.onSurface,
                                ),
                            )
                    }
                }
            }

            if (message.citations.isNotEmpty()) {
                CitationsSection(message.citations)
            }

            if (!message.isStreaming && !message.isError && message.content.isNotBlank()) {
                ActionRow(
                    message = message,
                    showRegenerate = isLastAssistant && !streaming,
                    onCopy = { onCopy(message.content) },
                    onFeedback = onFeedback,
                    onRegenerate = onRegenerate,
                )
            }
            if (message.status == "interrupted") {
                Text(
                    text = "已停止生成",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.outline,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
    }
}

@Composable
private fun ActionRow(
    message: ChatMessage,
    showRegenerate: Boolean,
    onCopy: () -> Unit,
    onFeedback: (ChatMessage, Int) -> Unit,
    onRegenerate: () -> Unit,
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        SmallIcon(Icons.Outlined.ContentCopy, "复制", onClick = onCopy)
        SmallIcon(
            Icons.Outlined.ThumbUp,
            "赞",
            tint = if (message.feedback == 1) MaterialTheme.colorScheme.primary else null,
            onClick = { onFeedback(message, 1) },
        )
        SmallIcon(
            Icons.Outlined.ThumbDown,
            "踩",
            tint = if (message.feedback == -1) MaterialTheme.colorScheme.error else null,
            onClick = { onFeedback(message, -1) },
        )
        if (showRegenerate) {
            SmallIcon(Icons.Outlined.Refresh, "重新生成", onClick = onRegenerate)
        }
    }
}

@Composable
private fun SmallIcon(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    desc: String,
    tint: Color? = null,
    onClick: () -> Unit,
) {
    IconButton(onClick = onClick, modifier = Modifier.size(32.dp)) {
        Icon(
            icon,
            contentDescription = desc,
            modifier = Modifier.size(16.dp),
            tint = tint ?: MaterialTheme.colorScheme.outline,
        )
    }
}

@Composable
private fun CitationsSection(citations: List<CitationDto>) {
    var expanded by remember { mutableStateOf(false) }
    Column(modifier = Modifier.padding(top = 6.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .clickable { expanded = !expanded }
                .padding(vertical = 2.dp),
        ) {
            Icon(
                if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
                tint = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = "引用来源 (${citations.size})",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(start = 4.dp),
            )
        }
        AnimatedVisibility(visible = expanded) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                citations.forEach { c ->
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(
                                text = "[${c.index}] ${c.documentName ?: "文档"}",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            c.knowledgeBaseName?.let {
                                Text(
                                    text = it,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.outline,
                                )
                            }
                            val body = c.snippet ?: c.content
                            if (!body.isNullOrBlank()) {
                                Text(
                                    text = body,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.padding(top = 4.dp),
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AttachmentPreviews(attachments: List<AttachmentDto>) {
    Column(
        horizontalAlignment = Alignment.End,
        verticalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier.padding(bottom = 6.dp),
    ) {
        attachments.forEach { a ->
            if (a.type == "image" && !a.url.isNullOrBlank()) {
                AsyncImage(
                    model = a.url,
                    contentDescription = a.name,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .size(140.dp)
                        .background(
                            MaterialTheme.colorScheme.surfaceVariant,
                            RoundedCornerShape(12.dp),
                        ),
                )
            } else {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                    ) {
                        Icon(
                            Icons.Outlined.InsertDriveFile,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            text = a.name ?: "附件",
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(start = 6.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TypingIndicator() {
    Row(verticalAlignment = Alignment.CenterVertically) {
        androidx.compose.material3.CircularProgressIndicator(
            strokeWidth = 2.dp,
            modifier = Modifier.size(14.dp),
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = "正在思考…",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 8.dp),
        )
    }
}

/** Convenience used by the screen to copy text. */
@Composable
fun rememberCopyAction(): (String) -> Unit {
    val clipboard = LocalClipboardManager.current
    return { text -> clipboard.setText(AnnotatedString(text)) }
}
