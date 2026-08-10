package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * Data class for the Dashboard API response.
 * Contains user name, standard government services and personalized recommendations.
 */
data class DashboardResponse(
    @SerializedName("user_name")
    val userName: String = "Guest User",

    @SerializedName("services")
    val services: List<GovService>,

    @SerializedName("recommendations")
    val recommendations: List<GovService>,

    @SerializedName("needs_onboarding")
    val needsOnboarding: Boolean = false,

    @SerializedName("recommended_next_step")
    val recommendedNextStep: GovService? = null
)
