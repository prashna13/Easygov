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
import com.example.easygov.model.UserOut
import com.example.easygov.network.RetrofitClient
import com.google.android.material.button.MaterialButtonToggleGroup
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * Shows the signed-in user's full profile (fetched live from /auth/me) plus
 * a "My Applications & Progress" list fetched from /api/v1/applications.
 * Tapping an application opens its step-level progress tracker.
 */
class ProfileFragment : Fragment() {

    private lateinit var applicationsAdapter: ApplicationsAdapter

    private lateinit var scrollContent: View
    private lateinit var errorLayout: View
    private lateinit var tvProfileError: TextView

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_profile, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        scrollContent = view.findViewById(R.id.scrollContent)
        errorLayout = view.findViewById(R.id.errorLayout)
        tvProfileError = view.findViewById(R.id.tvProfileError)

        val sessionManager = SessionManager.getInstance(requireContext())

        val rvApplications = view.findViewById<RecyclerView>(R.id.rvApplications)
        applicationsAdapter = ApplicationsAdapter { app -> openApplicationProgress(app) }
        rvApplications.layoutManager = LinearLayoutManager(requireContext())
        rvApplications.adapter = applicationsAdapter

        view.findViewById<View>(R.id.btnLogout).setOnClickListener {
            sessionManager.clearSession()
            parentFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, LoginFragment())
                .commit()
        }

        view.findViewById<View>(R.id.btnRetryProfile).setOnClickListener {
            errorLayout.visibility = View.GONE
            scrollContent.visibility = View.VISIBLE
            loadProfile()
        }

        setupLanguageSelector(view)

        loadProfile()
        loadApplications()
    }

    /**
     * Wires the English/नेपाली toggle. Applies the chosen locale app-wide via
     * AppCompatDelegate (which recreates the activity) and persists the choice.
     */
    private fun setupLanguageSelector(view: View) {
        val localeManager = LocaleManager.getInstance(requireContext())
        val langGroup = view.findViewById<MaterialButtonToggleGroup>(R.id.langGroup)
        langGroup.check(if (localeManager.getLanguage() == "ne") R.id.btnLangNe else R.id.btnLangEn)
        langGroup.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (!isChecked) return@addOnButtonCheckedListener
            val lang = if (checkedId == R.id.btnLangNe) "ne" else "en"
            if (lang != localeManager.getLanguage()) {
                localeManager.setLanguage(lang)
            }
        }
    }

    private fun loadProfile() {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) {
            showError(getString(R.string.sign_in_for_profile))
            return
        }

        RetrofitClient.apiService.getProfile(authToken)
            .enqueue(object : Callback<UserOut> {
                override fun onResponse(call: Call<UserOut>, response: Response<UserOut>) {
                    if (response.isSuccessful && response.body() != null) {
                        bindProfile(response.body()!!)
                    } else {
                        showError(getString(R.string.server_error, response.code().toString()))
                    }
                }

                override fun onFailure(call: Call<UserOut>, t: Throwable) {
                    showError(getString(R.string.network_failure, t.localizedMessage ?: ""))
                }
            })
    }

    private fun loadApplications() {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) return

        RetrofitClient.apiService.getApplications(authToken)
            .enqueue(object : Callback<List<ApplicationProgress>> {
                override fun onResponse(
                    call: Call<List<ApplicationProgress>>,
                    response: Response<List<ApplicationProgress>>
                ) {
                    if (response.isSuccessful && response.body() != null) {
                        bindApplications(response.body()!!)
                    }
                }

                override fun onFailure(call: Call<List<ApplicationProgress>>, t: Throwable) {
                    // Keep profile visible; the progress section simply stays empty.
                }
            })
    }

    private fun bindProfile(user: UserOut) {
        errorLayout.visibility = View.GONE
        scrollContent.visibility = View.VISIBLE

        view?.findViewById<TextView>(R.id.tvProfileName)?.text = user.fullName
        view?.findViewById<TextView>(R.id.tvProfileEmail)?.text = user.email

        setRow(R.id.rowCitizenship, R.id.tvCitizenshipNumber, user.citizenshipNumber)
        setRow(R.id.rowPhone, R.id.tvPhone, user.phone)
        setRow(R.id.rowProvince, R.id.tvProvince, user.province)
        setRow(R.id.rowDob, R.id.tvDob, user.dateOfBirth)
        setRow(R.id.rowAddress, R.id.tvAddress, user.address)
        setRow(R.id.rowAge, R.id.tvAge, user.age?.toString())
    }

    private fun setRow(rowId: Int, textId: Int, value: String?) {
        val view = view ?: return
        val row = view.findViewById<View>(rowId)
        val tv = view.findViewById<TextView>(textId)
        if (value.isNullOrBlank()) {
            row.visibility = View.GONE
        } else {
            tv.text = value
            row.visibility = View.VISIBLE
        }
    }

    private fun bindApplications(applications: List<ApplicationProgress>) {
        val emptyText = view?.findViewById<TextView>(R.id.tvProgressEmpty)
        if (applications.isEmpty()) {
            emptyText?.visibility = View.VISIBLE
        } else {
            emptyText?.visibility = View.GONE
        }
        applicationsAdapter.submitList(applications)
    }

    private fun openApplicationProgress(app: ApplicationProgress) {
        val fragment = ApplicationProgressFragment.newInstance(app.applicationId, app.serviceTitle)
        parentFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .addToBackStack(null)
            .commit()
    }

    private fun showError(message: String) {
        scrollContent.visibility = View.GONE
        errorLayout.visibility = View.VISIBLE
        tvProfileError.text = message
    }
}
