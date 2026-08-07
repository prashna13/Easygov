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
import com.example.easygov.model.RegisterRequest
import com.example.easygov.model.TokenResponse
import com.example.easygov.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

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
        val etEmail = view.findViewById<EditText>(R.id.etEmail)
        val etPhone = view.findViewById<EditText>(R.id.etPhone)
        val etPassword = view.findViewById<EditText>(R.id.etPassword)
        val btnRegister = view.findViewById<Button>(R.id.btnRegister)
        val tvSignIn = view.findViewById<TextView>(R.id.tvSignIn)

        tvSignIn.setOnClickListener {
            parentFragmentManager.popBackStack()
        }

        btnRegister.setOnClickListener {
            val fullName = etFullName.text.toString().trim()
            val email = etEmail.text.toString().trim()
            val phone = etPhone.text.toString().trim()
            val password = etPassword.text.toString().trim()

            if (fullName.isNotEmpty() && email.isNotEmpty() && password.isNotEmpty()) {
                btnRegister.isEnabled = false
                btnRegister.text = "Creating account..."

                val registerRequest = RegisterRequest(
                    email = email,
                    password = password,
                    fullName = fullName,
                    phone = if (phone.isNotEmpty()) phone else null
                )

                RetrofitClient.apiService.registerUser(registerRequest).enqueue(object : Callback<TokenResponse> {
                    override fun onResponse(call: Call<TokenResponse>, response: Response<TokenResponse>) {
                        btnRegister.isEnabled = true
                        btnRegister.text = "Create Account"

                        if (response.isSuccessful && response.body() != null) {
                            val tokenResponse = response.body()!!
                            val sessionManager = SessionManager.getInstance(requireContext())
                            sessionManager.saveAuthToken("Bearer ${tokenResponse.accessToken}")
                            sessionManager.saveUser(tokenResponse.user.fullName, tokenResponse.user.email)

                            Toast.makeText(context, "Account created successfully!", Toast.LENGTH_SHORT).show()

                            parentFragmentManager.beginTransaction()
                                .replace(R.id.fragmentContainer, DashboardFragment())
                                .commit()
                        } else {
                            Toast.makeText(context, "Registration failed: ${response.code()}", Toast.LENGTH_LONG).show()
                        }
                    }

                    override fun onFailure(call: Call<TokenResponse>, t: Throwable) {
                        btnRegister.isEnabled = true
                        btnRegister.text = "Create Account"
                        Toast.makeText(context, "Error: ${t.localizedMessage}", Toast.LENGTH_LONG).show()
                    }
                })
            } else {
                Toast.makeText(context, "Please fill in all required fields", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
