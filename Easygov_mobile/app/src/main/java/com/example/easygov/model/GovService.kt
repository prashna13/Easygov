package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * Data class representing a Government Service in Nepal.
 * Maps to the FastAPI backend model.
 */
data class GovService(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("title")
    val title: String,
    
    @SerializedName("category")
    val category: String,
    
    @SerializedName("description")
    val description: String,
    
    @SerializedName("is_recommended")
    val isRecommended: Boolean? = false
)
