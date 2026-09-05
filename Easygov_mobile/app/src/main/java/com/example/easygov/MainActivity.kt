package com.example.easygov

import android.os.Bundle
import android.view.View
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import androidx.fragment.app.Fragment
import com.google.android.material.navigation.NavigationBarView

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val mainRoot = findViewById<View>(R.id.mainRoot)
        val fragmentContainer = findViewById<View>(R.id.fragmentContainer)
        val bottomNav = findViewById<NavigationBarView>(R.id.bottomNavigation)

        ViewCompat.setOnApplyWindowInsetsListener(mainRoot) { _, insets ->
            val statusBars = insets.getInsets(
                WindowInsetsCompat.Type.statusBars() or WindowInsetsCompat.Type.displayCutout()
            )
            val navBars = insets.getInsets(WindowInsetsCompat.Type.navigationBars())

            fragmentContainer.updatePadding(
                left = statusBars.left,
                top = statusBars.top,
                right = statusBars.right,
                bottom = 0
            )

            bottomNav.updatePadding(
                left = navBars.left,
                top = 0,
                right = navBars.right,
                bottom = navBars.bottom
            )

            insets
        }

        // Set the default launch fragment tab when user opens app (Start with Chatbot for now)
        if (savedInstanceState == null) {
            bottomNav.selectedItemId = R.id.nav_chat
            loadFragment(ChatFragment())
        }

        // Handle navigation clicks across navigation targets
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                // We'll map real fragments here soon. For now, they swap or stay in ChatFragment
                R.id.nav_dashboard -> {
                    loadFragment(DashboardFragment())
                    true
                }
                R.id.nav_chat -> {
                    loadFragment(ChatFragment())
                    true
                }
                R.id.nav_documents -> {
                    val sessionManager = SessionManager.getInstance(this@MainActivity)
                    if (sessionManager.fetchAuthToken() != null) {
                        loadFragment(DocumentsFragment())
                    } else {
                        loadFragment(LoginFragment())
                    }
                    true
                }
                R.id.nav_profile -> {
                    val sessionManager = SessionManager.getInstance(this@MainActivity)
                    if (sessionManager.fetchAuthToken() != null) {
                        loadFragment(ProfileFragment())
                    } else {
                        loadFragment(LoginFragment())
                    }
                    true
                }
                else -> false
            }
        }
    }

    private fun loadFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }
}