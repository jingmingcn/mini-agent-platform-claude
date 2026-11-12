package com.miniagent.app.core.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.SmartToy
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.SubcomposeAsyncImage

/**
 * Agent / avatar image with graceful fallbacks: remote image -> first letter -> robot icon.
 */
@Composable
fun RemoteAvatar(
    url: String?,
    name: String?,
    modifier: Modifier = Modifier,
    size: androidx.compose.ui.unit.Dp = 44.dp,
) {
    val shape = RoundedCornerShape(12.dp)
    Box(
        modifier = modifier
            .size(size)
            .clip(shape)
            .background(MaterialTheme.colorScheme.primaryContainer),
        contentAlignment = Alignment.Center,
    ) {
        if (!url.isNullOrBlank()) {
            SubcomposeAsyncImage(
                model = url,
                contentDescription = name,
                contentScale = ContentScale.Crop,
                modifier = Modifier.size(size),
                loading = { Fallback(name) },
                error = { Fallback(name) },
            )
        } else {
            Fallback(name)
        }
    }
}

@Composable
private fun Fallback(name: String?) {
    val letter = name?.trim()?.firstOrNull()?.uppercaseChar()
    if (letter != null) {
        Text(
            text = letter.toString(),
            color = MaterialTheme.colorScheme.onPrimaryContainer,
            fontSize = 18.sp,
        )
    } else {
        Icon(
            Icons.Outlined.SmartToy,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onPrimaryContainer,
        )
    }
}
