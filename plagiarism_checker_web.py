# plagiarism_webapp.py

import streamlit as st
import os
import requests
import time
from collections import defaultdict
from nltk.tokenize import sent_tokenize
import PyPDF2
import docx
from googlesearch import search

# --- All the backend functions (same as before) ---

def read_document(uploaded_file):
    """Reads text from an uploaded file object."""
    text = ""
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif uploaded_file.name.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif uploaded_file.name.endswith('.txt'):
            text = uploaded_file.getvalue().decode("utf-8")
        return text
    except Exception as e:
        return f"ERROR: Could not read file. Reason: {e}"

def check_self_plagiarism(sentences):
    """Finds repeated sentences."""
    seen_sentences = defaultdict(int)
    duplicates = []
    for sentence in sentences:
        normalized_sentence = sentence.strip().lower()
        if len(normalized_sentence.split()) > 8:
            seen_sentences[normalized_sentence] += 1
    for sentence, count in seen_sentences.items():
        if count > 1:
            original_sentence = next((s for s in sentences if s.strip().lower() == sentence), sentence)
            duplicates.append({"sentence": original_sentence, "count": count})
    return duplicates

def check_sentence_academic(sentence):
    """Queries Semantic Scholar API."""
    try:
        api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {'query': f'"{sentence}"', 'fields': 'title,authors', 'limit': 1}
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
        if results.get('total', 0) > 0 and results.get('data'):
            paper = results['data'][0]
            authors = ", ".join([author['name'] for author in paper.get('authors', [])])
            return {"title": paper['title'], "authors": authors}
        return None
    except requests.RequestException:
        return None

def check_sentence_web(sentence):
    """Performs a web search."""
    try:
        query = f'"{sentence}"'
        time.sleep(2)
        search_results = list(search(query, num_results=1, lang="en"))
        if search_results:
            return search_results[0]
        return None
    except Exception:
        return None

# --- Streamlit UI ---

st.set_page_config(page_title="Ultimate Plagiarism Checker", layout="wide")
st.title("🔬 Ultimate Plagiarism Checker")
st.write("Upload your research paper (.pdf, .docx, or .txt) to check for three types of plagiarism: internal repetition, academic sources, and general web content.")

uploaded_file = st.file_uploader("Choose your research paper...", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    if st.button("Start Comprehensive Check", type="primary"):
        with st.spinner("Reading and analyzing document... This may take several minutes."):
            
            main_document_text = read_document(uploaded_file)
            if main_document_text.startswith("ERROR:"):
                st.error(main_document_text)
            else:
                sentences = sent_tokenize(main_document_text)
                st.info(f"✅ Loaded paper: **{uploaded_file.name}** ({len(sentences)} sentences found).")
                
                any_match_found = False
                
                # --- Step 1: Self-Plagiarism Check ---
                st.subheader("Stage 1: Checking for Repeated Lines (Self-Plagiarism)")
                with st.spinner("Scanning for internal repetitions..."):
                    duplicates = check_self_plagiarism(sentences)
                if duplicates:
                    any_match_found = True
                    for item in duplicates:
                        st.warning(f"Repeated Line: \"{item['sentence']}\" (Found {item['count']} times)")
                else:
                    st.success("No significant internal repetitions found.")

                # --- Step 2 & 3: External Checks ---
                st.subheader("Stage 2 & 3: Checking Academic Databases & Web")
                progress_bar = st.progress(0, text="Checking sentences...")
                
                results_placeholder = st.container()

                for i, sentence in enumerate(sentences):
                    clean_sentence = sentence.strip()
                    if len(clean_sentence.split()) < 10:
                        continue
                    
                    # Update progress
                    progress_text = f"Checking sentence {i+1}/{len(sentences)}"
                    progress_bar.progress((i + 1) / len(sentences), text=progress_text)
                    
                    # Academic Check
                    academic_match = check_sentence_academic(clean_sentence)
                    if academic_match:
                        any_match_found = True
                        with results_placeholder.container():
                            st.error("Academic Paper Match Found!")
                            st.markdown(f"**Line:** \"_{clean_sentence}_\"")
                            st.markdown(f"**Source:** '{academic_match['title']}' by {academic_match['authors']}")
                        continue
                    
                    # Web Check
                    web_match_url = check_sentence_web(clean_sentence)
                    if web_match_url:
                        any_match_found = True
                        with results_placeholder.container():
                            st.error("Web Match Found!")
                            st.markdown(f"**Line:** \"_{clean_sentence}_\"")
                            st.markdown(f"**Source:** {web_match_url}")

                progress_bar.empty()
                st.header("🏁 Check Complete")
                if not any_match_found:
                    st.balloons()
                    st.success("Excellent! No significant plagiarism matches were found.")