package com.example.easygov

import android.Manifest
import android.os.Bundle
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.isDisplayed
import androidx.test.espresso.matcher.ViewMatchers.withId
import androidx.test.espresso.matcher.ViewMatchers.withText
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Espresso coverage for the "Find Nearest Office" button flow:
 * the button exists on a service detail screen and tapping it opens the
 * Nearby Offices screen. Fragments are hosted in [FragmentTestHostActivity]
 * (debug variant); location is pre-granted via [GrantPermissionRule].
 */
@RunWith(AndroidJUnit4::class)
class NearbyOfficesTest {

    @get:Rule
    val locationPermission: GrantPermissionRule =
        GrantPermissionRule.grant(Manifest.permission.ACCESS_COARSE_LOCATION)

    private fun launchHost(args: Bundle): ActivityScenario<FragmentTestHostActivity> {
        val scenario = ActivityScenario.launch(FragmentTestHostActivity::class.java)
        scenario.onActivity { activity ->
            activity.supportFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, ServiceDetailFragment().apply { arguments = args })
                .commitNow()
        }
        return scenario
    }

    private fun serviceDetailArgs(): Bundle = Bundle().apply {
        putInt("service_id", 1)
        putString("service_title", "E-Passport Apply")
        putString("service_category", "Travel")
    }

    @Test
    fun serviceDetail_showsFindNearestOfficeButton() {
        launchHost(serviceDetailArgs())

        onView(withId(R.id.btnFindNearestOffice)).check(matches(isDisplayed()))
    }

    @Test
    fun serviceDetail_tapButton_opensNearbyOffices() {
        launchHost(serviceDetailArgs())

        onView(withId(R.id.btnFindNearestOffice)).perform(click())

        onView(withId(R.id.tvNearbyTitle)).check(matches(withText(R.string.office_nearby_title)))
    }

    @Test
    fun nearbyOffices_showsHeaderForService() {
        val scenario = ActivityScenario.launch(FragmentTestHostActivity::class.java)
        scenario.onActivity { activity ->
            activity.supportFragmentManager.beginTransaction()
                .replace(
                    R.id.fragmentContainer,
                    NearbyOfficesFragment.newInstance("citizenship", "Citizenship Certificate Copy")
                )
                .commitNow()
        }

        onView(withId(R.id.tvNearbyTitle)).check(matches(isDisplayed()))
    }
}