package com.example.easygov

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.ProgressStep
import com.google.android.material.checkbox.MaterialCheckBox

/**
 * Displays the step checklist of an application. Only the current
 * IN_PROGRESS step is tappable; completed steps are shown checked and
 * disabled, pending steps are shown unchecked and disabled.
 */
class ProgressStepAdapter(
    private val onStepClick: (stepNumber: Int) -> Unit
) : ListAdapter<ProgressStep, ProgressStepAdapter.StepViewHolder>(StepDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): StepViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_progress_step, parent, false)
        return StepViewHolder(view)
    }

    override fun onBindViewHolder(holder: StepViewHolder, position: Int) {
        val step = getItem(position)

        holder.checkbox.text = "Step ${step.stepNumber} — ${step.stepName}"
        holder.checkbox.isEnabled = step.status == "IN_PROGRESS"
        holder.checkbox.isChecked = step.status == "COMPLETED"

        if (!step.stepDescription.isNullOrBlank()) {
            holder.description.text = step.stepDescription
            holder.description.visibility = View.VISIBLE
        } else {
            holder.description.visibility = View.GONE
        }

        holder.itemView.setOnClickListener {
            if (step.status == "IN_PROGRESS") {
                onStepClick(step.stepNumber)
            }
        }
        holder.checkbox.setOnClickListener {
            if (step.status == "IN_PROGRESS") {
                onStepClick(step.stepNumber)
            }
        }
    }

    class StepViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val checkbox: MaterialCheckBox = view.findViewById(R.id.cbStep)
        val description: TextView = view.findViewById(R.id.tvStepDesc)
    }
}

private class StepDiffCallback : DiffUtil.ItemCallback<ProgressStep>() {
    override fun areItemsTheSame(oldItem: ProgressStep, newItem: ProgressStep): Boolean {
        return oldItem.stepNumber == newItem.stepNumber
    }

    override fun areContentsTheSame(oldItem: ProgressStep, newItem: ProgressStep): Boolean {
        return oldItem == newItem
    }
}
