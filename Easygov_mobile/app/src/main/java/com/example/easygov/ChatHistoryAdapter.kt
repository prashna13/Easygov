package com.example.easygov

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ChatHistoryAdapter : RecyclerView.Adapter<ChatHistoryAdapter.ViewHolder>() {

    private var messages: List<ChatMessageResponse> = emptyList()

    fun submitList(newList: List<ChatMessageResponse>) {
        messages = newList
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_chat_history, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = messages[position]
        holder.tvRole.text = if (item.role == "user") "You" else "EasyGov"
        holder.tvContent.text = item.content
        holder.tvDate.text = item.created_at.substringBefore("T") // Simple date split
    }

    override fun getItemCount() = messages.size

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvRole: TextView = view.findViewById(R.id.tvHistoryRole)
        val tvContent: TextView = view.findViewById(R.id.tvHistoryContent)
        val tvDate: TextView = view.findViewById(R.id.tvHistoryDate)
    }
}
