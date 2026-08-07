package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ChatHistoryBottomSheet : BottomSheetDialogFragment() {

    private lateinit var adapter: ChatHistoryAdapter
    private lateinit var rvHistory: RecyclerView
    private lateinit var tvNoHistory: TextView

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.bottom_sheet_chat_history, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        rvHistory = view.findViewById(R.id.rvChatHistory)
        tvNoHistory = view.findViewById(R.id.tvNoHistory)

        rvHistory.layoutManager = LinearLayoutManager(context)
        adapter = ChatHistoryAdapter()
        rvHistory.adapter = adapter

        fetchHistory()
    }

    private fun fetchHistory() {
        val context = requireContext()
        val authToken = SessionManager.getInstance(context).fetchAuthToken() ?: return

        com.example.easygov.network.RetrofitClient.apiService.getChatHistory(authToken)
            .enqueue(object : Callback<ChatHistoryResponse> {
                override fun onResponse(
                    call: Call<ChatHistoryResponse>,
                    response: Response<ChatHistoryResponse>
                ) {
                    if (response.isSuccessful && response.body() != null) {
                        val messages = response.body()!!.messages
                        if (messages.isEmpty()) {
                            tvNoHistory.visibility = View.VISIBLE
                        } else {
                            tvNoHistory.visibility = View.GONE
                            adapter.submitList(messages.reversed()) // Show latest first
                        }
                    }
                }

                override fun onFailure(call: Call<ChatHistoryResponse>, t: Throwable) {
                    Toast.makeText(context, "Error loading history", Toast.LENGTH_SHORT).show()
                }
            })
    }

    companion object {
        const val TAG = "ChatHistoryBottomSheet"
    }
}
