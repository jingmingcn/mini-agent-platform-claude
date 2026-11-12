package com.miniagent.app.data.repository

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.miniagent.app.core.network.ApiProvider
import com.miniagent.app.core.network.apiCall
import com.miniagent.app.data.model.UploadedFileDto
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class FileRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val apiProvider: ApiProvider,
) {
    /** Reads a picked content Uri and uploads it as a chat attachment. */
    suspend fun upload(uri: Uri): UploadedFileDto = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        val displayName = queryDisplayName(uri)
        val mime = resolver.getType(uri) ?: "application/octet-stream"
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
            ?: throw IllegalStateException("无法读取所选文件")

        val body = bytes.toRequestBody(mime.toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", displayName ?: "upload", body)
        apiCall { apiProvider.api().upload(part) }
    }

    private fun queryDisplayName(uri: Uri): String? {
        var name: String? = null
        context.contentResolver.query(uri, null, null, null, null)?.use { c ->
            if (c.moveToFirst()) {
                val nameIdx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (nameIdx >= 0) name = c.getString(nameIdx)
            }
        }
        return name
    }
}
