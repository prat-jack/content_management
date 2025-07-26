import streamlit as st
from analyzer import analyze_content

st.title("Enterprise Content Analysis Platform")

uploaded_file = st.file_uploader("Upload a business document", type=["txt", "pdf", "docx"])

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8")
    st.text_area("Document Content", content, height=300)

    if st.button("Analyze Content"):
        with st.spinner("Analyzing..."):
            analysis_result = analyze_content(content)
            st.subheader("Analysis Result")
            if "error" in analysis_result:
                st.error(analysis_result["error"])
            else:
                st.write("**Summary:**", analysis_result["summary"])
                st.write("**Sentiment:**", analysis_result["sentiment"])
                st.write("**Key Points:**")
                for point in analysis_result["key_points"]:
                    st.write(f"- {point}")
