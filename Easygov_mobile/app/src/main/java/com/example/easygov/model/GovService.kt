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
    val description: String? = null,

    @SerializedName("department")
    val department: String? = null,

    @SerializedName("estimated_days")
    val estimatedDays: Int? = null,

    @SerializedName("fee_npr")
    val feeNpr: Int = 0,

    @SerializedName("is_recommended")
    val isRecommended: Boolean? = false,

    @SerializedName("prerequisites_met")
    val prerequisitesMet: Boolean? = true,

    @SerializedName("missing_prerequisites")
    val missingPrerequisites: List<String>? = emptyList()
)
