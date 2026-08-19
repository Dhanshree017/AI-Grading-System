# GIBO: Grade & Guide with GIBO
### *An Automated AI-Driven Evaluation System with Personalized Remedial Micro-Lessons*

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

<div align="center">
  <img src="Images/System%20Architecture.png" alt="System Architecture" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 1: High-level 7-module block diagram illustrating the GIBO processing pipeline.</em></p>
</div>

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

## System UI & Step-by-Step Workflow Walkthrough

### 1. Home Page & Portal Entry
The landing interface establishing core value propositions, system capabilities, and navigation portals for both teachers and administrative personnel.

<div align="center">
  <img src="Images/Home%20Page.png" alt="Home Page" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 2: GIBO primary landing platform and navigation entry point.</em></p>
</div>

---

### 2. User Authentication & Administrative Approvals
Teachers register or log in via the dedicated portal, while administrators review, manage, and grant access through a secure control panel.

<div align="center">
  <img src="Images/teacher_login.png" alt="Teacher Registration Portal" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 3: Teacher Portal registration and authentication entry point.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/login_control_admin_panel.png" alt="Admin Control Panel" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 4: Administrative portal for reviewing access requests and user controls.</em></p>
</div>

---

### 3. Faculty Dashboard & Academic Records
Upon successful login, teachers enter the main dashboard where they can select a Question Paper template to view enrolled students, past submission records, and historical academic performances.

<div align="center">
  <img src="Images/Academic%20Insights.png" alt="Academic Insights Dashboard" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 5: Academic Insights dashboard showing student records and question paper selection.</em></p>
</div>

---

### 4. Question Paper Structure & Schema Demo
Instructors can inspect the reference Question Paper, its digitized schema, and the underlying section rules before evaluating submissions.

<div align="center">
  <img src="Images/question_paper.png" alt="Question Paper Document" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 6: Digitized examination question paper view.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/question_paper_template.png" alt="Question Paper Template Schema" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 7: Structured Question Paper template mapping rules and mark weightages.</em></p>
</div>

---

### 5. Initiating New Ingestion & Automated Processing
To evaluate new submissions, the instructor clicks the **"Grade New Student"** button, uploads the Question Paper along with student answer files, configures metadata, and triggers the automated pipeline.

<div align="center">
  <img src="Images/Uploading%20QP%20and%20Answer%20sheets.png" alt="Uploading Question Paper and Answer Sheets" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 8: Batch upload panel for question templates and student answer sheets.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/QP%20metadata%20form.png" alt="Question Paper Metadata Configuration" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 9: Form-based metadata configuration for section attempt rules and score constraints.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/answer_sheet_demo.png" alt="Student Answer Sheet Processing" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 10: Processed and indexed student answer sheet ready for automated evaluation.</em></p>
</div>

---

### 6. Automated Scoring, Attempt Auditing & AI Diagnostics
The system automatically checks responses, enforces attempt constraints, and generates multi-metric explanations across Logic Consistency, Semantic Accuracy, and Word Compliance.

<div align="center">
  <img src="Images/Student_Attempt_report.png" alt="Student Attempt Audit Report" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 11: Itemized student attempt report and section-wise raw score mapping.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/score_bars.png" alt="Intelligence Metric Score Bars" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 12: Visual breakdown of Logic Consistency, Semantic Accuracy, and Compliance per question for lower-performing responses.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/AI_Explanation_Behind_Marks.png" alt="AI Explanation Behind Marks" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 13: Explainable AI diagnostic panel illustrating score deductions and accuracy metrics for well-performing responses.</em></p>
</div>

---

### 7. AI Remedial Micro-Lessons & Personalized Tutoring
For missing concepts or low-scoring answers, GIBO leverages Gemini 1.5 Flash to automatically generate custom feedback, corrections, and tailored remedial lessons.

<div align="center">
  <img src="Images/GIBO's%20Feedback%20and%20Correction.png" alt="GIBO Feedback and Corrections" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 14: Automated evaluation feedback and immediate correction hints.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/GIBO%20teaching%20missing%20concept%20and%20feedback.png" alt="GIBO Remedial Micro-Lesson" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 15: AI-generated micro-lesson teaching missing concepts directly to the student.</em></p>
</div>

---

### 8. Pedagogical Analytics & Direct Email Delivery
Instructors monitor cohort-level performance metrics and track frequently skipped questions, while complete diagnostic score cards and micro-lessons are automatically emailed to each student.

<div align="center">
  <img src="Images/stud_performance_analysis.png" alt="Cohort Performance Analytics" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 16: Class grade distribution analytics and overall performance breakdown.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/mostly_skipped_Questions.png" alt="Aggregate Skipped Questions Overview" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 17: Cohort-level aggregate analytics highlighting frequently skipped topics.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/skipped_questions_by_student.png" alt="Skipped Questions Breakdown" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 18: Detailed per-student breakdown of unattempted or skipped questions.</em></p>
</div>

<br />

<div align="center">
  <img src="Images/Email_Received_by_student.png" alt="Automated Email Delivered to Student" style="border: 3px solid black; padding: 4px;" />
  <p><em>Figure 19: Diagnostic evaluation report delivered directly to a student's inbox via email.</em></p>
</div>

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
   git clone [https://github.com/Dhanshree017/AI-Grading-System.git](https://github.com/Dhanshree017/AI-Grading-System.git)
   cd AI-Grading-System
