package com.example.easygov.network

import android.content.Context
import com.example.easygov.LocaleManager
import com.example.easygov.SessionManager
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
    // Android Emulator reaches the host PC's localhost via 10.0.2.2.
    // On a physical phone (same Wi-Fi), change the base URL from the app's
    // Login or Profile screen to your PC's LAN IP, e.g. "http://192.168.1.72:8000/".
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"
    private const val PREFS_NAME = "easygov_server_prefs"
    private const val KEY_BASE_URL = "base_url"

    private lateinit var appContext: Context

    /** Call once from the Application class with the application context. */
    fun init(context: Context) {
        appContext = context.applicationContext
    }

    /** The current backend base URL (persisted; defaults to the emulator host). */
    fun getBaseUrl(): String {
        val stored = appContext
            .getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_BASE_URL, null)
        return stored?.takeIf { it.isNotBlank() } ?: DEFAULT_BASE_URL
    }

    /**
     * Persists a new backend base URL. Takes effect immediately — the next
     * call to [apiService] rebuilds with the new address.
     */
    fun setBaseUrl(url: String) {
        val normalized = url.trim().removeSuffix("/") + "/"
        appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit().putString(KEY_BASE_URL, normalized).apply()
        synchronized(this) {
            currentBaseUrl = null
            cachedApiService = null
        }
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
            // A 401 on a request that actually carried a token means the stored
            // session is stale/invalid (e.g. server secret rotated, token
            // expired). Clear it so the app stops erroring and asks for re-login
            // instead of silently hitting protected APIs forever.
            .addInterceptor { chain ->
                val resp = chain.proceed(chain.request())
                if (resp.code() == 401 && chain.request().header("Authorization") != null) {
                    SessionManager.getInstance(appContext).clearSession()
                }
                resp
            }
            .build()
    }

    @Volatile
    private var currentBaseUrl: String? = null

    @Volatile
    private var cachedApiService: ApiService? = null

    /** Lazy [ApiService] that rebuilds itself whenever the base URL changes. */
    val apiService: ApiService
        get() {
            val base = getBaseUrl()
            if (cachedApiService == null || base != currentBaseUrl) {
                synchronized(this) {
                    if (cachedApiService == null || base != currentBaseUrl) {
                        currentBaseUrl = base
                        cachedApiService = Retrofit.Builder()
                            .baseUrl(base)
                            .client(okHttpClient)
                            .addConverterFactory(GsonConverterFactory.create())
                            .build()
                            .create(ApiService::class.java)
                    }
                }
            }
            return cachedApiService!!
        }
}
