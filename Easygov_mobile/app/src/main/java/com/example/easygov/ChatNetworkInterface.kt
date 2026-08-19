package com.example.easygov

import com.google.gson.annotations.SerializedName

// Data classes matching your FastAPI JSON schema

data class ChatRequest(val question: String)
data class ChatResponse(
    val answer: String,
    val sources: List<String> = emptyList(),
    @SerializedName("guide_link") val guideLink: String? = null,
    @SerializedName("guide_service_id") val guideServiceId: Int? = null
)

data class ChatMessageResponse(
    val id: Int,
    val role: String,
    val content: String,
    val created_at: String
)

data class ChatHistoryResponse(
    val user_id: Int,
    val messages: List<ChatMessageResponse>
)
