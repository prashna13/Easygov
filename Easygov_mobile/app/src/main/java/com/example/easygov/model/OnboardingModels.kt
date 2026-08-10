package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * Request payload for the first-login onboarding flow.
 * `completedDocuments` are document keys the user already owns, e.g.
 * ["birth_certificate", "citizenship", "nid"].
 */
data class OnboardingRequest(
    @SerializedName("age") val age: Int,
    @SerializedName("completed_documents") val completedDocuments: List<String>
)

data class OnboardingResponse(
    @SerializedName("onboarding_completed") val onboardingCompleted: Boolean = false,
    @SerializedName("recommended_next_step") val recommendedNextStep: GovService? = null
)

data class ServiceDetailResponse(
    @SerializedName("service") val service: GovService? = null,
    @SerializedName("prerequisites_met") val prerequisitesMet: Boolean = true,
    @SerializedName("missing_prerequisites") val missingPrerequisites: List<String> = emptyList(),
    @SerializedName("recommended_next_step") val recommendedNextStep: GovService? = null
)
