package com.example.easygov

import android.content.Context

/**
 * Persists which completed applications the user has dismissed / already uploaded
 * a document for, so the dashboard "save your new document" banner is not shown
 * again for that application. Uses [android.content.SharedPreferences.Editor.commit]
 * (not apply) so the flag survives process death and a fresh refresh.
 */
object BannerDismiss {
    private const val PREFS = "easygov_banner_prefs"
    private const val KEY = "dismissed_app_ids"

    fun dismissedIds(context: Context): Set<Int> =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY, "")
            ?.split(",")
            ?.mapNotNull { it.toIntOrNull() }
            ?.toSet()
            ?: emptySet()

    fun dismiss(context: Context, appId: Int) {
        if (appId <= 0) return
        val set = dismissedIds(context).toMutableSet()
        set.add(appId)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY, set.joinToString(","))
            .commit()
    }
}
