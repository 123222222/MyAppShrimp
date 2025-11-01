package com.dung.myapplication.mainUI.gallery

import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dung.myapplication.models.ShrimpImage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import javax.inject.Inject

@HiltViewModel
class GalleryViewModel @Inject constructor() : ViewModel() {

    val imageList = mutableStateListOf<ShrimpImage>()
    val isLoading = mutableStateOf(false)
    val errorMessage = mutableStateOf("")

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    // URL backend của bạn
    private val BACKEND_URL = "https://unstrengthening-elizabeth-nondispensible.ngrok-free.dev"

    init {
        loadImages()
    }

    fun loadImages() {
        viewModelScope.launch {
            isLoading.value = true
            errorMessage.value = ""

            withContext(Dispatchers.IO) {
                try {
                    val request = Request.Builder()
                        .url("$BACKEND_URL/api/shrimp-images")
                        .get()
                        .addHeader("User-Agent", "Android-Camera-App")
                        .build()

                    client.newCall(request).execute().use { response ->
                        if (!response.isSuccessful) {
                            withContext(Dispatchers.Main) {
                                errorMessage.value = "Server error: ${response.code}"
                                isLoading.value = false
                            }
                            return@withContext
                        }

                        val responseBody = response.body?.string()
                        if (responseBody != null) {
                            val images = json.decodeFromString<List<ShrimpImage>>(responseBody)
                            withContext(Dispatchers.Main) {
                                imageList.clear()
                                imageList.addAll(images)
                                isLoading.value = false
                            }
                        }
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        errorMessage.value = "Error: ${e.message}"
                        isLoading.value = false
                    }
                }
            }
        }
    }

    fun deleteImage(imageId: String) {
        viewModelScope.launch {
            withContext(Dispatchers.IO) {
                try {
                    val request = Request.Builder()
                        .url("$BACKEND_URL/api/shrimp-images/$imageId")
                        .delete()
                        .addHeader("User-Agent", "Android-Camera-App")
                        .build()

                    client.newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            withContext(Dispatchers.Main) {
                                imageList.removeAll { it.id == imageId }
                            }
                        }
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        errorMessage.value = "Delete failed: ${e.message}"
                    }
                }
            }
        }
    }
}

