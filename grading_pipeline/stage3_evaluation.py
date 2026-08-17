import os
import json
import pandas as pd
from google import genai
from google.genai import types
from itertools import islice
from time import sleep

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_KEY = "Enter Your Key" 
MODEL_NAME = "gemini-2.5-flash"
client = genai.Client(api_key=API_KEY)

BASE_PATH = r"C:\AI_Grading_System"
RUBRIC_PATH = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "master_rubric.csv")
MARKS_JSON = os.path.join(BASE_PATH, "grading_engine", "stage2_marks_allocation.json")
MATCHED_JSON = os.path.join(BASE_PATH, "grading_engine", "matched_answers.json")
OUTPUT_JSON = os.path.join(BASE_PATH, "grading_engine", "stage3_results.json")

# ==========================================
# 2. LOAD DATA
# ==========================================
with open(MARKS_JSON, "r", encoding="utf-8") as f:
    marks_data = json.load(f)
with open(MATCHED_JSON, "r", encoding="utf-8") as f:
    matched_data = json.load(f)

try:
    rubric_df = pd.read_csv(RUBRIC_PATH, encoding="utf-8-sig")
except:
    rubric_df = pd.read_csv(RUBRIC_PATH, encoding="latin-1")

# ==========================================
# 3. KIBO AI LOGIC
# ==========================================
def get_kibo_evaluation(student_name, marks_summary, items_to_process):
    """
    Calls Gemini to generate the structured kibo_letter and a combined email_report.
    """
    context = f"Student: {student_name}\nResult: {marks_summary['percentage']} ({marks_summary['grade']})\n\n"
    for item in items_to_process:
        context += f"--- QID: {item['qid']} ({item['type']}) ---\n"
        context += f"Question: {item['q_text']}\nMarks: {item['score']}\n"
        context += f"Student Ans: {item.get('s_ans', 'SKIPPED')}\n\n"

    # Updated Prompt for more detailed email_report
    prompt = f"""
    Role: KIBO - An empathetic AI Tutor.
    Task: Evaluate the student and provide a structured letter + a final email report.

    Rules:
    1. intro_message: Intro yourself as KIBO an AI tutor. Warm greeting, check on student health, mention their score {marks_summary['percentage']}.
    2. results (List):
       - If FULL MARKS: feedback = Praise, missing_concepts = [], mini_lesson = "".
       - If PARTIAL MARKS: feedback = specific advice, missing_concepts = [list], mini_lesson = friendly teaching with real-world examples.
       - If REQUIRED_BUT_SKIPPED: feedback = "I noticed you skipped this!", missing_concepts = [concepts], mini_lesson = Full explanation.
    
    3. email_report (Crucial): Create a comprehensive string with this exact structure:
       - **Header**: Warm Intro.
       - **Detailed Performance Section**: For EVERY QID, list:
            * QID and Question Title
            * Feedback/Critique
            * Missing Concepts (if any)
            * Mini-Lesson (the educational part)
       - **Motivational Closing**: Encouraging words to keep learning.
       Use Markdown formatting (like bold headers and bullet points) within the string for readability.

    Input Data:
    {context}

    Output Format: JSON only
    {{
      "kibo_letter": {{
        "intro_message": "...",
        "results": [ {{ "qid": "...", "feedback": "...", "missing_concepts": [], "mini_lesson": "..." }} ]
      }},
      "email_report": "..."
    }}
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error: {e}")
        return {}

# ==========================================
# 4. DATA COMPILATION & FILTERING
# ==========================================
# ==========================================
# 4. DATA COMPILATION & FILTERING
# ==========================================
final_output = {}
# Change the '1' to process more students as needed
subset_data = dict(islice(marks_data.items(), 1))

for student_id, m_data in subset_data.items():
    s_info = m_data["student_info"]
    print(f"🤖 KIBO is analyzing: {s_info['name']}")
    
    items_to_process = []
    for sec_id, sec_data in m_data["transparency_report"].items():
        is_satisfied = sec_data["attempt_compliance"] == "Satisfied"
        
        for q_entry in sec_data["question_breakdown"]:
            qid = q_entry['qid']
            is_attempted = q_entry['status'] == "Attempted"
            
            item_type = None
            if is_attempted:
                item_type = "EVALUATE"
            elif not is_attempted and not is_satisfied:
                item_type = "REQUIRED_BUT_SKIPPED"
            else:
                continue 

            r_row = rubric_df[rubric_df['qid'] == qid]
            if r_row.empty: continue
            
            s_ans_text = ""
            if is_attempted:
                for ans in matched_data.get(student_id, {}).get("rubric_with_answers", []):
                    if ans['qid'] == qid:
                        s_ans_text = ans.get('student_answer', "")

            items_to_process.append({
                "qid": qid,
                "type": item_type,
                "q_text": r_row.iloc[0]['question_text'],
                "score": q_entry['marks'],
                "s_ans": s_ans_text
            })

    # 1. AI Generation (Getting the raw components)
    ai_response = get_kibo_evaluation(s_info['name'], m_data['final_result'], items_to_process)
    
    kibo_data = ai_response.get("kibo_letter", {})
    intro = kibo_data.get("intro_message", "")
    results_list = kibo_data.get("results", [])

    # 2. RULE-BASED EMAIL REPORT CONSTRUCTION (The Fix)
    # We manually join the intro and every single result item into one string
    email_content = f"{intro}\n\n"
    email_content += "📊 --- DETAILED ACADEMIC BREAKDOWN ---\n\n"
    
    for res in results_list:
        email_content += f"📍 QID: {res.get('qid')}\n"
        email_content += f"📝 Feedback: {res.get('feedback')}\n"
        
        concepts = res.get('missing_concepts', [])
        email_content += f"💡 Missing Concepts: {', '.join(concepts) if concepts else 'None'}\n"
        
        lesson = res.get('mini_lesson', '')
        if lesson:
            email_content += f"📖 Mini Lesson: {lesson}\n"
        
        email_content += "-"*40 + "\n"

    email_content += "\nWarm regards,\nKIBO AI Tutor 🌸"

    # 3. BUILD FINAL STRUCTURE
    final_output[student_id] = {
        "student_info": s_info,
        "marks_summary": m_data['final_result'],
        "kibo_letter": kibo_data,
        "email_report": email_content  # This is now the perfectly matched copy
    }
    
    sleep(3)

    # AI Generation
    ai_response = get_kibo_evaluation(s_info['name'], m_data['final_result'], items_to_process)
    
    # BUILD FINAL STRUCTURE
    final_output[student_id] = {
        "student_info": s_info,
        "marks_summary": m_data['final_result'],
        "kibo_letter": ai_response.get("kibo_letter", {}),
        "email_report": ai_response.get("email_report", "")
    }
    
    sleep(3) # Delay to stay safe

# ==========================================
# 5. SAVE
# ==========================================
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(final_output, f, indent=4, ensure_ascii=False)

print(f"🏁 Done! Report generated at {OUTPUT_JSON}")