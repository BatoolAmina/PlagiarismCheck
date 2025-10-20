import streamlit as st
import os
import requests
import time
from collections import defaultdict
from nltk.tokenize import sent_tokenize, word_tokenize
import PyPDF2
import docx
from googlesearch import search
import nltk
from datetime import datetime

@st.cache_resource
def download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)

download_nltk_data()

def read_document(uploaded_file):
    """Reads text from uploaded .pdf, .docx, or .txt file."""
    text = ""
    try:
        uploaded_file.seek(0)
        file_name = uploaded_file.name
        if file_name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages: text += (page.extract_text() or "") + "\n"
        elif file_name.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs: text += para.text + "\n"
        elif file_name.endswith('.txt'):
            text = uploaded_file.getvalue().decode("utf-8")
        return text
    except Exception as e:
        st.error(f"ERROR: Could not read file. Reason: {e}")
        return None

def check_self_plagiarism(sentences):
    """Checks for duplicate sentences within the same document."""
    seen_sentences = defaultdict(list)
    duplicates = []
    for i, sentence in enumerate(sentences, 1):
        normalized_sentence = sentence.strip().lower()
        if len(normalized_sentence.split()) > 8:
            seen_sentences[normalized_sentence].append(i)
    
    for sentence_key, lines in seen_sentences.items():
        if len(lines) > 1:
            original_sentence = next((s for s in sentences if s.strip().lower() == sentence_key), sentence_key)
            duplicates.append({
                "sentence": original_sentence, "lines": lines, "type": "Self-Plagiarism",
                "source": f"Repeated {len(lines)} times in the document."
            })
    return duplicates

def check_sentence_academic(sentence):
    """Queries Semantic Scholar API to find matches in academic papers."""
    try:
        query = f'"{sentence}"'
        api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {'query': query, 'fields': 'title,authors,url', 'limit': 1}
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
    """Performs a Google search to find web matches."""
    try:
        query = f'"{sentence}"'
        time.sleep(2)
        search_results = list(search(query, num_results=1, lang="en"))
        if search_results: return search_results[0]
        return None
    except Exception:
        return None

def generate_highlighted_text(sentences, matches):
    """Generates an HTML string with plagiarized sentences highlighted."""
    plagiarized_sentences = {match['sentence'].strip() for match in matches}
    highlighted_parts = []
    for sentence in sentences:
        clean_sentence = sentence.strip()
        if clean_sentence in plagiarized_sentences:
            highlighted_parts.append(f"<span style='background-color: #ffcccb; padding: 2px 4px; border-radius: 3px;'>{sentence}</span>")
        else:
            highlighted_parts.append(sentence)
    return " ".join(highlighted_parts)

def generate_report_content(matches, summary_stats):
    """Generates a downloadable text report of the findings."""
    report = ["--- Plagiarism Check Report ---", f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
              "\n--- Summary ---"]
    for key, value in summary_stats.items():
        report.append(f"{key}: {value}")
    report.append("\n--- Detailed Findings ---")
    if not matches:
        report.append("No potential plagiarism matches were found.")
    else:
        for i, match in enumerate(matches, 1):
            report.append(f"\nMatch #{i}")
            report.append(f"  Sentence: \"{match['sentence']}\"")
            report.append(f"  Type: {match['type']}")
            if match['type'] == "Self-Plagiarism":
                report.append(f"  Found on lines: {', '.join(map(str, match['lines']))}")
            else:
                report.append(f"  Found on line: {match['line_num']}")
            if 'source_details' in match:
                if match['type'] == "Academic Match":
                    report.append(f"  Source: [{match['source_details']['title']}]({match['source_details']['url']})")
                    report.append(f"  Authors: {match['source_details']['authors']}")
                elif match['type'] == "Web Match":
                    report.append(f"  Source: {match['source_details']}")
    return "\n".join(report)

st.set_page_config(page_title="Pro Plagiarism Checker", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.title("About the Checker")
    st.info(
        "This tool provides a comprehensive plagiarism check by analyzing a document through three stages:\n"
        "1.  **Self-Plagiarism**: Detects repeated sentences within the document itself.\n"
        "2.  **Academic Search**: Queries Semantic Scholar for academic matches.\n"
        "3.  **Web Search**: Performs a Google search for matches on public websites."
    )
    st.warning("Note: This is a tool for preliminary checks. Always consult official plagiarism services for definitive reports.")

st.title("🔬 Pro Plagiarism Checker")
st.write("Upload your document, and the tool will analyze its originality against web and academic sources.")

with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload your document (.pdf, .docx, or .txt)", type=["pdf", "docx", "txt"])
        start_button = st.button("Start Comprehensive Check", type="primary", use_container_width=True, disabled=not uploaded_file)
    
    with col2:
        st.markdown("#### Analysis Summary")
        total_sentences_ph = st.metric("Total Sentences", "N/A")
        total_words_ph = st.metric("Total Words", "N/A")
        matches_found_ph = st.metric("Matches Found", "N/A")
        similarity_ph = st.metric("Similarity", "N/A")
        originality_ph = st.metric("Originality", "N/A")

st.markdown("---")

if start_button and uploaded_file:
    with st.spinner("Reading and analyzing document... This may take a few moments."):
        document_text = read_document(uploaded_file)
        if document_text:
            sentences = sent_tokenize(document_text)
            words = word_tokenize(document_text)
            total_sentences = len(sentences)
            total_words = len(words)
            all_matches = []
            all_matches.extend(check_self_plagiarism(sentences))
            
            progress_bar = st.progress(0, text="Initializing check...")
            matched_sentences_for_external_check = set()
            
            for line_num, sentence in enumerate(sentences, 1):
                clean_sentence = sentence.strip()
                if len(clean_sentence.split()) < 10 or clean_sentence in matched_sentences_for_external_check:
                    continue
                
                progress_bar.progress(line_num / total_sentences, text=f"Analyzing sentence {line_num}/{total_sentences}")
                
                academic_match = check_sentence_academic(clean_sentence)
                if academic_match:
                    all_matches.append({
                        "sentence": clean_sentence, "line_num": line_num, "type": "Academic Match",
                        "source_details": academic_match
                    })
                    matched_sentences_for_external_check.add(clean_sentence)
                    continue

                web_match_url = check_sentence_web(clean_sentence)
                if web_match_url:
                    all_matches.append({
                        "sentence": clean_sentence, "line_num": line_num, "type": "Web Match",
                        "source_details": web_match_url
                    })
                    matched_sentences_for_external_check.add(clean_sentence)

            progress_bar.empty()

            matches_count = len(all_matches)
            similarity_percentage = (matches_count / total_sentences * 100) if total_sentences > 0 else 0
            originality_percentage = 100 - similarity_percentage
            
            total_sentences_ph.metric("Total Sentences", f"{total_sentences}")
            total_words_ph.metric("Total Words", f"{total_words}")
            matches_found_ph.metric("Matches Found", f"{matches_count}")
            similarity_ph.metric("Similarity", f"{similarity_percentage:.2f}%")
            originality_ph.metric("Originality", f"{originality_percentage:.2f}%")
            
            st.subheader("Results")
            
            if matches_count == 0:
                st.balloons()
                st.success("### 🎉 Excellent! No potential plagiarism matches were found.")
            else:
                tab1, tab2, tab3 = st.tabs(["📊 Highlights", "🔍 Detailed Findings", "📥 Download Report"])

                with tab1:
                    st.info("Sentences flagged for potential plagiarism are highlighted below.")
                    highlighted_doc = generate_highlighted_text(sentences, all_matches)
                    st.markdown(f"<div style='border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9; max-height: 400px; overflow-y: auto;'>{highlighted_doc}</div>", unsafe_allow_html=True)

                with tab2:
                    st.info("Click on each finding to expand and see more details.")
                    for match in all_matches:
                        if match['type'] == "Self-Plagiarism":
                            with st.expander(f"🚨 **Self-Plagiarism**: Sentence repeated {len(match['lines'])} times"):
                                st.markdown(f"**Sentence:** \"_{match['sentence']}_\"")
                                st.markdown(f"**Found on lines:** {', '.join(map(str, match['lines']))}")
                        else:
                            with st.expander(f"🚨 **{match['type']}**: Match on line {match['line_num']}"):
                                st.markdown(f"**Original Sentence:** \"_{match['sentence']}_\"")
                                if match['type'] == 'Academic Match':
                                    st.markdown(f"**Source:** [{match['source_details']['title']}]({match['source_details']['url']})")
                                    st.markdown(f"**Authors:** {match['source_details']['authors']}")
                                elif match['type'] == 'Web Match':
                                    st.markdown(f"**Source:** [{match['source_details']}]({match['source_details']})")
                
                with tab3:
                    st.info("Download a full text report of all findings for your records.")
                    summary_stats = {
                        "Total Sentences": total_sentences, "Total Words": total_words, "Matches Found": matches_count,
                        "Similarity": f"{similarity_percentage:.2f}%", "Originality": f"{originality_percentage:.2f}%"
                    }
                    report_data = generate_report_content(all_matches, summary_stats)
                    st.download_button(
                        label="📥 Download Full Report (.txt)", data=report_data, file_name="plagiarism_report.txt",
                        mime="text/plain", use_container_width=True
                    )