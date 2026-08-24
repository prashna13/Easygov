package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.example.easygov.model.ApplicationProgress
import com.example.easygov.model.ServiceDetailResponse
import com.example.easygov.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * Shows full detail for a single government service, including the official
 * guide (prerequisites, documents, procedure, fees, processing time, links).
 *
 * When the user is signed in, the backend also reports whether the service's
 * prerequisites are satisfied. Blocked services only allow informational
 * (read-only) viewing until the user completes the required documents.
 */
class ServiceDetailFragment : Fragment() {

    private var readOnlyMode = false
    private var applicationId: Int? = null
    private var isApplying = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_service_detail, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val serviceId = arguments?.getInt("service_id", -1) ?: -1
        val title = arguments?.getString("service_title") ?: "Service Details"
        val category = arguments?.getString("service_category") ?: "General"
        val description = arguments?.getString("service_description")
        val guidance = arguments?.getString("service_guidance")

        view.findViewById<TextView>(R.id.tvDetailTitle).text = title
        view.findViewById<TextView>(R.id.tvDetailCategory).text = category
        if (!description.isNullOrEmpty()) {
            view.findViewById<TextView>(R.id.tvDetailDescription).text = description
        }
        showGuidance(view, guidance)

        val prereqBlockPanel = view.findViewById<View>(R.id.prereqBlockPanel)
        val tvMissingPrereqs = view.findViewById<TextView>(R.id.tvMissingPrereqs)
        val infoNoteLayout = view.findViewById<View>(R.id.infoNoteLayout)
        val btnViewInfo = view.findViewById<View>(R.id.btnViewInfo)
        val btnApplyNow = view.findViewById<TextView>(R.id.btnApplyNow)

        btnViewInfo.setOnClickListener {
            readOnlyMode = true
            prereqBlockPanel.visibility = View.GONE
            infoNoteLayout.visibility = View.VISIBLE
        }

        btnApplyNow.setOnClickListener {
            if (applicationId != null) {
                openApplicationProgress(applicationId!!)
            } else {
                startApplication(serviceId)
            }
        }

        view.findViewById<View>(R.id.btnBackDetail).setOnClickListener {
            parentFragmentManager.popBackStack()
        }

        view.findViewById<View>(R.id.btnFindNearestOffice).setOnClickListener {
            openNearbyOffices(title)
        }

        if (serviceId > 0) {
            val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
            if (authToken != null) {
                RetrofitClient.apiService.getServiceDetail(authToken, serviceId)
                    .enqueue(object : Callback<ServiceDetailResponse> {
                        override fun onResponse(
                            call: Call<ServiceDetailResponse>,
                            response: Response<ServiceDetailResponse>
                        ) {
                            if (response.isSuccessful && response.body() != null) {
                                val detail = response.body()!!
                                // Refresh header from the (localized) API detail —
                                // used when deep-linking from the chat guide chip.
                                detail.service?.let { svc ->
                                    view.findViewById<TextView>(R.id.tvDetailTitle).text = svc.title
                                    view.findViewById<TextView>(R.id.tvDetailCategory).text = svc.category
                                }
                                showGuidance(view, detail.service?.guidance ?: guidance)
                                applyPrerequisiteState(
                                    detail,
                                    prereqBlockPanel,
                                    tvMissingPrereqs,
                                    infoNoteLayout,
                                    btnApplyNow
                                )
                            }
                        }

                        override fun onFailure(call: Call<ServiceDetailResponse>, t: Throwable) {
                            // Keep static content; blocking info simply won't load.
                        }
                    })
            }
        }
    }

    private fun showGuidance(view: View, guidance: String?) {
        val guidancePanel = view.findViewById<View>(R.id.guidancePanel)
        val tvDetailGuidance = view.findViewById<TextView>(R.id.tvDetailGuidance)
        if (!guidance.isNullOrBlank()) {
            tvDetailGuidance.text = guidance
            guidancePanel.visibility = View.VISIBLE
        }
    }

    private fun startApplication(serviceId: Int) {
        if (isApplying || serviceId <= 0) return
        isApplying = true

        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) {
            isApplying = false
            Toast.makeText(requireContext(), getString(R.string.start_app_sign_in), Toast.LENGTH_SHORT).show()
            return
        }

        RetrofitClient.apiService.startApplication(authToken, serviceId)
            .enqueue(object : Callback<ApplicationProgress> {
                override fun onResponse(
                    call: Call<ApplicationProgress>,
                    response: Response<ApplicationProgress>
                ) {
                    isApplying = false
                    if (response.isSuccessful && response.body() != null) {
                        openApplicationProgress(response.body()!!.applicationId)
                    } else {
                        val msg = try {
                            response.errorBody()?.string()
                        } catch (e: Exception) {
                            null
                        }
                        Toast.makeText(
                            requireContext(),
                            msg ?: getString(R.string.start_app_failed, response.code().toString()),
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }

                override fun onFailure(call: Call<ApplicationProgress>, t: Throwable) {
                    isApplying = false
                    Toast.makeText(
                        requireContext(),
                        getString(R.string.start_app_network, t.localizedMessage ?: ""),
                        Toast.LENGTH_LONG
                    ).show()
                }
            })
    }

    private fun openApplicationProgress(applicationId: Int) {
        val title = arguments?.getString("service_title") ?: "Application"
        val fragment = ApplicationProgressFragment.newInstance(applicationId, title)
        parentFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .addToBackStack(null)
            .commit()
    }

    private fun openNearbyOffices(title: String) {
        val fragment = NearbyOfficesFragment.newInstance(nearbyServiceType(title), title)
        // In the real app the host has R.id.fragmentContainer; in fragment-testing
        // the host only exposes android.R.id.content.
        val containerId =
            if (requireActivity().findViewById<View>(R.id.fragmentContainer) != null) R.id.fragmentContainer
            else android.R.id.content
        parentFragmentManager.beginTransaction()
            .replace(containerId, fragment)
            .addToBackStack(null)
            .commit()
    }

    private fun nearbyServiceType(title: String): String = when {
        title.contains("Passport", ignoreCase = true) -> "passport"
        title.contains("NID", ignoreCase = true) -> "nid"
        title.contains("Driving", ignoreCase = true) || title.contains("License", ignoreCase = true) -> "driving_license"
        else -> "citizenship"
    }

    private fun applyPrerequisiteState(
        detail: ServiceDetailResponse,
        prereqBlockPanel: View,
        tvMissingPrereqs: TextView,
        infoNoteLayout: View,
        btnApplyNow: TextView
    ) {
        if (readOnlyMode) {
            infoNoteLayout.visibility = View.VISIBLE
            return
        }

        detail.application?.let { app ->
            if (app.status != "COMPLETED") {
                applicationId = app.applicationId
                btnApplyNow.text = getString(R.string.view_my_application)
            }
        }

        if (detail.prerequisitesMet) {
            prereqBlockPanel.visibility = View.GONE
            btnApplyNow.isEnabled = true
            return
        }

        val missing = detail.missingPrerequisites
        tvMissingPrereqs.text = if (missing.isEmpty()) {
            "This service becomes available after completing its required documents."
        } else {
            "This service is blocked until you complete:\n\n• ${missing.joinToString("\n• ")}\n\nYou can still read its information below."
        }
        prereqBlockPanel.visibility = View.VISIBLE
        btnApplyNow.isEnabled = false
    }

    companion object {
        fun newInstance(
            serviceId: Int,
            title: String,
            category: String,
            description: String? = null,
            guidance: String? = null
        ): ServiceDetailFragment {
            val fragment = ServiceDetailFragment()
            val args = Bundle().apply {
                putInt("service_id", serviceId)
                putString("service_title", title)
                putString("service_category", category)
                putString("service_description", description)
                putString("service_guidance", guidance)
            }
            fragment.arguments = args
            return fragment
        }
    }
}
