package com.example.easygov

// Data classes matching your FastAPI JSON schema

data class ChatRequest(val question: String)
data class ChatResponse(val answer: String)

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
