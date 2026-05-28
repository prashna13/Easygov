package com.example.easygov.network

import com.example.easygov.model.DashboardResponse
import retrofit2.Call
import retrofit2.http.GET
import retrofit2.http.Header

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
}
