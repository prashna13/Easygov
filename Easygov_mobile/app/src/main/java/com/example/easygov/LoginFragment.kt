package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.example.easygov.model.LoginRequest
import com.example.easygov.model.TokenResponse
import com.example.easygov.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_login, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        val etEmail = view.findViewById<EditText>(R.id.etEmail)
        val etPassword = view.findViewById<EditText>(R.id.etPassword)
        val btnLogin = view.findViewById<Button>(R.id.btnLogin)
        val tvSignUp = view.findViewById<TextView>(R.id.tvSignUp)

        tvSignUp.setOnClickListener {
            parentFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, RegisterFragment())
                .addToBackStack(null)
                .commit()
        }

        // Check if user is already logged in
        val sessionManager = SessionManager.getInstance(requireContext())
        val existingToken = sessionManager.fetchAuthToken()
        if (existingToken != null) {
            Toast.makeText(context, "Session Active", Toast.LENGTH_SHORT).show()
        }

        btnLogin.setOnClickListener {
            val email = etEmail.text.toString().trim()
            val password = etPassword.text.toString().trim()
            
            if (email.isNotEmpty() && password.isNotEmpty()) {
                btnLogin.isEnabled = false
                btnLogin.text = getString(R.string.signing_in)
                
                val loginRequest = LoginRequest(email = email, password = password)
                RetrofitClient.apiService.loginUser(loginRequest).enqueue(object : Callback<TokenResponse> {
                    override fun onResponse(call: Call<TokenResponse>, response: Response<TokenResponse>) {
                        btnLogin.isEnabled = true
                        btnLogin.text = getString(R.string.login)

                        if (response.isSuccessful && response.body() != null) {
                            val tokenResponse = response.body()!!
                            val jwtToken = tokenResponse.accessToken
                            val user = tokenResponse.user

                            // Save token and user info securely
                            sessionManager.saveAuthToken("Bearer $jwtToken")
                            sessionManager.saveUser(user.fullName, user.email)

                            Toast.makeText(
                                context,
                                "Welcome back, ${user.fullName}!",
                                Toast.LENGTH_LONG
                            ).show()

                            // Navigate to Dashboard
                            parentFragmentManager.beginTransaction()
                                .replace(R.id.fragmentContainer, DashboardFragment())
                                .commit()
                        } else {
                            val errorMsg = when (response.code()) {
                                401 -> "Invalid email or password"
                                403 -> "Account is deactivated"
                                else -> "Login failed (${response.code()})"
                            }
                            Toast.makeText(context, errorMsg, Toast.LENGTH_LONG).show()
                        }
                    }

                    override fun onFailure(call: Call<TokenResponse>, t: Throwable) {
                        btnLogin.isEnabled = true
                        btnLogin.text = getString(R.string.login)
                        Toast.makeText(
                            context,
                            "Network Error: ${t.localizedMessage}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                })
            } else {
                Toast.makeText(context, "Please enter both email and password", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
