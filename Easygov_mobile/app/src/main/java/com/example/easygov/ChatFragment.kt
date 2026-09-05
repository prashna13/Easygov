package com.example.easygov

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.widget.NestedScrollView
import androidx.fragment.app.Fragment
import com.example.easygov.network.RetrofitClient
import com.google.android.material.chip.Chip
import com.google.android.material.color.MaterialColors
import io.noties.markwon.AbstractMarkwonPlugin
import io.noties.markwon.LinkResolver
import io.noties.markwon.Markwon
import io.noties.markwon.MarkwonConfiguration
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ChatFragment : Fragment() {

    private lateinit var llChatStack: LinearLayout
    private lateinit var emptyState: View
    private lateinit var etQuestion: EditText
    private lateinit var scrollView: NestedScrollView
    private lateinit var markwon: Markwon
    private var pendingBubble: TextView? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_chat, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        llChatStack = view.findViewById(R.id.llChatStack)
        emptyState = view.findViewById(R.id.emptyState)
        etQuestion = view.findViewById(R.id.etQuestion)
        scrollView = view.findViewById(R.id.scrollView)

        val btnSend = view.findViewById<ImageButton>(R.id.btnSend)
        val btnHistory = view.findViewById<ImageButton>(R.id.btnHistory)
        val btnNewChat = view.findViewById<ImageButton>(R.id.btnNewChat)

        markwon = Markwon.builder(requireContext())
            .usePlugin(object : AbstractMarkwonPlugin() {
                override fun configureConfiguration(builder: MarkwonConfiguration.Builder) {
                    builder.linkResolver(LinkResolver { _, link -> handleGuideLink(link) })
                }
            })
            .build()

        btnSend.setOnClickListener {
            val queryText = etQuestion.text.toString().trim()
            if (queryText.isNotEmpty()) {
                executeNetworkQuery(queryText)
            } else {
                Toast.makeText(context, getString(R.string.chat_enter_question), Toast.LENGTH_SHORT).show()
            }
        }

        btnHistory.setOnClickListener {
            ChatHistoryBottomSheet().show(parentFragmentManager, ChatHistoryBottomSheet.TAG)
        }

        btnNewChat.setOnClickListener { resetConversation() }

        setupSuggestionChips()
        checkInitialQuestion()
    }

    private fun setupSuggestionChips() {
        val chipSpecs = listOf(
            R.id.chipSuggestion1 to R.string.suggestion_nid,
            R.id.chipSuggestion2 to R.string.suggestion_passport,
            R.id.chipSuggestion3 to R.string.suggestion_license
        )
        val root = view ?: return
        chipSpecs.forEach { (id, stringRes) ->
            val chip = root.findViewById<Chip>(id) ?: return@forEach
            chip.setText(stringRes)
            chip.setOnClickListener { executeNetworkQuery(chip.text.toString()) }
        }
    }

    private fun executeNetworkQuery(userQuestion: String) {
        val authToken = SessionManager.getInstance(requireContext()).fetchAuthToken()
        if (authToken == null) {
            Toast.makeText(context, getString(R.string.chat_sign_in_required), Toast.LENGTH_LONG).show()
            return
        }

        hideEmptyState()
        appendMessage(isUser = true, text = userQuestion)
        val typingBubble = appendMessage(isUser = false, text = getString(R.string.chat_typing))
        pendingBubble = typingBubble
        etQuestion.text.clear()

        val requestPayload = ChatRequest(question = userQuestion)

        RetrofitClient.apiService.getBotResponse(authToken, requestPayload)
            .enqueue(object : Callback<ChatResponse> {
                override fun onResponse(call: Call<ChatResponse>, response: Response<ChatResponse>) {
                    val bubble = pendingBubble ?: return
                    centerTypingBubblePadding(bubble)
                    if (response.isSuccessful && response.body() != null) {
                        val body = response.body()!!
                        var replyMarkdown = body.answer
                        if (body.sources.isNotEmpty()) {
                            replyMarkdown += "\n\n**${getString(R.string.chat_sources_header)}**\n"
                            body.sources.forEach { source ->
                                replyMarkdown += "- $source\n"
                            }
                        }
                        if (body.guideLink != null && body.guideServiceId != null && body.guideServiceId > 0) {
                            replyMarkdown += "\n[${getString(R.string.chat_view_guide)}](easygov://guide/${body.guideServiceId})"
                        }
                        render(bubble, replyMarkdown)
                    } else {
                        render(bubble, getString(R.string.chat_error_prefix, response.code().toString()))
                    }
                    pendingBubble = null
                }

                override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                    val bubble = pendingBubble ?: return
                    render(bubble, getString(R.string.chat_conn_failed, t.localizedMessage ?: ""))
                    pendingBubble = null
                }
            })
    }

    private fun appendMessage(isUser: Boolean, text: String): TextView {
        val density = resources.displayMetrics.density

        val row = LinearLayout(requireContext())
        row.orientation = LinearLayout.HORIZONTAL
        row.gravity = if (isUser) Gravity.END else Gravity.START
        val rowLp = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        )
        rowLp.bottomMargin = (10 * density).toInt()

        val bubble = TextView(requireContext())
        bubble.maxWidth = (resources.displayMetrics.widthPixels * 0.78f).toInt()
        val hPad = (14 * density).toInt()
        val vPad = (10 * density).toInt()
        bubble.setPadding(hPad, vPad, hPad, vPad)
        bubble.setTextSize(15f)
        bubble.setBackgroundResource(if (isUser) R.drawable.bg_bubble_user else R.drawable.bg_bubble_assistant)
        if (isUser) {
            bubble.setTextColor(0xFFFFFFFF.toInt())
        } else {
            bubble.setTextColor(MaterialColors.getColor(bubble, com.google.android.material.R.attr.colorOnSurface))
        }

        bubble.text = text
        row.addView(bubble)
        llChatStack.addView(row, rowLp)
        scrollToBottom()
        return bubble
    }

    private fun centerTypingBubblePadding(bubble: TextView) {
        // no-op placeholder to keep wide markdown (links) readable
    }

    private fun render(bubble: TextView, markdown: String) {
        markwon.setMarkdown(bubble, markdown)
        scrollToBottom()
    }

    private fun hideEmptyState() {
        emptyState.visibility = View.GONE
    }

    private fun resetConversation() {
        llChatStack.removeAllViews()
        pendingBubble = null
        emptyState.visibility = View.VISIBLE
        Toast.makeText(context, getString(R.string.chat_new_started), Toast.LENGTH_SHORT).show()
    }

    private fun scrollToBottom() {
        scrollView.post { scrollView.fullScroll(View.FOCUS_DOWN) }
    }

    /** Parses a `easygov://guide/<serviceId>` deep-link or official website http(s) URL. */
    private fun handleGuideLink(link: String) {
        if (link.startsWith("easygov://guide/")) {
            val serviceId = link.removePrefix("easygov://guide/").toIntOrNull() ?: return
            openGuide(serviceId)
        } else if (link.startsWith("http://") || link.startsWith("https://")) {
            try {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(link))
                startActivity(intent)
            } catch (e: Exception) {
                Toast.makeText(context, link, Toast.LENGTH_SHORT).show()
            }
        }
    }

    /** Reuses the same guide screen the Dashboard opens — no new screen. */
    private fun openGuide(serviceId: Int) {
        val detailFragment = ServiceDetailFragment.newInstance(
            serviceId,
            getString(R.string.chat_guide_title),
            ""
        )
        parentFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, detailFragment)
            .addToBackStack(null)
            .commit()
    }

    private fun checkInitialQuestion() {
        arguments?.getString("initial_question")?.let { question ->
            arguments?.remove("initial_question")
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