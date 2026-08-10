package com.example.easygov

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.GovService

/**
 * Modern Adapter for Dashboard services using ListAdapter for efficient updates.
 */
class DashboardAdapter(
    private val onItemClick: (GovService) -> Unit
) : ListAdapter<GovService, DashboardAdapter.ServiceViewHolder>(ServiceDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ServiceViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_dashboard_card, parent, false)
        return ServiceViewHolder(view)
    }

    override fun onBindViewHolder(holder: ServiceViewHolder, position: Int) {
        val service = getItem(position)
        holder.name.text = service.title
        
        // Map service titles to appropriate icons (Fallback to help icon)
        val iconRes = when {
            service.title.contains("Passport", ignoreCase = true) -> android.R.drawable.ic_menu_agenda
            service.title.contains("License", ignoreCase = true) -> android.R.drawable.ic_menu_directions
            service.title.contains("Tax", ignoreCase = true) -> android.R.drawable.ic_menu_save
            service.title.contains("PAN", ignoreCase = true) -> android.R.drawable.ic_menu_manage
            service.title.contains("Citizenship", ignoreCase = true) -> android.R.drawable.ic_menu_info_details
            service.title.contains("NID", ignoreCase = true) -> android.R.drawable.ic_menu_myplaces
            else -> android.R.drawable.ic_menu_help
        }
        
        holder.icon.setImageResource(iconRes)
        holder.itemView.setOnClickListener { onItemClick(service) }
    }

    class ServiceViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val icon: ImageView = view.findViewById(R.id.ivServiceIcon)
        val name: TextView = view.findViewById(R.id.tvServiceName)
    }
}

private class ServiceDiffCallback : DiffUtil.ItemCallback<GovService>() {
    override fun areItemsTheSame(oldItem: GovService, newItem: GovService): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: GovService, newItem: GovService): Boolean {
        return oldItem == newItem
    }
}
