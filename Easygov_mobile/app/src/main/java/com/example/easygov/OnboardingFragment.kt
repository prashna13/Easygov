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
import com.example.easygov.model.UserOut
import com.example.easygov.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * First-login onboarding: collects which government documents the user already
 * owns, then submits so the service recommendations and prerequisite chain are
 * personalized. Age is captured at registration (date_of_birth), so it is only
 * asked here as a fallback for accounts that have no date of birth (e.g. Google
 * sign-in).
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
        val aboutYouPanel = view.findViewById<View>(R.id.aboutYouPanel)
        val btnSubmit = view.findViewById<Button>(R.id.btnSubmitOnboarding)

        // Decide whether the age field is needed. Normally age is derived from
        // date_of_birth at registration, so hide the panel for those accounts.
        val profileToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: ""
        RetrofitClient.apiService.getProfile(profileToken).enqueue(object : Callback<UserOut> {
            override fun onResponse(call: Call<UserOut>, response: Response<UserOut>) {
                val hasDob = response.isSuccessful
                    && response.body() != null
                    && !response.body()!!.dateOfBirth.isNullOrBlank()
                aboutYouPanel.visibility = if (hasDob) View.GONE else View.VISIBLE
            }

            override fun onFailure(call: Call<UserOut>, t: Throwable) {
                // Can't confirm a DOB — keep the age field as a safety net.
                aboutYouPanel.visibility = View.VISIBLE
            }
        })

        view.findViewById<View>(R.id.btnSkipOnboarding).setOnClickListener {
            parentFragmentManager.popBackStack(null, FragmentManager.POP_BACK_STACK_INCLUSIVE)
            parentFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, DashboardFragment())
                .commit()
        }

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
            val age: Int? = if (aboutYouPanel.visibility == View.VISIBLE) {
                val parsed = etAge.text.toString().trim().toIntOrNull()
                if (parsed == null || parsed < 1 || parsed > 120) {
                    Toast.makeText(context, getString(R.string.onboarding_valid_age), Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                parsed
            } else {
                null
            }

            val completed = documentKeys.filterIndexed { index, _ ->
                checkboxes[index].isChecked
            }

            btnSubmit.isEnabled = false
            btnSubmit.text = getString(R.string.saving)

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
                    btnSubmit.text = getString(R.string.action_continue)

                    if (response.isSuccessful) {
                        Toast.makeText(
                            context,
                            getString(R.string.onboarding_success),
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
                            getString(R.string.onboarding_save_failed, response.code().toString()),
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }

                override fun onFailure(call: Call<OnboardingResponse>, t: Throwable) {
                    btnSubmit.isEnabled = true
                    btnSubmit.text = getString(R.string.action_continue)
                    Toast.makeText(
                        context,
                        getString(R.string.onboarding_error, t.localizedMessage ?: ""),
                        Toast.LENGTH_LONG
                    ).show()
                }
            })
        }
    }
}
