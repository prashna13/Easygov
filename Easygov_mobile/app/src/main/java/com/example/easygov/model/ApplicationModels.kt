package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * A single step within a user's application for a service.
 * Status values: PENDING, IN_PROGRESS, COMPLETED, SKIPPED.
 */
data class ProgressStep(
    @SerializedName("step_number")
    val stepNumber: Int,

    @SerializedName("step_name")
    val stepName: String,

    @SerializedName("step_description")
    val stepDescription: String? = null,

    @SerializedName("status")
    val status: String = "PENDING",

    @SerializedName("completed_at")
    val completedAt: String? = null
)

/**
 * A user's application for a service, with step-level progress.
 * Returned by the apply, get-application, and complete-step endpoints.
 */
data class ApplicationProgress(
    @SerializedName("application_id")
    val applicationId: Int,

    @SerializedName("service_id")
    val serviceId: Int,

    @SerializedName("service_title")
    val serviceTitle: String,

    @SerializedName("status")
    val status: String = "IN_PROGRESS",

    @SerializedName("progress_percent")
    val progressPercent: Int = 0,

    @SerializedName("started_at")
    val startedAt: String? = null,

    @SerializedName("completed_at")
    val completedAt: String? = null,

    @SerializedName("steps")
    val steps: List<ProgressStep> = emptyList()
)
