package com.example.easygov

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.ApplicationProgress
import com.google.android.material.progressindicator.LinearProgressIndicator

/**
 * Displays a user's applications (title, status, progress %) on the profile
 * screen. Tapping a card opens the full progress tracker for that application.
 */
class ApplicationsAdapter(
    private val onItemClick: (ApplicationProgress) -> Unit
) : ListAdapter<ApplicationProgress, ApplicationsAdapter.ApplicationViewHolder>(ApplicationDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ApplicationViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_application_card, parent, false)
        return ApplicationViewHolder(view)
    }

    override fun onBindViewHolder(holder: ApplicationViewHolder, position: Int) {
        val app = getItem(position)
        val context = holder.itemView.context
        holder.title.text = app.serviceTitle
        holder.percent.text = "${app.progressPercent}%"
        holder.status.text = when (app.status) {
            "COMPLETED" -> context.getString(R.string.status_completed)
            "IN_PROGRESS" -> context.getString(R.string.status_in_progress)
            "NOT_STARTED" -> context.getString(R.string.status_not_started)
            else -> app.status.replace("_", " ")
        }
        holder.progressBar.progress = app.progressPercent
        holder.itemView.setOnClickListener { onItemClick(app) }
    }

    class ApplicationViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.tvAppTitle)
        val percent: TextView = view.findViewById(R.id.tvAppPercent)
        val status: TextView = view.findViewById(R.id.tvAppStatus)
        val progressBar: LinearProgressIndicator = view.findViewById(R.id.progressBar)
    }
}

private class ApplicationDiffCallback : DiffUtil.ItemCallback<ApplicationProgress>() {
    override fun areItemsTheSame(oldItem: ApplicationProgress, newItem: ApplicationProgress): Boolean {
        return oldItem.applicationId == newItem.applicationId
    }

    override fun areContentsTheSame(oldItem: ApplicationProgress, newItem: ApplicationProgress): Boolean {
        return oldItem == newItem
    }
}
