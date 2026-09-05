package com.example.easygov

import android.os.Bundle
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.isDisplayed
import androidx.test.espresso.matcher.ViewMatchers.withId
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Espresso smoke tests for the auth forms, hosted in [FragmentTestHostActivity]
 * (debug variant). Verifies the key form controls render without needing a live
 * backend. Run via `./gradlew connectedDebugAndroidTest`.
 */
@RunWith(AndroidJUnit4::class)
class AuthFormsTest {

    private fun launch(fragment: androidx.fragment.app.Fragment): ActivityScenario<FragmentTestHostActivity> {
        val scenario = ActivityScenario.launch(FragmentTestHostActivity::class.java)
        scenario.onActivity { activity ->
            activity.supportFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, fragment)
                .commitNow()
        }
        return scenario
    }

    @Test
    fun loginForm_showsKeyFields() {
        launch(LoginFragment())
        onView(withId(R.id.etEmail)).check(matches(isDisplayed()))
        onView(withId(R.id.etPassword)).check(matches(isDisplayed()))
        onView(withId(R.id.btnLogin)).check(matches(isDisplayed()))
        onView(withId(R.id.tvSignUp)).check(matches(isDisplayed()))
    }

    @Test
    fun registerForm_showsKeyFields() {
        launch(RegisterFragment())
        onView(withId(R.id.etFullName)).check(matches(isDisplayed()))
        onView(withId(R.id.etDateOfBirth)).check(matches(isDisplayed()))
        onView(withId(R.id.etEmail)).check(matches(isDisplayed()))
        onView(withId(R.id.btnRegister)).check(matches(isDisplayed()))
    }
}
