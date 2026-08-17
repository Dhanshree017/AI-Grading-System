import os
import json
import re
import csv

# --- PATHS ---
BASE_DIR = r"C:\AI_Grading_System"
STUDENT_TXT_DIR = os.path.join(BASE_DIR, "dataset", "ocr_output", "answers")
RUBRIC_FILE = os.path.join(BASE_DIR, "grading_engine", "rubric.json")
STUDENT_CSV = os.path.join(BASE_DIR, "dataset", "Machine_Learning", "metadata", "students_details.csv")
METADATA_CSV = os.path.join(BASE_DIR, "dataset", "Machine_Learning", "metadata", "template_metadata.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "grading_engine", "matched_answers.json")

def load_student_details(path):
    data = {}
    if not os.path.exists(path): return data
    with open(path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = row.get("template_id", "").strip()
            roll = row.get("roll_no", "").strip()
            composite_key = f"{tid}_{roll}"
            data[composite_key] = row
    return data

def extract_answer_fixed(qid, full_text, all_qids):
    """
    Captures text starting from the QID (e.g., A-1) until the next QID 
    OR a section boundary (handles typos like 'Attemp').
    """
    # 1. Escape other QIDs to create boundaries
    other_qids = [re.escape(q) for q in all_qids if q != qid]
    
    # 2. FUZZY STOP MARKERS
    # Matches: Next QID, "Section B", "C) Attemp", "B) Attempt", "Part A"
    stop_markers = other_qids + [r"Section\s+[A-Z]", r"[A-Z]\)\s+Attem", r"Part\s+[A-Z]"]
    stop_pattern = "|".join([rf"(?:\n\s*{m})" for m in stop_markers])
    
    # 3. THE PATTERN
    # (.*?) captures everything until the stop_pattern lookahead
    pattern = rf"{re.escape(qid)}[\s\)\.\-\:]*(.*?)(?={stop_pattern}|\Z)"
    
    match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
    
    if match:
        extracted = match.group(1).strip()
        
        # --- ROBUST SAFETY SCRUB ---
        # We split line by line to ensure no header text leaked in
        lines = extracted.split('\n')
        cleaned_lines = []
        for line in lines:
            clean_line = line.strip()
            # Stop if line is a Section Header or contains the 'Attempt/Attemp' keyword
            if re.search(r"^[A-Z]\)", clean_line) or \
               re.search(r"Attem", clean_line, re.I) or \
               re.search(r"^Section\s+[A-Z]", clean_line, re.I):
                break
            cleaned_lines.append(line)
        
        final_text = "\n".join(cleaned_lines).strip()
        return final_text if len(final_text) > 2 else "SKIPPED/NOT_FOUND"
    
    return "SKIPPED/NOT_FOUND"

def clean_repeated_question(question, answer):
    """
    Removes the question prompt text from the beginning of the student's answer.
    """
    if answer == "SKIPPED/NOT_FOUND" or len(answer) < 10:
        return answer

    q_words = question.strip().split()
    if len(q_words) < 3: return answer
    
    # Tail Anchor: Use the last 3 words of the question text
    tail_anchor = " ".join(q_words[-3:]).lower().strip(".:?")
    anchor_pattern = re.escape(tail_anchor).replace(r"\ ", r"\s+")
    
    match = re.search(anchor_pattern, answer[:450], re.IGNORECASE | re.DOTALL)
    
    if match:
        cleaned = answer[match.end():].strip()
        # Clean leading punctuation like dots, brackets, or newlines
        cleaned = re.sub(r"^[ \.\)\-\:\n\r]+", "", cleaned)
        return cleaned if cleaned else "CONTENT_STRIPPED_EMPTY"

    # Fallback: simple character length cut if the header matches
    q_head = " ".join(q_words[:2]).lower()
    if q_head in answer[:100].lower():
        return answer[len(question):].strip()

    return answer

def main():
    print("🚀 Running Robust Alignment (Typo-Tolerant Version)...")
    
    if not os.path.exists(RUBRIC_FILE):
        print(f"❌ Error: {RUBRIC_FILE} not found!")
        return

    with open(RUBRIC_FILE, "r", encoding="utf-8") as f:
        rubric = json.load(f)
        
    student_db = load_student_details(STUDENT_CSV)
    
    attempt_rules = {}
    if os.path.exists(METADATA_CSV):
        with open(METADATA_CSV, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                attempt_rules[row['template_id']] = row['attempt_rule']
    
    final_output = {} 
    txt_files = [f for f in os.listdir(STUDENT_TXT_DIR) if f.endswith(".txt")]

    for fname in sorted(txt_files):
        tid_match = re.search(r"T(\d{1,3})", fname, re.I)
        if not tid_match: continue
        tid = f"T{int(tid_match.group(1)):03d}"
        
        if tid not in rubric: continue

        file_roll_match = re.search(r"_(\d+)\.txt", fname)
        raw_roll = str(int(file_roll_match.group(1))) if file_roll_match else "Unknown"
        roll_no = f"3065{raw_roll.zfill(2)}" if tid == "T031" else raw_roll

        lookup_key = f"{tid}_{roll_no}"
        student_info = student_db.get(lookup_key, {})
        student_key = fname.replace('.txt', '')

        print(f"✅ Aligning: {student_key}")

        file_path = os.path.join(STUDENT_TXT_DIR, fname)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        student_record = {
            "student_id": student_key,
            "student_info": {
                "name": student_info.get("name", "Name Not Found"),
                "roll_no": roll_no,
                "template_id": tid,
                "attempt_rule": attempt_rules.get(tid, "No Rule Specified")
            },
            "rubric_with_answers": []
        }

        all_qids = [q['qid'] for q in rubric[tid]]

        for rq in rubric[tid]:
            # Extract content using the manual QID (e.g., A-1)
            raw_ans = extract_answer_fixed(rq["qid"], raw_content, all_qids)
            # Remove the question text from the captured block
            clean_ans = clean_repeated_question(rq.get("text", ""), raw_ans)

            student_record["rubric_with_answers"].append({
                "qid": rq["qid"],
                "section": rq.get("section"),
                "question_text": rq.get("text"),
                "max_marks": rq.get("marks"),
                "keywords": rq.get("keywords", []),
                "student_answer": clean_ans
            })

        final_output[student_key] = student_record

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"\n🏁 Alignment Complete. Check results in: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()