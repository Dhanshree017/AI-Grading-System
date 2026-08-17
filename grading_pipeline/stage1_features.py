import os
import json
import torch
import sys
import pandas as pd
from sentence_transformers import CrossEncoder, SentenceTransformer, util
import io
import time
from huggingface_hub import login

# --- 1. SILENCE THE LOADING BARS & FORCE OFFLINE ---
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1" 
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Fix encoding for Windows terminals
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = r"C:\AI_Grading_System"
INPUT_JSON = os.path.join(BASE_DIR, "grading_engine", "matched_answers.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "grading_engine", "stage1_features.json")
MASTER_RUBRIC_CSV = os.path.join(BASE_DIR, "dataset", "Machine_Learning", "metadata", "master_rubric.csv")

def get_target_word_count(marks):
    m = float(marks)
    if m <= 2: return 70
    elif m <= 3: return 90
    elif m <= 5: return 150
    elif m <= 8: return 170
    elif m <= 10: return 200
    else: return 250

def main():
    # --- 2. AUTHENTICATION & FILE CHECKS ---
    HF_TOKEN = "Enter Your Token"
    os.environ["HF_TOKEN"] = HF_TOKEN 
    
    if not os.path.exists(MASTER_RUBRIC_CSV): 
        print("Error: Master Rubric missing")
        return
    
    if not os.path.exists(INPUT_JSON):
        print(f"Error: {INPUT_JSON} not found")
        return

    rubric_df = pd.read_csv(MASTER_RUBRIC_CSV, encoding="latin-1")
    
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        all_matched_data = json.load(f)

    # --- 3. LOAD MODELS ONCE (Memory Efficient) ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔄 Loading AI Models on {device}...")
    
    try:
        ranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=device)
        depth_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
        print("✅ Models Loaded Successfully!")
    except Exception as e:
        print(f"❌ Model Loading Failed: {e}")
        return

    final_features = {}
    total_students = len(all_matched_data)
    
    # --- 4. START BULK PROCESSING ---
    print(f"🚀 Starting Feature Extraction for {total_students} students...")
    
    for idx, (sid, content) in enumerate(all_matched_data.items(), 1):
        print(f"[{idx}/{total_students}] Processing: {sid}")
        
        tid = content['student_info'].get('template_id')
        analysis_list = []

        for item in content['rubric_with_answers']:
            ans_text = str(item.get('student_answer', ""))
            qid = item.get('qid')
            max_marks = float(item.get('max_marks', 0))
            target_goal = get_target_word_count(max_marks)
            actual_words = len(ans_text.split())
            
            # Logic score init
            logic_score = 0.0
            semantic_score = 0.0
            final_grade_score = 0.0
            
            # Handle SKIPPED or Short Answers
            if "SKIPPED" in ans_text or actual_words < 15:
                # Keep scores at 0.0 as per your required structure
                pass
            else:
                ref_match = rubric_df[(rubric_df['template_id'] == tid) & (rubric_df['qid'] == qid)]
                if not ref_match.empty:
                    ideal_ans = str(ref_match.iloc[0]['ideal_reference_answer'])
                    
                    # 🧠 Logic Scoring
                    raw_logic = ranker.predict((ideal_ans, ans_text))
                    logic_score = float(1 / (1 + pow(2.718, -raw_logic))) 

                    # 🎨 Semantic Depth
                    emb1 = depth_model.encode(ideal_ans, convert_to_tensor=True)
                    emb2 = depth_model.encode(ans_text, convert_to_tensor=True)
                    depth_val = float(util.pytorch_cos_sim(emb1, emb2))
                    semantic_score = depth_val # Saving raw similarity as depth_score

                    # ⚖️ Hybrid Calculation (Matching your exact logic)
                    final_grade_score = (logic_score * 0.6) + (depth_val * 0.4)

            # Update the item with features exactly as you requested
            item.update({
                "semantic_score": round(final_grade_score, 4),
                "logic_score": round(logic_score, 4),
                "depth_score": round(semantic_score, 4),
                "actual_word_count": actual_words,
                "target_word_count": target_goal,
                "length_compliance_score": min(round(actual_words / target_goal, 4), 1.0) if target_goal > 0 else 0.0
            })
            analysis_list.append(item)

        # Build final structure for this student
        final_features[sid] = {
            "info": content['student_info'], 
            "analysis": analysis_list
        }

    # --- 5. FINAL SAVE ---
    print(f"💾 Saving all features to {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_features, f, indent=4, ensure_ascii=False)
    
    print("✅ Done! All student features extracted.")

if __name__ == "__main__":
    main()