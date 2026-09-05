package com.example.easygov

import com.example.easygov.model.ApplicationProgress
import com.example.easygov.model.DashboardResponse
import com.example.easygov.model.GovService
import com.example.easygov.model.Office
import com.example.easygov.model.TokenResponse
import com.example.easygov.model.UserDocument
import com.example.easygov.model.UserOut
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * JVM unit tests that pin the Android → FastAPI contract by round-tripping the
 * backend's JSON (snake_case) through the Gson-backed data classes. A mismatch
 * here means the app would silently read nulls/wrong values in production.
 */
class ApiModelsTest {

    private val gson = Gson()

    @Test
    fun tokenResponse_mapsUserAndToken() {
        val json = """
            {
              "access_token": "eyJhbGciOi.abc.def",
              "token_type": "bearer",
              "user": {
                "id": 7,
                "email": "ram@example.np",
                "full_name": "Ram Shrestha",
                "date_of_birth": "2000-05-10",
                "onboarding_completed": true,
                "is_active": true
              }
            }
        """.trimIndent()
        val t = gson.fromJson(json, TokenResponse::class.java)
        assertEquals("eyJhbGciOi.abc.def", t.accessToken)
        assertEquals("bearer", t.tokenType)
        assertEquals("ram@example.np", t.user.email)
        assertEquals("Ram Shrestha", t.user.fullName)
        assertEquals("2000-05-10", t.user.dateOfBirth)
        assertTrue(t.user.onboardingCompleted)
        assertTrue(t.user.isActive)
    }

    @Test
    fun userOut_nullsOptionalFields() {
        val json = """{"id":1,"email":"a@b.np","full_name":"A","is_active":true}"""
        val u = gson.fromJson(json, UserOut::class.java)
        assertNull(u.phone)
        assertNull(u.citizenshipNumber)
        assertNull(u.province)
        assertNull(u.age)
        assertNull(u.address)
        assertFalse(u.onboardingCompleted)
    }

    @Test
    fun applicationProgress_mapsSteps() {
        val json = """
            {
              "application_id": 11,
              "service_id": 2,
              "service_title": "NID Registration",
              "status": "IN_PROGRESS",
              "progress_percent": 50,
              "steps": [
                {"step_number": 1, "step_name": "Register online", "status": "COMPLETED"},
                {"step_number": 2, "step_name": "Visit centre", "status": "PENDING"}
              ]
            }
        """.trimIndent()
        val a = gson.fromJson(json, ApplicationProgress::class.java)
        assertEquals(11, a.applicationId)
        assertEquals(2, a.serviceId)
        assertEquals("NID Registration", a.serviceTitle)
        assertEquals("IN_PROGRESS", a.status)
        assertEquals(50, a.progressPercent)
        assertEquals(2, a.steps.size)
        assertEquals("COMPLETED", a.steps[0].status)
        assertEquals("PENDING", a.steps[1].status)
    }

    @Test
    fun userDocument_mapsVaultFields() {
        val json = """
            {
              "id": 3,
              "label": "Citizenship",
              "tags": ["citizenship", "copy"],
              "mime_type": "image/png",
              "filename": "citizenship.png",
              "size_bytes": 2048,
              "created_at": "2026-01-01T10:00:00"
            }
        """.trimIndent()
        val d = gson.fromJson(json, UserDocument::class.java)
        assertEquals(3, d.id)
        assertEquals("Citizenship", d.label)
        assertEquals(listOf("citizenship", "copy"), d.tags)
        assertEquals("image/png", d.mimeType)
        assertEquals("citizenship.png", d.filename)
        assertEquals(2048L, d.sizeBytes)
    }

    @Test
    fun dashboard_mapsRecsAndNextStep() {
        val json = """
            {
              "user_name": "Guest User",
              "needs_onboarding": false,
              "services": [
                {"id": 1, "title": "Citizenship", "category": "Identity", "fee_npr": 10}
              ],
              "recommendations": [
                {"id": 2, "title": "NID Registration", "category": "Identity"}
              ],
              "recommended_next_step": {"id": 3, "title": "E-Passport Apply", "category": "Travel"}
            }
        """.trimIndent()
        val d = gson.fromJson(json, DashboardResponse::class.java)
        assertEquals("Guest User", d.userName)
        assertFalse(d.needsOnboarding)
        assertEquals(1, d.services.size)
        assertEquals(10, d.services[0].feeNpr)
        assertEquals(1, d.recommendations.size)
        assertEquals("NID Registration", d.recommendations[0].title)
        assertNotNull(d.recommendedNextStep)
        assertEquals(3, d.recommendedNextStep!!.id)
    }

    @Test
    fun govService_mapsCatalogFields() {
        // Mirrors the backend's GovServiceOut, which always emits these flags.
        val json = """
            {
              "id": 5,
              "title": "Business Registration",
              "category": "Business",
              "is_recommended": false,
              "prerequisites_met": true,
              "missing_prerequisites": []
            }
        """.trimIndent()
        val s = gson.fromJson(json, GovService::class.java)
        assertEquals(0, s.feeNpr)                    // absent -> Java int default
        assertNull(s.estimatedDays)                  // absent -> null (Kotlin default not applied)
        assertNull(s.description)
        assertNull(s.department)
        assertEquals(false, s.isRecommended)
        assertTrue(s.prerequisitesMet == true)
        assertTrue(s.missingPrerequisites!!.isEmpty())
    }

    @Test
    fun office_mapsTagsAndNote() {
        val json = """
            {
              "id": 9,
              "name": "Office of the Company Registrar (OCR)",
              "office_type": "Company Registrar Office",
              "service_tags": ["business_registration", "business"],
              "district": "Kathmandu",
              "address": "Tripureshwor, Kathmandu",
              "latitude": 27.6953,
              "longitude": 85.3148,
              "distance_km": 1.2,
              "note": "Primary body for company incorporation."
            }
        """.trimIndent()
        val o = gson.fromJson(json, Office::class.java)
        assertEquals("Office of the Company Registrar (OCR)", o.name)
        assertEquals(listOf("business_registration", "business"), o.serviceTags)
        assertEquals(27.6953, o.latitude, 1e-6)
        assertEquals(1.2, o.distanceKm!!, 1e-6)
        assertEquals("Primary body for company incorporation.", o.note)
    }
}
