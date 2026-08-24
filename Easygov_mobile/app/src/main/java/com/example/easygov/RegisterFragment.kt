package com.example.easygov

import android.app.DatePickerDialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.example.easygov.model.RegisterRequest
import com.example.easygov.model.TokenResponse
import com.example.easygov.network.RetrofitClient
import org.json.JSONObject
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.util.Calendar
import java.util.Locale

class RegisterFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_register, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val etFullName = view.findViewById<EditText>(R.id.etFullName)
        val etDateOfBirth = view.findViewById<EditText>(R.id.etDateOfBirth)
        val tilDob = view.findViewById<com.google.android.material.textfield.TextInputLayout>(R.id.tilDob)
        val etEmail = view.findViewById<EditText>(R.id.etEmail)
        val etPhone = view.findViewById<EditText>(R.id.etPhone)
        val etPassword = view.findViewById<EditText>(R.id.etPassword)
        val btnRegister = view.findViewById<Button>(R.id.btnRegister)
        val tvSignIn = view.findViewById<TextView>(R.id.tvSignIn)
        val btnBackRegister = view.findViewById<View>(R.id.btnBackRegister)

        var selectedDob: Calendar? = null

        val openDatePicker = {
            val cal = Calendar.getInstance()
            selectedDob?.let { cal.timeInMillis = it.timeInMillis }
            val picker = DatePickerDialog(
                requireContext(),
                { _, year, month, dayOfMonth ->
                    val picked = Calendar.getInstance().apply { set(year, month, dayOfMonth) }
                    selectedDob = picked
                    etDateOfBirth.setText(String.format(Locale.US, "%04d-%02d-%02d", year, month + 1, dayOfMonth))
                    tilDob.error = null
                },
                cal.get(Calendar.YEAR),
                cal.get(Calendar.MONTH),
                cal.get(Calendar.DAY_OF_MONTH)
            )
            picker.datePicker.maxDate = System.currentTimeMillis()
            picker.show()
        }
        etDateOfBirth.setOnClickListener { openDatePicker() }
        etDateOfBirth.setOnFocusChangeListener { _, hasFocus -> if (hasFocus) openDatePicker() }

        val backToLogin = { parentFragmentManager.popBackStack() }
        tvSignIn.setOnClickListener { backToLogin() }
        btnBackRegister.setOnClickListener { backToLogin() }

        btnRegister.setOnClickListener {
            val fullName = etFullName.text.toString().trim()
            val email = etEmail.text.toString().trim()
            val phone = etPhone.text.toString().trim()
            val password = etPassword.text.toString().trim()

            if (fullName.isEmpty() || email.isEmpty() || password.isEmpty() || selectedDob == null) {
                Toast.makeText(context, getString(R.string.register_fill_fields), Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Client-side age gate (server enforces it too): official documents need 16+
            val today = Calendar.getInstance()
            var age = today.get(Calendar.YEAR) - selectedDob!!.get(Calendar.YEAR)
            if (today.get(Calendar.DAY_OF_YEAR) < selectedDob!!.get(Calendar.DAY_OF_YEAR)) age--
            if (age < 16) {
                tilDob.error = getString(R.string.error_minimum_age)
                Toast.makeText(context, getString(R.string.error_minimum_age), Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }

            btnRegister.isEnabled = false
            btnRegister.text = getString(R.string.creating_account)

            val dobIso = String.format(
                Locale.US, "%04d-%02d-%02d",
                selectedDob!!.get(Calendar.YEAR),
                selectedDob!!.get(Calendar.MONTH) + 1,
                selectedDob!!.get(Calendar.DAY_OF_MONTH)
            )

            val registerRequest = RegisterRequest(
                email = email,
                password = password,
                fullName = fullName,
                dateOfBirth = dobIso,
                phone = if (phone.isNotEmpty()) phone else null
            )

            RetrofitClient.apiService.registerUser(registerRequest).enqueue(object : Callback<TokenResponse> {
                override fun onResponse(call: Call<TokenResponse>, response: Response<TokenResponse>) {
                    btnRegister.isEnabled = true
                    btnRegister.text = getString(R.string.create_account)

                    if (response.isSuccessful && response.body() != null) {
                        val tokenResponse = response.body()!!
                        val sessionManager = SessionManager.getInstance(requireContext())
                        sessionManager.saveAuthToken("Bearer ${tokenResponse.accessToken}")
                        sessionManager.saveUser(tokenResponse.user.fullName, tokenResponse.user.email)

                        Toast.makeText(context, getString(R.string.register_success), Toast.LENGTH_SHORT).show()

                        parentFragmentManager.beginTransaction()
                            .replace(R.id.fragmentContainer, DashboardFragment())
                            .commit()
                    } else {
                        val detail = parseErrorDetail(response)
                        val message = detail ?: getString(R.string.register_failed_code, response.code().toString())
                        if (detail?.contains("age", ignoreCase = true) == true) tilDob.error = detail
                        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<TokenResponse>, t: Throwable) {
                    btnRegister.isEnabled = true
                    btnRegister.text = getString(R.string.create_account)
                    Toast.makeText(
                        context,
                        getString(R.string.register_error, t.localizedMessage ?: ""),
                        Toast.LENGTH_LONG
                    ).show()
                }
            })
        }
    }

    private fun parseErrorDetail(response: Response<TokenResponse>): String? = try {
        val body = response.errorBody()?.string()
        if (body != null) {
            val json = JSONObject(body)
            val detail = json.opt("detail")
            when (detail) {
                is String -> detail
                else -> null
            }
        } else null
    } catch (_: Exception) {
        null
    }
}
