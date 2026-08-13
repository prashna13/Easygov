package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.ApplicationProgress
import com.example.easygov.network.RetrofitClient
import com.google.android.material.progressindicator.LinearProgressIndicator
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * Shows a user's application progress: overall percentage, a status chip,
 * and a step-by-step checklist the user ticks off as they complete each step.
 */
class ApplicationProgressFragment : Fragment() {

    private lateinit var stepAdapter: ProgressStepAdapter
    private var applicationId: Int = -1
    private var isUpdating = false

    private lateinit var tvAppTitle: TextView
    private lateinit var tvAppSubtitle: TextView
    private lateinit var tvAppStatus: TextView
    private lateinit var tvProgressPercent: TextView
    private lateinit var progressBar: LinearProgressIndicator
    private lateinit var tvNextStepHint: TextView
    private lateinit var completedPanel: View
    private lateinit var rvSteps: RecyclerView
    private lateinit var errorLayout: View
    private lateinit var tvProgressError: TextView
    private lateinit var btnRetryProgress: View
    private lateinit var scrollContent: View

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_application_progress, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        applicationId = arguments?.getInt("application_id", -1) ?: -1
        val serviceTitle = arguments?.getString("service_title") ?: "Application"

        tvAppTitle = view.findViewById(R.id.tvAppTitle)
        tvAppSubtitle = view.findViewById(R.id.tvAppSubtitle)
        tvAppStatus = view.findViewById(R.id.tvAppStatus)
        tvProgressPercent = view.findViewById(R.id.tvProgressPercent)
        progressBar = view.findViewById(R.id.progressBar)
        tvNextStepHint = view.findViewById(R.id.tvNextStepHint)
        completedPanel = view.findViewById(R.id.completedPanel)
        rvSteps = view.findViewById(R.id.rvSteps)
        errorLayout = view.findViewById(R.id.errorLayout)
        tvProgressError = view.findViewById(R.id.tvProgressError)
        btnRetryProgress = view.findViewById(R.id.btnRetryProgress)
        scrollContent = view.findViewById(R.id.scrollContent)

        tvAppTitle.text = serviceTitle
        tvAppSubtitle.text = "Track your progress step by step"

        stepAdapter = ProgressStepAdapter { stepNumber -> completeStep(stepNumber) }
        rvSteps.layoutManager = LinearLayoutManager(requireContext())
        rvSteps.adapter = stepAdapter

        btnRetryProgress.setOnClickListener {
            errorLayout.visibility = View.GONE
            scrollContent.visibility = View.VISIBLE
            loadApplication()
        }

        loadApplication()
    }

    private fun loadApplication() {
        if (applicationId <= 0) {
            showError("Application not found.")
            return
        }
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) {
            showError("Please sign in to view your application.")
            return
        }

        RetrofitClient.apiService.getApplication(authToken, applicationId)
            .enqueue(object : Callback<ApplicationProgress> {
                override fun onResponse(
                    call: Call<ApplicationProgress>,
                    response: Response<ApplicationProgress>
                ) {
                    if (response.isSuccessful && response.body() != null) {
                        bindApplication(response.body()!!)
                    } else {
                        showError("Server Error: ${response.code()}")
                    }
                }

                override fun onFailure(call: Call<ApplicationProgress>, t: Throwable) {
                    showError("Network Failure: ${t.localizedMessage}")
                }
            })
    }

    private fun completeStep(stepNumber: Int) {
        if (isUpdating) return
        isUpdating = true

        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: return
        RetrofitClient.apiService.completeStep(authToken, applicationId, stepNumber)
            .enqueue(object : Callback<ApplicationProgress> {
                override fun onResponse(
                    call: Call<ApplicationProgress>,
                    response: Response<ApplicationProgress>
                ) {
                    isUpdating = false
                    if (response.isSuccessful && response.body() != null) {
                        bindApplication(response.body()!!)
                    } else {
                        showError("Server Error: ${response.code()}")
                    }
                }

                override fun onFailure(call: Call<ApplicationProgress>, t: Throwable) {
                    isUpdating = false
                    showError("Network Failure: ${t.localizedMessage}")
                }
            })
    }

    private fun bindApplication(app: ApplicationProgress) {
        errorLayout.visibility = View.GONE
        scrollContent.visibility = View.VISIBLE

        val isCompleted = app.status == "COMPLETED"
        tvAppStatus.text = app.status.replace("_", " ")
        tvProgressPercent.text = "${app.progressPercent}%"
        progressBar.progress = app.progressPercent

        if (isCompleted) {
            tvNextStepHint.text = "Every step is done — this application is complete."
            completedPanel.visibility = View.VISIBLE
        } else {
            completedPanel.visibility = View.GONE
        }

        stepAdapter.submitList(app.steps)
    }

    private fun showError(message: String) {
        scrollContent.visibility = View.GONE
        errorLayout.visibility = View.VISIBLE
        tvProgressError.text = message
    }

    companion object {
        fun newInstance(applicationId: Int, serviceTitle: String): ApplicationProgressFragment {
            val fragment = ApplicationProgressFragment()
            val args = Bundle().apply {
                putInt("application_id", applicationId)
                putString("service_title", serviceTitle)
            }
            fragment.arguments = args
            return fragment
        }
    }
}
