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

st.set_page_config(page_title="Pro Plagiarism Checker", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.title("About the Checker")
    st.info(
        "This tool provides a comprehensive plagiarism check by analyzing a document through three stages:\n"
        "1.  **Self-Plagiarism**: Detects repeated sentences within the document itself.\n"
        "2.  **Academic Search**: Queries the Semantic Scholar database for matches in millions of published papers.\n"
        "3.  **Web Search**: Performs a Google search to find matches on any public website."
    )
    st.warning("Note: This is a tool for preliminary checks. Always consult official plagiarism services for definitive reports.")

st.title("🔬 Pro Plagiarism Checker")
st.write("A professional interface for detecting potential plagiarism.")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader("Upload your research paper (.pdf, .docx, or .txt)", type=["pdf", "docx", "txt"], label_visibility="collapsed")
    start_button = st.button("Start Comprehensive Check", type="primary", use_container_width=True, disabled=not uploaded_file)

with col2:
    st.markdown("#### Summary")
    total_sentences_placeholder = st.empty()
    matches_found_placeholder = st.empty()
    total_sentences_placeholder.metric("Total Sentences Analyzed", "N/A")
    matches_found_placeholder.metric("Potential Matches Found", "N/A")

st.markdown("---")

if start_button:
    with st.spinner("Reading and analyzing document... Please wait."):
        main_document_text = read_document(uploaded_file)
        if main_document_text.startswith("ERROR:"):
            st.error(main_document_text)
        else:
            sentences = sent_tokenize(main_document_text)
            total_sentences = len(sentences)
            total_sentences_placeholder.metric("Total Sentences Analyzed", str(total_sentences))
            
            matches_count = 0
            matches_found_placeholder.metric("Potential Matches Found", "0")
            
            st.subheader("Results")
            
            st.markdown("##### Stage 1: Internal Repetitions")
            duplicates = check_self_plagiarism(sentences)
            if duplicates:
                for item in duplicates:
                    matches_count += 1
                    with st.expander(f"🚨 Self-Plagiarism: Line repeated {len(item['lines'])} times"):
                        st.markdown(f"**Sentence:** \"_{item['sentence']}_\"")
                        st.markdown(f"**Found on lines:** {', '.join(map(str, item['lines']))}")
            else:
                st.success("✅ No significant internal repetitions found.")
            
            st.markdown("##### Stage 2 & 3: Academic & Web Search")
            progress_bar = st.progress(0, text="Initializing check...")
            
            for line_num, sentence in enumerate(sentences, 1):
                clean_sentence = sentence.strip()
                if len(clean_sentence.split()) < 10:
                    continue
                
                progress_bar.progress(line_num / total_sentences, text=f"Analyzing sentence {line_num}/{total_sentences}")
                
                academic_match = check_sentence_academic(clean_sentence)
                if academic_match:
                    matches_count += 1
                    with st.expander(f"🚨 Academic Match: Found on Line {line_num}"):
                        st.markdown(f"**Original Sentence:** \"_{clean_sentence}_\"")
                        st.markdown(f"**Source:** [{academic_match['title']}]({academic_match['url']}) by {academic_match['authors']}")
                    continue
                
                web_match_url = check_sentence_web(clean_sentence)
                if web_match_url:
                    matches_count += 1
                    with st.expander(f"🚨 Web Match: Found on Line {line_num}"):
                        st.markdown(f"**Original Sentence:** \"_{clean_sentence}_\"")
                        st.markdown(f"**Source:** {web_match_url}")

            progress_bar.empty()
            matches_found_placeholder.metric("Potential Matches Found", str(matches_count))
            
            if matches_count == 0:
                st.balloons()
                st.success("### 🎉 Excellent! No potential plagiarism matches were found.")