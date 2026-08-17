package com.example.easygov.network

import android.content.Context
import com.example.easygov.LocaleManager
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton object to provide a configured Retrofit instance.
 *
 * [init] must be called once from the Application class with the application
 * context. Every outgoing request then gets a `lang` query parameter appended
 * (read from [LocaleManager]) so the server returns localized content.
 */
object RetrofitClient {
    // For Android Emulator, use "http://10.0.2.2:8000/" to connect to host PC localhost.
    // For a physical Android phone on local Wi-Fi, use your laptop's IP e.g. "http://192.168.1.72:8000/"
    private const val BASE_URL = "http://10.0.2.2:8000/"

    private lateinit var appContext: Context

    /** Call once from the Application class with the application context. */
    fun init(context: Context) {
        appContext = context.applicationContext
    }

    private val okHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(2, TimeUnit.MINUTES)
            .readTimeout(2, TimeUnit.MINUTES)
            .writeTimeout(2, TimeUnit.MINUTES)
            .addInterceptor { chain ->
                val original = chain.request()
                val lang = LocaleManager.getInstance(appContext).getLanguage()
                val url = original.url()
                    .newBuilder()
                    .addQueryParameter("lang", lang)
                    .build()
                chain.proceed(original.newBuilder().url(url).build())
            }
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val apiService: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }
}
