package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import com.example.easygov.model.GoogleLoginRequest
import com.example.easygov.model.LoginRequest
import com.example.easygov.model.TokenResponse
import com.example.easygov.network.RetrofitClient
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginFragment : Fragment() {

    private lateinit var sessionManager: SessionManager
    private lateinit var googleSignInClient: GoogleSignInClient

    private val googleSignInLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val task = GoogleSignIn.getSignedInAccountFromIntent(result.data)
        try {
            val account = task.getResult(ApiException::class.java)
            handleGoogleAccount(account)
        } catch (e: ApiException) {
            // User cancelled, or sign-in produced an error code.
            Toast.makeText(
                context,
                getString(R.string.google_sign_in_error, e.localizedMessage ?: "cancelled"),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_login, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        setupGoogleSignIn()

        val etEmail = view.findViewById<EditText>(R.id.etEmail)
        val etPassword = view.findViewById<EditText>(R.id.etPassword)
        val btnLogin = view.findViewById<Button>(R.id.btnLogin)
        val btnGoogleSignIn = view.findViewById<Button>(R.id.btnGoogleSignIn)
        val tvSignUp = view.findViewById<TextView>(R.id.tvSignUp)

        tvSignUp.setOnClickListener {
            parentFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, RegisterFragment())
                .addToBackStack(null)
                .commit()
        }

        // Check if user is already logged in
        val existingToken = sessionManager.fetchAuthToken()
        if (existingToken != null) {
            Toast.makeText(context, "Session Active", Toast.LENGTH_SHORT).show()
        }

        btnLogin.setOnClickListener {
            val email = etEmail.text.toString().trim()
            val password = etPassword.text.toString().trim()

            if (email.isNotEmpty() && password.isNotEmpty()) {
                setLoginLoading(btnLogin, loading = true)
                val loginRequest = LoginRequest(email = email, password = password)
                RetrofitClient.apiService.loginUser(loginRequest).enqueue(object : Callback<TokenResponse> {
                    override fun onResponse(call: Call<TokenResponse>, response: Response<TokenResponse>) {
                        setLoginLoading(btnLogin, loading = false)

                        if (response.isSuccessful && response.body() != null) {
                            onAuthSuccess(response.body()!!)
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
                        setLoginLoading(btnLogin, loading = false)
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

        btnGoogleSignIn.setOnClickListener {
            val webClientId = getString(R.string.default_web_client_id)
            if (webClientId.startsWith("YOUR_")) {
                // Scaffold mode — the real client ID has not been filled in yet.
                Toast.makeText(
                    context,
                    getString(R.string.google_sign_in_not_configured),
                    Toast.LENGTH_LONG
                ).show()
                return@setOnClickListener
            }
            // Sign out first so the account chooser always appears even if a
            // previous Google sign-in cached the chosen account.
            googleSignInClient.signOut().addOnCompleteListener {
                googleSignInLauncher.launch(googleSignInClient.signInIntent)
            }
        }
    }

    private fun setupGoogleSignIn() {
        val webClientId = getString(R.string.default_web_client_id)
        googleSignInClient = GoogleSignIn.getClient(
            requireContext(),
            GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                .requestIdToken(webClientId)
                .requestEmail()
                .build()
        )
    }

    private fun handleGoogleAccount(account: GoogleSignInAccount) {
        val btnGoogleSignIn = view?.findViewById<Button>(R.id.btnGoogleSignIn)
        val idToken = account.idToken
        if (idToken.isNullOrEmpty()) {
            Toast.makeText(
                context,
                getString(R.string.google_sign_in_error, "no ID token"),
                Toast.LENGTH_LONG
            ).show()
            return
        }

        btnGoogleSignIn?.isEnabled = false
        btnGoogleSignIn?.text = getString(R.string.google_sign_in_signing)

        RetrofitClient.apiService.googleLogin(GoogleLoginRequest(idToken))
            .enqueue(object : Callback<TokenResponse> {
                override fun onResponse(call: Call<TokenResponse>, response: Response<TokenResponse>) {
                    btnGoogleSignIn?.isEnabled = true
                    btnGoogleSignIn?.text = getString(R.string.google_sign_in_continue)

                    if (response.isSuccessful && response.body() != null) {
                        onAuthSuccess(response.body()!!)
                    } else {
                        val errorMsg = when (response.code()) {
                            401 -> "Google Sign-In failed: token rejected"
                            403 -> "Account is deactivated"
                            409 -> "This Google account is linked to a different EasyGov account"
                            else -> "Google Sign-In failed (${response.code()})"
                        }
                        Toast.makeText(context, errorMsg, Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<TokenResponse>, t: Throwable) {
                    btnGoogleSignIn?.isEnabled = true
                    btnGoogleSignIn?.text = getString(R.string.google_sign_in_continue)
                    Toast.makeText(
                        context,
                        "Network Error: ${t.localizedMessage}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            })
    }

    /** Saves the session and opens the dashboard. Shared by both sign-in flows. */
    private fun onAuthSuccess(tokenResponse: TokenResponse) {
        val jwtToken = tokenResponse.accessToken
        val user = tokenResponse.user

        sessionManager.saveAuthToken("Bearer $jwtToken")
        sessionManager.saveUser(user.fullName, user.email)

        Toast.makeText(
            context,
            "Welcome back, ${user.fullName}!",
            Toast.LENGTH_LONG
        ).show()

        parentFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, DashboardFragment())
            .commit()
    }

    private fun setLoginLoading(btn: Button, loading: Boolean) {
        btn.isEnabled = !loading
        btn.text = getString(if (loading) R.string.signing_in else R.string.login)
    }
}