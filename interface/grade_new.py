import os
import sys
import json
import re
import csv
import pandas as pd
import subprocess
import streamlit as st
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import train_test_split
import numpy as np

df = pd.read_csv("dataset.csv")

# Define Features and Target
# We use semantic, logic, and a ratio of length (actual/target)
df['length_ratio'] = df['actual_word_count'] / df['total_word_count']
X = df[['logic_score', 'semantic_score', 'length_ratio']]
y = df['human_score'] / df['max_marks'] # Target is percentage (0.0 to 1.0)

# Split: 70% Train, 30% for Val/Test
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
# Split the 30% into half Validation and half Testing
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

# Train XGBoost
model = xgb.XGBRegressor(
    n_estimators=1000,
    learning_rate=0.05,
    max_depth=5,
    early_stopping_rounds=50
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)

# Save the brain
model.save_model("grading_model.json")
print("✅ Model Trained and Saved as grading_model.json")
# =====================================================
# PATH CONFIG
# =====================================================
BASE_PATH = r"C:\AI_Grading_System"
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# 🟢 Define paths for OCR storage (No deletion logic added)
OCR_TEMPLATES_DIR = os.path.join(BASE_PATH, "dataset", "ocr_output", "templates")
OCR_ANSWERS_DIR = os.path.join(BASE_PATH, "dataset", "ocr_output", "answers")

# Ensure these directories exist
os.makedirs(OCR_TEMPLATES_DIR, exist_ok=True)
os.makedirs(OCR_ANSWERS_DIR, exist_ok=True)

# Import database tools
try:
    from database.database import sync_data
except ImportError:
    def sync_data(): 
        pass 

METADATA_CSV = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "template_metadata.csv")
STUDENT_CSV = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "students_details.csv")
RUBRIC_JSON = os.path.join(BASE_PATH, "grading_engine", "rubric.json")
MATCHED_JSON = os.path.join(BASE_PATH, "grading_engine", "matched_answers.json")
STAGE1_FEATURES = os.path.join(BASE_PATH, "grading_engine", "stage1_features.json")
FINAL_REPORT = os.path.join(BASE_PATH, "grading_engine", "stage2_marks_allocation.json")

os.makedirs(os.path.dirname(METADATA_CSV), exist_ok=True)
os.makedirs(os.path.dirname(RUBRIC_JSON), exist_ok=True)

# =====================================================
# ROBUST EXTRACTION PATTERNS
# =====================================================
NAME_LINE_RE = re.compile(r"name\s*[:\-]\s*(.*)", re.I)
ROLL_RE = re.compile(r"roll\s*no\s*[:\-]?\s*(\d+)", re.I)
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+")
CLASS_RE = re.compile(r"(?:class|grade|year|dept|div)\s*[:\-]\s*([A-Za-z0-9\- ]+)", re.I)

def clean_name_robust(raw_line):
    if not raw_line: return "Unknown"
    stop_words = ["roll", "no", "class", "grade", "email", "year", "div"]
    cleaned = raw_line
    for word in stop_words:
        match = re.search(rf"\b{word}\b", cleaned, re.IGNORECASE)
        if match:
            cleaned = cleaned[:match.start()]
    cleaned = re.sub(r"[^A-Za-z\s\.]", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned if len(cleaned) > 2 else "Unknown"

def extract_student_info_robust(text, tid, filename, ui_class):
    ans_id = os.path.splitext(filename)[0]
    m_roll = re.search(r"_(\d+)$", ans_id)
    roll_from_fname = m_roll.group(1) if m_roll else "00"

    name = "Unknown"
    nm_match = NAME_LINE_RE.search(text)
    if nm_match:
        name = clean_name_robust(nm_match.group(1))

    rm = ROLL_RE.search(text)
    roll = rm.group(1) if rm else roll_from_fname

    em = EMAIL_RE.search(text)
    email = em.group(0) if em else "Not Found"

    cm = CLASS_RE.search(text)
    student_class = cm.group(1).strip() if cm else ui_class

    return {
        "ans_id": ans_id,
        "template_id": tid,
        "roll_no": roll.zfill(2),
        "name": name,
        "email": email,
        "class": student_class
    }

def safe_read(file_obj):
    raw_data = file_obj.read()
    try:
        return raw_data.decode("utf-8")
    except:
        return raw_data.decode("latin-1")

def parse_rules(rule_str, section_counts):
    rules = {}
    if pd.isna(rule_str) or not rule_str: return rules
    parts = rule_str.split('|')
    for p in parts:
        p = p.strip()
        match_sec = re.search(r"([A-Z])", p, re.I)
        if match_sec:
            sec_letter = match_sec.group(1).upper()
            if "all" in p.lower():
                rules[sec_letter] = section_counts.get(sec_letter, 0)
            else:
                match_num = re.search(r"any\s*(\d+)", p, re.I)
                if match_num:
                    rules[sec_letter] = int(match_num.group(1))
    return rules

def clean_repeated_question(question, answer):
    if answer == "SKIPPED/NOT_FOUND" or len(answer) < 10: return answer
    q_words = question.strip().split()
    if len(q_words) < 3: return answer
    tail_anchor = " ".join(q_words[-3:]).lower().strip(".:?")
    anchor_pattern = re.escape(tail_anchor).replace(r"\ ", r"\s+")
    match = re.search(anchor_pattern, answer[:500], re.IGNORECASE | re.DOTALL)
    if match:
        cleaned = answer[match.end():].strip()
        cleaned = re.sub(r"^[ \.\)\-\:\n\r\=\/]+", "", cleaned)
        return cleaned if cleaned else "CONTENT_STRIPPED_EMPTY"
    return answer

# =====================================================
# CORE LOGIC
# =====================================================

def internal_generate_rubric(template_text, tid, per_q_mark_rule):
    SECTION_RE = re.compile(r"^([A-Z]|\d)[\s\)\.\-\]—|]*(?:Attemp|Answer|All|Section|Any|Question|carry|each)", re.I)
    Q_START_RE = re.compile(r"^((?:Q)?\d+|[a-j]|i)[\s\)\.\-\]—|]+", re.I)
    lines = template_text.split('\n')
    tid_questions = []
    current_sec = "A"
    for line in lines:
        line = line.strip()
        if not line: continue
        sec_match = SECTION_RE.match(line)
        if sec_match: 
            current_sec = sec_match.group(1).upper()
            continue
        q_match = Q_START_RE.match(line)
        if q_match:
            raw_qid = re.sub(r'^[Qq]', '', q_match.group(1))
            qid = f"{current_sec}-{raw_qid}"
            mark_val = 5.0
            if per_q_mark_rule:
                for p in re.split(r'[,;]', per_q_mark_rule):
                    if ':' in p:
                        s, v = p.split(':')
                        if s.strip().upper() == current_sec:
                            m = re.findall(r"\d+", v)
                            if m: mark_val = float(m[0])
            tid_questions.append({"qid": qid, "section": current_sec, "text": line, "max_marks": mark_val})
        elif tid_questions: tid_questions[-1]["text"] += " " + line
    
    all_rubrics = {}
    if os.path.exists(RUBRIC_JSON):
        try:
            with open(RUBRIC_JSON, "r", encoding="utf-8") as f: all_rubrics = json.load(f)
        except: pass
    all_rubrics[tid] = tid_questions
    with open(RUBRIC_JSON, "w", encoding="utf-8") as f: json.dump(all_rubrics, f, indent=2)

def internal_align_answers(answer_files_dict, tid, attempt_rule, ui_class):
    with open(RUBRIC_JSON, "r", encoding="utf-8") as f: rubric = json.load(f)
    template_rubric = rubric.get(tid, [])
    final_output = {}
    if os.path.exists(MATCHED_JSON):
        try:
            with open(MATCHED_JSON, "r", encoding="utf-8") as f: final_output = json.load(f)
        except: pass

    all_qids = [q['qid'] for q in template_rubric]
    new_student_ids = []
    student_details_list = []

    for fname, content in answer_files_dict.items():
        s_info = extract_student_info_robust(content, tid, fname, ui_class)
        s_id = s_info['ans_id']
        new_student_ids.append(s_id)
        student_details_list.append(s_info)

        student_record = {"student_id": s_id, "student_info": {**s_info, "attempt_rule": attempt_rule}, "rubric_with_answers": []}
        for rq in template_rubric:
            other_qids = [re.escape(q) for q in all_qids if q != rq['qid']]
            stop_pattern = "|".join([rf"(?:\n\s*{m})" for m in other_qids + [r"Section\s+[A-Z]", r"[A-Z]\)\s+Attem"]])
            pattern = rf"{re.escape(rq['qid'])}[\s\)\.\-\:]*(.*?)(?={stop_pattern}|\Z)"
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            raw_ans = match.group(1).strip() if match else "SKIPPED/NOT_FOUND"
            student_record["rubric_with_answers"].append({"qid": rq["qid"], "section": rq["section"], "question_text": rq["text"], "max_marks": rq["max_marks"], "student_answer": clean_repeated_question(rq['text'], raw_ans)})
        final_output[s_id] = student_record

    with open(MATCHED_JSON, "w", encoding="utf-8") as f: json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    df_new = pd.DataFrame(student_details_list)
    if os.path.exists(STUDENT_CSV):
        try:
            df_old = pd.read_csv(STUDENT_CSV)
            df_new = pd.concat([df_old, df_new], ignore_index=True).drop_duplicates(subset=['ans_id'], keep='last')
            df_new.to_csv(STUDENT_CSV, index=False)
        except PermissionError:
            st.error(f"Permission denied: Close {STUDENT_CSV} in Excel.")
    else:
        df_new.to_csv(STUDENT_CSV, index=False)
    return new_student_ids

def run_ai_feature_extraction(student_ids):
    """
    Triggers the AI worker for each student to generate stage1_features.json.
    This is the critical step that creates the scores Stage 2 needs.
    """
    st.info(f"🛰️ Processing {len(student_ids)} students through AI Engine...")
    
    # 1. Locate the worker script accurately
    worker_path = os.path.join(BASE_PATH, "grading_engine", "ai_worker.py")
    if not os.path.exists(worker_path):
        # Fallback to interface folder if moved
        worker_path = os.path.join(BASE_PATH, "interface", "ai_worker.py")
    
    if not os.path.exists(worker_path):
        st.error(f"❌ Critical Error: ai_worker.py not found at {worker_path}")
        return

    # 2. Execute worker for each student ID (e.g., ans_T036_01)
    for sid in student_ids:
        try:
            # We use capture_output=True to catch errors without crashing the main UI
            process = subprocess.run(
                [sys.executable, worker_path, sid], 
                capture_output=True, 
                text=True,
                check=True # This will raise an error if the script fails
            )
            
            # If there is specific output you want to see for debugging:
            # print(process.stdout)
            
        except subprocess.CalledProcessError as e:
            st.error(f"⚠️ AI Worker failed for {sid}")
            st.code(e.stderr) # Shows the actual Python error from ai_worker.py
            continue
        except Exception as ex:
            st.error(f"Unexpected error processing {sid}: {ex}")
            continue

    st.success("✅ AI Feature Extraction Complete! stage1_features.json updated.")

# ... [Keep all your imports and extraction utils the same] ...

def run_marks_allocation(target_ids):
    if not os.path.exists(STAGE1_FEATURES): 
        st.error("❌ Stage 1 features not found!")
        return
        
    with open(STAGE1_FEATURES, "r", encoding="utf-8") as f: 
        stage1_data = json.load(f)
    
    # 🟢 LOAD THE XGBOOST MODEL
    model = xgb.XGBRegressor()
    model_loaded = False
    if os.path.exists("grading_model.json"):
        try:
            model.load_model("grading_model.json")
            model_loaded = True
        except:
            st.warning("⚠️ Model file corrupted. Falling back to manual rule calculation.")

    final_report_data = {}
    if os.path.exists(FINAL_REPORT):
        try:
            with open(FINAL_REPORT, "r", encoding="utf-8") as f:
                final_report_data = json.load(f)
        except: pass

    meta_df = pd.read_csv(METADATA_CSV)

    for sid in target_ids:
        if sid not in stage1_data: continue
        content = stage1_data[sid]
        tid = content['info'].get('template_id')
        
        t_meta_match = meta_df[meta_df['template_id'] == tid]
        if t_meta_match.empty: continue
        t_meta = t_meta_match.iloc[0]
        
        section_counts = {}
        for item in content['analysis']:
            s = item['section'].upper()
            section_counts[s] = section_counts.get(s, 0) + 1
            
        rules = parse_rules(t_meta.get('attempt_rule', 'A:all'), section_counts)
        total_paper_max = float(t_meta.get('total_marks', 100))
        
        section_buckets = {}
        for item in content['analysis']:
            sec = item['section'].upper()
            if sec not in section_buckets: section_buckets[sec] = []
            
            # --- EXTRACT ALL FEATURES ---
            logic = item.get('logic_score', 0)
            semantic = item.get('depth_score', 0)
            len_comp = item.get('length_compliance_score', 0) 
            word_count = item.get('actual_word_count', 0)
            target_words = item.get('target_word_count', 150)
            max_m = float(item.get('max_marks', 10.0))

            # 1. 🟢 XGBOOST VS MANUAL QUALITY CALCULATION
            if model_loaded and word_count > 10:
                # Use ML to predict the quality factor
                len_ratio = word_count / target_words
                features = np.array([[logic, semantic, len_ratio]])
                quality_factor = float(model.predict(features)[0])
                quality_factor = max(0.0, min(1.0, quality_factor))
            else:
                # FALLBACK: Your exact 50/30/20 Rule
                quality_factor = (logic * 0.5) + (semantic * 0.3) + (len_comp * 0.2)
            
            # 2. 🟢 GRACE MARK FOR LOW LOGIC
            if logic < 0.15:
                quality_factor *= 0.9
            
            earned = max_m * quality_factor

            # 3. 🟢 CONDITIONAL BONUS LOGIC
            bonus = 0.0
            if max_m > 2.0:
                if word_count >= 70:
                    bonus += 0.5
                if word_count >= target_words:
                    bonus += 1.0
            
            earned += bonus

            # 4. 🟢 FINAL VALIDATION & ROUNDING
            earned = min(earned, max_m)
            earned = round(earned * 2) / 2 

            status_str = "Attempted" if word_count > 10 else "Not Attempted"
            if status_str == "Not Attempted": earned = 0.0

            section_buckets[sec].append({
                "qid": item['qid'], 
                "status": status_str,
                "score_val": earned,
                "max": max_m
            })

        # --- BEST OF X SELECTION (Same as your original) ---
        total_awarded = 0
        transparency = {}
        for sec, q_list in section_buckets.items():
            req = rules.get(sec, len(q_list))
            attempted_qs = [q for q in q_list if q['status'] == "Attempted"]
            best = sorted(attempted_qs, key=lambda x: x['score_val'], reverse=True)[:req]
            sec_score = sum(q['score_val'] for q in best)
            total_awarded += sec_score
            
            transparency[sec] = {
                "rule": f"Attempt {req}",
                "attempt_compliance": "Satisfied" if len(attempted_qs) >= req else "Not Satisfied",
                "section_total": f"{round(sec_score, 2)} / {round(sum(q['max'] for q in best) if best else 0, 2)}",
                "question_breakdown": [
                    {"qid": q['qid'], "status": q['status'], "marks": f"{q['score_val']} / {q['max']}"} 
                    for q in q_list
                ]
            }

        total_awarded = min(total_awarded, total_paper_max)
        percentage = (total_awarded / total_paper_max) * 100
        
        final_report_data[sid] = {
            "student_info": {
                "ans_id": sid, "template_id": tid,
                "roll_no": content['info'].get('roll_no', '00'),
                "name": content['info'].get('name', 'Unknown'),
                "email": content['info'].get('email', 'Not Found'),
                "class": content['info'].get('class', 'Not Specified'),
                "attempt_rule": t_meta.get('attempt_rule', 'Not Set')
            },
            "final_result": {
                "marks_awarded": round(total_awarded, 2), 
                "total_marks": total_paper_max,
                "percentage": f"{round(percentage, 2)}%",
                "grade": "O" if percentage >= 85 else "A+" if percentage >= 75 else "A" if percentage >= 65 else "B+" if percentage >= 55 else "B" if percentage >= 45 else "C" if percentage >= 35 else "F"
            },
            "transparency_report": transparency
        }

    with open(FINAL_REPORT, "w", encoding="utf-8") as f:
        json.dump(final_report_data, f, indent=4, ensure_ascii=False)

# ... [Keep the rest of your show_grade_new_page() function] ...

# =====================================================
# STREAMLIT UI
# =====================================================
def show_grade_new_page():
    st.header("📝 Create New Grading Session")
    col1, col2 = st.columns(2)
    template_file = col1.file_uploader("Upload Template (TXT)", type=['txt'])
    answer_files = col2.file_uploader("Upload Answer Sheets (TXT)", type=['txt'], accept_multiple_files=True)

    if template_file and answer_files:
        st.divider()
        tid_input = st.text_input("Enter Template ID (e.g., T035)", value="T035").upper()
        
        existing_data = {}
        if os.path.exists(METADATA_CSV):
            df_m = pd.read_csv(METADATA_CSV)
            match = df_m[df_m['template_id'] == tid_input]
            if not match.empty:
                existing_data = match.iloc[0].to_dict()
                st.info(f"✨ Found existing data for {tid_input}. Fields auto-filled.")

        with st.form("metadata_form"):
            c1, c2, c3 = st.columns(3)
            cls = c1.text_input("Class", value=existing_data.get('class', 'ML-01'))
            sub = c2.text_input("Subject", value=existing_data.get('subject', 'Machine Learning'))
            exam_options = ["Internal Examination", "Mid-Term", "End Semester Examination", "Final", "Quiz", "Assignment"]
            exam_t = c3.selectbox("Exam Type", exam_options, index=0)
            
            c4, c5, c6 = st.columns(3)
            sem = c4.text_input("Semester", value=existing_data.get('semester', 'Sem-1'))
            total_m = c5.number_input("Total Marks", value=float(existing_data.get('total_marks', 100.0)))
            exam_d = c6.date_input("Exam Date", value=datetime.now())
            
            st.write("---")
            c7, c8 = st.columns(2)
            sec_labels = c7.text_input("Section Labels (A,B,C)", value=existing_data.get('section_labels', 'A,B'))
            per_q = c8.text_input("Per Q Mark Rule (A:5, B:10)", value=existing_data.get('per_question_mark', 'A:5, B:10'))
            
            att_rule = st.text_area("Attempt Rule (A:all | B:any 2)", value=existing_data.get('attempt_rule', 'A:all'))
            marks_rule = st.text_input("Marks Rule Description", value=existing_data.get('marks_rule', 'Standard logic + keywords'))

            if st.form_submit_button("💾 Save Metadata & Start Grading"):
                # Save Template
                t_text = safe_read(template_file)
                t_filename = f"{tid_input}.txt"
                with open(os.path.join(OCR_TEMPLATES_DIR, t_filename), "w", encoding="utf-8") as tf:
                    tf.write(t_text)

                # Save Answers
                a_dict = {}
                for f in answer_files:
                    content = safe_read(f)
                    a_dict[f.name] = content
                    with open(os.path.join(OCR_ANSWERS_DIR, f.name), "w", encoding="utf-8") as af:
                        af.write(content)

                # Original metadata/grading logic
                new_row = {
                    "template_id": tid_input, "class": cls, "subject": sub, "exam_type": exam_t,
                    "semester": sem, "total_marks": total_m, "section_labels": sec_labels,
                    "attempt_rule": att_rule, "marks_rule": marks_rule, "per_question_mark": per_q,
                    "exam_date": exam_d.strftime("%Y-%m-%d"), "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                df = pd.read_csv(METADATA_CSV) if os.path.exists(METADATA_CSV) else pd.DataFrame()
                df = pd.concat([df[df['template_id'] != tid_input], pd.DataFrame([new_row])]).reset_index(drop=True)
                df.to_csv(METADATA_CSV, index=False)
                
                internal_generate_rubric(t_text, tid_input, per_q)
                new_ids = internal_align_answers(a_dict, tid_input, att_rule, cls)
                run_ai_feature_extraction(new_ids)
                run_marks_allocation(new_ids) # Pass new_ids here
                sync_data()
                st.success(f"🚀 Grading for {tid_input} successful! Files saved to OCR folders.")

if __name__ == "__main__":
    show_grade_new_page()