import streamlit as st
import os
import requests
import time
from collections import defaultdict
from nltk.tokenize import sent_tokenize
import PyPDF2
import docx
from googlesearch import search
import nltk
import re

@st.cache_resource
def download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('punkt_tab', quiet=True)

download_nltk_data()

def read_document(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages: text += page.extract_text() or ""
        elif uploaded_file.name.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs: text += para.text + "\n"
        elif uploaded_file.name.endswith('.txt'):
            text = uploaded_file.getvalue().decode("utf-8")
        return text
    except Exception as e:
        return f"ERROR: Could not read file. Reason: {e}"

def check_self_plagiarism(sentences):
    seen_sentences = defaultdict(list)
    duplicates = []
    for i, sentence in enumerate(sentences, 1):
        normalized_sentence = sentence.strip().lower()
        if len(normalized_sentence.split()) > 8:
            seen_sentences[normalized_sentence].append(i)
    
    for sentence, lines in seen_sentences.items():
        if len(lines) > 1:
            original_sentence = next((s for s in sentences if s.strip().lower() == sentence), sentence)
            duplicates.append({"sentence": original_sentence, "lines": lines})
    return duplicates

def check_sentence_academic(sentence):
    try:
        api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {'query': f'"{sentence}"', 'fields': 'title,authors,url', 'limit': 1}
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
        if results.get('total', 0) > 0 and results.get('data'):
            paper = results['data'][0]
            authors = ", ".join([author['name'] for author in paper.get('authors', [])])
            return {"title": paper['title'], "authors": authors, "url": paper['url']}
        return None
    except requests.RequestException:
        return None

def check_sentence_web(sentence):
    try:
        query = f'"{sentence}"'
        time.sleep(2)
        search_results = list(search(query, num_results=1, lang="en"))
        if search_results: return search_results[0]
        return None
    except Exception:
        return None

def run_full_analysis(sentences):
    results = {}
    
    duplicates = check_self_plagiarism(sentences)
    for item in duplicates:
        normalized_sentence = item['sentence'].strip().lower()
        results[normalized_sentence] = {
            "type": "🚨 Self-Plagiarism",
            "source": f"Repeated {len(item['lines'])} times (lines: {', '.join(map(str, item['lines']))})",
            "sentence": item['sentence']
        }

    for line_num, sentence in enumerate(sentences, 1):
        clean_sentence = sentence.strip()
        normalized_sentence = clean_sentence.lower()

        if normalized_sentence in results or len(clean_sentence.split()) < 10:
            continue
        
        academic_match = check_sentence_academic(clean_sentence)
        if academic_match:
            results[normalized_sentence] = {
                "type": "🚨 Academic Match",
                "source": f"[{academic_match['title']}]({academic_match['url']}) by {academic_match['authors']}",
                "sentence": clean_sentence
            }
            continue
        
        web_match_url = check_sentence_web(clean_sentence)
        if web_match_url:
            results[normalized_sentence] = {
                "type": "🚨 Web Match",
                "source": web_match_url,
                "sentence": clean_sentence
            }
            
    return results

st.set_page_config(page_title="Pro Plagiarism Checker", layout="wide", initial_sidebar_state="expanded")

if 'results' not in st.session_state:
    st.session_state.results = None
if 'document_text' not in st.session_state:
    st.session_state.document_text = ""
if 'file_name' not in st.session_state:
    st.session_state.file_name = ""

with st.sidebar:
    st.title("About the Checker")
    st.info("This tool provides a comprehensive plagiarism check. Upload your document, run the analysis, and review the results highlighted directly in the text.")
    st.warning("Note: This is a tool for preliminary checks. Always consult official plagiarism services for definitive reports.")

st.title("🔬 Pro Plagiarism Checker")

uploaded_file = st.file_uploader("Upload your paper to begin", type=["pdf", "docx", "txt"])

if uploaded_file:
    if uploaded_file.name != st.session_state.file_name:
        st.session_state.results = None
        st.session_state.document_text = read_document(uploaded_file)
        st.session_state.file_name = uploaded_file.name

    if st.session_state.document_text.startswith("ERROR:"):
        st.error(st.session_state.document_text)
    else:
        if st.button("Start Comprehensive Check", type="primary", use_container_width=True):
            with st.spinner("Performing full analysis... This may take several minutes."):
                sentences = sent_tokenize(st.session_state.document_text)
                st.session_state.results = run_full_analysis(sentences)

if st.session_state.results is not None:
    st.markdown("---")
    st.header("Analysis Results")
    
    results = st.session_state.results
    if not results:
        st.balloons()
        st.success("### 🎉 Excellent! No potential plagiarism matches were found.")
    else:
        st.metric("Potential Matches Found", f"{len(results)}")
        
        st.subheader("Highlighted Document")
        st.info("Sentences with potential matches are highlighted below. Expand the text to view the source.")
        
        sentences_to_display = sent_tokenize(st.session_state.document_text)
        
        for sentence in sentences_to_display:
            clean_sentence = sentence.strip()
            normalized_sentence = clean_sentence.lower()
            
            escaped_sentence = re.sub(r'<', '&lt;', re.sub(r'>', '&gt;', sentence))

            if normalized_sentence in results:
                match_info = results[normalized_sentence]
                with st.expander(f"**{match_info['type']}** - {clean_sentence[:80]}..."):
                    st.markdown(f'<p style="background-color:#8B0000; padding: 10px; border-radius: 5px;">{escaped_sentence}</p>', unsafe_allow_html=True)
                    st.markdown(f"**Source:** {match_info['source']}")
            else:
                st.write(escaped_sentence, unsafe_allow_html=True)