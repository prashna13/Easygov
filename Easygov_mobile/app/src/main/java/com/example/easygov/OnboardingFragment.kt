package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentManager
import com.example.easygov.model.OnboardingRequest
import com.example.easygov.model.OnboardingResponse
import com.example.easygov.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * First-login onboarding: collects the user's age and which government
 * documents they already own, then submits to the backend so the service
 * recommendations and prerequisite chain are personalized.
 */
class OnboardingFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_onboarding, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val etAge = view.findViewById<EditText>(R.id.etAge)
        val btnSubmit = view.findViewById<Button>(R.id.btnSubmitOnboarding)

        val checkboxes = listOf(
            view.findViewById<com.google.android.material.checkbox.MaterialCheckBox>(R.id.cbCitizenship),
            view.findViewById<com.google.android.material.checkbox.MaterialCheckBox>(R.id.cbNid),
            view.findViewById<com.google.android.material.checkbox.MaterialCheckBox>(R.id.cbPassport),
            view.findViewById<com.google.android.material.checkbox.MaterialCheckBox>(R.id.cbDrivingLicense)
        )
        val documentKeys = listOf(
            "citizenship",
            "nid",
            "passport",
            "driving_license"
        )

        btnSubmit.setOnClickListener {
            val age = etAge.text.toString().trim().toIntOrNull()
            if (age == null || age < 1 || age > 120) {
                Toast.makeText(context, "Please enter a valid age", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val completed = documentKeys.filterIndexed { index, _ ->
                checkboxes[index].isChecked
            }

            btnSubmit.isEnabled = false
            btnSubmit.text = "Saving..."

            val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: ""
            RetrofitClient.apiService.submitOnboarding(
                authToken,
                OnboardingRequest(age = age, completedDocuments = completed)
            ).enqueue(object : Callback<OnboardingResponse> {
                override fun onResponse(
                    call: Call<OnboardingResponse>,
                    response: Response<OnboardingResponse>
                ) {
                    btnSubmit.isEnabled = true
                    btnSubmit.text = "Continue"

                    if (response.isSuccessful) {
                        Toast.makeText(
                            context,
                            "Profile completed! Here are your personalized services.",
                            Toast.LENGTH_SHORT
                        ).show()

                        parentFragmentManager.popBackStack(
                            null,
                            FragmentManager.POP_BACK_STACK_INCLUSIVE
                        )
                        parentFragmentManager.beginTransaction()
                            .replace(R.id.fragmentContainer, DashboardFragment())
                            .commit()
                    } else {
                        Toast.makeText(
                            context,
                            "Could not save: ${response.code()}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }

                override fun onFailure(call: Call<OnboardingResponse>, t: Throwable) {
                    btnSubmit.isEnabled = true
                    btnSubmit.text = "Continue"
                    Toast.makeText(
                        context,
                        "Error: ${t.localizedMessage}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            })
        }
    }
}
