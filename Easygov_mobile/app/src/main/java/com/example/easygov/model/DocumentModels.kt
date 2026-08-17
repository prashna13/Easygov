package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * A user-uploaded document stored in their private vault.
 * Returned by the upload, list, and update endpoints.
 */
data class UserDocument(
    @SerializedName("id")
    val id: Int,

    @SerializedName("label")
    val label: String,

    @SerializedName("tags")
    val tags: List<String> = emptyList(),

    @SerializedName("description")
    val description: String? = null,

    @SerializedName("filename")
    val filename: String,

    @SerializedName("mime_type")
    val mimeType: String,

    @SerializedName("size_bytes")
    val sizeBytes: Long = 0,

    @SerializedName("created_at")
    val createdAt: String? = null
)
