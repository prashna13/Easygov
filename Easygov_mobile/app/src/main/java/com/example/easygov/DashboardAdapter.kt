package com.example.easygov

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.ServiceItem
import com.google.android.material.progressindicator.LinearProgressIndicator

/**
 * ListAdapter for the dashboard service grids. Renders the [ServiceItem] card
 * with a pastel squircle icon, bold title and a linear progress tracker.
 */
class DashboardAdapter(
    private val onItemClick: (ServiceItem) -> Unit
) : ListAdapter<ServiceItem, DashboardAdapter.ServiceViewHolder>(ServiceDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ServiceViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_dashboard_card, parent, false)
        return ServiceViewHolder(view)
    }

    override fun onBindViewHolder(holder: ServiceViewHolder, position: Int) {
        val item = getItem(position)
        holder.name.text = item.title
        holder.icon.setImageResource(item.iconRes)
        holder.icon.setBackgroundResource(discFor(item.id))
        holder.icon.setColorFilter(ContextCompat.getColor(holder.itemView.context, R.color.white))

        holder.progressBar.progress = item.progressPercent
        holder.progressText.text = if (item.isCompleted) {
            holder.itemView.context.getString(R.string.dash_progress_completed)
        } else {
            holder.itemView.context.getString(
                R.string.dash_progress_fraction,
                item.completedSteps,
                item.totalSteps
            )
        }
        holder.itemView.setOnClickListener { onItemClick(item) }
    }

    private fun discFor(id: Int): Int = when (id) {
        1 -> R.drawable.bg_icon_circle_teal          // Citizenship
        2 -> R.drawable.bg_icon_circle_purple        // NID
        3 -> R.drawable.bg_icon_circle_amber         // E-Passport
        7 -> R.drawable.bg_icon_circle_green         // Driving License
        else -> R.drawable.bg_icon_circle_neutral
    }

    class ServiceViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val icon: ImageView = view.findViewById(R.id.ivServiceIcon)
        val name: TextView = view.findViewById(R.id.tvServiceName)
        val progressBar: LinearProgressIndicator = view.findViewById(R.id.piServiceProgress)
        val progressText: TextView = view.findViewById(R.id.tvServiceProgress)
    }
}

private class ServiceDiffCallback : DiffUtil.ItemCallback<ServiceItem>() {
    override fun areItemsTheSame(oldItem: ServiceItem, newItem: ServiceItem): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: ServiceItem, newItem: ServiceItem): Boolean {
        return oldItem == newItem
    }
}