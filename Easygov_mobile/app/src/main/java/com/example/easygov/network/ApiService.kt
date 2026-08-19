package com.example.easygov.network

import com.example.easygov.ChatHistoryResponse
import com.example.easygov.ChatRequest
import com.example.easygov.ChatResponse
import com.example.easygov.model.ApplicationProgress
import com.example.easygov.model.DashboardResponse
import com.example.easygov.model.Office
import com.example.easygov.model.OnboardingRequest
import com.example.easygov.model.OnboardingResponse
import com.example.easygov.model.ServiceDetailResponse
import com.example.easygov.model.UserDocument
import com.example.easygov.model.UserOut
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit interface for EasyGov API endpoints.
 */
interface ApiService {

    /**
     * Fetches the dashboard data including standard services and recommendations.
     * 
     * @param authToken The JWT Bearer token for authentication.
     * @return A Call object for the DashboardResponse.
     */
    @GET("/api/v1/dashboard")
    fun getDashboardData(
        @Header("Authorization") authToken: String
    ): Call<DashboardResponse>

    /**
     * Submits the first-login onboarding form (age + owned documents).
     */
    @POST("/api/v1/onboarding")
    fun submitOnboarding(
        @Header("Authorization") authToken: String,
        @Body request: OnboardingRequest
    ): Call<OnboardingResponse>

    /**
     * Fetches full detail for a single service, including whether its
     * prerequisites are satisfied. Drives the blocked/informational flow.
     */
    @GET("/api/v1/services/{serviceId}")
    fun getServiceDetail(
        @Header("Authorization") authToken: String,
        @Path("serviceId") serviceId: Int
    ): Call<ServiceDetailResponse>

    /**
     * Starts an application for a service, creating its step-level progress
     * checklist. Returns the application with its steps.
     */
    @POST("/api/v1/services/{serviceId}/apply")
    fun startApplication(
        @Header("Authorization") authToken: String,
        @Path("serviceId") serviceId: Int
    ): Call<ApplicationProgress>

    /**
     * Returns the authenticated user's full profile.
     */
    @GET("/auth/me")
    fun getProfile(
        @Header("Authorization") authToken: String
    ): Call<UserOut>

    /**
     * Returns all of the user's applications with step-level progress,
     * newest first. Drives the profile "My Progress" section.
     */
    @GET("/api/v1/applications")
    fun getApplications(
        @Header("Authorization") authToken: String
    ): Call<List<ApplicationProgress>>

    /**
     * Fetches a user's application and its step-level progress.
     */
    @GET("/api/v1/applications/{applicationId}")
    fun getApplication(
        @Header("Authorization") authToken: String,
        @Path("applicationId") applicationId: Int
    ): Call<ApplicationProgress>

    /**
     * Marks a step of an application as COMPLETED and advances the checklist.
     * Returns the updated application.
     */
    @POST("/api/v1/applications/{applicationId}/steps/{stepNumber}/complete")
    fun completeStep(
        @Header("Authorization") authToken: String,
        @Path("applicationId") applicationId: Int,
        @Path("stepNumber") stepNumber: Int
    ): Call<ApplicationProgress>

    /**
     * Sends a question to the RAG AI chatbot.
     */
    @POST("/ask")
    fun getBotResponse(
        @Header("Authorization") authToken: String,
        @Body request: ChatRequest
    ): Call<ChatResponse>

    /**
     * Retrieves saved chatbot history for the authenticated user.
     */
    @GET("/chat/history")
    fun getChatHistory(
        @Header("Authorization") authToken: String
    ): Call<ChatHistoryResponse>

    /**
     * Authenticates user with email and password, returning JWT token and profile details.
     */
    @POST("/auth/login")
    fun loginUser(
        @Body request: com.example.easygov.model.LoginRequest
    ): Call<com.example.easygov.model.TokenResponse>

    /**
     * Registers a new user account and returns JWT token.
     */
    @POST("/auth/register")
    fun registerUser(
        @Body request: com.example.easygov.model.RegisterRequest
    ): Call<com.example.easygov.model.TokenResponse>

    /**
     * Authenticates (or auto-registers) a user via a Google Sign-In ID token.
     */
    @POST("/auth/google")
    fun googleLogin(
        @Body request: com.example.easygov.model.GoogleLoginRequest
    ): Call<com.example.easygov.model.TokenResponse>

    /**
     * Uploads a document (image/PDF) into the user's document vault.
     * The label and tags are sent as multipart form fields.
     */
    @Multipart
    @POST("/api/v1/documents")
    fun uploadDocument(
        @Header("Authorization") authToken: String,
        @Part("label") label: RequestBody,
        @Part("tags") tags: RequestBody,
        @Part("description") description: RequestBody,
        @Part file: MultipartBody.Part
    ): Call<UserDocument>

    /**
     * Returns all documents in the user's vault, newest first.
     */
    @GET("/api/v1/documents")
    fun getDocuments(
        @Header("Authorization") authToken: String
    ): Call<List<UserDocument>>

    /**
     * Deletes a document from the user's vault.
     */
    @DELETE("/api/v1/documents/{documentId}")
    fun deleteDocument(
        @Header("Authorization") authToken: String,
        @Path("documentId") documentId: Int
    ): Call<ResponseBody>

    /**
     * Returns the government offices serving `serviceType` within `radius` km
     * of (`lat`, `lng`), sorted nearest-first.
     *
     * Public endpoint — pass null authToken when the user is not signed in
     * (Retrofit omits null @Header values).
     */
    @GET("/api/v1/offices/nearby")
    fun getNearbyOffices(
        @Header("Authorization") authToken: String?,
        @Query("service_type") serviceType: String,
        @Query("lat") lat: Double,
        @Query("lng") lng: Double,
        @Query("radius") radius: Double
    ): Call<List<Office>>

    /**
     * Downloads the raw file bytes for a document.
     */
    @GET("/api/v1/documents/{documentId}/download")
    fun downloadDocument(
        @Header("Authorization") authToken: String,
        @Path("documentId") documentId: Int
    ): Call<ResponseBody>
}


