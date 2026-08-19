package com.example.easygov.model

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String
)

data class RegisterRequest(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("phone") val phone: String? = null,
    @SerializedName("citizenship_number") val citizenshipNumber: String? = null,
    @SerializedName("province") val province: String? = null
)

data class GoogleLoginRequest(
    @SerializedName("id_token") val idToken: String
)

data class UserOut(
    @SerializedName("id") val id: Int,
    @SerializedName("email") val email: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("phone") val phone: String? = null,
    @SerializedName("citizenship_number") val citizenshipNumber: String? = null,
    @SerializedName("province") val province: String? = null,
    @SerializedName("age") val age: Int? = null,
    @SerializedName("date_of_birth") val dateOfBirth: String? = null,
    @SerializedName("address") val address: String? = null,
    @SerializedName("onboarding_completed") val onboardingCompleted: Boolean = false,
    @SerializedName("is_active") val isActive: Boolean = true
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer",
    @SerializedName("user") val user: UserOut
)
