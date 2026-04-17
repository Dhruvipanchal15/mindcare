from flask import Flask, render_template, request, redirect, session, jsonify
from dotenv import load_dotenv
from flask_mysqldb import MySQL
import google.generativeai as genai
import pymysql
import os
from datetime import datetime

# Load Environment
load_dotenv()

# Flask App
app = Flask(__name__)
app.secret_key = "mindcare_secret_key"

from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

app = Flask(__name__)
# SECRET KEY FOR SESSION
app.secret_key = "mindcare_secret_key_two"
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mind_care'


mysql = MySQL(app)

# Database Connection
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="mind_care",
    autocommit=True
)
cursor = conn.cursor()

from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy


# ✅ DB CONNECTION
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/mind_care'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= MODELS =================
# ================= MODELS =================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))   # ✅ you have this in DB


class Mood(db.Model):
    __tablename__ = 'mood'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    mood = db.Column(db.String(50))
    # ❌ removed date (not in DB)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    # ❌ removed doctor (not in DB)
    # ❌ removed date (if not in DB)


class Journal(db.Model):
    __tablename__ = 'journal'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
   
    # ❌ removed date (if not in DB)


class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))



# ================= HOME =================
@app.route('/')
def index():
    return render_template('index.html')


# ================= ADMIN DASHBOARD =================
@app.route('/admin')
def admin():

    print("SESSION DATA:", session)

    if 'admin' not in session:
        return redirect('/admin_login')

    admin_user = Admin.query.get(session['admin'])   # ✅ AFTER CHECK

    return render_template("admin.html",
                           admin=admin_user,   # ✅ THIS WAS MISSING
                           users=User.query.all(),
                           moods=Mood.query.all(),
                           appointments=Appointment.query.all(),
                           journals=Journal.query.all(),
                           happy=Mood.query.filter_by(mood="Happy").count(),
                           sad=Mood.query.filter_by(mood="Sad").count(),
                           neutral=Mood.query.filter_by(mood="Neutral").count())
# ================= ADMIN LOGIN =================
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():

    print("METHOD:", request.method)
    print("FORM DATA:", request.form)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username, password=password).first()

        print("ADMIN FOUND:", admin)

        if admin:
            session['admin'] = admin.id
            return redirect('/admin')

    return render_template('admin_login.html')


@app.route('/check_admin')
def check_admin():
    admins = Admin.query.all()
    return str([(a.username, a.password) for a in admins])

# ================= ADMIN REGISTER =================
@app.route('/admin_register', methods=['POST'])
def admin_register():

    username = request.form['username']
    password = request.form['password']

    new_admin = Admin(username=username, password=password)
    db.session.add(new_admin)
    db.session.commit()

    # ✅ AUTO LOGIN
    session['admin'] = new_admin.id

    return redirect('/admin')


# ================= ADMIN LOGOUT =================
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin_login')


# ================= UPDATE PASSWORD =================
@app.route('/update_admin_password', methods=['POST'])
def update_admin_password():

    if 'admin' not in session:
        return redirect('/admin_login')

    admin = Admin.query.get(session['admin'])
    admin.password = request.form['new_password']

    db.session.commit()

    return redirect('/admin')


@app.route('/clear')
def clear():
    session.clear()
    return "Session Cleared"

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":
        u = request.form["username"]
        e = request.form["email"]
        p = request.form["password"]

        cursor.execute(
            "INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
            (u,e,p)
        )
        conn.commit()

        return redirect("/login")

    return render_template("register.html")
@app.route("/firebase_login", methods=["POST"])
def firebase_login():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")

    # check if user exists
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
            (name, email, "google_auth")
        )
        conn.commit()

    session["user"] = name
    session["email"] = email
    session["photo"] = data.get("photo")

    return jsonify({"status":"success"})

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (u, p)
        )
        user = cursor.fetchone()

        if user:
            session["user"] = user[1]
            session["user_id"] = user[0]
            session["chat_history"] = []
            return redirect("/dashboard")

    return render_template("login.html")

from datetime import datetime, timedelta
from flask import session, redirect, render_template


# -------- STREAK FUNCTION --------

def calculate_streak(dates):

    # Remove duplicates and sort latest first
    dates = sorted(set(dates), reverse=True)

    today = datetime.today().date()

    streak = 0

    for i, d in enumerate(dates):

        if d == today - timedelta(days=i):
            streak += 1
        else:
            break

    return streak
# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    user_id = session['user_id']

    cur = conn.cursor()

    cur.execute(
        "SELECT created_at FROM journal WHERE user_id=%s",
        (user_id,)
    )

    rows = cur.fetchall()

    dates = [r[0].date() for r in rows]

    streak = calculate_streak(dates)
    

    # GET ALL APPOINTMENTS

    cursor.execute("""
        SELECT doctors.name, appointments.date, appointments.time
        FROM appointments
        JOIN doctors ON appointments.doctor_id = doctors.id
        WHERE appointments.user_id = %s
        ORDER BY appointments.date ASC, appointments.time ASC
    """, (session["user_id"],))

    data = cursor.fetchall()

    from datetime import datetime

    now = datetime.now()

    upcoming = None

    # FIND NEXT UPCOMING APPOINTMENT

    for apt in data:

        date_str = str(apt[1])
        time_str = str(apt[2]).strip()

        try:
            appointment_datetime = datetime.strptime(
                date_str + " " + time_str,
                "%Y-%m-%d %H:%M"
            )
        except:
            try:
                appointment_datetime = datetime.strptime(
                    date_str + " " + time_str,
                    "%Y-%m-%d %I:%M %p"
                )
            except:
                continue

        if appointment_datetime > now:
            upcoming = apt
            break

    return render_template(
        "dashboard.html",
        streak=streak,
        upcoming=upcoming
    )


# ---------------- AI CHAT ----------------
@app.route("/ai_chat", methods=["GET","POST"])
def ai_chat():

    if "messages" not in session:
        session["messages"] = []

    # Only handle message when POST
    if request.method == "POST":

        user_msg = request.form.get("message")

        if user_msg:  # avoid empty input

            # Save user message
            session["messages"].append({
                "sender": "You",
                "text": user_msg
            })

            response = client.chat.completions.create(
                model="google/gemini-2.5-flash-lite",
                messages=[
                    {
                        "role": "system",
                        "content": """
You are a calm mental wellness assistant.
Keep replies Medium (5-6 lines).
Use bullet points if helpful.
Avoid long paragraphs.
"""
                    },
                    {"role": "user", "content": user_msg}
                ]
            )

            reply = response.choices[0].message.content

            # Save AI reply
            session["messages"].append({
                "sender": "AI",
                "text": reply
            })

            session.modified = True

        return redirect("/ai_chat")

    # For GET request just show chat page
    return render_template("ai_chat.html",
                           messages=session["messages"])




# ---------------- BREATHING ----------------
@app.route("/breathing")
def breathing():
    return render_template("breathing.html")


# ---------------- JOURNAL ----------------
@app.route("/journal", methods=["GET","POST"])
def journal():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    if request.method == "POST":
        text = request.form["entry"]
        cursor.execute(
            "INSERT INTO journal (user_id, entry) VALUES (%s,%s)",
            (user_id, text)
        )
        conn.commit()
        return redirect("/journal?success=1")

    cursor.execute(
        "SELECT id, entry, created_at FROM journal WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,)
    )
    entries = cursor.fetchall()

    return render_template("journal.html", entries=entries)


# ---------------- VIEW JOURNAL ----------------
@app.route("/journal/view")
def view_journal():
    if "user_id" not in session:
        return redirect("/login")

    cursor.execute(
        "SELECT entry, created_at FROM journal WHERE user_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    entries = cursor.fetchall()

    return render_template("view_journal.html", entries=entries)


# ---------------- MOOD TRACKER ----------------
@app.route("/mood", methods=["GET","POST"])
def mood():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        mood_text = request.form.get("mood")
        category = request.form.get("category")
        note = request.form.get("note")

        cursor.execute(
            """
            INSERT INTO mood (user_id, mood, category, note)
            VALUES (%s,%s,%s,%s)
            """,
            (session["user_id"], mood_text, category, note)
        )

        conn.commit()
        return redirect("/mood?success=1")
    
    return render_template("mood.html")


# ---------------- WEEKLY REPORT ----------------
@app.route("/weekly_report")
def weekly_report():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    # Mood Data
    cursor.execute("""
        SELECT mood, created_at
        FROM mood
        WHERE user_id=%s
        AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """, (user_id,))
    moods = cursor.fetchall()

    avg_mood = 0
    best_day = None
    worst_day = None

    if moods:
        valid_moods = [m for m in moods if m[0] is not None]

        if valid_moods:

         mood_map = {
         "Happy":5,
         "Calm":4,
         "Neutral":3,
         "Annoyed":2,
         "Sad":1
    }

    ratings = [mood_map.get(m[0],3) for m in valid_moods]

    avg_mood = sum(ratings)/len(ratings)

    best = max(valid_moods, key=lambda x: mood_map.get(x[0],3))
    worst = min(valid_moods, key=lambda x: mood_map.get(x[0],3))

    best_day = best[1].strftime("%Y-%m-%d")
    worst_day = worst[1].strftime("%Y-%m-%d")

    # Journal Data
    cursor.execute("""
        SELECT entry FROM journal
        WHERE user_id=%s
        AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """, (user_id,))
    journals = cursor.fetchall()

    total_entries = len(journals)

    positive_words = ["happy","good","great","relaxed","excited"]
    negative_words = ["sad","stress","tired","angry","bad"]

    pos_count = 0
    neg_count = 0

    for j in journals:
        text = j[0].lower()
        if any(w in text for w in positive_words):
            pos_count += 1
        if any(w in text for w in negative_words):
            neg_count += 1

    # Wellness Score
    wellness_score = max(0, min(100, (avg_mood*20) + (pos_count-neg_count)*2))

    return render_template(
        "weekly_report.html",
        avg_mood=round(avg_mood,2),
        best_day=best_day or "No Data",
        worst_day=worst_day or "No Data",
        total_entries=total_entries,
        pos_count=pos_count,
        neg_count=neg_count,
        wellness_score=round(wellness_score,2)
    )

from datetime import datetime

@app.route("/book/<int:doc_id>", methods=["GET","POST"])
def book(doc_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]
        concern = request.form.get("concern")

        # Save appointment
        cursor.execute("""
            INSERT INTO appointments
            (user_id, doctor_id, name, date, time, concern)
            VALUES (%s,%s,%s,%s,%s,%s)
        """,(session["user_id"], doc_id, name, date, time, concern))

        conn.commit()

        # Get doctor name
        cursor.execute("SELECT name FROM doctors WHERE id=%s",(doc_id,))
        doctor = cursor.fetchone()

        # Google Calendar format
        start = datetime.strptime(date+" "+time,"%Y-%m-%d %H:%M")
        start_str = start.strftime("%Y%m%dT%H%M%S")

        calendar_link = (
            "https://calendar.google.com/calendar/render?"
            f"action=TEMPLATE&text=Doctor Appointment"
            f"&dates={start_str}/{start_str}"
            f"&details=Mental wellness consultation reminder"
        )

        return render_template(
            "confirm.html",
            doctor=doctor[0],
            date=date,
            time=time,
            calendar_link=calendar_link
        )

    return render_template("book.html", doc_id=doc_id)

# ---------------- appointments ----------------
from datetime import datetime

@app.route("/appointments")
def appointments():

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT a.name, d.name, a.date, a.time, a.concern
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id=%s
        ORDER BY a.date, a.time
    """, (session["user_id"],))

    data = cursor.fetchall()

    now = datetime.now()

    upcoming = []
    past = []

    for apt in data:

        date_str = str(apt[2])
        time_str = str(apt[3]).upper().strip()

        try:
            # 24-hour format
            appointment_datetime = datetime.strptime(
                date_str + " " + time_str,
                "%Y-%m-%d %H:%M"
            )
        except:
            try:
                # 12-hour format (6 PM)
                appointment_datetime = datetime.strptime(
                    date_str + " " + time_str,
                    "%Y-%m-%d %I %p"
                )
            except:
                continue

        if appointment_datetime >= now:
            upcoming.append(apt)
        else:
            past.append(apt)

    return render_template(
        "appointments.html",
        upcoming=upcoming,
        past=past
    )
# ---------------- OTHER PAGES ----------------
@app.route("/help")
def help():

    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()

    return render_template("help.html", doctors=doctors)


@app.route("/affirmations", methods=["GET", "POST"])
def affirmations():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    # Save affirmation
    if request.method == "POST":
        text = request.form.get("affirmation")

        if text:
            cursor.execute(
                "INSERT INTO affirmations (user_id, text) VALUES (%s,%s)",
                (user_id, text)
            )
            conn.commit()

        return redirect("/affirmations")   # ⭐ IMPORTANT

    # Default affirmations
    default_affirmations = [
        "I am strong and capable.",
        "I deserve happiness.",
        "I grow every day.",
        "I believe in myself.",
        "Peace begins with me."
    ]

    cursor.execute(
        "SELECT id, text FROM affirmations WHERE user_id=%s ORDER BY id DESC",
    (user_id,)
    )
    user_affirmations = cursor.fetchall()

    return render_template(
        "affirmations.html",
        default_affirmations=default_affirmations,
        user_affirmations=user_affirmations
    )
    
@app.route("/delete_affirmation/<int:id>")
def delete_affirmation(id):
    if "user_id" not in session:
        return redirect("/login")

    cursor.execute(
        "DELETE FROM affirmations WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    conn.commit()

    return redirect("/affirmations")

@app.route("/thoughts")
@app.route("/tips/<topic>")
def thoughts(topic=None):

    tips_data = {
        "stress": [
            "Practice deep breathing daily.",
            "Break tasks into smaller steps.",
            "Stay physically active regularly.",
            "Share feelings with trusted people.",
            "Maintain healthy personal boundaries."
        ],

        "panic": [
            "Focus on slow breathing.",
            "Ground yourself using senses.",
            "Remind yourself it is temporary.",
            "Relax muscles consciously.",
            "Move to a calm environment."
        ],

        "selfcare": [
            "Prioritize rest and sleep.",
            "Engage in hobbies you enjoy.",
            "Practice gratitude daily.",
            "Avoid negative self-talk.",
            "Take guilt-free breaks."
        ],

        "detox": [
            "Schedule device-free time daily.",
            "Avoid screens before bedtime.",
            "Disable unnecessary notifications.",
            "Engage in offline activities.",
            "Monitor social media usage."
        ],

        "sleep": [
            "Maintain consistent sleep schedule.",
            "Create calming bedtime routine.",
            "Limit caffeine at night.",
            "Keep bedroom dark and quiet.",
            "Journal to reduce overthinking."
        ]
    }

    return render_template(
        "thoughts.html",
        topic=topic,
        tips=tips_data.get(topic, [])
    )



# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
