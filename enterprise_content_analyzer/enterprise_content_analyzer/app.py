
import streamlit as st
from content_analyzer import ContentAnalyzer

# Initialize the ContentAnalyzer
analyzer = ContentAnalyzer()

# Streamlit App
st.set_page_config(layout="wide")

st.title("Enterprise Content Analysis Platform")

st.write("Paste your business document into the text area below and click 'Analyze' to get a detailed analysis.")

content_input = st.text_area("Enter your content here", height=300)

if st.button("Analyze"):
    if content_input:
        with st.spinner("Analyzing..."):
            analysis_result = analyzer.analyze_content(content_input)
            
            st.subheader("Analysis Results")
            
            col1, col2 = st.columns([3, 1])

            with col1:
                if "error" in analysis_result:
                    st.error(analysis_result["error"])
                else:
                    st.markdown(f"**Summary:** {analysis_result['summary']}")
                    st.markdown(f"**Sentiment:** {analysis_result['sentiment']}")
                    st.markdown("**Key Points:**")
                    for point in analysis_result['key_points']:
                        st.markdown(f"- {point}")

            with col2:
                st.info("API Cost Estimate")
                st.write("Cost per analysis: $0.05")

    else:
        st.warning("Please enter some content to analyze.")
