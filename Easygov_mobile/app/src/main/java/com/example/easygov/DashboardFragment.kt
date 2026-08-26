package com.example.easygov

import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.example.easygov.model.ApplicationProgress
import com.example.easygov.model.DashboardResponse
import com.example.easygov.model.GovService
import com.example.easygov.model.ServiceItem
import com.example.easygov.model.UserDocument
import com.example.easygov.network.RetrofitClient
import com.google.android.material.button.MaterialButton
import com.google.android.material.chip.Chip
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.progressindicator.LinearProgressIndicator
import okhttp3.MediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class DashboardFragment : Fragment() {

    private lateinit var standardAdapter: DashboardAdapter
    private lateinit var recommendedAdapter: DashboardAdapter

    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var mainContent: View
    private lateinit var errorLayout: View
    private lateinit var tvErrorMessage: TextView
    private lateinit var btnRetry: MaterialButton

    private lateinit var llForYouSection: View
    private lateinit var llAllServicesSection: View

    private lateinit var nextStepBanner: View
    private lateinit var tvNextStepTitle: TextView
    private lateinit var ivHeroIcon: android.widget.ImageView
    private lateinit var piHeroProgress: LinearProgressIndicator
    private lateinit var tvHeroProgress: TextView
    private lateinit var btnHeroAction: MaterialButton

    private lateinit var chipPriority: Chip
    private lateinit var chipServices: Chip

    private lateinit var uploadBanner: View
    private lateinit var tvUploadBannerMsg: TextView
    private lateinit var btnUploadBanner: MaterialButton
    private lateinit var btnDismissBanner: View

    private lateinit var etSearch: EditText
    private lateinit var tvName: TextView

    private var allServices: List<ServiceItem> = emptyList()
    private var priorityServices: List<ServiceItem> = emptyList()

    private var heroService: ServiceItem? = null
    private var bannerAppId: Int = -1
    private var bannerServiceTitle: String = ""

    private val pickDocument =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            if (uri != null) showLabelDialog(uri)
        }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_dashboard, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        swipeRefresh = view.findViewById(R.id.swipeRefresh)
        mainContent = view.findViewById(R.id.mainContent)
        errorLayout = view.findViewById(R.id.errorLayout)
        tvErrorMessage = view.findViewById(R.id.tvErrorMessage)
        btnRetry = view.findViewById(R.id.btnRetry)

        llForYouSection = view.findViewById(R.id.llForYouSection)
        llAllServicesSection = view.findViewById(R.id.llAllServicesSection)

        nextStepBanner = view.findViewById(R.id.nextStepBanner)
        tvNextStepTitle = view.findViewById(R.id.tvNextStepTitle)
        ivHeroIcon = view.findViewById(R.id.ivHeroIcon)
        piHeroProgress = view.findViewById(R.id.piHeroProgress)
        tvHeroProgress = view.findViewById(R.id.tvHeroProgress)
        btnHeroAction = view.findViewById(R.id.btnHeroAction)

        chipPriority = view.findViewById(R.id.chipPriority)
        chipServices = view.findViewById(R.id.chipServices)
        uploadBanner = view.findViewById(R.id.uploadBanner)
        tvUploadBannerMsg = view.findViewById(R.id.tvUploadBannerMsg)
        btnUploadBanner = view.findViewById(R.id.btnUploadBanner)
        btnDismissBanner = view.findViewById(R.id.btnDismissBanner)
        etSearch = view.findViewById(R.id.etSearch)
        tvName = view.findViewById(R.id.tvDashboardTitle)

        val rvDashboard = view.findViewById<RecyclerView>(R.id.rvDashboard)
        val rvRecommendations = view.findViewById<RecyclerView>(R.id.rvRecommendations)

        rvDashboard.layoutManager = GridLayoutManager(requireContext(), 2)
        rvRecommendations.layoutManager = GridLayoutManager(requireContext(), 2)

        standardAdapter = DashboardAdapter(::navigateToDetail)
        recommendedAdapter = DashboardAdapter(::navigateToDetail)

        rvDashboard.adapter = standardAdapter
        rvRecommendations.adapter = recommendedAdapter

        btnHeroAction.setOnClickListener { heroService?.let(::navigateToDetail) }
        nextStepBanner.setOnClickListener { heroService?.let(::navigateToDetail) }

        btnUploadBanner.setOnClickListener { pickDocument.launch("*/*") }
        btnDismissBanner.setOnClickListener {
            dismissApp(bannerAppId)
            uploadBanner.visibility = View.GONE
        }

        chipPriority.setOnCheckedChangeListener { _, checked ->
            llForYouSection.visibility = if (checked) View.VISIBLE else View.GONE
        }
        chipServices.setOnCheckedChangeListener { _, checked ->
            llAllServicesSection.visibility = if (checked) View.VISIBLE else View.GONE
        }

        etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                applySearchFilter(s?.toString().orEmpty())
            }
        })

        swipeRefresh.setOnRefreshListener { fetchDashboardData() }
        btnRetry.setOnClickListener {
            showLoading()
            fetchDashboardData()
        }

        fetchDashboardData()
    }

    private fun fetchDashboardData() {
        swipeRefresh.isRefreshing = true

        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: ""
        RetrofitClient.apiService.getDashboardData(authToken)
            .enqueue(object : Callback<DashboardResponse> {
                override fun onResponse(call: Call<DashboardResponse>, response: Response<DashboardResponse>) {
                    if (response.isSuccessful && response.body() != null) {
                        fetchApplications { apps -> bindDashboard(response.body()!!, apps) }
                    } else {
                        swipeRefresh.isRefreshing = false
                        val msg = if (response.code() == 401) getString(R.string.sign_in_required)
                            else getString(R.string.server_error, response.code().toString())
                        showError(msg)
                    }
                }

                override fun onFailure(call: Call<DashboardResponse>, t: Throwable) {
                    swipeRefresh.isRefreshing = false
                    showError(getString(R.string.network_failure, t.localizedMessage ?: ""))
                }
            })
    }

    private fun fetchApplications(onDone: (List<ApplicationProgress>) -> Unit) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: run {
            onDone(emptyList()); return
        }
        RetrofitClient.apiService.getApplications(authToken).enqueue(object : Callback<List<ApplicationProgress>> {
            override fun onResponse(call: Call<List<ApplicationProgress>>, response: Response<List<ApplicationProgress>>) {
                onDone(response.body() ?: emptyList())
            }

            override fun onFailure(call: Call<List<ApplicationProgress>>, t: Throwable) {
                onDone(emptyList())
            }
        })
    }

    private fun bindDashboard(data: DashboardResponse, applications: List<ApplicationProgress>) {
        swipeRefresh.isRefreshing = false
        if (data.needsOnboarding) {
            showContent()
            parentFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, OnboardingFragment())
                .addToBackStack(null)
                .commit()
            return
        }

        showContent()

        val recommendedIds = data.recommendations.map { it.id }.toSet()
        priorityServices = data.recommendations.map { toServiceItem(it, isPriority = true, applications) }
        allServices = data.services.map { toServiceItem(it, isPriority = it.id in recommendedIds, applications) }

        tvName.text = data.userName

        // Counts on the filter chips.
        chipPriority.setText(getString(R.string.dash_priority_count_live, priorityServices.size))
        chipServices.setText(getString(R.string.dash_service_count_live, allServices.size))

        bindHero(data.recommendedNextStep ?: data.recommendations.firstOrNull(), applications)

        bindUploadBanner(applications)

        applySearchFilter(etSearch.text?.toString().orEmpty())
    }

    private fun bindUploadBanner(applications: List<ApplicationProgress>) {
        val dismissed = dismissedAppIds()
        val completed = applications.firstOrNull {
            it.status == "COMPLETED" && it.applicationId != -1 && it.applicationId !in dismissed
        }
        if (completed == null) {
            uploadBanner.visibility = View.GONE
            bannerAppId = -1
            return
        }
        bannerAppId = completed.applicationId
        bannerServiceTitle = completed.serviceTitle
        tvUploadBannerMsg.text = getString(R.string.dash_upload_banner_msg, completed.serviceTitle)
        uploadBanner.visibility = View.VISIBLE
    }

    private fun toServiceItem(gs: GovService, isPriority: Boolean, applications: List<ApplicationProgress>): ServiceItem {
        val app = applications.firstOrNull { it.serviceId == gs.id }
        val completed = app?.steps?.count { it.status == "COMPLETED" } ?: 0
        val total = app?.steps?.size ?: DEFAULT_TOTAL_STEPS
        return ServiceItem(
            id = gs.id,
            title = gs.title,
            category = gs.category,
            iconRes = iconFor(gs.id),
            completedSteps = completed,
            totalSteps = total,
            isPriority = isPriority
        )
    }

    private fun iconFor(id: Int): Int = when (id) {
        1 -> R.drawable.ic_doc_image          // Citizenship
        2 -> R.drawable.ic_id_card            // NID
        3 -> R.drawable.ic_passport           // E-Passport
        7 -> R.drawable.ic_service            // Driving License
        else -> R.drawable.ic_service
    }

    private fun bindHero(nextStep: GovService?, applications: List<ApplicationProgress>) {
        if (nextStep == null) {
            nextStepBanner.visibility = View.GONE
            heroService = null
            return
        }
        heroService = toServiceItem(nextStep, isPriority = true, applications)
        tvNextStepTitle.text = nextStep.title
        ivHeroIcon.setImageResource(heroService!!.iconRes)
        ivHeroIcon.setColorFilter(androidx.core.content.ContextCompat.getColor(requireContext(), R.color.brand_light))
        piHeroProgress.progress = heroService!!.progressPercent
        tvHeroProgress.text = progressLabel(heroService!!)
        nextStepBanner.visibility = View.VISIBLE
    }

    private fun progressLabel(item: ServiceItem): String = if (item.isCompleted) {
        getString(R.string.dash_progress_completed)
    } else {
        getString(R.string.dash_progress_fraction, item.completedSteps, item.totalSteps)
    }

    private fun applySearchFilter(query: String) {
        if (query.isBlank()) {
            standardAdapter.submitList(allServices)
        } else {
            val q = query.trim()
            standardAdapter.submitList(allServices.filter {
                it.title.contains(q, ignoreCase = true) || it.category.contains(q, ignoreCase = true)
            })
        }
        recommendedAdapter.submitList(priorityServices)
    }

    private fun navigateToDetail(service: ServiceItem) {
        val detailFragment = ServiceDetailFragment.newInstance(
            service.id,
            service.title,
            service.category
        )
        parentFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, detailFragment)
            .addToBackStack(null)
            .commit()
    }

    private fun showContent() {
        mainContent.visibility = View.VISIBLE
        errorLayout.visibility = View.GONE
    }

    private fun showError(message: String) {
        mainContent.visibility = View.GONE
        errorLayout.visibility = View.VISIBLE
        tvErrorMessage.text = message
    }

    private fun showLoading() {
        mainContent.visibility = View.GONE
        errorLayout.visibility = View.GONE
        swipeRefresh.isRefreshing = true
    }

    // ── Upload banner (save a newly completed service's document) ─────────────

    private val bannerPrefs by lazy {
        requireContext().getSharedPreferences("easygov_banner_prefs", Context.MODE_PRIVATE)
    }

    private fun dismissedAppIds(): Set<Int> =
        bannerPrefs.getString("dismissed_app_ids", "")
            ?.split(",")
            ?.mapNotNull { it.toIntOrNull() }
            ?.toSet()
            ?: emptySet()

    private fun dismissApp(appId: Int) {
        if (appId <= 0) return
        val set = dismissedAppIds().toMutableSet()
        set.add(appId)
        bannerPrefs.edit().putString("dismissed_app_ids", set.joinToString(",")).apply()
    }

    private fun showLabelDialog(uri: Uri) {
        val input = EditText(requireContext()).apply {
            hint = getString(R.string.doc_pick_label)
            setText(bannerServiceTitle)
        }
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.doc_upload)
            .setView(input)
            .setNegativeButton(R.string.doc_cancel, null)
            .setPositiveButton(R.string.doc_upload_btn) { _, _ ->
                val label = input.text.toString().trim()
                if (label.isEmpty()) {
                    Toast.makeText(requireContext(), getString(R.string.doc_pick_label), Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                uploadDocument(uri, label)
            }
            .show()
    }

    private fun uploadDocument(uri: Uri, label: String) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: return
        val resolver = requireContext().contentResolver
        val filename = resolveFilename(uri)
        val mime = resolver.getType(uri) ?: guessMimeFromFilename(filename)
        val bytes = resolver.openInputStream(uri)?.readBytes() ?: return

        Toast.makeText(requireContext(), getString(R.string.doc_uploading), Toast.LENGTH_SHORT).show()

        val fileBody = RequestBody.create(MediaType.parse(mime) ?: MediaType.parse("application/octet-stream"), bytes)
        val filePart = MultipartBody.Part.createFormData("file", filename, fileBody)
        val labelBody = RequestBody.create(MediaType.parse("text/plain"), label)
        val tagsBody = RequestBody.create(MediaType.parse("text/plain"), bannerServiceTitle.lowercase())
        val descriptionBody = RequestBody.create(
            MediaType.parse("text/plain"),
            "Uploaded after completing $bannerServiceTitle"
        )

        RetrofitClient.apiService.uploadDocument(authToken, labelBody, tagsBody, descriptionBody, filePart)
            .enqueue(object : Callback<UserDocument> {
                override fun onResponse(call: Call<UserDocument>, response: Response<UserDocument>) {
                    if (response.isSuccessful && response.body() != null) {
                        Toast.makeText(requireContext(), getString(R.string.doc_uploaded_vault), Toast.LENGTH_SHORT).show()
                        dismissApp(bannerAppId)
                        uploadBanner.visibility = View.GONE
                    } else {
                        Toast.makeText(requireContext(), getString(R.string.doc_upload_fail), Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<UserDocument>, t: Throwable) {
                    Toast.makeText(requireContext(), getString(R.string.doc_upload_fail), Toast.LENGTH_LONG).show()
                }
            })
    }

    private fun resolveFilename(uri: Uri): String {
        requireContext().contentResolver.query(
            uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val name = cursor.getString(0)
                if (!name.isNullOrBlank()) return name
            }
        }
        return uri.lastPathSegment ?: "document"
    }

    private fun guessMimeFromFilename(filename: String): String = when {
        filename.endsWith(".pdf", ignoreCase = true) -> "application/pdf"
        filename.endsWith(".png", ignoreCase = true) -> "image/png"
        filename.endsWith(".webp", ignoreCase = true) -> "image/webp"
        filename.endsWith(".heic", ignoreCase = true) -> "image/heic"
        else -> "image/jpeg"
    }

    companion object {
        const val DEFAULT_TOTAL_STEPS = 5
    }
}