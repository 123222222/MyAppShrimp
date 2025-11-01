package com.dung.myapplication.utils

import android.graphics.Bitmap
import android.util.Base64
import com.dung.myapplication.models.YoloProcessResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

class ShrimpApiService {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    // URL backend của bạn (cần thay đổi theo backend thực tế)
    private val BACKEND_URL = "https://unstrengthening-elizabeth-nondispensible.ngrok-free.dev"

    suspend fun processImage(bitmap: Bitmap, sourceUrl: String): Result<YoloProcessResponse> {
        return withContext(Dispatchers.IO) {
            try {
                // Convert bitmap to Base64
                val base64Image = bitmapToBase64(bitmap)

                // Create JSON request
                val jsonBody = """
                    {
                        "image": "$base64Image",
                        "source": "$sourceUrl"
                    }
                """.trimIndent()

                val request = Request.Builder()
                    .url("$BACKEND_URL/api/detect-shrimp")
                    .post(jsonBody.toRequestBody("application/json".toMediaType()))
                    .addHeader("User-Agent", "Android-Camera-App")
                    .build()

                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        return@withContext Result.failure(
                            Exception("Server error: ${response.code} - ${response.message}")
                        )
                    }

                    val responseBody = response.body?.string()
                        ?: return@withContext Result.failure(Exception("Empty response"))

                    val result = json.decodeFromString<YoloProcessResponse>(responseBody)
                    Result.success(result)
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val outputStream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, outputStream)
        val byteArray = outputStream.toByteArray()
        return Base64.encodeToString(byteArray, Base64.NO_WRAP)
    }
}

