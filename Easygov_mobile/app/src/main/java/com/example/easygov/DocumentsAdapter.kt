package com.example.easygov

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.UserDocument
import java.text.SimpleDateFormat
import java.util.Locale

/**
 * Displays a user's uploaded documents (label, filename, tag chips, size, date).
 * Tapping a card opens the detail dialog for that document.
 */
class DocumentsAdapter(
    private val onItemClick: (UserDocument) -> Unit
) : ListAdapter<UserDocument, DocumentsAdapter.DocumentViewHolder>(DocumentDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): DocumentViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_document, parent, false)
        return DocumentViewHolder(view)
    }

    override fun onBindViewHolder(holder: DocumentViewHolder, position: Int) {
        val doc = getItem(position)
        val context = holder.itemView.context

        holder.label.text = doc.label
        holder.filename.text = doc.filename
        holder.icon.setImageResource(
            if (doc.mimeType == "application/pdf") R.drawable.ic_documents
            else R.drawable.ic_doc_image
        )
        holder.meta.text = "${formatSize(doc.sizeBytes)} · ${formatDate(doc.createdAt)}"

        holder.tagsRow.removeAllViews()
        if (doc.tags.isEmpty()) {
            holder.tagsRow.visibility = View.GONE
        } else {
            holder.tagsRow.visibility = View.VISIBLE
            doc.tags.take(3).forEach { tag ->
                val chip = TextView(context)
                chip.text = tag
                chip.setTextColor(context.getColor(R.color.onSecondaryContainer_light))
                chip.textSize = 12f
                chip.setBackgroundResource(R.drawable.bg_category_tag)
                chip.setPadding(dp(context, 8f), dp(context, 3f), dp(context, 8f), dp(context, 3f))
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                )
                lp.setMargins(0, 0, dp(context, 8f), 0)
                chip.layoutParams = lp
                holder.tagsRow.addView(chip)
            }
        }

        holder.itemView.setOnClickListener { onItemClick(doc) }
    }

    private fun dp(context: Context, value: Float): Int =
        (value * context.resources.displayMetrics.density).toInt()

    private fun formatSize(bytes: Long): String = when {
        bytes >= 1024 * 1024 -> String.format(Locale.getDefault(), "%.1f MB", bytes / (1024.0 * 1024.0))
        bytes >= 1024 -> String.format(Locale.getDefault(), "%.0f KB", bytes / 1024.0)
        else -> "$bytes B"
    }

    private fun formatDate(iso: String?): String {
        if (iso.isNullOrBlank()) return ""
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
            val out = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            out.format(sdf.parse(iso)!!)
        } catch (_: Exception) {
            iso
        }
    }

    class DocumentViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val icon: ImageView = view.findViewById(R.id.ivDocIcon)
        val label: TextView = view.findViewById(R.id.tvDocLabel)
        val filename: TextView = view.findViewById(R.id.tvDocFilename)
        val tagsRow: LinearLayout = view.findViewById(R.id.docTagsRow)
        val meta: TextView = view.findViewById(R.id.tvDocMeta)
    }
}

private class DocumentDiffCallback : DiffUtil.ItemCallback<UserDocument>() {
    override fun areItemsTheSame(oldItem: UserDocument, newItem: UserDocument): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: UserDocument, newItem: UserDocument): Boolean {
        return oldItem == newItem
    }
}
