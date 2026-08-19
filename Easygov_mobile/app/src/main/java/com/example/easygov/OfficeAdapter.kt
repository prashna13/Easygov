package com.example.easygov

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.Office
import com.google.android.material.button.MaterialButton
import java.util.Locale

/**
 * Displays nearby government offices (name, type, address, district/phone
 * meta, distance, and a Directions button). Tapping Directions fires the
 * [onDirectionsClick] callback for that office.
 */
class OfficeAdapter(
    private val onDirectionsClick: (Office) -> Unit
) : ListAdapter<Office, OfficeAdapter.OfficeViewHolder>(OfficeDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): OfficeViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_office, parent, false)
        return OfficeViewHolder(view)
    }

    override fun onBindViewHolder(holder: OfficeViewHolder, position: Int) {
        val office = getItem(position)

        holder.name.text = office.name
        holder.type.text = office.officeType
        holder.address.text = office.address

        val meta = buildList {
            if (office.district.isNotBlank()) add(office.district)
            office.phone?.takeIf { it.isNotBlank() }?.let { add(it) }
            office.hours?.takeIf { it.isNotBlank() }?.let { add(it) }
        }.joinToString(" · ")
        holder.meta.text = meta

        holder.distance.text = office.distanceKm?.let {
            String.format(Locale.getDefault(), "%.1f km", it)
        }.orEmpty()

        holder.btnDirections.setOnClickListener { onDirectionsClick(office) }
    }

    class OfficeViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val name: TextView = view.findViewById(R.id.tvOfficeName)
        val type: TextView = view.findViewById(R.id.tvOfficeType)
        val address: TextView = view.findViewById(R.id.tvOfficeAddress)
        val meta: TextView = view.findViewById(R.id.tvOfficeMeta)
        val distance: TextView = view.findViewById(R.id.tvOfficeDistance)
        val btnDirections: MaterialButton = view.findViewById(R.id.btnOfficeDirections)
    }
}

private class OfficeDiffCallback : DiffUtil.ItemCallback<Office>() {
    override fun areItemsTheSame(oldItem: Office, newItem: Office): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: Office, newItem: Office): Boolean {
        return oldItem == newItem
    }
}