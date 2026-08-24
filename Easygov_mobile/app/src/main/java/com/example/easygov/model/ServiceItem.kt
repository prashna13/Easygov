package com.example.easygov.model

import androidx.annotation.DrawableRes

/**
 * UI-facing service model for the dashboard grid cards and hero card.
 * Populated from [GovService] + the user's application progress.
 */
data class ServiceItem(
    val id: Int,
    val title: String,
    val category: String,
    @DrawableRes val iconRes: Int,
    val completedSteps: Int = 0,
    val totalSteps: Int = 5,
    val isPriority: Boolean = false
) {
    val progressPercent: Int
        get() = if (totalSteps > 0) (completedSteps * 100 / totalSteps).coerceIn(0, 100) else 0

    val isCompleted: Boolean
        get() = totalSteps > 0 && completedSteps >= totalSteps
}