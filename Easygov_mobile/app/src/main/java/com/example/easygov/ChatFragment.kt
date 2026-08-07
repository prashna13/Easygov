package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
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
    private lateinit var btnHistory: ImageButton
    private lateinit var btnNewChat: ImageButton
    private lateinit var markwon: Markwon
    private var chatAccumulator = ""

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_chat, container, false)

        tvChatLog = view.findViewById(R.id.tvChatLog)
        etQuestion = view.findViewById(R.id.etQuestion)
        btnSend = view.findViewById(R.id.btnSend)
        btnHistory = view.findViewById(R.id.btnHistory)
        btnNewChat = view.findViewById(R.id.btnNewChat)

        markwon = Markwon.create(requireContext())

        btnSend.setOnClickListener {
            val queryText = etQuestion.text.toString().trim()
            if (queryText.isNotEmpty()) {
                executeNetworkQuery(queryText)
            } else {
                Toast.makeText(context, "Please enter a question", Toast.LENGTH_SHORT).show()
            }
        }

        btnHistory.setOnClickListener {
            val historySheet = ChatHistoryBottomSheet()
            historySheet.show(parentFragmentManager, ChatHistoryBottomSheet.TAG)
        }

        btnNewChat.setOnClickListener {
            chatAccumulator = ""
            tvChatLog.text = "Ready for your question."
            Toast.makeText(context, "New conversation started", Toast.LENGTH_SHORT).show()
        }

        return view
    }

    private fun executeNetworkQuery(userQuestion: String) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) {
            Toast.makeText(context, "Please sign in to use the AI assistant", Toast.LENGTH_LONG).show()
            return
        }

        // Add user question to log
        if (chatAccumulator.isEmpty()) chatAccumulator = ""
        chatAccumulator += "\n\n👤 You: $userQuestion\n🤖 EasyGov: Typing..."
        updateChatDisplay()
        etQuestion.text.clear()

        val requestPayload = ChatRequest(question = userQuestion)

        com.example.easygov.network.RetrofitClient.apiService.getBotResponse(authToken, requestPayload)
            .enqueue(object : Callback<ChatResponse> {
                override fun onResponse(call: Call<ChatResponse>, response: Response<ChatResponse>) {
                    if (response.isSuccessful && response.body() != null) {
                        val systemReply = response.body()!!.answer
                        chatAccumulator = chatAccumulator.replace("🤖 EasyGov: Typing...", "🤖 EasyGov:\n$systemReply")
                        updateChatDisplay()
                    } else {
                        revertTypingState("Error: ${response.code()}")
                    }
                }

                override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                    revertTypingState("Connection Failed: ${t.localizedMessage}")
                }
            })
    }

    private fun updateChatDisplay() {
        markwon.setMarkdown(tvChatLog, chatAccumulator)
    }

    private fun revertTypingState(errorMessage: String) {
        chatAccumulator = chatAccumulator.replace("🤖 EasyGov: Typing...", "❌ Error: $errorMessage")
        updateChatDisplay()
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        // Check for initial question passed from Dashboard
        checkInitialQuestion()
    }

    private fun checkInitialQuestion() {
        arguments?.getString("initial_question")?.let { question ->
            arguments?.remove("initial_question") // Only process once
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