import os
import json
import time
import pandas as pd
from google import genai
from google.genai import types

# ==========================================
# 1. CONFIGURATION & PATHS
# ==========================================
API_KEY = "Enter Your Gemini API" 
MODEL_NAME = "gemini-2.5-flash"

BASE_PATH = r"C:\AI_Grading_System"
RUBRIC_PATH = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "master_rubric.csv")
MARKS_JSON = os.path.join(BASE_PATH, "grading_engine", "stage2_marks_allocation.json")
MATCHED_JSON = os.path.join(BASE_PATH, "grading_engine", "matched_answers.json")
FEATURES_JSON = os.path.join(BASE_PATH, "grading_engine", "stage1_features.json") # Added path
OUTPUT_JSON = os.path.join(BASE_PATH, "grading_engine", "stage3_results.json")

client = genai.Client(api_key=API_KEY)

# ==========================================
# 2. THE GIBO AI CALL
# ==========================================
# ==========================================
# 2. THE GIBO AI CALL (Updated with Retry Logic)
# ==========================================
def get_gibo_evaluation(student_name, marks_summary, items_to_process):
    """Sends all questions for ONE student in a single API call with 503 error handling."""
    context = f"Student: {student_name}\nResult: {marks_summary['percentage']} ({marks_summary['grade']})\n\n"
    for item in items_to_process:
        context += f"--- QID: {item['qid']} ({item['type']}) ---\n"
        context += f"Question: {item['q_text']}\nMarks: {item['score']}\n"
        context += f"Semantic Score: {item.get('semantic', 'N/A')} | Logic Score: {item.get('logic', 'N/A')}\n"
        context += f"Word Count: {item.get('word_count', 'N/A')} (Target: {item.get('target_word', 'N/A')})\n"
        context += f"Length Compliance: {item.get('length_comp', 'N/A')}\n"
        context += f"Student Ans: {item.get('s_ans', 'SKIPPED')}\n\n"

    prompt = f"""
    Role: GIBO - An empathetic yet rigorous AI Tutor.
    Task: Evaluate the student and provide a structured letter + a final email report.

    Rules:
    1. intro_message: Intro yourself as GIBO an AI tutor.Example: "Hello! I am GIBO. I've finished reviewing your paper..." Warm greeting, check on student health, mention their score {marks_summary['percentage']}.
    
    2. results (List):
       - **Requirement Traceability**: Carefully check if the student answered ALL parts of the question (e.g., if asked for a 'definition AND example', ensure both are present). If a part is missing, mention it specifically in the feedback.
       - **Fact-Checking**: Identify and flag any "rubbish," irrelevant, or logically nonsensical lines (e.g., "computers are like apples"). Do not give conceptual credit for nonsense.
       - If FULL MARKS: feedback = Praise, missing_concepts = [], mini_lesson = "".
       - If PARTIAL MARKS: feedback = specific advice (pointing out missing sub-parts or logical errors), missing_concepts = [list], mini_lesson = friendly teaching with real-world examples to correct misconceptions.
       - If REQUIRED_BUT_SKIPPED: feedback = "I noticed you skipped this!", missing_concepts = [concepts], mini_lesson = Full explanation.
    
    3. email_report (Crucial): Create a comprehensive string with this exact structure:
       - **Header**: Warm Intro.
       - **Detailed Performance Section**: For EVERY QID, list:
            * QID and Question Title
            * Feedback/Critique (mentioning if sub-parts were missed or if nonsense was detected)
            * Missing Concepts (if any)
            * Mini-Lesson (the educational part)
       - **Motivational Closing**: Encouraging words to keep learning.
       Use Markdown formatting (like bold headers and bullet points) within the string for readability.

    Input Data:
    {context}

    Output Format: JSON only
    {{
      "gibo_letter": {{
        "intro_message": "...",
        "results": [ {{ "qid": "...", "feedback": "...", "missing_concepts": [], "mini_lesson": "..." }} ]
      }},
      "email_report": "..."
    }}
    """

    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Increased delay slightly to respect rate limits during peak demand
            time.sleep(2.0) 
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            # If it's a 503 (High Demand) error, wait and retry
            if "503" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 8
                print(f"⚠️ GIBO is busy (503). Retrying {student_name} in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            print(f"❌ Gemini Error for {student_name}: {e}")
            return None

# ==========================================
# 3. MAIN EVALUATION WRAPPER
# ==========================================
def run_targeted_evaluation(tid, ans_id):
    try:
        # Load datasets
        with open(MARKS_JSON, "r", encoding="utf-8") as f: marks_data = json.load(f)
        with open(MATCHED_JSON, "r", encoding="utf-8") as f: matched_data = json.load(f)
        # Load stage1 features
        with open(FEATURES_JSON, "r", encoding="utf-8") as f: feature_data = json.load(f)
        
        try:
            full_rubric = pd.read_csv(RUBRIC_PATH, encoding="utf-8-sig")
        except:
            full_rubric = pd.read_csv(RUBRIC_PATH, encoding="latin-1")

        rubric_df = full_rubric[full_rubric['template_id'] == tid]

        m_data = marks_data.get(ans_id)
        if not m_data: return False

        s_info = m_data["student_info"]
        items_to_process = []

        # Access feature analysis for this specific student
        student_features = feature_data.get(ans_id, {}).get("analysis", [])

        for sec_id, sec_data in m_data["transparency_report"].items():
            if sec_id == "Section_Overall": continue
            is_satisfied = sec_data.get("attempt_compliance") == "Satisfied"
            
            for q_entry in sec_data.get("question_breakdown", []):
                qid = q_entry['qid']
                is_attempted = q_entry['status'] == "Attempted"
                
                item_type = "EVALUATE" if is_attempted else ("REQUIRED_BUT_SKIPPED" if not is_satisfied else None)
                if not item_type: continue

                r_row = rubric_df[rubric_df['qid'] == qid]
                if r_row.empty: continue
                
                s_ans_text = ""
                if is_attempted:
                    for ans in matched_data.get(ans_id, {}).get("rubric_with_answers", []):
                        if ans['qid'] == qid:
                            s_ans_text = ans.get('student_answer', "")

                # Fetch matching features for this QID from stage1_features.json
                q_features = next((f for f in student_features if f['qid'] == qid), {})

                items_to_process.append({
                    "qid": qid,
                    "type": item_type,
                    "q_text": r_row.iloc[0]['question_text'],
                    "score": q_entry['marks'],
                    "s_ans": s_ans_text,
                    # Added Feature extraction
                    "semantic": q_features.get("semantic_score", 0.0),
                    "logic": q_features.get("logic_score", 0.0),
                    "word_count": q_features.get("actual_word_count", 0),
                    "target_word": q_features.get("target_word_count", 0),
                    "length_comp": q_features.get("length_compliance_score", 0.0)
                })

        print(f"🤖 GIBO is analyzing: {s_info['name']} for Template {tid}...")
        ai_response = get_gibo_evaluation(s_info['name'], m_data['final_result'], items_to_process)
        
        if not ai_response: return False

        gibo_data = ai_response.get("gibo_letter", {})
        intro = gibo_data.get("intro_message", "")
        results_list = gibo_data.get("results", [])

        email_content = f"{intro}\n\n"
        email_content += "📊 --- DETAILED ACADEMIC BREAKDOWN ---\n\n"
        
        for res in results_list:
            q_text = next((item['q_text'] for item in items_to_process if item['qid'] == res.get('qid')), "Question")
            
            email_content += f"📍 **QID: {res.get('qid')}** | {q_text}\n"
            email_content += f"📝 **Feedback:** {res.get('feedback')}\n"
            
            concepts = res.get('missing_concepts', [])
            email_content += f"💡 **Concepts:** {', '.join(concepts) if concepts else 'None'}\n"
            
            lesson = res.get('mini_lesson', '')
            if lesson:
                email_content += f"📖 **Mini Lesson:** {lesson}\n"
            
            email_content += "-"*40 + "\n"

        email_content += "\nKeep going! Every mistake is a step toward mastery. 🌟\nWarm regards,\nGIBO AI Tutor 🌸"

        new_result = {
            "student_info": s_info,
            "marks_summary": m_data['final_result'],
            "gibo_letter": gibo_data,
            "email_report": email_content 
        }

        all_results = {}
        if os.path.exists(OUTPUT_JSON):
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                try:
                    all_results = json.load(f)
                except:
                    all_results = {}

        all_results[ans_id] = new_result

        sorted_keys = sorted(all_results.keys())
        sorted_results = {k: all_results[k] for k in sorted_keys}

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(sorted_results, f, indent=4, ensure_ascii=False)

        from database.database import sync_data
        sync_data()
        
        print(f"✅ Evaluation complete and synced for {s_info['name']}")
        return True

    except Exception as e:
        print(f"💥 Error in grading_station: {e}")
        return False