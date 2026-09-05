package com.example.easygov.model

import com.google.gson.annotations.SerializedName

/**
 * A government office returned by the nearby-offices endpoint.
 * Maps to the FastAPI `GovernmentOfficeOut` schema.
 */
data class Office(
    @SerializedName("id")
    val id: Int,

    @SerializedName("name")
    val name: String,

    @SerializedName("office_type")
    val officeType: String,

    @SerializedName("service_tags")
    val serviceTags: List<String> = emptyList(),

    @SerializedName("district")
    val district: String,

    @SerializedName("address")
    val address: String,

    @SerializedName("latitude")
    val latitude: Double,

    @SerializedName("longitude")
    val longitude: Double,

    @SerializedName("phone")
    val phone: String? = null,

    @SerializedName("hours")
    val hours: String? = null,

    // Straight-line (haversine) distance from the query point, in km.
    @SerializedName("distance_km")
    val distanceKm: Double? = null,

    @SerializedName("note")
    val note: String? = null
)