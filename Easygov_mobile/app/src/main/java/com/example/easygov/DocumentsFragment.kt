package com.example.easygov

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.easygov.model.UserDocument
import com.example.easygov.network.RetrofitClient
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import okhttp3.MediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Locale

/**
 * The user's private document vault. Users upload document images (or PDFs)
 * with a label + tags and can view/download or delete them from anywhere.
 */
class DocumentsFragment : Fragment() {

    private lateinit var documentsAdapter: DocumentsAdapter
    private lateinit var scrollContent: View
    private lateinit var errorLayout: View
    private lateinit var tvDocsError: TextView
    private lateinit var tvDocsEmpty: TextView

    private val pickDocument =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            if (uri != null) showUploadDetailsDialog(uri)
        }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_documents, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        scrollContent = view.findViewById(R.id.scrollContent)
        errorLayout = view.findViewById(R.id.errorLayout)
        tvDocsError = view.findViewById(R.id.tvDocsError)
        tvDocsEmpty = view.findViewById(R.id.tvDocsEmpty)

        val rvDocuments = view.findViewById<RecyclerView>(R.id.rvDocuments)
        documentsAdapter = DocumentsAdapter { doc -> showDetailDialog(doc) }
        rvDocuments.layoutManager = LinearLayoutManager(requireContext())
        rvDocuments.adapter = documentsAdapter

        view.findViewById<View>(R.id.btnUploadDocument).setOnClickListener {
            pickDocument.launch("*/*")
        }
        view.findViewById<View>(R.id.btnAddDocument).setOnClickListener {
            pickDocument.launch("*/*")
        }
        view.findViewById<View>(R.id.btnRetryDocs).setOnClickListener {
            errorLayout.visibility = View.GONE
            scrollContent.visibility = View.VISIBLE
            loadDocuments()
        }

        loadDocuments()
    }

    private fun loadDocuments() {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) {
            showError(getString(R.string.doc_sign_in))
            return
        }

        RetrofitClient.apiService.getDocuments(authToken)
            .enqueue(object : Callback<List<UserDocument>> {
                override fun onResponse(
                    call: Call<List<UserDocument>>,
                    response: Response<List<UserDocument>>
                ) {
                    if (response.isSuccessful && response.body() != null) {
                        bindDocuments(response.body()!!)
                    } else {
                        val msg = if (response.code() == 401) getString(R.string.doc_sign_in)
                            else getString(R.string.server_error, response.code().toString())
                        showError(msg)
                    }
                }

                override fun onFailure(call: Call<List<UserDocument>>, t: Throwable) {
                    showError(getString(R.string.network_failure, t.localizedMessage ?: ""))
                }
            })
    }

    private fun bindDocuments(documents: List<UserDocument>) {
        errorLayout.visibility = View.GONE
        scrollContent.visibility = View.VISIBLE
        tvDocsEmpty.visibility = if (documents.isEmpty()) View.VISIBLE else View.GONE
        documentsAdapter.submitList(documents)
    }

    private fun showError(message: String) {
        scrollContent.visibility = View.GONE
        errorLayout.visibility = View.VISIBLE
        tvDocsError.text = message
    }

    // ── UPLOAD FLOW ──────────────────────────────────────────────────────────

    private fun showUploadDetailsDialog(uri: Uri) {
        val view = layoutInflater.inflate(R.layout.dialog_document_upload, null)
        val etLabel = view.findViewById<EditText>(R.id.etDocLabel)
        val etTags = view.findViewById<EditText>(R.id.etDocTags)
        val etDescription = view.findViewById<EditText>(R.id.etDocDescription)

        MaterialAlertDialogBuilder(requireContext())
            .setTitle(getString(R.string.doc_upload))
            .setView(view)
            .setNegativeButton(getString(R.string.doc_cancel), null)
            .setPositiveButton(getString(R.string.doc_upload_btn)) { dialog, _ ->
                val label = etLabel.text.toString().trim()
                val tags = etTags.text.toString().trim()
                val description = etDescription.text.toString().trim()
                dialog.dismiss()
                if (label.isEmpty()) {
                    Toast.makeText(requireContext(), getString(R.string.doc_pick_label), Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                uploadDocument(uri, label, tags, description)
            }
            .show()
    }

    private fun uploadDocument(uri: Uri, label: String, tags: String, description: String) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: return
        val resolver = requireContext().contentResolver
        val filename = resolveFilename(uri)
        val mime = resolver.getType(uri) ?: guessMimeFromFilename(filename)
        val bytes = resolver.openInputStream(uri)?.readBytes() ?: return

        Toast.makeText(requireContext(), getString(R.string.doc_uploading), Toast.LENGTH_SHORT).show()

        val fileBody = RequestBody.create(MediaType.parse(mime) ?: MediaType.parse("application/octet-stream"), bytes)
        val filePart = MultipartBody.Part.createFormData("file", filename, fileBody)
        val labelBody = RequestBody.create(MediaType.parse("text/plain"), label)
        val tagsBody = RequestBody.create(MediaType.parse("text/plain"), tags)
        val descriptionBody = RequestBody.create(MediaType.parse("text/plain"), description)

        RetrofitClient.apiService.uploadDocument(authToken, labelBody, tagsBody, descriptionBody, filePart)
            .enqueue(object : Callback<UserDocument> {
                override fun onResponse(call: Call<UserDocument>, response: Response<UserDocument>) {
                    if (response.isSuccessful && response.body() != null) {
                        loadDocuments()
                    } else {
                        Toast.makeText(requireContext(), getString(R.string.doc_upload_fail), Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<UserDocument>, t: Throwable) {
                    Toast.makeText(requireContext(), getString(R.string.doc_upload_fail), Toast.LENGTH_LONG).show()
                }
            })
    }

    // ── DETAIL / VIEW / DELETE ───────────────────────────────────────────────

    private fun showDetailDialog(doc: UserDocument) {
        val view = layoutInflater.inflate(R.layout.dialog_document_detail, null)
        view.findViewById<TextView>(R.id.tvDetailLabel).text = doc.label
        view.findViewById<TextView>(R.id.tvDetailFilename).text = doc.filename
        view.findViewById<TextView>(R.id.tvDetailMeta).text =
            "${formatSize(doc.sizeBytes)} · ${formatDate(doc.createdAt)}"

        val desc = view.findViewById<TextView>(R.id.tvDetailDesc)
        if (doc.description.isNullOrBlank()) desc.visibility = View.GONE
        else desc.text = doc.description

        val tagsRow = view.findViewById<LinearLayout>(R.id.detailTagsRow)
        doc.tags.take(5).forEach { tag ->
            val chip = TextView(requireContext())
            chip.text = tag
            chip.setTextColor(requireContext().getColor(R.color.onSecondaryContainer_light))
            chip.textSize = 12f
            chip.setBackgroundResource(R.drawable.bg_category_tag)
            chip.setPadding(dp(8f), dp(3f), dp(8f), dp(3f))
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            lp.setMargins(0, 0, dp(8f), 0)
            chip.layoutParams = lp
            tagsRow.addView(chip)
        }

        MaterialAlertDialogBuilder(requireContext())
            .setTitle(getString(R.string.doc_details))
            .setView(view)
            .setNegativeButton(getString(R.string.doc_cancel), null)
            .setNeutralButton(getString(R.string.doc_delete)) { _, _ ->
                confirmDelete(doc)
            }
            .setPositiveButton(getString(R.string.doc_view)) { _, _ ->
                openDocument(doc)
            }
            .show()
    }

    private fun confirmDelete(doc: UserDocument) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(getString(R.string.doc_delete_confirm))
            .setMessage(getString(R.string.doc_delete_msg, doc.label))
            .setNegativeButton(getString(R.string.doc_cancel), null)
            .setPositiveButton(getString(R.string.doc_delete)) { _, _ ->
                deleteDocument(doc)
            }
            .show()
    }

    private fun deleteDocument(doc: UserDocument) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: return
        RetrofitClient.apiService.deleteDocument(authToken, doc.id)
            .enqueue(object : Callback<okhttp3.ResponseBody> {
                override fun onResponse(
                    call: Call<okhttp3.ResponseBody>,
                    response: Response<okhttp3.ResponseBody>
                ) {
                    if (response.isSuccessful) {
                        Toast.makeText(requireContext(), getString(R.string.doc_deleted), Toast.LENGTH_SHORT).show()
                        loadDocuments()
                    } else {
                        Toast.makeText(requireContext(), getString(R.string.server_error, response.code().toString()), Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<okhttp3.ResponseBody>, t: Throwable) {
                    Toast.makeText(requireContext(), getString(R.string.network_failure, t.localizedMessage ?: ""), Toast.LENGTH_LONG).show()
                }
            })
    }

    private fun openDocument(doc: UserDocument) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken() ?: return
        Toast.makeText(requireContext(), getString(R.string.doc_downloading), Toast.LENGTH_SHORT).show()

        RetrofitClient.apiService.downloadDocument(authToken, doc.id)
            .enqueue(object : Callback<okhttp3.ResponseBody> {
                override fun onResponse(
                    call: Call<okhttp3.ResponseBody>,
                    response: Response<okhttp3.ResponseBody>
                ) {
                    val body = response.body()
                    if (!response.isSuccessful || body == null) {
                        Toast.makeText(requireContext(), getString(R.string.server_error, response.code().toString()), Toast.LENGTH_LONG).show()
                        return
                    }
                    val bytes = body.bytes()
                    if (doc.mimeType.startsWith("image/")) showImage(bytes)
                    else openPdf(doc, bytes)
                }

                override fun onFailure(call: Call<okhttp3.ResponseBody>, t: Throwable) {
                    Toast.makeText(requireContext(), getString(R.string.network_failure, t.localizedMessage ?: ""), Toast.LENGTH_LONG).show()
                }
            })
    }

    private fun showImage(bytes: ByteArray) {
        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return
        val imageView = ImageView(requireContext())
        imageView.setImageBitmap(bitmap)
        imageView.adjustViewBounds = true
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(getString(R.string.doc_view))
            .setView(imageView)
            .setPositiveButton(getString(R.string.doc_cancel), null)
            .show()
    }

    private fun openPdf(doc: UserDocument, bytes: ByteArray) {
        try {
            val dir = File(requireContext().cacheDir, "documents")
            dir.mkdirs()
            val file = File(dir, doc.filename)
            FileOutputStream(file).use { it.write(bytes) }
            val uri = FileProvider.getUriForFile(
                requireContext(),
                "${requireContext().packageName}.fileprovider",
                file
            )
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, doc.mimeType)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(intent)
        } catch (e: Exception) {
            Toast.makeText(requireContext(), getString(R.string.doc_no_viewer), Toast.LENGTH_LONG).show()
        }
    }

    // ── HELPERS ──────────────────────────────────────────────────────────────

    private fun resolveFilename(uri: Uri): String {
        requireContext().contentResolver.query(
            uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val name = cursor.getString(0)
                if (!name.isNullOrBlank()) return name
            }
        }
        return uri.lastPathSegment ?: getString(R.string.doc_unknown_name)
    }

    private fun guessMimeFromFilename(filename: String): String = when {
        filename.endsWith(".pdf", ignoreCase = true) -> "application/pdf"
        filename.endsWith(".png", ignoreCase = true) -> "image/png"
        filename.endsWith(".webp", ignoreCase = true) -> "image/webp"
        filename.endsWith(".heic", ignoreCase = true) -> "image/heic"
        else -> "image/jpeg"
    }

    private fun dp(value: Float): Int =
        (value * resources.displayMetrics.density).toInt()

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
}
