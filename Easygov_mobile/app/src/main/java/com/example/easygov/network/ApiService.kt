package com.example.easygov.network

import com.example.easygov.ChatHistoryResponse
import com.example.easygov.ChatRequest
import com.example.easygov.ChatResponse
import com.example.easygov.model.DashboardResponse
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/**
 * Retrofit interface for EasyGov API endpoints.
 */
interface ApiService {

    /**
     * Fetches the dashboard data including standard services and recommendations.
     * 
     * @param authToken The JWT Bearer token for authentication.
     * @return A Call object for the DashboardResponse.
     */
    @GET("/api/v1/dashboard")
    fun getDashboardData(
        @Header("Authorization") authToken: String
    ): Call<DashboardResponse>

    /**
     * Sends a question to the RAG AI chatbot.
     */
    @POST("/ask")
    fun getBotResponse(
        @Header("Authorization") authToken: String,
        @Body request: ChatRequest
    ): Call<ChatResponse>

    /**
     * Retrieves saved chatbot history for the authenticated user.
     */
    @GET("/chat/history")
    fun getChatHistory(
        @Header("Authorization") authToken: String
    ): Call<ChatHistoryResponse>

    /**
     * Authenticates user with email and password, returning JWT token and profile details.
     */
    @POST("/auth/login")
    fun loginUser(
        @Body request: com.example.easygov.model.LoginRequest
    ): Call<com.example.easygov.model.TokenResponse>

    /**
     * Registers a new user account and returns JWT token.
     */
    @POST("/auth/register")
    fun registerUser(
        @Body request: com.example.easygov.model.RegisterRequest
    ): Call<com.example.easygov.model.TokenResponse>
}


