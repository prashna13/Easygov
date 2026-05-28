package com.example.easygov

import okhttp3.OkHttpClient
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

// Data classes matching your FastAPI JSON schema
data class ChatRequest(val question: String)
data class ChatResponse(val answer: String)

// API service structure definition
interface ChatApiService {
    @POST("/ask")
    fun getBotResponse(@Body request: ChatRequest): Call<ChatResponse>
}

// Singleton client provider
object RetrofitClient {
    // 10.0.2.2 points directly to your laptop's localhost from the emulator
    private const val BASE_URL = "http://10.0.2.2:8000/"

    // Custom HTTP client configured with a 2-minute window for local LLM processing
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(2, TimeUnit.MINUTES) // Time allowed to connect to server
        .readTimeout(2, TimeUnit.MINUTES)    // Time allowed to wait for the bot's response
        .writeTimeout(2, TimeUnit.MINUTES)   // Time allowed to send request strings
        .build()

    val instance: ChatApiService by lazy {
        val retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient) // Injects the custom timeout configuration
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        retrofit.create(ChatApiService::class.java)
    }
}