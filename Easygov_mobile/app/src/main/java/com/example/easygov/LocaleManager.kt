package com.example.easygov

import android.content.Context
import android.content.SharedPreferences
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat

/**
 * Manages the app-wide display language ("en" or "ne").
 *
 * The chosen language is persisted in a plain SharedPreferences file and
 * applied through [AppCompatDelegate.setApplicationLocales], which
 * recreates the activity/fragments with the new configuration. The same
 * value is also appended as a `lang` query parameter to API calls by the
 * Retrofit interceptor so the server returns localized content.
 */
class LocaleManager private constructor(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getLanguage(): String {
        return prefs.getString(KEY_LANGUAGE, DEFAULT_LANGUAGE) ?: DEFAULT_LANGUAGE
    }

    fun setLanguage(language: String) {
        val normalized = if (language == "ne") "ne" else "en"
        prefs.edit().putString(KEY_LANGUAGE, normalized).apply()
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(normalized))
    }

    companion object {
        private const val PREFS_NAME = "easygov_locale_prefs"
        private const val KEY_LANGUAGE = "app_language"
        private const val DEFAULT_LANGUAGE = "en"

        @Volatile
        private var instance: LocaleManager? = null

        fun getInstance(context: Context): LocaleManager {
            return instance ?: synchronized(this) {
                instance ?: LocaleManager(context.applicationContext).also { instance = it }
            }
        }
    }
}
