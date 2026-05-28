package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * Data class for the Dashboard API response.
 * Contains standard government services and personalized recommendations.
 */
data class DashboardResponse(
    @SerializedName("services")
    val services: List<GovService>,
    
    @SerializedName("recommendations")
    val recommendations: List<GovService>
)
