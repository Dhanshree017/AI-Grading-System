import os
import re
import csv

BASE = r"C:\AI_Grading_System"
ANS_DIR = os.path.join(BASE, "dataset", "ocr_output", "answers")
OUT_CSV = os.path.join(BASE, "dataset", "Machine_Learning", "metadata", "students_details.csv")

# --- IMPROVED PATTERNS ---
# We look for "Name" and grab the rest of the line, then we clean it manually.
NAME_LINE_RE = re.compile(r"name\s*[:\-]\s*(.*)", re.I)
ROLL_RE = re.compile(r"roll\s*no\s*[:\-]?\s*(\d+)", re.I)
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+")
CLASS_RE = re.compile(r"(?:class|grade|year|dept|div)\s*[:\-]\s*([A-Za-z0-9\- ]+)", re.I)

def clean_name_robust(raw_line):
    """
    Takes the whole line after 'Name:' and removes everything from 
    'Roll no', 'Class', or messy symbols.
    """
    if not raw_line:
        return "Unknown"
    
    # 1. Force stop at common markers
    # This cuts the string as soon as any of these words appear
    stop_words = ["roll", "no", "class", "grade", "email", "year", "div"]
    cleaned = raw_line
    for word in stop_words:
        # Find the word (case insensitive) and cut everything after it
        match = re.search(rf"\b{word}\b", cleaned, re.IGNORECASE)
        if match:
            cleaned = cleaned[:match.start()]
            
    # 2. Remove non-alphabetic junk at the end or beginning (OCR noise)
    # This leaves only Letters, Spaces, and Dots (for initials)
    cleaned = re.sub(r"[^A-Za-z\s\.]", "", cleaned)
    
    # 3. Final trim
    cleaned = cleaned.strip()
    
    # 4. Fallback if the cleaning removed everything
    return cleaned if len(cleaned) > 2 else "Unknown"

print("🔍 Scanning OCR answers folder:", ANS_DIR)

rows = []
for fname in os.listdir(ANS_DIR):
    if not fname.lower().endswith(".txt"): continue
    
    path = os.path.join(ANS_DIR, fname)
    m = re.match(r"ans_(T\d+)_?(\d+)", fname, re.I)
    if not m: continue

    template_id = m.group(1)
    roll_from_name = m.group(2)

    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # --- NEW EXTRACTION LOGIC ---
    name = "Unknown"
    nm_match = NAME_LINE_RE.search(text)
    if nm_match:
        name = clean_name_robust(nm_match.group(1))

    # Roll No
    rm = ROLL_RE.search(text)
    roll = rm.group(1) if rm else roll_from_name

    # Email
    em = EMAIL_RE.search(text)
    email = em.group(0) if em else "Not Found"

    # Class
    cm = CLASS_RE.search(text)
    student_class = cm.group(1).strip() if cm else "Not Specified"

    rows.append([fname.replace(".txt", ""), template_id, roll, name, email, student_class])

# Save CSV
try:
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ans_id", "template_id", "roll_no", "name", "email", "class"])
        writer.writerows(rows)
    print(f"\n✅ Clean names saved to: {OUT_CSV}")
except PermissionError:
    print(f"\n❌ ERROR: Close the CSV file in Excel first!")