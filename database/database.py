import sqlite3
import json
import os
import re
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# =====================================================
# PATHS
# =====================================================
BASE_PATH = r"C:\AI_Grading_System"
DB_DIR = os.path.join(BASE_PATH, "database")
DB_PATH = os.path.join(DB_DIR, "gibo_master.db")

# Source Files
STAGE2_JSON = os.path.join(BASE_PATH, "grading_engine", "stage2_marks_allocation.json")
STAGE3_JSON = os.path.join(BASE_PATH, "grading_engine", "stage3_results.json")
FEATURES_JSON = os.path.join(BASE_PATH, "grading_engine", "stage1_features.json")
RUBRIC_CSV = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "master_rubric.csv")
RUBRIC_JSON = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "rubric.json")
STUDENT_DETAILS_CSV = os.path.join(BASE_PATH, "dataset", "Machine_Learning", "metadata", "students_details.csv")

def get_connection():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS student_details")
    cur.execute("DROP TABLE IF EXISTS students_details")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS students_details (
        ans_id TEXT PRIMARY KEY, 
        template_id TEXT, 
        roll_no TEXT, 
        name TEXT, 
        email TEXT, 
        class TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS grading_results (
        ans_id TEXT PRIMARY KEY, name TEXT, roll_no TEXT, template_id TEXT, 
        marks_awarded REAL, total_marks REAL, percentage TEXT, grade TEXT, transparency_json TEXT)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS gibo_evaluations (
        ans_id TEXT PRIMARY KEY, name TEXT, roll_no TEXT, template_id TEXT, 
        gibo_intro TEXT, email_report TEXT)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS gibo_detailed_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ans_id TEXT, qid TEXT, 
        feedback TEXT, missing_concepts TEXT, mini_lesson TEXT)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS marks_per_question (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ans_id TEXT, section TEXT, 
        qid TEXT, status TEXT, marks_obtained REAL, max_marks REAL)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS master_rubric (
        template_id TEXT, qid TEXT, question_text TEXT, marks REAL, 
        ideal_reference_answer TEXT, key_pillars TEXT, PRIMARY KEY (template_id, qid))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS rubric_templates (
        template_id TEXT, qid TEXT, original_label TEXT, section TEXT, 
        question_text TEXT, marks REAL, keywords TEXT, PRIMARY KEY (template_id, qid))""")

    cur.execute("""CREATE TABLE IF NOT EXISTS student_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ans_id TEXT, qid TEXT, 
        semantic_score REAL, logic_score REAL, actual_word_count INTEGER, 
        target_word_count INTEGER, length_compliance_score REAL, keyword_coverage REAL)""")
    
    cur.execute("CREATE TABLE IF NOT EXISTS gibo_quota (date TEXT PRIMARY KEY, usage_count INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT)")

    conn.commit()
    conn.close()
    print("✨ Database structures ready (students_details plural fixed).")

def sync_data():
    conn = get_connection()
    print("🔄 Starting Sync...")

    print("🧹 Cleaning up ghost IDs (T001, T002...) from student columns...")
    conn.execute("DELETE FROM students_details WHERE length(ans_id) <= 5")
    conn.execute("DELETE FROM grading_results WHERE length(ans_id) <= 5")
    conn.execute("DELETE FROM gibo_evaluations WHERE length(ans_id) <= 5")
    conn.commit()

    if os.path.exists(STUDENT_DETAILS_CSV):
        try:
            df_details = pd.read_csv(STUDENT_DETAILS_CSV).dropna(how='all')
            df_details.columns = [c.strip().lower() for c in df_details.columns]
            
            for _, row in df_details.iterrows():
                raw_id = str(row.get('ans_id', '')).strip()
                
                if raw_id.startswith('T') and len(raw_id) <= 5:
                    continue 

                conn.execute("""INSERT OR REPLACE INTO students_details 
                    (ans_id, template_id, roll_no, name, email, class) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (raw_id, str(row.get('template_id', '')), 
                     str(row.get('roll_no', '')), str(row.get('name', '')), 
                     str(row.get('email', '')), str(row.get('class', ''))))
            conn.commit()
            print(f"✅ Student details cleaned and synced.")
        except Exception as e: print(f"❌ Student Details Sync Error: {e}")

    if os.path.exists(RUBRIC_CSV):
        try:
            df = None
            for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(RUBRIC_CSV, encoding=enc)
                    break
                except: continue
            
            if df is not None:
                df.columns = [c.strip().lower() for c in df.columns]
                df = df.astype(str).replace('nan', '')
                for _, row in df.iterrows():
                    conn.execute("""INSERT OR REPLACE INTO master_rubric 
                        (template_id, qid, question_text, marks, ideal_reference_answer, key_pillars) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (row.get('template_id', '').strip(), row.get('qid', '').strip(), 
                         row.get('question_text', '').strip(), row.get('marks', '0.0'), 
                         row.get('ideal_reference_answer', '').strip(), row.get('key_pillars', '').strip()))
                conn.commit()
                print("✅ master_rubric synced.")
        except Exception as e: print(f"❌ CSV Sync Error: {e}")

    if os.path.exists(RUBRIC_JSON):
        try:
            with open(RUBRIC_JSON, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                for tid, q_list in raw_data.items():
                    for q in q_list:
                        conn.execute("""INSERT OR REPLACE INTO rubric_templates 
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (tid, q.get('qid'), q.get('original_label'), q.get('section'), 
                             q.get('text'), float(q.get('marks', 0.0)), ", ".join(q.get('keywords', []))))
            conn.commit()
            print("✅ rubric_templates updated.")
        except Exception as e: print(f"❌ JSON Rubric Error: {e}")

    if os.path.exists(STAGE2_JSON):
        try:
            with open(STAGE2_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for aid, content in data.items():
                if not aid.startswith('ans_'): continue 

                info = content.get('student_info', {})
                res = content.get('final_result', {})
                report = content.get('transparency_report', {})
                
                awarded = float(res.get('marks_awarded', 0.0))
                total = float(res.get('total_marks', 0.0))
                perc_val = res.get('percentage', f"{(awarded/total*100):.1f}%" if total > 0 else "0%")
                grade_val = res.get('grade', "F")

                conn.execute("""INSERT OR REPLACE INTO grading_results 
                    (ans_id, name, roll_no, template_id, marks_awarded, total_marks, percentage, grade, transparency_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (aid, info.get('name'), info.get('roll_no'), info.get('template_id'),
                     awarded, total, perc_val, grade_val, json.dumps(report)))
                
                conn.execute("DELETE FROM marks_per_question WHERE ans_id=?", (aid,))
                
                for section_name, section_data in report.items():
                    if isinstance(section_data, dict):
                        for q in section_data.get('question_breakdown', []):
                            qid = q.get('qid')
                            status = q.get('status')
                            raw_marks = q.get('marks', "0.0 / 0.0")
                            try:
                                m_obt = float(raw_marks.split('/')[0].strip())
                                m_max = float(raw_marks.split('/')[1].strip())
                            except:
                                m_obt, m_max = 0.0, 0.0

                            conn.execute("""INSERT INTO marks_per_question 
                                (ans_id, section, qid, status, marks_obtained, max_marks) 
                                VALUES (?, ?, ?, ?, ?, ?)""",
                                (aid, section_name, qid, status, m_obt, m_max))
            
            conn.commit()
            print(f"✅ Synced {len(data)} records and updated question-wise marks.")
        except Exception as e:
            print(f"❌ Stage 2 Sync Error: {e}")

    if os.path.exists(STAGE3_JSON):
        try:
            with open(STAGE3_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for aid, content in data.items():
                    if not aid.startswith('ans_'): continue
                    info, gibo = content.get('student_info', {}), content.get('gibo_letter', {})
                    conn.execute("INSERT OR REPLACE INTO gibo_evaluations VALUES (?, ?, ?, ?, ?, ?)",
                                 (aid, info.get('name'), info.get('roll_no'), info.get('template_id'), gibo.get('intro_message', ''), content.get('email_report', '')))
                    
                    conn.execute("DELETE FROM gibo_detailed_feedback WHERE ans_id=?", (aid,))
                    for item in gibo.get('results', []):
                        conn.execute("INSERT INTO gibo_detailed_feedback (ans_id, qid, feedback, missing_concepts, mini_lesson) VALUES (?, ?, ?, ?, ?)",
                                     (aid, item.get('qid'), item.get('feedback'), ", ".join(item.get('missing_concepts', [])), item.get('mini_lesson')))
            conn.commit()
            print("✅ Stage 3 Feedback synced.")
        except Exception as e: print(f"❌ Stage 3 Sync Error: {e}")
    
    conn.close()
    print("🏁 All systems fully synced and cleaned.")

# =====================================================
# AUTHENTICATION & TEACHER MANAGEMENT
# =====================================================

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Primary Users Table (Only for approved logins)
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY, 
        password TEXT, 
        role TEXT
    )""")

    # 2. New Teacher Table (For registration information)
    # Status can be 'pending', 'approved', or 'blocked'
    cur.execute("""CREATE TABLE IF NOT EXISTS teacher_table (
        email TEXT PRIMARY KEY, 
        name TEXT, 
        mobile TEXT, 
        password TEXT,
        status TEXT DEFAULT 'pending'
    )""")
    
    conn.commit()
    conn.close()

def register_teacher(name, email, mobile, _):
    """Enforces the 'TeacherLogin' password regardless of user input."""
    try:
        conn = get_connection()
        # We manually set the password here so it is always 'TeacherLogin'
        fixed_pass = "TeacherLogin" 
        
        conn.execute("""
            INSERT INTO teacher_table (email, name, mobile, password, status) 
            VALUES (?, ?, ?, ?, 'pending')
        """, (email, name, mobile, fixed_pass))
        conn.commit()
        conn.close()
        return True, "request sent ! check your email"
    except Exception as e:
        return False, "This email is already registered."

def hard_delete_teacher(email):
    """Completely wipes the account so the email can be used again."""
    conn = get_connection()
    # Remove from both the login table and the registration table
    conn.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.execute("DELETE FROM teacher_table WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return True

def verify_login(username_email, password):
    """Checks hardcoded defaults and the approved users table."""
    # 1. Default Hardcoded Credentials
    if username_email == "admin" and password == "admin123":
        return True, {"email": "admin", "role": "admin"}
    if username_email == "teacher" and password == "teacher123":
        return True, {"email": "teacher", "role": "teacher"}

    # 2. Check the primary users table
    try:
        conn = get_connection()
        user = conn.execute("SELECT email, role FROM users WHERE email = ? AND password = ?", 
                            (username_email, password)).fetchone()
        conn.close()

        if user:
            return True, {"email": user[0], "role": user[1]}
        return False, None
    except:
        return False, None

def approve_teacher_request(email):
    try:
        conn = get_connection()
        teacher = conn.execute("SELECT email, password FROM teacher_table WHERE email = ?", (email,)).fetchone()
        
        if teacher:
            # 1. Move to login table
            conn.execute("INSERT OR REPLACE INTO users (email, password, role) VALUES (?, ?, 'teacher')", 
                         (teacher[0], teacher[1]))
            
            # 2. Update status
            conn.execute("UPDATE teacher_table SET status = 'approved' WHERE email = ?", (email,))
            conn.commit()
            conn.close()

            # 3. SEND THE EMAIL
            send_approval_email(teacher[0], teacher[1])
            return True
        return False
    except Exception as e:
        return False

def get_all_teacher_requests():
    """Fetches every entry from the teacher_table for the Admin to view."""
    conn = get_connection()
    # Returns everyone so we can show 'Approved', 'Pending', and 'Blocked' lists
    df = pd.read_sql_query("SELECT name, email, mobile, status FROM teacher_table", conn)
    conn.close()
    return df

def block_teacher_request(email):
    """
    Blocks a teacher: 
    1. Sets status to 'blocked' in teacher_table.
    2. Deletes them from the 'users' login table so they can't log in.
    """
    conn = get_connection()
    # Update status in the info table
    conn.execute("UPDATE teacher_table SET status = 'blocked' WHERE email = ?", (email,))
    # Completely remove from the login table
    conn.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    
    
def send_approval_email(receiver_email, password):
    """Sends the credentials to the teacher via email."""
    sender_email = "create sender email"
    sender_password = "Enter Your Password"  # Use Google App Password
    
    subject = "🎉 Your Teacher Account is Approved!"
    body = f"""
    Hello,

    Your registration for the AI Grading System has been approved by the Admin.
    
    You can now login using these credentials:
    Username: {receiver_email}
    Password: {password}
    
    Best Regards,
    GIBO AI Team
    """
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def get_class_missing_concepts(template_id):
    try:
        conn = get_connection()
        query = """
            SELECT f.missing_concepts 
            FROM gibo_detailed_feedback f
            JOIN grading_results r ON f.ans_id = r.ans_id
            WHERE r.template_id = ? AND f.missing_concepts != ''
        """
        df = pd.read_sql_query(query, conn, params=(template_id,))
        conn.close()
        
        if not df.empty:
            concepts = df['missing_concepts'].str.split(',').explode().str.strip()
            return concepts.value_counts().to_dict()
        return {}
    except Exception as e:
        print(f"Error fetching concepts: {e}")
        return {}

def update_manual_grade(ans_id, new_marks, new_grade):
    try:
        conn = get_connection()
        conn.execute("""
            UPDATE grading_results 
            SET marks_awarded = ?, grade = ? 
            WHERE ans_id = ?
        """, (new_marks, new_grade, ans_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating grade: {e}")
        return False
    

if __name__ == "__main__":
    init_db()
    sync_data()