package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.example.easygov.model.DashboardResponse
import com.example.easygov.model.GovService
import com.example.easygov.network.RetrofitClient
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
    private lateinit var btnRetry: Button

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_dashboard, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Initialize Views
        swipeRefresh = view.findViewById(R.id.swipeRefresh)
        mainContent = view.findViewById(R.id.mainContent)
        errorLayout = view.findViewById(R.id.errorLayout)
        tvErrorMessage = view.findViewById(R.id.tvErrorMessage)
        btnRetry = view.findViewById(R.id.btnRetry)

        val rvDashboard = view.findViewById<RecyclerView>(R.id.rvDashboard)
        val rvRecommendations = view.findViewById<RecyclerView>(R.id.rvRecommendations)

        // Setup RecyclerViews
        rvDashboard.layoutManager = GridLayoutManager(requireContext(), 2)
        rvRecommendations.layoutManager = GridLayoutManager(requireContext(), 2)

        standardAdapter = DashboardAdapter { service -> navigateToDetail(service) }
        recommendedAdapter = DashboardAdapter { service -> navigateToDetail(service) }

        rvDashboard.adapter = standardAdapter
        rvRecommendations.adapter = recommendedAdapter

        // Setup Refresh Logic
        swipeRefresh.setOnRefreshListener {
            fetchDashboardData()
        }

        btnRetry.setOnClickListener {
            showLoading()
            fetchDashboardData()
        }

        // Initial Fetch
        fetchDashboardData()
    }

    /**
     * Fetches dashboard data from the FastAPI backend using saved auth token.
     */
    private fun fetchDashboardData() {
        swipeRefresh.isRefreshing = true

        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: ""
        RetrofitClient.apiService.getDashboardData(authToken).enqueue(object : Callback<DashboardResponse> {
            override fun onResponse(call: Call<DashboardResponse>, response: Response<DashboardResponse>) {
                swipeRefresh.isRefreshing = false
                if (response.isSuccessful && response.body() != null) {
                    showContent()
                    val data = response.body()!!
                    standardAdapter.submitList(data.services)
                    recommendedAdapter.submitList(data.recommendations)

                    val tvDashboardTitle = view?.findViewById<TextView>(R.id.tvDashboardTitle)
                    tvDashboardTitle?.text = "Welcome, ${data.userName} • Personalized services & guides"
                } else {
                    showError("Server Error: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<DashboardResponse>, t: Throwable) {
                swipeRefresh.isRefreshing = false
                showError("Network Failure: ${t.localizedMessage}")
            }
        })
    }

    private fun navigateToDetail(service: GovService) {
        val detailFragment = ServiceDetailFragment.newInstance(
            service.title,
            service.category,
            service.description
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
}
