package com.example.easygov

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Thread-safe singleton utility to manage secure storage of user session tokens.
 */
class SessionManager private constructor(context: Context) {

    private val prefs: SharedPreferences

    init {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        prefs = EncryptedSharedPreferences.create(
            context,
            "easygov_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    /**
     * Securely saves the JWT auth token.
     */
    fun saveAuthToken(token: String) {
        prefs.edit().putString(KEY_AUTH_TOKEN, token).apply()
    }

    /**
     * Retrieves the saved JWT auth token.
     */
    fun fetchAuthToken(): String? {
        return prefs.getString(KEY_AUTH_TOKEN, null)
    }

    /**
     * Clears all session data (logout).
     */
    fun clearSession() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_AUTH_TOKEN = "auth_token"

        @Volatile
        private var instance: SessionManager? = null

        fun getInstance(context: Context): SessionManager {
            return instance ?: synchronized(this) {
                instance ?: SessionManager(context.applicationContext).also { instance = it }
            }
        }
    }
}
