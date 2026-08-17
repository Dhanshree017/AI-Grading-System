import json
import pandas as pd
import os
import re
import xgboost as xgb
import numpy as np

# --- 📍 PATHS ---
BASE_DIR = r"C:\AI_Grading_System"
STAGE1_JSON = os.path.join(BASE_DIR, "grading_engine", "stage1_features.json")
METADATA_CSV = os.path.join(BASE_DIR, "dataset", "Machine_Learning", "metadata", "template_metadata.csv")
FINAL_REPORT = os.path.join(BASE_DIR, "grading_engine", "stage2_marks_allocation.json")
MODEL_PATH = "grading_model.json"

def parse_rules(rule_str, section_counts):
    rules = {}
    if pd.isna(rule_str) or not rule_str: return rules
    parts = str(rule_str).split('|')
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

def main():
    # 1. Load Data
    if not os.path.exists(STAGE1_JSON):
        print(f"❌ ERROR: {STAGE1_JSON} not found!")
        return
    
    with open(STAGE1_JSON, "r", encoding="utf-8") as f:
        stage1_data = json.load(f)
    
    meta_df = pd.read_csv(METADATA_CSV)
    
    # 2. Load XGBoost Model
    model = xgb.XGBRegressor()
    model_loaded = False
    if os.path.exists(MODEL_PATH):
        try:
            model.load_model(MODEL_PATH)
            print("🤖 XGBoost Model Loaded Successfully.")
            model_loaded = True
        except:
            print("⚠️ Warning: Model file corrupted. Using fallback logic.")
    else:
        print("⚠️ Warning: grading_model.json not found. Using fallback logic.")

    final_output = {}

    print(f"⚖️ Processing {len(stage1_data)} students...")

    for sid, content in stage1_data.items():
        tid = content['info'].get('template_id')
        t_meta_match = meta_df[meta_df['template_id'] == tid]
        
        if t_meta_match.empty:
            print(f"Skipping {sid}: Template {tid} not in metadata.")
            continue
            
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
            
            # 1. 🔮 QUALITY FACTOR CALCULATION
            if model_loaded and word_count > 10:
                # Prepare features exactly as trained
                len_ratio = word_count / target_words
                features = np.array([[logic, semantic, len_ratio]])
                quality_factor = float(model.predict(features)[0])
                quality_factor = max(0.0, min(1.0, quality_factor))
            else:
                # 🟢 FALLBACK: YOUR EXACT 50/30/20 RULE
                quality_factor = (logic * 0.4) + (semantic * 0.4) + (len_comp * 0.2)

            # 2. 🟢 GRACE MARK / PENALTY FOR LOW LOGIC
            if logic < 0.15:
                quality_factor *= 0.9
            
            earned = max_m * quality_factor

            # 3. 🟢 CONDITIONAL BONUS LOGIC (Word Count Bonuses)
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

        # --- 📊 BEST-OF-X SELECTION ---
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
                "attempt_compliance": "Satisfied" if len(attempted_qs) >= req else "Partial",
                "section_total": f"{round(sec_score, 2)} / {round(sum(q['max'] for q in best) if best else 0, 2)}",
                "question_breakdown": [
                    {"qid": q['qid'], "status": q['status'], "marks": f"{q['score_val']} / {q['max']}"} 
                    for q in q_list
                ]
            }

        total_awarded = min(total_awarded, total_paper_max)
        percentage = (total_awarded / total_paper_max) * 100
        
        # --- 🏁 FINAL JSON STRUCTURE ---
        final_output[sid] = {
            "student_info": {
                "ans_id": sid,
                "template_id": tid,
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
                "grade": "O" if percentage >= 85 else "A+" if percentage >= 75 else "A" if percentage >= 65 else "B+" if percentage >= 55 else "B" if percentage >= 45 else "C" if percentage >= 33.74 else "F"
            },
            "transparency_report": transparency
        }

    # Save output
    with open(FINAL_REPORT, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
    
    print(f"🏁 DONE! Processed {len(final_output)} students. Saved to {FINAL_REPORT}")

if __name__ == "__main__":
    main()