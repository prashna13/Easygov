package com.example.easygov

import android.app.Application
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import com.example.easygov.network.RetrofitClient

/**
 * Application class that restores the user's saved display language before
 * any activity is created, so the whole UI renders in the chosen locale.
 */
class EasyGovApp : Application() {

    override fun onCreate() {
        super.onCreate()
        RetrofitClient.init(this)
        val language = LocaleManager.getInstance(this).getLanguage()
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(language))
    }
}
