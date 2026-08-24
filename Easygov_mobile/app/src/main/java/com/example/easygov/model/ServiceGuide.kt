package com.example.easygov.model

/**
 * UI-facing service guide model used by the service detail / guide screen.
 * Sections are carved out of the raw guidance text (OVERVIEW / PREREQUISITES /
 * DOCUMENTS NEEDED / OFFICIAL RESOURCES) so the screen can render discrete cards.
 */
data class ServiceGuide(
    val id: Int,
    val title: String,
    val category: String,
    val overview: String,
    val prerequisites: List<String>,
    val requiredDocuments: List<String>,
    val officialUrl: String? = null
) {
    companion object {
        const val EMPTY_GUIDE_ID = 0
    }
}