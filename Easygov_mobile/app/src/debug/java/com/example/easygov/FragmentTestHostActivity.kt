package com.example.easygov

import android.os.Bundle
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity

/**
 * Minimal debug-only host activity used by Espresso tests that need to host a
 * fragment with the app's real theme and container id. Declared in the debug
 * manifest so `connectedDebugAndroidTest` can launch and drive the app UI
 * without a launcher activity.
 */
class FragmentTestHostActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = FrameLayout(this)
        container.id = R.id.fragmentContainer
        setContentView(container)
    }
}