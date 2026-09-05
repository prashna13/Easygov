import streamlit as st
import requests

# Page configuration for a professional look
st.set_page_config(
    page_title="EasyGov Nepal",
    page_icon="🇳🇵",
    layout="centered"
)

# Custom Styling
st.title("🇳🇵 EasyGov Nepal")
st.markdown("### AI Assistant for Government Services")
st.info("Ask about Passports, National ID, Citizenship, or Local Government rules.")

# User Input Section
user_input = st.text_input(
    "How can I help you today?", 
    placeholder="e.g., What are the requirements for a minor's passport?"
)

if st.button("Ask Bot"):
    if user_input:
        with st.spinner("🔍 Searching government documents..."):
            try:
                # Send request to FastAPI backend
                response = requests.post(
                    "http://127.0.0.1:8000/ask", 
                    json={"question": user_input}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 1. Display the Main Answer
                    st.success("Response Received:")
                    st.markdown(data["answer"])
                    
                    # 2. Display the Sources (The new part!)
                    if "sources" in data and data["sources"]:
                        st.markdown("---")
                        st.markdown("##### 📄 Sources Used:")
                        # Using a columns layout or just bullet points for sources
                        for source in data["sources"]:
                            st.caption(f"• {source}")
                    else:
                        st.warning("No specific document sources were cited for this answer.")
                        
                else:
                    st.error(f"Backend Error: {response.status_code}")
                    st.json(response.json()) # Useful for debugging

            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to the FastAPI server. Please ensure `app/main.py` is running on port 8000.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please enter a question before clicking 'Ask Bot'.")

# Footer
st.markdown("---")
st.caption("EasyGov Nepal (Experimental RAG System)")