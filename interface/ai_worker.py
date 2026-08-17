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
os.environ["HF_HUB_OFFLINE"] = "1"  # Try to use local files first
os.environ["TRANSFORMERS_VERBOSITY"] = "error" # Only show errors, not loading bars

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
    # --- 2. AUTHENTICATION (Only if needed) ---
    HF_TOKEN = "Enter Token"
    # Set environment variable so the library sees it without calling login() every time
    os.environ["HF_TOKEN"] = HF_TOKEN 
    
    if not os.path.exists(MASTER_RUBRIC_CSV): 
        print("Error: Master Rubric missing")
        return
    
    rubric_df = pd.read_csv(MASTER_RUBRIC_CSV, encoding="latin-1")

    if len(sys.argv) < 2: return
    target_sid = sys.argv[1] 

    # Use CPU if CUDA is causing memory crashes
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # --- 3. LOAD MODELS WITH ERROR HANDLING ---
    try:
        ranker = CrossEncoder(
            'cross-encoder/ms-marco-MiniLM-L-6-v2',
            device=device
        )

        depth_model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            device=device
        )
    except Exception as e:
        print(f"Model Loading Failed: {e}")
        # If offline fails, try turning offline mode off once
        os.environ["HF_HUB_OFFLINE"] = "0"
        return

    # 1. READ MATCHED ANSWERS
    if not os.path.exists(INPUT_JSON): return
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        all_matched_data = json.load(f)

    if target_sid not in all_matched_data: return

    content = all_matched_data[target_sid]
    tid = content['student_info'].get('template_id')
    analysis_list = []

    # 2. PERFORM ANALYSIS
    for item in content['rubric_with_answers']:
        ans_text = str(item.get('student_answer', ""))
        qid = item.get('qid')
        max_marks = float(item.get('max_marks', 0))
        target_goal = get_target_word_count(max_marks)
        actual_words = len(ans_text.split())
        
        ref_match = rubric_df[(rubric_df['template_id'] == tid) & (rubric_df['qid'] == qid)]
        
        logic_score = 0.0
        semantic_score = 0.0
        final_grade_score = 0.0

        if actual_words >= 15 and not ref_match.empty:
            ideal_ans = str(ref_match.iloc[0]['ideal_reference_answer'])
            
            # Conceptual Logic
            raw_logic = ranker.predict((ideal_ans, ans_text))
            logic_score = float(1 / (1 + pow(2.718, -raw_logic))) 

            # Semantic Distance
            emb1 = depth_model.encode(ideal_ans, convert_to_tensor=True)
            emb2 = depth_model.encode(ans_text, convert_to_tensor=True)
            semantic_score = float(util.pytorch_cos_sim(emb1, emb2))

            # Hybrid Score
            final_grade_score = (logic_score * 0.6) + (semantic_score * 0.4)

            # Anti-Yap Penalty
            #if logic_score < 0.35:
                #final_grade_score *= 0.5 

        # Update the item with features
        item.update({
            "semantic_score": round(final_grade_score, 4),
            "logic_score": round(logic_score, 4),
            "depth_score": round(semantic_score, 4),
            "actual_word_count": actual_words,
            "target_word_count": target_goal,
            "length_compliance_score": min(actual_words / target_goal, 1.0)
        })
        analysis_list.append(item)

    # 3. SAVE WITH FILE LOCKING
    final_features = {}
    for _ in range(10): # Increased retries
        try:
            if os.path.exists(OUTPUT_JSON):
                if os.path.getsize(OUTPUT_JSON) > 0:
                    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                        final_features = json.load(f)
            
            final_features[target_sid] = {
                "info": content['student_info'], 
                "analysis": analysis_list
            }

            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(final_features, f, indent=4, ensure_ascii=False)
            break 
        except (json.JSONDecodeError, PermissionError):
            time.sleep(2) 

if __name__ == "__main__":
    main()