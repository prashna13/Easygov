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
import io.noties.markwon.Markwon
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ChatFragment : Fragment() {

    private lateinit var tvChatLog: TextView
    private lateinit var etQuestion: EditText
    private lateinit var btnSend: Button
    private lateinit var markwon: Markwon

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        // Inflate our new isolated layout file instead of hijacking activity_main
        val view = inflater.inflate(R.layout.fragment_chat, container, false)

        // Bind IDs directly from fragment_chat.xml view context
        tvChatLog = view.findViewById(R.id.tvChatLog)
        etQuestion = view.findViewById(R.id.etQuestion)
        btnSend = view.findViewById(R.id.btnSend)

        // Initialize Markwon using fragment contextual parameters safely
        markwon = Markwon.create(requireContext())

        btnSend.setOnClickListener {
            val queryText = etQuestion.text.toString().trim()
            if (queryText.isNotEmpty()) {
                executeNetworkQuery(queryText)
            } else {
                Toast.makeText(context, "Please enter a question", Toast.LENGTH_SHORT).show()
            }
        }

        return view
    }

    private fun executeNetworkQuery(userQuestion: String) {
        // Log user submission string state update to viewport
        val currentLog = tvChatLog.text.toString()
        tvChatLog.text = "$currentLog\n\n👤 You: $userQuestion\n🤖 EasyGov: Typing..."
        etQuestion.text.clear()

        // Build network transfer data payload instance object
        val requestPayload = ChatRequest(question = userQuestion)

        // Execute asynchronous HTTP stream connection via Retrofit instance
        RetrofitClient.instance.getBotResponse(requestPayload).enqueue(object : Callback<ChatResponse> {
            override fun onResponse(call: Call<ChatResponse>, response: Response<ChatResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val systemReply = response.body()!!.answer

                    // Clear out our temporary fallback state placeholder
                    val freshLogBase = tvChatLog.text.toString().replace("🤖 EasyGov: Typing...", "")

                    // Map fresh logs and parse native formatted markdown elements
                    tvChatLog.text = freshLogBase
                    markwon.setMarkdown(tvChatLog, "$freshLogBase\n🤖 EasyGov:\n$systemReply")
                } else {
                    revertTypingState("Error processing request: Code ${response.code()}")
                }
            }

            override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                revertTypingState("Failed to connect to backend server: ${t.message}")
            }
        })
    }

    private fun revertTypingState(errorMessage: String) {
        val cleanLog = tvChatLog.text.toString().replace("🤖 EasyGov: Typing...", "")
        tvChatLog.text = "$cleanLog\n❌ System Error:\n$errorMessage"
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Check for initial question passed from Dashboard
        arguments?.getString("initial_question")?.let { question ->
            executeNetworkQuery(question)
        }
    }

    companion object {
        fun newInstance(initialQuestion: String? = null): ChatFragment {
            val fragment = ChatFragment()
            if (initialQuestion != null) {
                val args = Bundle()
                args.putString("initial_question", initialQuestion)
                fragment.arguments = args
            }
            return fragment
        }
    }
}