package com.example.easygov

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.Office
import com.example.easygov.network.RetrofitClient
import com.google.android.material.button.MaterialButton
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * "Find Nearest Office" screen. Uses the device's coarse location once,
 * on demand (no continuous tracking), then calls
 * GET /api/v1/offices/nearby to list government offices serving the
 * current service, sorted nearest-first. Tapping Directions opens
 * turn-by-turn navigation in Google Maps.
 */
class NearbyOfficesFragment : Fragment() {

    private val radiusKm = 20.0

    private var serviceType = "citizenship"
    private var lastLocation: Location? = null
    private var currentAction = Action.LOAD

    private lateinit var officeAdapter: OfficeAdapter
    private lateinit var rvOffices: RecyclerView
    private lateinit var progress: View
    private lateinit var stateLayout: View
    private lateinit var tvOfficeMessage: TextView
    private lateinit var btnOfficeAction: MaterialButton
    private lateinit var tvNearbyFor: TextView
    private lateinit var tvOfficeRadiusHint: TextView

    private var locationManager: LocationManager? = null
    private var singleUpdateListener: LocationListener? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_nearby_offices, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        serviceType = arguments?.getString(ARG_SERVICE_TYPE) ?: "citizenship"
        val title = arguments?.getString(ARG_TITLE) ?: ""

        view.findViewById<View>(R.id.btnBackOffices).setOnClickListener {
            parentFragmentManager.popBackStack()
        }

        tvNearbyFor = view.findViewById(R.id.tvNearbyFor)
        tvNearbyFor.text = getString(R.string.office_nearby_for, title)

        tvOfficeRadiusHint = view.findViewById(R.id.tvOfficeRadiusHint)

        rvOffices = view.findViewById(R.id.rvOffices)
        officeAdapter = OfficeAdapter { office -> openDirections(office) }
        rvOffices.layoutManager = LinearLayoutManager(requireContext())
        rvOffices.adapter = officeAdapter

        progress = view.findViewById(R.id.officeProgress)
        stateLayout = view.findViewById(R.id.officeState)
        tvOfficeMessage = view.findViewById(R.id.tvOfficeMessage)
        btnOfficeAction = view.findViewById(R.id.btnOfficeAction)
        btnOfficeAction.setOnClickListener { onActionClick() }

        ensureLocationPermission()
    }

    override fun onDestroyView() {
        finishSingleUpdate()
        super.onDestroyView()
    }

    // ── PERMISSION ───────────────────────────────────────────────────────────

    private fun ensureLocationPermission() {
        if (hasLocationPermission()) {
            locateAndLoad()
        } else {
            showLoading()
            requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION), REQ_LOCATION)
        }
    }

    private fun hasLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQ_LOCATION) return

        if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            locateAndLoad()
        } else {
            val permanent = !shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_COARSE_LOCATION)
            showState(
                getString(R.string.office_permission_denied),
                if (permanent) getString(R.string.office_open_settings) else getString(R.string.office_grant_access),
                if (permanent) Action.OPEN_SETTINGS else Action.REQUEST_PERMISSION
            )
        }
    }

    // ── LOCATION ─────────────────────────────────────────────────────────────

    private fun locateAndLoad() {
        showLoading()
        val lm = requireContext().getSystemService(Context.LOCATION_SERVICE) as LocationManager
        locationManager = lm

        if (!lm.isProviderEnabled(LocationManager.GPS_PROVIDER) &&
            !lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        ) {
            showState(getString(R.string.office_location_unavailable), getString(R.string.office_retry), Action.LOCATE)
            return
        }

        if (!hasLocationPermission()) {
            showState(getString(R.string.office_permission_denied), getString(R.string.office_grant_access), Action.REQUEST_PERMISSION)
            return
        }

        val lastKnown = try {
            lm.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                ?: lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
        } catch (_: SecurityException) {
            null
        }

        if (lastKnown != null) {
            loadOffices(lastKnown)
            return
        }

        requestSingleFix(lm)
    }

    private fun requestSingleFix(lm: LocationManager) {
        singleUpdateListener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                finishSingleUpdate()
                loadOffices(location)
            }
        }

        mainHandler.postDelayed({
            finishSingleUpdate()
            showState(getString(R.string.office_location_unavailable), getString(R.string.office_retry), Action.LOCATE)
        }, LOCATION_TIMEOUT_MS)

        try {
            lm.requestSingleUpdate(LocationManager.GPS_PROVIDER, singleUpdateListener!!, Looper.getMainLooper())
            lm.requestSingleUpdate(LocationManager.NETWORK_PROVIDER, singleUpdateListener!!, Looper.getMainLooper())
        } catch (e: SecurityException) {
            finishSingleUpdate()
            showState(getString(R.string.office_permission_denied), getString(R.string.office_grant_access), Action.REQUEST_PERMISSION)
        }
    }

    private fun finishSingleUpdate() {
        mainHandler.removeCallbacksAndMessages(null)
        singleUpdateListener?.let { locationManager?.removeUpdates(it) }
        singleUpdateListener = null
    }

    // ── NETWORK ──────────────────────────────────────────────────────────────

    private fun loadOffices(location: Location) {
        lastLocation = location
        showLoading()

        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        RetrofitClient.apiService.getNearbyOffices(
            authToken, serviceType, location.latitude, location.longitude, radiusKm
        ).enqueue(object : Callback<List<Office>> {
            override fun onResponse(call: Call<List<Office>>, response: Response<List<Office>>) {
                val body = response.body()
                if (response.isSuccessful && body != null) {
                    if (body.isEmpty()) {
                        showState(
                            getString(R.string.office_empty, radiusKm.toInt()),
                            getString(R.string.office_retry),
                            Action.LOAD
                        )
                    } else {
                        bindOffices(body)
                    }
                } else {
                    showState(getString(R.string.office_error), getString(R.string.office_retry), Action.LOAD)
                }
            }

            override fun onFailure(call: Call<List<Office>>, t: Throwable) {
                showState(getString(R.string.office_error), getString(R.string.office_retry), Action.LOAD)
            }
        })
    }

    private fun bindOffices(offices: List<Office>) {
        progress.visibility = View.GONE
        stateLayout.visibility = View.GONE
        rvOffices.visibility = View.VISIBLE
        tvOfficeRadiusHint.text = getString(R.string.office_radius_hint, radiusKm.toInt())
        tvOfficeRadiusHint.visibility = View.VISIBLE
        officeAdapter.submitList(offices)
    }

    // ── UI STATES ────────────────────────────────────────────────────────────

    private fun showLoading() {
        rvOffices.visibility = View.GONE
        stateLayout.visibility = View.GONE
        progress.visibility = View.VISIBLE
    }

    private fun showState(message: String, actionText: String, action: Action) {
        finishSingleUpdate()
        progress.visibility = View.GONE
        rvOffices.visibility = View.GONE
        tvOfficeMessage.text = message
        btnOfficeAction.text = actionText
        btnOfficeAction.visibility = View.VISIBLE
        currentAction = action
        stateLayout.visibility = View.VISIBLE
    }

    private fun onActionClick() {
        when (currentAction) {
            Action.LOCATE -> locateAndLoad()
            Action.LOAD -> {
                val location = lastLocation
                if (location != null) loadOffices(location) else locateAndLoad()
            }
            Action.REQUEST_PERMISSION -> {
                requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION), REQ_LOCATION)
            }
            Action.OPEN_SETTINGS -> openAppSettings()
        }
    }

    private fun openAppSettings() {
        try {
            val intent = Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:${requireContext().packageName}")
            )
            startActivity(intent)
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(requireContext(), R.string.office_permission_denied, Toast.LENGTH_SHORT).show()
        }
    }

    // ── DIRECTIONS ───────────────────────────────────────────────────────────

    private fun openDirections(office: Office) {
        val q = "${office.latitude},${office.longitude}"
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("google.navigation:q=$q")))
        } catch (_: ActivityNotFoundException) {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("geo:$q?q=$q")))
            } catch (_: ActivityNotFoundException) {
                Toast.makeText(requireContext(), R.string.office_error, Toast.LENGTH_LONG).show()
            }
        }
    }

    companion object {
        private const val ARG_SERVICE_TYPE = "service_type"
        private const val ARG_TITLE = "service_title"
        private const val REQ_LOCATION = 101
        private const val LOCATION_TIMEOUT_MS = 15000L

        fun newInstance(serviceType: String, title: String): NearbyOfficesFragment {
            val fragment = NearbyOfficesFragment()
            val args = Bundle().apply {
                putString(ARG_SERVICE_TYPE, serviceType)
                putString(ARG_TITLE, title)
            }
            fragment.arguments = args
            return fragment
        }
    }

    private enum class Action { LOCATE, LOAD, REQUEST_PERMISSION, OPEN_SETTINGS }
}