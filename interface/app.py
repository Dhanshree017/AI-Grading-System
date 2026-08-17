import sys
import os
import re
from fpdf import FPDF
import io
import time
from email_service import send_gibo_email

# =====================================================
# 0. FOLDER PATH FIX
# =====================================================
# This ensures that 'grading_engine' and 'interface' folders are discoverable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd

import json
import plotly.express as px
from database.database import (
    get_connection, 
    verify_login, 
    register_teacher, 
    approve_teacher_request, 
    block_teacher_request
)

# =====================================================
# 1. PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Grade & Guide with GIBO",
    page_icon="✨",
    layout="wide"
)

# =====================================================
# 2. SESSION STATE INIT
# =====================================================
if "page" not in st.session_state:
    st.session_state.page = "landing"
if "role" not in st.session_state:
    st.session_state.role = None
if "know_more" not in st.session_state:
    st.session_state.know_more = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "viewing_student_id" not in st.session_state:
    st.session_state.viewing_student_id = None

# =====================================================
# 3. CUSTOM CSS
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap');
.stApp { background: linear-gradient(135deg, #ffffff, #f5f0ff); font-family: 'Poppins', sans-serif; }
.main-title { font-size: 65px; font-weight: 700; color: #2d1b69; line-height: 1.1; }
.neon-title { font-size: 80px; font-weight: 700; background: linear-gradient(90deg, #7b2cff, #00c6ff, #ff2fcf); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.2; }
.subtitle { font-size: 22px; color: #444; margin-top: -10px; }
.gibo-meaning { font-size: 18px; color: #555; line-height: 1.6; }
.glow-box { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(123,44,255,0.15); border: 1px solid rgba(123,44,255,0.1); margin-bottom: 20px; }
footer { text-align: center; color: #888; margin-top: 50px; padding-bottom: 20px; }
div.stButton > button:contains("✉️") { background-color: #ff4b91 !important; color: white !important; border: none !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 4. HELPER FUNCTIONS
# =====================================================
def delete_gibo_evaluation(ans_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. DELETE FROM DATABASE
        cursor.execute("DELETE FROM gibo_evaluations WHERE ans_id = ?", (ans_id,))
        cursor.execute("DELETE FROM gibo_detailed_feedback WHERE ans_id = ?", (ans_id,))
        conn.commit()

        # 2. DELETE FROM JSON FILE
        OUTPUT_JSON = r"C:\AI_Grading_System\grading_engine\stage3_results.json"
        
        if os.path.exists(OUTPUT_JSON):
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                try:
                    all_results = json.load(f)
                except:
                    all_results = {}

            # Remove the specific student key if it exists
            if ans_id in all_results:
                del all_results[ans_id]
                
                # Save the cleaned JSON back to the file
                with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, indent=4, ensure_ascii=False)
                
        return True
    except Exception as e:
        st.error(f"Error deleting evaluation: {e}")
        return False
    finally:
        conn.close()

def generate_score_pdf(name, roll_no, template_id, grade, mq_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"ACADEMIC PERFORMANCE TABLE: {name}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 7, f"Roll No: {roll_no} | Template: {template_id} | Grade: {grade}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(230, 230, 250) 
    pdf.cell(40, 10, "Section", 1, 0, 'C', True)
    pdf.cell(30, 10, "QID", 1, 0, 'C', True)
    pdf.cell(60, 10, "Status", 1, 0, 'C', True)
    pdf.cell(40, 10, "Marks", 1, 1, 'C', True)
    pdf.set_font("Arial", size=10)
    for _, row in mq_df.iterrows():
        pdf.cell(40, 10, str(row['section']), 1, 0, 'C')
        pdf.cell(30, 10, str(row['qid']), 1, 0, 'C')
        pdf.cell(60, 10, str(row['status']), 1, 0, 'C')
        pdf.cell(40, 10, f"{row['marks_obtained']} / {row['max_marks']}", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

# =====================================================
# 5. PAGES
# =====================================================
def landing_page():
    if not st.session_state.know_more:
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.markdown("<div class='main-title'>Grade & Guide with</div>", unsafe_allow_html=True)
            st.markdown("<div class='neon-title'>GIBO 🧠</div>", unsafe_allow_html=True)
            st.markdown("<p class='subtitle'>AI Grading for Teachers | AI Tutor for Students</p>", unsafe_allow_html=True)
            st.markdown("<p class='gibo-meaning'><b>GIBO</b> stands for <b>Grading Intelligence for Behavioral Optimization</b>. We believe grading shouldn't just be a final score—it should be a friendly conversation. GIBO acts as an empathetic tutor, simplifying complex concepts with real-world examples to help students grow.</p>", unsafe_allow_html=True)
            st.write("---")
            st.write("### 🔐 Secure Access")
            c1, c2 = st.columns(2)
            if c1.button("👩‍🏫 Teacher Login", use_container_width=True):
                st.session_state.page, st.session_state.role = "login", "teacher"
                st.rerun()
            if c2.button("🧑‍💼 Admin Login", use_container_width=True):
                st.session_state.page, st.session_state.role = "login", "admin"
                st.rerun()
            st.write("---")
            if st.button("🌟 Why GIBO is different?", type="secondary", use_container_width=True):
                st.session_state.know_more = True
                st.rerun()
        with col2:
            st.markdown("<div class='glow-box'><h3 style='color: #7b2cff;'>🚀 The GIBO Advantage</h3><ul style='list-style-type: none; padding-left: 0;'><li>✅ <b>Fair & Unbiased:</b> XGBoost-powered grading logic.</li><li>✅ <b>Empathetic Feedback:</b> Real-world analogies for better grip.</li><li>✅ <b>Concept Reinforcement:</b> Identifying weak spots instantly.</li><li>✅ <b>Seamless Automation:</b> Reducing teacher workload by 80%.</li></ul></div>", unsafe_allow_html=True)
            st.markdown("<div class='glow-box'><h3 style='color: #7b2cff;'>🚀 Longitudinal Growth Tracking</h3><ul style='list-style-type: none; padding-left: 0;'><li>✅ <b>Skill Mapping:</b> track student improvement across specific topics over time. </li><li>✅ <b>Predictive Insights:</b> Identify learning gaps before they become critical failures.</li><li>✅ <b>Custom Learning Paths:</b>Suggest targeted resources for students based on their specific performance history.</li><li>", unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)
        st.info("Grading Intelligence for Behavioral Optimization (GIBO) — Redefining Academic Evaluation.")
        st.markdown("<footer>© 2026 Automated Grading System with GIBO AI • Built for Progress 🌸</footer>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: center;'><div class='neon-title'>GIBO Intelligence 🧠</div></div>", unsafe_allow_html=True)
        st.markdown("""
        ### Understanding Behavioral Optimization
        GIBO doesn't just look for keywords; it understands the student's logic. By analyzing semantic depth and conceptual clarity, it provides feedback that encourages a 'Growth Mindset'. 
        - **Friendly Tone:** No more robotic 'Incorrect' marks. GIBO explains *why* and *how* to improve.
        - **Real-World Examples:** Concepts like Neural Networks or Calculus are explained using everyday life scenarios.
        - **Data Driven:** Teachers get high-level insights while students get personalized guidance.
        """)
        if st.button("⬅ Back to Main Page"):
            st.session_state.know_more = False
            st.rerun()

def login_page():
    # FIXED NAVIGATION: Back to Home
    if st.button("⬅️ Back to Home Page"):
        st.session_state.role = None
        st.session_state.page = "landing" # Ensure your landing page logic uses this key
        st.rerun()

    title = "👩‍🏫 TEACHER PORTAL" if st.session_state.role == "teacher" else "🧑‍💼 ADMIN PORTAL"
    st.markdown(f"# {title}")
    
    if st.session_state.role == "teacher":
        tab1, tab2 = st.tabs(["Login", "Register as New Teacher"])
        with tab1:
            render_login_form()
        with tab2:
            st.markdown("### 📝 Registration")
            reg_name = st.text_input("Full Name")
            reg_email = st.text_input("Email ID (@)")
            reg_mob = st.text_input("Mobile Number")
            st.info("Note: You will get username and password on email*")
            
            if st.button("Submit Registration"):
                if "@" in reg_email:
                    from database.database import register_teacher
                    success, msg = register_teacher(reg_name, reg_email, reg_mob, "")
                    if success: st.success(msg)
                    else: st.error(msg)
    else:
        render_login_form()

def admin_management_section():
    if st.button("🏠 Logout & Return Home"):
        st.session_state.role = None
        st.session_state.page = "landing"
        st.rerun()

    st.title("👥 Teacher Access Management")
    from database.database import get_all_teacher_requests, approve_teacher_request, block_teacher_request, hard_delete_teacher
    
    df = get_all_teacher_requests()

    # --- SECTION 1: ALL REQUESTS ---
    for _, row in df.iterrows():
        with st.container():
            st.write(f"### {row['name']} ({row['email']})")
            
            # This creates 4 columns; we use the middle two (c2 and c3)
            # This keeps the buttons away from the corners and in the middle
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            
            with c2:
                if row['status'] == 'pending':
                    if st.button("✅ Approve", key=f"all_app_{row['email']}", use_container_width=True):
                        approve_teacher_request(row['email'])
                        st.rerun()
                elif row['status'] == 'approved':
                    if st.button("🚫 Block", key=f"all_blk_{row['email']}", use_container_width=True):
                        block_teacher_request(row['email'])
                        st.rerun()

            with c3:
                # DELETE BUTTON: Now right in the middle next to the other action
                if st.button("🗑️ Delete", key=f"all_del_{row['email']}", use_container_width=True):
                    hard_delete_teacher(row['email'])
                    st.rerun()
        st.divider()

    # --- SECTION 2: ACTIVE ---
    st.subheader("🟢 Active Accounts")
    approved = df[df['status'] == 'approved']
    for _, row in approved.iterrows():
        st.write(f"👤 **{row['name']}**")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c2:
            if st.button("🚫 Block", key=f"act_blk_{row['email']}", use_container_width=True):
                block_teacher_request(row['email'])
                st.rerun()
        with c3:
            if st.button("🗑️ Delete", key=f"act_del_{row['email']}", use_container_width=True):
                hard_delete_teacher(row['email'])
                st.rerun()

    # --- SECTION 3: BLOCKED ---
    st.subheader("🔴 Blocked Accounts")
    blocked = df[df['status'] == 'blocked']
    for _, row in blocked.iterrows():
        st.write(f"~~{row['name']}~~")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c2:
            if st.button("♻️ Restore", key=f"blk_res_{row['email']}", use_container_width=True):
                # Status update logic
                st.rerun()
        with c3:
            if st.button("🗑️ Delete", key=f"blk_del_{row['email']}", use_container_width=True):
                hard_delete_teacher(row['email'])
                st.rerun()

def render_login_form():
    st.markdown("<div class='glow-box'>", unsafe_allow_html=True)
    u_input = st.text_input("Username / Email", key="log_u")
    p_input = st.text_input("Password", type="password", key="log_p")
    
    if st.button("Login"):
        from database.database import verify_login
        success, user_data = verify_login(u_input, p_input)
        
        if success:
            st.session_state.user_email = u_input
            st.session_state.page = "teacher_dashboard" if st.session_state.role == "teacher" else "admin_dashboard"
            st.rerun()
        else:
            st.error("❌ Invalid Login or Account Pending Approval.")
            
def admin_management_section():
    # --- NAVIGATION SIDEBAR FOR ADMIN ---
    with st.sidebar:
        st.title("🛡️ Admin Panel")
        admin_view = st.radio("Management Menu", ["Pending Requests", "Approved Accounts", "Blocked Accounts"])
        st.divider()
        if st.button("⬅️ Logout & Home"):
            st.session_state.role = None
            st.session_state.page = "landing"
            st.rerun()

    from database.database import get_all_teacher_requests, approve_teacher_request, block_teacher_request, hard_delete_teacher
    df = get_all_teacher_requests()

    # --- VIEW 1: PENDING ---
    if admin_view == "Pending Requests":
        st.header("⏳ Pending Approvals")
        pending = df[df['status'] == 'pending']
        if pending.empty:
            st.info("No pending requests at the moment.")
        for _, row in pending.iterrows():
            with st.container():
                st.write(f"### {row['name']}")
                st.write(f"📧 {row['email']} | 📱 {row['mobile']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Approve {row['name']}", key=f"p_app_{row['email']}", use_container_width=True):
                        approve_teacher_request(row['email'])
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Reject & Delete", key=f"p_del_{row['email']}", use_container_width=True):
                        hard_delete_teacher(row['email'])
                        st.rerun()
            st.divider()

    # --- VIEW 2: APPROVED (Now with the Delete Button in the Middle) ---
    elif admin_view == "Approved Accounts":
        st.header("🟢 Approved Accounts")
        approved = df[df['status'] == 'approved']
        if approved.empty:
            st.info("No active teacher accounts.")
        for _, row in approved.iterrows():
            with st.container():
                st.write(f"### 👤 {row['name']}")
                st.write(f"Email: {row['email']}")
                
                # Putting buttons in the center of the page
                _, btn1, btn2, _ = st.columns([0.5, 1, 1, 0.5])
                with btn1:
                    if st.button("🚫 Block Access", key=f"a_blk_{row['email']}", use_container_width=True):
                        block_teacher_request(row['email'])
                        st.rerun()
                with btn2:
                    # THE DELETE BUTTON: Safe and visible in the middle
                    if st.button("🗑️ Delete Account", key=f"a_del_{row['email']}", use_container_width=True):
                        hard_delete_teacher(row['email'])
                        st.rerun()
            st.divider()

    # --- VIEW 3: BLOCKED ---
    elif admin_view == "Blocked Accounts":
        st.header("🔴 Blocked / Rejected Accounts")
        blocked = df[df['status'] == 'blocked']
        if blocked.empty:
            st.info("No blocked accounts.")
        for _, row in blocked.iterrows():
            with st.container():
                st.write(f"### ~~{row['name']}~~")
                st.write(f"Contact: {row['email']}")
                
                _, b_col1, b_col2, _ = st.columns([0.5, 1, 1, 0.5])
                with b_col1:
                    if st.button("♻️ Restore Access", key=f"b_res_{row['email']}", use_container_width=True):
                        approve_teacher_request(row['email']) # Re-approving restores them
                        st.rerun()
                with b_col2:
                    if st.button("🗑️ Permanent Wipe", key=f"b_del_{row['email']}", use_container_width=True):
                        hard_delete_teacher(row['email'])
                        st.rerun()
            st.divider()

def render_full_academic_report(ans_id, conn):
    if st.button("⬅️ Back to Student List"):
        st.session_state.viewing_student_id = None
        st.rerun()
    
    # --- 1. ACADEMIC PROFILE ---
    res = pd.read_sql(f"SELECT * FROM grading_results WHERE ans_id = '{ans_id}'", conn).iloc[0]
    st.markdown(f"<h2 style='color: #2d1b69;'>🎓 Academic Profile: {res['name']}</h2>", unsafe_allow_html=True)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Final Grade", res['grade'])
    m2.metric("Marks Awarded", f"{res['marks_awarded']} / {res['total_marks']}")
    m3.metric("Percentage", res['percentage'])
    
    st.markdown("<div class='glow-box'>### 📝 Question-wise Breakdown</div>", unsafe_allow_html=True)
    mq_df = pd.read_sql(f"SELECT section, qid, status, marks_obtained, max_marks FROM marks_per_question WHERE ans_id='{ans_id}'", conn)
    if not mq_df.empty: st.table(mq_df)

    st.markdown("<div class='glow-box'>### 🌸 GIBO AI Behavioral Evaluation</div>", unsafe_allow_html=True)
    eval_data = pd.read_sql(f"SELECT gibo_intro, email_report FROM gibo_evaluations WHERE ans_id='{ans_id}'", conn)
    
    if eval_data.empty:
        st.warning("⚠️ Not yet evaluated by GIBO.")
        if st.button(f"🚀 Evaluate {res['name']} Now"):
            from interface.grading_station import run_targeted_evaluation
            with st.spinner("🤖 GIBO is analyzing behavior..."):
                if run_targeted_evaluation(res['template_id'], ans_id):
                    st.success("✅ Evaluation Complete!"); time.sleep(1); st.rerun()
    else:
        # --- 2. GIBO FEEDBACK LETTER ---
        report_text = eval_data['email_report'].iloc[0]
        clean_report = re.sub(r'#+', '', report_text).replace("---", "")
        st.markdown("#### 📧 Friendly Mentorship Report")
        st.markdown(f'<div style="background-color: white; padding: 20px; border: 1px solid #ddd; border-radius: 10px; font-size: 15px; color: #333; line-height: 1.6;">{clean_report.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        
        pdf_bytes = generate_score_pdf(res['name'], res['roll_no'], res['template_id'], res['grade'], mq_df)
        c_pdf, c_del = st.columns([1, 1])
        c_pdf.download_button("📥 Download Score Table (PDF)", data=pdf_bytes, file_name=f"ScoreTable_{res['name']}.pdf", mime="application/pdf")
        
        if c_del.button("🗑️ Delete Evaluation", type="secondary"):
            if delete_gibo_evaluation(ans_id): 
                st.success("Evaluation Deleted!")
                time.sleep(1)
                st.rerun()

        st.divider()
        st.chat_message("assistant").write(eval_data['gibo_intro'].iloc[0])

        # --- 3. PURE VISUAL BARS ---
        STAGE1_JSON = r"C:\AI_Grading_System\grading_engine\stage1_features.json"
        feature_scores = {}
        if os.path.exists(STAGE1_JSON):
            with open(STAGE1_JSON, "r", encoding="utf-8") as f:
                all_features = json.load(f)
                feature_scores = {item['qid']: item for item in all_features.get(ans_id, {}).get("analysis", [])}

        detailed = pd.read_sql(f"SELECT qid FROM gibo_detailed_feedback WHERE ans_id='{ans_id}'", conn)
        
        for _, drow in detailed.iterrows():
            with st.expander(f"Question {drow['qid']} - Intelligence Metrics"):
                q_id = drow['qid']
                if q_id in feature_scores:
                    data = feature_scores[q_id]
                    
                    def get_bar_html(label, value):
                        val = float(value)
                        percent = int(val * 100)
                        if val < 0.4: color = "#FF4B4B" 
                        elif val < 0.7: color = "#FFA500" 
                        else: color = "#2ECC71" 
                        
                        return f"""
                        <div style="margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span style="font-size: 13px; font-weight: 500; color: #555;">{label}</span>
                                <span style="font-size: 13px; font-weight: 700; color: {color};">{percent}%</span>
                            </div>
                            <div style="background-color: #e0e0e0; border-radius: 10px; height: 8px; width: 100%;">
                                <div style="background-color: {color}; height: 8px; width: {percent}%; border-radius: 10px;"></div>
                            </div>
                        </div>
                        """

                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.markdown(get_bar_html("Logic Consistency", data.get('logic_score', 0)), unsafe_allow_html=True)
                    with c2: st.markdown(get_bar_html("Semantic Accuracy", data.get('semantic_score', 0)), unsafe_allow_html=True)
                    with c3: st.markdown(get_bar_html("Compliance", data.get('length_compliance_score', 0)), unsafe_allow_html=True)
                else:
                    st.info("Metrics not available for this question.")

def teacher_dashboard():
    conn = get_connection()
    
    # --- Persistence Logic for Template Selection ---
    if "selected_tid_key" not in st.session_state:
        st.session_state.selected_tid_key = "-- Select Template --"

    if st.session_state.viewing_student_id:
        render_full_academic_report(st.session_state.viewing_student_id, conn)
        conn.close(); return

    st.markdown("<h2 style='color: #2d1b69; border-bottom: 2px solid #7b2cff; padding-bottom: 10px;'>📊 Faculty Insights & Academic Control</h2>", unsafe_allow_html=True)
    with st.sidebar:
        st.write(f"🧬 *Portal:* {st.session_state.user_email}"); st.divider()
        available_tids = pd.read_sql("SELECT DISTINCT template_id FROM grading_results", conn)['template_id'].tolist()
        
        # ADDED "Concept Analysis" to your original list
        option = st.radio("Navigation", ["Student Records", "Grade New Student", "Analysis", "Concept Analysis"])
        
        st.divider()
        # Updated to use session state for persistence
        st.session_state.selected_tid_key = st.selectbox(
            "🎯 Select Academic Template", 
            ["-- Select Template --"] + [f"{tid} | Machine Learning" for tid in sorted(available_tids)],
            index=0 if st.session_state.selected_tid_key == "-- Select Template --" else (sorted(available_tids).index(st.session_state.selected_tid_key.split(" | ")[0]) + 1)
        )
        st.divider()
        if st.button("Logout"): st.session_state.page = "landing"; st.rerun()

    selected_display = st.session_state.selected_tid_key

    if option == "Grade New Student":
        try:
            from interface.grade_new import show_grade_new_page
            show_grade_new_page()
        except Exception as e:
            st.error(f"Error loading GIBO Grading Engine: {e}")
    
    elif selected_display != "-- Select Template --":
        selected_tid = selected_display.split(" | ")[0].strip()
        
        if option == "Student Records":
            # --- ADDED SEARCH BY NAME/ROLL ---
            s_col1, s_col2 = st.columns(2)
            search_name = s_col1.text_input("🔍 Search Name")
            search_roll = s_col2.text_input("🔢 Search Roll No")

            query = """
                SELECT gr.ans_id, gr.roll_no, gr.name, gr.grade, sd.email, sd.class 
                FROM grading_results gr 
                LEFT JOIN students_details sd ON gr.ans_id = sd.ans_id 
                WHERE gr.template_id = ? 
                GROUP BY gr.ans_id
            """
            df = pd.read_sql(query, conn, params=(selected_tid,))
            
            if search_name:
                df = df[df['name'].str.contains(search_name, case=False, na=False)]
            if search_roll:
                df = df[df['roll_no'].astype(str).str.contains(search_roll)]

            if df.empty: 
                st.info(f"No records found.")
            else:
                st.write(f"📍 Template: {selected_tid} | Records: {len(df)}")
                for idx, row in df.iterrows():
                    st.markdown(f"<div style='background:white; padding:12px; border-radius:10px; border-left:5px solid #7b2cff; margin-bottom:8px;'><b>{row['name']}</b> | ID: {row['ans_id']} | Roll: {row['roll_no']}<br><span style='color:gray;'>{row['class']} | {row['email']}</span></div>", unsafe_allow_html=True)
                    cv, ce = st.columns([3, 1])
                    if cv.button(f"🔍 View Full Academic Profile", key=f"v_{row['ans_id']}"):
                        st.session_state.viewing_student_id = row['ans_id']
                        st.rerun()
                    
                    if ce.button(f"✉️ Send Email", key=f"e_{row['ans_id']}"):
                        with st.spinner(f"Sending email to {row['name']}..."):
                            # 1. Get GIBO Report from Database
                            eval_query = f"SELECT email_report FROM gibo_evaluations WHERE ans_id='{row['ans_id']}'"
                            eval_df = pd.read_sql(eval_query, conn)
                            
                            if eval_df.empty:
                                st.error("❌ Please run GIBO Evaluation first to generate the report!")
                            else:
                                report_text = eval_df['email_report'].iloc[0]
                                
                                # 2. Generate the PDF on the fly
                                # UPDATED: Fetching the full result row to get grade and marks for the PDF
                                full_res = pd.read_sql(f"SELECT * FROM grading_results WHERE ans_id='{row['ans_id']}'", conn).iloc[0]
                                mq_df_mail = pd.read_sql(f"SELECT section, qid, status, marks_obtained, max_marks FROM marks_per_question WHERE ans_id='{row['ans_id']}'", conn)
                                
                                # This now passes the Grade, Roll, and Marks correctly to the generator
                                pdf_data = generate_score_pdf(
                                    full_res['name'], 
                                    full_res['roll_no'], 
                                    selected_tid, 
                                    full_res['grade'], 
                                    mq_df_mail
                                )
                                
                                # 3. Prepare a summary for the email body (Optional but recommended)
                                summary_header = f"""
                                ACADEMIC PERFORMANCE SUMMARY
                                ----------------------------
                                Final Grade: {full_res['grade']}
                                Marks: {full_res['marks_awarded']} / {full_res['total_marks']}
                                Percentage: {full_res['percentage']}
                                ----------------------------
                                
                                """
                                full_email_body = summary_header + report_text

                                # 4. Send via Email Service
                                success = send_gibo_email(
                                    recipient_email=row['email'],
                                    student_name=row['name'],
                                    report_data=full_email_body, # Includes the grade summary in the text too
                                    attachment_data=pdf_data
                                )
                                
                                if success:
                                    st.success(f"✅ Email successfully sent to {row['email']}!")
                                else:
                                    st.error("❌ SMTP Error. Check your App Password or Internet.")
                    
        elif option == "Analysis":
            # THIS IS YOUR ORIGINAL CODE INTACT
            df = pd.read_sql("SELECT DISTINCT ans_id, grade, marks_awarded, total_marks, percentage FROM grading_results WHERE template_id = ?", conn, params=(selected_tid,))
            if not df.empty:
                st.markdown(f"### 📈 Performance Analytics - {selected_tid}")
                c1, c2, c3, c4 = st.columns(4)
                total_s = len(df); avg_p = df['percentage'].str.replace('%','').astype(float).mean()
                top_g = df[df['grade'].isin(['A','A+'])].shape[0]; fail_g = df[df['grade'] == 'F'].shape[0]
                c1.metric("Total Students", total_s); c2.metric("Avg. Percentage", f"{avg_p:.1f}%")
                c3.metric("High Achievers (A/A+)", top_g); c4.metric("Needs Support (F)", fail_g)
                col_pie, col_bar = st.columns(2)
                with col_pie:
                    fig_pie = px.pie(df, names='grade', hole=0.4, title="Grade Distribution", color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col_bar:
                    grade_counts = df['grade'].value_counts().reset_index()
                    grade_counts.columns = ['Grade', 'Count']
                    grade_order = ['A+', 'A', 'B', 'C', 'D', 'E', 'F']
                    grade_counts['Grade'] = pd.Categorical(grade_counts['Grade'], categories=grade_order, ordered=True)
                    grade_counts = grade_counts.sort_values('Grade')
                    fig_bar = px.bar(grade_counts, x='Grade', y='Count', title="Student Count per Grade", color='Grade', color_discrete_map={'A+':'#2ECC71','A':'#27AE60','B':'#F1C40F','C':'#E67E22','F':'#E74C3C'})
                    st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown("#### 🎯 Student Marks Distribution")
                fig_scatter = px.scatter(df, x='ans_id', y='percentage', color='grade', hover_data=['grade'], size_max=15, title="Individual Student Percentages")
                st.plotly_chart(fig_scatter, use_container_width=True)

        elif option == "Concept Analysis":
            st.markdown(f"### 🧠 Advanced Pedagogical Insights - {selected_tid}")
            
            # --- 1. MOST SKIPPED QUESTIONS (TEMPLATE SPECIFIC) ---
            st.markdown("#### 🚫 Mostly Skipped Questions")
            
            # The JOIN condition now 'locks' the template ID for the rubric as well
            skipped_query = f"""
                SELECT m.qid, r.question_text, COUNT(*) as skip_count
                FROM marks_per_question m
                JOIN master_rubric r ON m.qid = r.qid 
                WHERE r.template_id = '{selected_tid}' 
                AND m.ans_id LIKE 'ans_{selected_tid}%' 
                AND m.status = 'Not Attempted'
                GROUP BY m.qid, r.question_text
                ORDER BY skip_count DESC
            """
            
            skip_df = pd.read_sql(skipped_query, conn)
            
            if not skip_df.empty:
                # Bar chart stays as is since you liked it
                fig_skip = px.bar(
                    skip_df, 
                    x='qid', 
                    y='skip_count', 
                    hover_data=['question_text'],
                    labels={'qid': 'Question ID', 'skip_count': 'Total Skips'},
                    title=f"Commonly Skipped Questions in {selected_tid}",
                    color='skip_count',
                    color_continuous_scale='Reds' 
                )
                st.plotly_chart(fig_skip, use_container_width=True)
                
                st.write(f"📝 **Question Text for {selected_tid}:**")
                st.dataframe(skip_df[['qid', 'question_text', 'skip_count']], use_container_width=True, hide_index=True)
            else:
                st.success(f"✨ Great news! No questions were skipped in template {selected_tid}.")

            st.divider()

            # --- 2. COMMONLY MISSED CONCEPTS ---
            st.markdown("#### 💡 Commonly Missed Concepts")
            
            concept_query = f"""
                SELECT gdf.missing_concepts FROM gibo_detailed_feedback gdf
                JOIN grading_results gr ON gdf.ans_id = gr.ans_id
                WHERE gr.template_id = '{selected_tid}'
            """
            c_df = pd.read_sql(concept_query, conn)
            
            if not c_df.empty:
                all_concepts = []
                for row in c_df['missing_concepts'].dropna():
                    parts = [c.strip() for c in row.split(',') if c.strip()]
                    all_concepts.extend(parts)
                
                if all_concepts:
                    concept_counts = pd.Series(all_concepts).value_counts().reset_index()
                    concept_counts.columns = ['Concept', 'Frequency']
                    
                    # UPDATED: Using 'YlOrBr' for better text contrast and added label formatting
                    fig_tree = px.treemap(
                        concept_counts, 
                        path=['Concept'], 
                        values='Frequency', 
                        title=f"Top Conceptual Gaps in {selected_tid}", 
                        color='Frequency', 
                        color_continuous_scale='YlOrBr' # Much better for visibility
                    )
                    
                    # Forces the text to be visible and clean
                    fig_tree.update_traces(textinfo="label+value", textfont_size=14)
                    
                    st.plotly_chart(fig_tree, use_container_width=True)
                    st.table(concept_counts.head(10))
                else:
                    st.info(f"No specific conceptual gaps identified for {selected_tid}.")
            else:
                st.warning(f"⚠️ No GIBO evaluation data found for {selected_tid}.")

    # FINAL ELSE: When no template is selected in the sidebar
    else:
        st.info("👈 Please select an Academic Template from the sidebar to view records or analysis.")
    conn.close()
# =====================================================
# 6. ROUTER
# =====================================================
pages = {
    "landing": landing_page,
    "login": login_page,
    "admin_dashboard": admin_management_section,
    "teacher_dashboard": teacher_dashboard
}
pages[st.session_state.page]()