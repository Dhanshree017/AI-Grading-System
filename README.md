# GIBO: Grade & Guide with GIBO
### *An Automated AI-Driven Evaluation System with Personalized Lessons*

GIBO (**Grading Intelligence for Behavioral Optimization**) is an end-to-end, multi-model evaluation and feedback system engineered for descriptive theory examinations in Machine Learning. Unlike conventional auto-graders that rely on shallow keyword matching, GIBO enforces strict institutional examination rules (section attempt limits, length compliance, and mark-mapping policies) while providing explainable grading and targeted micro-lessons directly to students.

---

## Key Highlights & Performance Metrics

* **Evaluation Accuracy**: Achieved **86.22% overall grading accuracy** against human evaluator baselines across complex descriptive answers.
* **Custom Dataset Engineering**: Built a proprietary dataset over **6 months** containing **~1,030 answer sheets** (~30 student sheets per Question Paper template) and over **12,000 Question-Answer pairs**.
* **High-Throughput Batch Processing**: Enables batch evaluations of **50+ student answer sheets** per grading session against a single question paper template.
* **Explainable AI Diagnostics**: Powered by **Gemini 1.5 Flash**, delivering Tri-Level Diagnostics (personalized feedback, missing concept identification, and tailored mini-lessons).
* **Automated Delivery Pipeline**: Compiles diagnostic reports and delivers itemized results directly to student email inboxes.

---

## Core System Architecture

GIBO operates across a 7-stage pipeline that bridges raw text extraction, deep semantic comparison, regressive score prediction, and LLM-driven feedback generation:

![System Architecture](Image/System%20Architecture.png)
*Figure 1: High-level 7-module block diagram illustrating the GIBO processing pipeline.*

### Pipeline Breakdown:
1. **Question Paper Configuration and Parsing**: Parses complex multi-section question paper templates, extracting attempt constraints, mark allocations, and question definitions.
2. **Student Registration and Answer Sheet Management**: Digitizes, cleans, and indexes student response files against metadata schemas.
3. **Question–Answer Structuring and Rule Mapping**: Enforces institutional rules (e.g., "Attempt any 4 of 5") and dynamically computes maximum allowable marks per section.
4. **AI-Based Feature Extraction**: Embeds student responses and compares them against ideal candidate answers using **MiniLM** and **DeBERTa-v3** to extract semantic, logical, and structural features.
5. **Rule-Constrained Marks Allocation**: Uses an **XGBoost Regressor** to predict scores based on weighted semantic similarity, logical coherence, and strict length compliance heuristics.
6. **Feedback and Lesson Generation**: Leverages **Gemini 1.5 Flash** to analyze answer gaps and construct targeted mini-lessons for skipped or sub-optimal responses.
7. **Result Compilation and Delivery**: Automatically aggregates section scores, grade distributions, and feedback into direct student email reports and faculty dashboards.

---

## Machine Learning & Feature Engineering Pipeline

### Multi-Model Feature Extraction
To capture deep answer semantics rather than simple syntax, GIBO calculates three primary feature dimensions:

* **Semantic Similarity (Weight: 0.5)**: Powered by **DeBERTa-v3** to capture contextual and deep semantic alignment against ideal responses.
* **Logic & Structure (Weight: 0.4)**: Powered by **MiniLM** to evaluate concept flow, domain terminology consistency, and argument structure.
* **Length Compliance (Weight: 0.1)**: Strictly enforces target word count boundaries calibrated by question weightage:
  * **2 Marks**: 60–70 words
  * **5 Marks**: 120–130 words
  * **8 Marks**: 140–150 words
  * **10 Marks**: 170–200 words

### Marks Prediction Engine
Extracted feature vectors (Semantic, Logic, and Length Compliance scores) are passed into an **XGBoost Regressor** trained on 12,000+ human-graded question-answer pairs. The model outputs precise scores while adhering strictly to rule-constrained upper limits dictated by section-level attempt policies.

---

## Custom Dataset Engineering

Due to the lack of publicly available descriptive answer datasets for specialized engineering curricula, a proprietary benchmark dataset was systematically built over a 6-month development cycle:

* **Answer Sheets Processed**: ~1,030 full-length student answer sheets.
* **Question-Answer Pairs**: 12,000+ individually annotated responses.
* **Exam Templates**: Multiple distinct question paper structures covering core Machine Learning concepts (Supervised/Unsupervised Learning, Neural Networks, Optimization, Regularization, and Evaluation Metrics).
* **Ground Truth Annotation**: Each response was dual-graded by domain experts across correctness, logical structure, and clarity.

---

## Technical Stack

* **Machine Learning & NLP**: XGBoost, DeBERTa-v3, Sentence-Transformers (MiniLM), PyTorch, Scikit-learn
* **Large Language Models**: Gemini 1.5 Flash (Prompt Engineering, Tri-Level Remedial Generation)
* **Data Processing & Backend**: Python 3.10+, Pandas, NumPy, SQL
* **Notification Engine**: SMTP Email Service Engine

---

## System UI & Workflow Walkthrough

### 1. Home Page & Portal Interface
The primary landing portal establishing core value propositions, system features, and authentication entry points for faculty and administrative users.

![Home Page](Image/Home%20Page.png)
*Figure 2: GIBO landing platform and portal navigation.*

---

### 2. Administrative Control Panel
Granular user access management workflow allowing administrators to review, approve, or reject user registration requests.

![Admin Management Panel](Image/login_control_admin_panel.png)
*Figure 3: Administrative portal for security controls and pending user approvals.*

---

### 3. Question Paper Configuration & Metadata Parsing
Instructors set up examination parameters, section-wise rules, per-question mark distributions, and custom attempt conditions.

![Question Paper Metadata Form](Image/QP%20metadata%20form.png)
*Figure 4: Form-based Question Paper configuration and metadata parsing module.*

![Question Paper Template](Image/question_paper_template.png)
*Figure 5: Sample structured question paper template schema.*

![Question Paper Document](Image/question_paper.png)
*Figure 6: Digitized examination question paper layout.*

---

### 4. High-Throughput Batch Ingestion & Answer Sheet Processing
Faculty members execute bulk evaluation sessions by loading question templates alongside student text response files.

![Uploading QP and Answer Sheets](Image/Uploading%20QP%20and%20Answer%20sheets.png)
*Figure 7: Batch upload interface for exam templates and student answer sheets.*

![Student Answer Sheet Processing](Image/answer_sheet_demo.png)
*Figure 8: Digitized student answer record indexed by metadata and parsed into Q&A blocks.*

---

### 5. Academic Controls & Student Attempt Auditing
The system maps individual student answers against institutional attempt constraints, auto-marking skipped questions while computing section score breakdowns.

![Faculty Insights & Academic Control](Image/Academic%20Insights.png)
*Figure 9: Academic control portal featuring student search and template selection.*

![Student Attempt Report](Image/Student_Attempt_report.png)
*Figure 10: Itemized student attempt report and raw score mapping.*

---

### 6. AI Evaluation Metrics & Diagnostic Explanation
Comprehensive score breakdown revealing model reasoning across Semantic Accuracy, Logical Consistency, and Structural Compliance.

![AI Explanation Behind Marks Report](Image/AI%20Explanation%20behind%20marks%20report.png)
*Figure 11: Multi-metric model evaluation breakdown per question response.*

---

### 7. Automated Remedial Mini-Lessons & Feedback Generation
Generative AI module using Gemini 1.5 Flash to highlight missed key concepts, deliver question-level feedback, and produce customized micro-lessons.

![GIBO Feedback and Correction](Image/GIBO's%20Feedback%20and%20Correction.png)
*Figure 12: Automated feedback generation and correction interface.*

![GIBO Teaching Missing Concepts](Image/GIBO%20teaching%20missing%20concept%20and%20feedback.png)
*Figure 13: Targeted micro-lessons generated for student conceptual gaps.*

---

### 8. Pedagogical Analytics & Automated Result Delivery
Cohort performance reports map overall score distributions, while itemized diagnostic feedback is delivered straight to student email inboxes.

![Performance Analytics](Image/stud_performance_analysis.png)
*Figure 14: Cohort performance dashboard and grade distribution analytics.*

![Skipped Questions Analytics](Image/mostly_skipped_Questions.png)
*Figure 15: Aggregate analytics tracking class-wide skipped question metrics.*

![Skipped Questions Breakdown](Image/skipped_questions_by_student.png)
*Figure 16: Detailed itemized list of frequently skipped questions.*

![Email Received by Student](Image/Email_Received_by_student.png)
*Figure 17: Sample email report received by a student containing final grades and remedial lessons.*

---

## Getting Started & Setup Guide

### 1. Prerequisites
* **Python 3.10** installed on your system.
* **CUDA-compatible GPU** (Recommended for accelerated DeBERTa-v3 and MiniLM inference).
* Accounts for **Google AI Studio** (Gemini API), **Hugging Face**, and an **Email Provider** (e.g., Gmail).

---

### 2. Service Credentials Setup

#### A. Generating Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on **Get API Key** and generate a new API key.
4. Copy the generated key for your environment variables.

#### B. Generating Hugging Face Token
1. Go to [Hugging Face](https://huggingface.co/) and log in.
2. Navigate to **Settings** -> **Access Tokens**.
3. Click **New Token**, set the role to `Read`, name it (e.g., `GIBO_Model_Access`), and click **Generate**.
4. Copy your token string.

#### C. Setting Up Gmail App Passwords (Sender Email)
To send automated result reports to students, configure a Gmail App Password:
1. Go to your [Google Account Security Settings](https://myaccount.google.com/security).
2. Enable **2-Step Verification** if it is not already enabled.
3. Search for **App Passwords** in the security settings search bar.
4. Enter an app name (e.g., `GIBO System`) and click **Create**.
5. Copy the 16-character generated passkey (without spaces).

---

### 3. Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone [https://github.com/your-username/GIBO-Grading-System.git](https://github.com/your-username/GIBO-Grading-System.git)
   cd GIBO-Grading-System
