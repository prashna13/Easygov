package com.example.easygov

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment

class ServiceDetailFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_service_detail, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val title = arguments?.getString("service_title") ?: "Service Details"
        val category = arguments?.getString("service_category") ?: "General"
        val description = arguments?.getString("service_description") ?: ""

        view.findViewById<TextView>(R.id.tvDetailTitle).text = title
        view.findViewById<TextView>(R.id.tvDetailCategory).text = category
        if (description.isNotEmpty()) {
            view.findViewById<TextView>(R.id.tvDetailDescription).text = description
        }
    }

    companion object {
        fun newInstance(title: String, category: String, description: String): ServiceDetailFragment {
            val fragment = ServiceDetailFragment()
            val args = Bundle().apply {
                putString("service_title", title)
                putString("service_category", category)
                putString("service_description", description)
            }
            fragment.arguments = args
            return fragment
        }
    }
}
