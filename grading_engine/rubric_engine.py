import os
import json
import re
import csv

# --- PATHS ---
BASE_PATH = r"C:\AI_Grading_System"
TEMPLATE_OCR_DIR = os.path.join(BASE_PATH, "dataset", "ocr_output", "templates")
METADATA_CSV = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "template_metadata.csv") 
OUTPUT_RUBRIC_FILE = os.path.join(BASE_PATH, "grading_engine", "rubric.json")

def load_metadata_csv():
    meta_dict = {}
    if not os.path.exists(METADATA_CSV):
        print(f"❌ METADATA NOT FOUND: {METADATA_CSV}")
        return {}
    try:
        with open(METADATA_CSV, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # Standardize headers to lowercase
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
            for row in reader:
                tid = (row.get('template_id') or row.get('id', "")).strip().upper()
                marks = row.get('per_question_mark', "").strip()
                if tid:
                    meta_dict[tid] = marks
    except Exception as e:
        print(f"❌ CSV Error: {e}")
    return meta_dict

def generate_rubric():
    meta_dict = load_metadata_csv()
    
    # regex for Section headers
    SECTION_RE = re.compile(r"^([A-Z]|\d)[\s\)\.\-\]—|]*(?:Attemp|Answer|All|Section|Any|Question|carry|each|Date|Time)", re.I)
    
    # Regex for Questions
    Q_START_RE = re.compile(r"^((?:Q)?\d+|[a-j]|i)[\s\)\.\-\]—|]+", re.I)

    rubric_data = {}

    if not os.path.exists(TEMPLATE_OCR_DIR):
        print(f"❌ Template directory not found: {TEMPLATE_OCR_DIR}")
        return

    for fname in sorted(os.listdir(TEMPLATE_OCR_DIR)):
        if not fname.endswith(".txt"): continue
        tid = fname.replace(".txt", "").strip().upper()
        marks_rule = meta_dict.get(tid, "")
        
        print(f"📝 Processing {tid}...")
        
        with open(os.path.join(TEMPLATE_OCR_DIR, fname), "r", encoding="utf-8") as f:
            lines = f.readlines()

        tid_questions = []
        current_sec = "A" # Default start
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # 1. Check for Section (e.g., B] Attempt All)
            sec_match = SECTION_RE.match(line)
            if sec_match:
                current_sec = sec_match.group(1).upper()
                continue
            
            # 2. Check for Question Start
            q_match = Q_START_RE.match(line)
            if q_match:
                literal_label = q_match.group(1)
                
                # --- FIX: Standardize labels by removing "Q" prefix ---
                # This turns 'Q1' into '1', but leaves '1' or 'a' alone.
                clean_label = re.sub(r"^[Qq]", "", literal_label)
                qid = f"{current_sec}-{clean_label}"
                
                # Marks Logic
                mark_val = 5.0
                if marks_rule:
                    for p in re.split(r'[,;]', marks_rule):
                        if ':' in p:
                            s, v = p.split(':')
                            if s.strip().upper() == current_sec:
                                m = re.findall(r"\d+", v)
                                if m: mark_val = float(m[0])

                tid_questions.append({
                    "qid": qid,
                    "original_label": literal_label, # Keep the original for reference
                    "section": current_sec,
                    "text": line,
                    "marks": mark_val
                })
            
            # 3. FIX FOR T011: Multi-line Capture
            elif tid_questions:
                tid_questions[-1]["text"] += " " + line

        # 4. Final Cleanup (Keywords & Formatting)
        for q in tid_questions:
            words = re.findall(r"[A-Za-z]{4,}", q["text"].lower())
            q["keywords"] = [w for w in words if w not in {"explain","define","describe","what","following"}][:10]

        rubric_data[tid] = tid_questions

    with open(OUTPUT_RUBRIC_FILE, "w", encoding="utf-8") as f:
        json.dump(rubric_data, f, indent=2)
    
    print(f"\n🚀 SUCCESS! Standardized QIDs (e.g., A-1 instead of A-Q1) for all templates.")

if __name__ == "__main__":
    generate_rubric()