# Pro Plagiarism Checker

A Streamlit web application to detect potential plagiarism in documents by checking against internal, academic, and web sources.

---
## Key Features

* **Multi-Format Upload**: Supports uploading `.pdf`, `.docx`, and `.txt` files.
* **Three-Stage Analysis**: Checks for self-plagiarism, academic sources, and web matches.
* **Interactive Dashboard**: Displays metrics like similarity percentage and originality.
* **Tabbed Results**: Organizes findings into "Highlights," "Detailed Findings," and "Download Report" tabs.
* **Highlighted Text**: Shows the full document with potential matches highlighted.
* **Downloadable Reports**: Generates a `.txt` file summarizing the findings.

---
## Setup & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Dependencies
```bash
streamlit run plagiarism_webapp.py
```

### 2.Run the app
```bash
streamlit run plagiarism_checker_web.py
```

---
## Setup & Run

**Upload a File:** Use the file uploader to select a document.
**Start Analysis:** Click the "Start Comprehensive Check" button.
**View Results:** Explore the summary and result tabs.
**Download:** Go to the "Download Report" tab to save the analysis.
