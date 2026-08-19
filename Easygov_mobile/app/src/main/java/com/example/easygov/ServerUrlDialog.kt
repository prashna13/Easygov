package com.example.easygov

import android.content.Context
import android.text.InputType
import android.view.ViewGroup
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import com.example.easygov.network.RetrofitClient
import com.google.android.material.dialog.MaterialAlertDialogBuilder

/**
 * Edits the backend base URL (visible on Login and Profile screens so users
 * on a physical phone can point the app at their PC's LAN IP instead of the
 * emulator-only 10.0.2.2 default, e.g. "http://192.168.1.72:8000/").
 */
object ServerUrlDialog {

    fun show(context: Context, onSaved: (() -> Unit)? = null) {
        val input = EditText(context).apply {
            setText(RetrofitClient.getBaseUrl())
            hint = context.getString(R.string.server_address_hint)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setSelection(text.length)
        }
        val container = FrameLayout(context).apply {
            addView(
                input,
                FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            )
            setPadding(48, 16, 48, 16)
        }

        MaterialAlertDialogBuilder(context)
            .setTitle(R.string.server_address)
            .setView(container)
            .setPositiveButton(R.string.doc_save) { _, _ ->
                val url = input.text.toString().trim()
                if (url.isNotEmpty()) {
                    RetrofitClient.setBaseUrl(url)
                    onSaved?.invoke()
                    Toast.makeText(context, R.string.server_address_saved, Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(context, R.string.server_address_empty, Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton(R.string.doc_cancel, null)
            .show()
    }
}