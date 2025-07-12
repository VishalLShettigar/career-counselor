from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify, flash
from utils.resume_parser import extract_resume_data, recommend_career
from io import BytesIO
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename
from collections import defaultdict
import os
import json
import math
import bcrypt
import sqlite3
from datetime import datetime



app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = 'static/resumes/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
def get_db_connection():
    conn = sqlite3.connect('career_counselor.db')  # Use the correct DB file
    conn.row_factory = sqlite3.Row
    return conn



@app.route('/')
def root():
    return redirect('/home')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        flash("Please login to continue.", "warning")
        return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
    return render_template('register.html')

@app.route('/recruiter-register', methods=['GET', 'POST'])
def recruiter_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO recruiter (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
            conn.commit()
            flash("Recruiter registration successful! Please login.", "success")
            return redirect('/recruiter-login')
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
    return render_template('recruiter_register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['username'] = username
            session['user_email'] = user['email']
            flash("Login successful!", "success")
            return redirect('/index')
        else:
            flash("Invalid username or password!", "danger")
    return render_template('login.html')

@app.route('/recruiter-login', methods=['GET', 'POST'])
def recruiter_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, password FROM recruiter WHERE username = ?", (username,))
        recruiter = cursor.fetchone()

        if recruiter and bcrypt.checkpw(password.encode('utf-8'), recruiter['password']):
            session['recruiter_id'] = recruiter['id']
            return redirect('/job-postings')
        else:
            flash("Invalid username or password!", "danger")

    return render_template('recruiter_login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect('/login')

@app.route('/logout1')
def logout1():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect('/recruiter-login')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        flash("Please log in first.", "warning")
        return redirect('/login')


@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return render_template('result.html', result={'error': 'No file uploaded.'}, recommendations=[])

    file = request.files['resume']
    if file.filename == '':
        return render_template('result.html', result={'error': 'No file selected.'}, recommendations=[])

    file.seek(0)
    result = extract_resume_data(file)
    if 'error' in result:
        return render_template('result.html', result=result, recommendations=[])

    skills = result.get('skills', [])
    recommendations = recommend_career(skills)
    result['recommendations'] = recommendations

    score = result.get('score', 0)
    label = "Excellent" if score >= 85 else "Good" if score >= 70 else "Average" if score >= 50 else "Poor"
    result['score_label'] = label

    session['result'] = result
    session['recommendations'] = recommendations

    return render_template('result.html', result=result, recommendations=recommendations)


@app.route('/result')
def show_result():
    result = session.get('result')
    recommendations = session.get('recommendations', [])
    if not result:
        return redirect(url_for('home'))
    return render_template('result.html', result=result, recommendations=recommendations)


@app.route('/about-scoring')
def about_scoring():
    result = session.get('result')
    return render_template('about_scoring.html', result=result)


@app.route('/chart', methods=['POST'])
def chart():
    skills = request.form.get('skills')
    email = request.form.get('email', 'Not Found')
    phone = request.form.get('phone', 'Not Found')
    education = request.form.get('education', '')
    length = int(request.form.get('length', 0))

    # Convert stringified skills JSON into Python list
    try:
        skills_list = json.loads(skills) if skills else []
    except Exception:
        skills_list = eval(skills) if skills else []

    score_breakdown = {
        'Email': 10 if email != 'Not Found' else 0,
        'Phone': 10 if phone != 'Not Found' else 0,
        'Skills': min(len(skills_list), 6) * 5,
        'Education': 10 if education and education != 'Not Found' else 0,
        'Experience': 10 if 'experience' in request.form else 0,
        'Length': 10 if length > 500 else 0
    }

    return render_template("chart.html", skills=skills_list, score_breakdown=score_breakdown)

@app.route("/download-report", methods=["POST"])
def download_report():
    data = request.form
    email = data.get("email", "Not Available")
    phone = data.get("phone", "Not Available")
    score = data.get("score", "N/A")
    score_label = data.get("score_label", "N/A")
    skills = data.getlist("skills")
    careers = data.getlist("careers")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(100, 800, "Career Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 780, f"Email: {email}")
    pdf.drawString(100, 760, f"Phone: {phone}")
    pdf.drawString(100, 740, f"Score: {score} - {score_label}")
    pdf.drawString(100, 720, "Skills: " + ', '.join(skills))
    pdf.drawString(100, 700, "Recommended Careers:")
    y = 680
    for career in careers:
        pdf.drawString(120, y, f"- {career}")
        y -= 20
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="career_report.pdf", mimetype='application/pdf')


@app.route('/generate-resume-template', methods=["POST"])
def generate_resume_template():
    email = request.form.get('email')
    phone = request.form.get('phone')
    score = request.form.get('score')
    score_label = request.form.get('score_label')
    skills = request.form.getlist('skills')
    careers = request.form.getlist('careers')
    data = {
        'name': 'Your Name Here',
        'email': email,
        'phone': phone,
        'summary': f'Skilled in {", ".join(skills)}. Looking for opportunities as {", ".join(careers)}.',
        'skills': skills,
        'education': 'MCA, Your University Name, 2025',
        'experience': 'Internship at XYZ Company (2024)',
        'projects': ['AI Career Counselor Project'],
        'score': score,
        'score_label': score_label
    }
    return render_template('resume_template.html', data=data)


@app.route('/resume-builder')
def resume_builder():
    return render_template('resume_questions.html')


@app.route("/generate-resume", methods=["POST"])
def generate_resume():
    data = request.form
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    linkedin = data.get("linkedin")
    skills = data.get("skills")
    experience = data.get("experience")
    courses = data.get("courses")
    education = request.form.getlist("education[]")
    projects = request.form.getlist("projects[]")
    achievements = request.form.getlist("achievements[]")
    workshops = request.form.getlist("workshops[]")
    certifications = request.form.getlist("certifications[]")
    photo_file = request.files.get("photo")
    photo_filename = None
    if photo_file and photo_file.filename:
        os.makedirs("static/uploads", exist_ok=True)
        photo_filename = secure_filename(photo_file.filename)
        photo_path = os.path.join("static/uploads", photo_filename)
        photo_file.save(photo_path)

    return render_template("generated_resume.html",
        name=name, email=email, phone=phone, linkedin=linkedin, skills=skills, experience=experience,
        courses=courses, education=education, projects=projects, achievements=achievements,
        workshops=workshops, certifications=certifications, photo=photo_filename)


@app.route('/email-resume', methods=['POST'])
def email_resume():
    recipient = request.form.get('recipient')
    return jsonify({
        "success": True,
        "message": f"✅ Resume successfully sent to {recipient}"
    })


@app.route('/free-ai')
def redirect_to_free_ai():
    return redirect("https://huggingface.co/chat/")


@app.route('/about-project')
def about_project():
    return render_template('about.html')


@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')


@app.route('/owner-login')
def owner_login():
    return render_template('owner_login.html')


@app.route('/job-postings', methods=['GET', 'POST'])
def job_postings():
    if 'recruiter_id' not in session:
        return redirect('/recruiter-login')

    recruiter_id = session['recruiter_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form
        job_id = data.get('job_id')

        if job_id:
            cursor.execute("""
                UPDATE job SET company=?, designation=?, experience_required=?, qualification=?, 
                    skills_required=?, contact_number=?, email=?
                WHERE id=? AND recruiter_id=?
            """, (
                data['company'], data['designation'], data['experience_required'], data['qualification'],
                data['skills_required'], data['contact_number'], data['email'], job_id, recruiter_id
            ))
            session['job_message'] = "Job updated successfully!"
        else:
            cursor.execute("""
                INSERT INTO job (recruiter_id, company, designation, experience_required, qualification, 
                    skills_required, contact_number, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recruiter_id, data['company'], data['designation'], data['experience_required'],
                data['qualification'], data['skills_required'], data['contact_number'], data['email']
            ))
            session['job_message'] = "Job posted successfully!"

        conn.commit()
        return redirect('/job-postings')

    cursor.execute("SELECT * FROM job WHERE recruiter_id = ? ORDER BY posted_at DESC", (recruiter_id,))
    jobs = cursor.fetchall()
    return render_template("job_postings.html", jobs=jobs, job_data=None)

@app.route('/edit-job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    if 'recruiter_id' not in session:
        return redirect('/recruiter-login')

    recruiter_id = session['recruiter_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form
        cursor.execute("""
            UPDATE job SET company=?, designation=?, experience_required=?, qualification=?, 
                skills_required=?, contact_number=?, email=?
            WHERE id=? AND recruiter_id=?
        """, (
            data['company'], data['designation'], data['experience_required'], data['qualification'],
            data['skills_required'], data['contact_number'], data['email'], job_id, recruiter_id
        ))
        conn.commit()
        session['job_message'] = "Job updated successfully!"
        return redirect('/job-postings')

    cursor.execute("SELECT * FROM job WHERE id = ? AND recruiter_id = ?", (job_id, recruiter_id))
    job_data = cursor.fetchone()

    if not job_data:
        return redirect('/job-postings')

    cursor.execute("SELECT * FROM job WHERE recruiter_id = ? ORDER BY posted_at DESC", (recruiter_id,))
    jobs = cursor.fetchall()
    return render_template("job_postings.html", jobs=jobs, job_data=job_data)


@app.route('/delete-job/<int:job_id>')
def delete_job(job_id):
    if 'recruiter_id' not in session:
        return redirect('/recruiter-login')

    recruiter_id = session['recruiter_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job WHERE id = ? AND recruiter_id = ?", (job_id, recruiter_id))
    conn.commit()
    session['job_message'] = "Job deleted successfully!"
    return redirect('/job-postings')



@app.route('/clear-message', methods=['POST'])
def clear_message():
    session.pop('job_message', None)
    return redirect('/job-postings')


@app.route('/owner', methods=['GET', 'POST'])
def owner():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM owner WHERE username = ?", (username,))
        owner = cursor.fetchone()

        if owner and bcrypt.checkpw(password.encode('utf-8'), owner['password']):
            session['owner_id'] = owner['id']
            return redirect('/admin-dashboard')
        else:
            flash('Invalid username or password', 'danger')
            return redirect('/owner-login')

    return render_template('owner_login.html')


@app.route('/admin-dashboard')
def admin_dashboard():
    if 'owner_id' not in session:
        return redirect('/owner-login')
    return render_template('admin_dashboard.html')


@app.route('/logout-owner')
def logout_owner():
    session.pop('owner_id', None)
    flash("Logged out successfully!", "info")
    return redirect('/owner-login')


@app.route('/set-owner', methods=['GET', 'POST'])
def set_owner():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        stage = request.args.get('stage')
        if stage == 'change':
            return render_template('set_owner.html', stage='change_form')
        return render_template('set_owner.html', stage='initial')

    if request.method == 'POST':
        step = request.form.get('step')

        if step == 'verify_old':
            old_username = request.form['old_username']
            old_password = request.form['old_password']

            cursor.execute("SELECT * FROM owner WHERE username = ?", (old_username,))
            owner = cursor.fetchone()

            if owner and bcrypt.checkpw(old_password.encode('utf-8'), owner['password']):
                return render_template('set_owner.html', stage='verified')
            else:
                return render_template('set_owner.html', stage='verify_failed')

        elif step == 'change_new':
            new_username = request.form['new_username']
            confirm_username = request.form['confirm_username']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if new_username != confirm_username or new_password != confirm_password:
                return render_template('set_owner.html', stage='change_form')

            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("DELETE FROM owner")
            cursor.execute("INSERT INTO owner (username, password) VALUES (?, ?)", (new_username, hashed_password))
            conn.commit()

            return render_template('set_owner.html', stage='change_success')


@app.route('/job-search', methods=['GET', 'POST'])
def job_search():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        skill_input = request.form.get('skill', '').lower()
        qualification_input = request.form.get('qualification', '').lower()
        experience_input = request.form.get('experience', '0')

        try:
            experience_val = int(experience_input)
        except ValueError:
            experience_val = 0

        query = """
        SELECT * FROM job
        WHERE 
            LOWER(skills_required) LIKE ? OR
            LOWER(qualification) LIKE ? OR
            experience_required LIKE ?
        """
        cursor.execute(query, (
            f"%{skill_input}%",
            f"%{qualification_input}%",
            f"{experience_val}%",
        ))
        jobs = cursor.fetchall()
        return render_template("job_finder.html", stage="results", jobs=[dict(row) for row in jobs])

    return render_template("job_finder.html", stage="initial")



@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_password = request.form['password']

        query = "UPDATE users SET username=?, email=?, password=? WHERE id=?"
        cursor.execute(query, (new_username, new_email, new_password, user_id))
        conn.commit()
        return redirect(url_for('view_users', status='edit'))

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    return render_template('edit_user.html', user=dict(user) if user else None)


@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return redirect(url_for('view_users', status='delete'))


@app.route('/view-users', methods=['GET'])
def view_users():
    conn = get_db_connection()
    cursor = conn.cursor()

    search = request.args.get('search', '')
    sort = request.args.get('sort', 'username')
    page = int(request.args.get('page', 1))
    per_page = 6

    base_query = "SELECT * FROM users"
    params = []

    if search:
        base_query += " WHERE username LIKE ? OR email LIKE ?"
        params.extend([f"%{search}%", f"%{search}%"])

    base_query += f" ORDER BY {sort}"
    cursor.execute(base_query, params)
    all_users = cursor.fetchall()

    total_users = len(all_users)
    total_pages = (total_users + per_page - 1) // per_page
    start = (page - 1) * per_page
    users = all_users[start:start + per_page]

    edit_user_data = None
    edit_id = request.args.get('edit_id')
    if edit_id:
        cursor.execute("SELECT * FROM users WHERE id = ?", (edit_id,))
        edit_user_data = cursor.fetchone()

    return render_template("view_users.html",
                           users=[dict(user) for user in users],
                           page=page,
                           total_pages=total_pages,
                           total_users=total_users,
                           action_status=request.args.get("status"),
                           edit_user=dict(edit_user_data) if edit_user_data else None)


@app.route('/view-recruiters')
def view_recruiters():
    conn = get_db_connection()
    cursor = conn.cursor()

    search = request.args.get('search', '')
    sort = request.args.get('sort', 'username')
    page = int(request.args.get('page', 1))
    per_page = 6

    query = "SELECT * FROM recruiter"
    params = []

    if search:
        query += " WHERE username LIKE ? OR email LIKE ?"
        params.extend([f"%{search}%", f"%{search}%"])

    query += f" ORDER BY {sort}"
    cursor.execute(query, params)
    all_recruiters = cursor.fetchall()

    total = len(all_recruiters)
    total_pages = (total + per_page - 1) // per_page
    recruiters = all_recruiters[(page - 1) * per_page: page * per_page]

    edit_id = request.args.get("edit_id")
    edit_recruiter = None
    if edit_id:
        cursor.execute("SELECT * FROM recruiter WHERE id = ?", (edit_id,))
        edit_recruiter = cursor.fetchone()

    return render_template("view_recruiters.html",
                           recruiters=[dict(r) for r in recruiters],
                           edit_recruiter=dict(edit_recruiter) if edit_recruiter else None,
                           page=page,
                           total_pages=total_pages,
                           total_recruiters=total,
                           action_status=request.args.get("status"))


@app.route('/edit-recruiter/<int:id>', methods=['POST'])
def edit_recruiter(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    cursor.execute("UPDATE recruiter SET username=?, email=?, password=? WHERE id=?",
                   (username, email, password, id))
    conn.commit()
    return redirect(url_for('view_recruiters', status='edit'))

@app.route('/delete-recruiter/<int:id>', methods=['POST'])
def delete_recruiter(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recruiter WHERE id = ?", (id,))
    conn.commit()
    return redirect(url_for('view_recruiters', status='delete'))

@app.route('/view-jobs')
def view_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()

    search = request.args.get('search', '')
    sort = request.args.get('sort', 'designation')
    page = int(request.args.get('page', 1))
    per_page = 6

    query = "SELECT * FROM job"
    params = []

    if search:
        query += " WHERE company LIKE ? OR designation LIKE ? OR skills_required LIKE ?"
        params.extend([f"%{search}%"] * 3)

    query += f" ORDER BY {sort}"

    cursor.execute(query, params)
    all_jobs = cursor.fetchall()

    total = len(all_jobs)
    total_pages = (total + per_page - 1) // per_page
    jobs = all_jobs[(page - 1) * per_page: page * per_page]

    return render_template("view_jobs.html",
                           jobs=[dict(row) for row in jobs],
                           page=page,
                           total_pages=total_pages,
                           total_jobs=total,
                           request=request,
                           action_status=request.args.get("status"))

@app.route('/delete-jobs/<int:id>', methods=['POST'])
def delete_jobs(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job WHERE id = ?", (id,))
    conn.commit()
    return redirect(url_for('view_jobs', status='delete'))

@app.route('/analytics')
def analytics():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM recruiter")
    recruiter_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM job")
    job_count = cursor.fetchone()[0]

    return render_template("analytics.html",
                           user_count=user_count,
                           recruiter_count=recruiter_count,
                           job_count=job_count)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        data = request.get_json()
        name = data['name']
        email = data['email']
        experience = data['experience']
        user_type = data['user_type']
        suggestions = data['suggestions']
        rating = data['rating']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO feedback (name, email, experience, user_type, suggestions, rating) VALUES (?, ?, ?, ?, ?, ?)",
                       (name, email, experience, user_type, suggestions, rating))
        conn.commit()
        return jsonify({"status": "success"})

    return render_template("feedback.html")

@app.route('/view-feedback')
def view_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()

    search = request.args.get('search', '')
    sort = request.args.get('sort', 'name')
    page = int(request.args.get('page', 1))
    per_page = 6

    query = "SELECT * FROM feedback"
    params = []

    if search:
        query += " WHERE name LIKE ? OR email LIKE ? OR user_type LIKE ?"
        params.extend([f"%{search}%"] * 3)

    query += f" ORDER BY {sort}"

    cursor.execute(query, params)
    all_feedback = cursor.fetchall()

    total = len(all_feedback)
    total_pages = (total + per_page - 1) // per_page
    feedbacks = all_feedback[(page - 1) * per_page: page * per_page]

    return render_template('view-feedback.html',
        feedbacks=[dict(row) for row in feedbacks],
        total_feedback=total,
        total_pages=total_pages,
        page=page,
        action_status=request.args.get('status')
    )

@app.route('/delete-feedback/<int:id>', methods=['POST'])
def delete_feedback(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feedback WHERE id = ?", (id,))
    conn.commit()
    return redirect(url_for('view_feedback', status='delete'))

@app.route('/system-settings')
def system_settings():
    scoring = {
        "skills_weight": 30,
        "experience_weight": 40,
        "education_weight": 30
    }

    ai = {
        "enable_ai_suggestions": True,
        "enable_resume_parsing": True
    }

    owner_name = "Vishal L Shettigar"
    footer = "Smart Career Guidance System"

    return render_template(
        "system_settings.html",
        scoring=scoring,
        ai=ai,
        owner_name=owner_name,
        footer=footer
    )
from flask import request, render_template, session
from werkzeug.utils import secure_filename
from datetime import datetime
import os

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        try:
            applicant_name = request.form.get('applicant_name', '').strip()
            applicant_email = session.get('user_email')
            qualification = request.form.get('qualification', '').strip()
            university = request.form.get('university', '').strip()
            experience = request.form.get('experience', '').strip()
            skills = request.form.get('skills', '').strip()
            resume = request.files.get('resume')

            recruiter_id = request.form.get('recruiter_id')
            job_id = request.form.get('job_id')

            if not resume or resume.filename == '':
                resume_error = "Please upload your resume."
                job = {
                    'designation': request.form.get('designation'),
                    'company': request.form.get('company'),
                    'skills_required': request.form.get('skills_required'),
                    'qualification': qualification,
                    'job_id': job_id,
                    'recruiter_id': recruiter_id
                }
                return render_template('apply.html', job=job, resume_error=resume_error, application_status=None)

            # Save resume file
            filename = secure_filename(resume.filename)
            resume_path = f"resumes/{filename}"
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Insert application data
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO apply (
                    applicant_name, applicant_email, qualification, university,
                    experience, skills, resume_path, recruiter_id, job_id,
                    applied_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                applicant_name, applicant_email, qualification, university,
                experience, skills, resume_path, recruiter_id, job_id,
                datetime.now(), 'pending'
            )
            cursor.execute(query, values)
            conn.commit()

            job = {
                'designation': request.form.get('designation'),
                'company': request.form.get('company'),
                'skills_required': request.form.get('skills_required'),
                'qualification': qualification,
                'job_id': job_id,
                'recruiter_id': recruiter_id
            }

            return render_template('apply.html', job=job, application_status='success', resume_error=None)

        except Exception as e:
            return f"Unexpected Error: {str(e)}", 500

    # For GET requests (loading the form)
    job = {
        'designation': request.args.get('designation'),
        'company': request.args.get('company'),
        'skills_required': request.args.get('skills_required'),
        'qualification': request.args.get('qualification'),
        'job_id': request.args.get('job_id'),
        'recruiter_id': request.args.get('recruiter_id')
    }
    return render_template('apply.html', job=job, application_status=None, resume_error=None)


from flask import request, render_template, session, redirect
from collections import defaultdict
import math

@app.route('/view-applications')
def view_applications():
    recruiter_id = session.get('recruiter_id')
    if not recruiter_id:
        return redirect('/login')

    action_status = request.args.get('action_status')
    apply_filter = request.args.get('filter') == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = 3

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all applications posted for this recruiter
    cursor.execute("""
        SELECT a.*, j.designation, j.company, j.skills_required
        FROM apply a
        JOIN job j ON a.job_id = j.id
        WHERE a.recruiter_id = ?
        ORDER BY j.company ASC, j.designation ASC, a.applied_at DESC
    """, (recruiter_id,))
    rows = cursor.fetchall()
    applications = [dict(row) for row in rows]

    # Grouping + filtering
    company_groups = defaultdict(lambda: defaultdict(list))
    company_counts = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'eligible': 0}))

    for app in applications:
        comp = app['company']
        desg = app['designation']

        # ✅ Eligibility only based on skills
        required_skills = app['skills_required'].lower().split(',') if app['skills_required'] else []
        user_skills = app['skills'].lower().split(',') if app['skills'] else []
        matched_skills = set(s.strip() for s in required_skills).intersection(set(s.strip() for s in user_skills))
        eligible = len(matched_skills) >= 2

        company_counts[comp][desg]['total'] += 1
        if eligible:
            company_counts[comp][desg]['eligible'] += 1

        if not apply_filter or eligible:
            company_groups[comp][desg].append(app)

    # Pagination
    all_companies = list(company_groups.keys())
    total_pages = math.ceil(len(all_companies) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    selected_companies = all_companies[start:end]

    grouped_applications = {company: company_groups[company] for company in selected_companies}
    grouped_counts = {company: company_counts[company] for company in selected_companies}

    return render_template("view_applicants.html",
                           grouped_applications=grouped_applications,
                           grouped_counts=grouped_counts,
                           page=page,
                           total_pages=total_pages,
                           apply_filter=apply_filter,
                           action_status=action_status)



@app.route('/shortlist-application/<int:app_id>', methods=['POST'])
def shortlist_application(app_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE apply SET status = 'shortlisted' WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_applications', action_status='shortlisted'))

@app.route('/reject-application/<int:app_id>', methods=['POST'])
def reject_application(app_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE apply SET status = 'rejected' WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_applications', action_status='rejected'))



@app.route('/delete-application/<int:app_id>', methods=['POST'])
def delete_application(app_id):
    recruiter_id = session.get('recruiter_id')
    if not recruiter_id:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apply WHERE id = ? AND recruiter_id = ?", (app_id, recruiter_id))
    conn.commit()
    return redirect(url_for('view_applications', action_status='delete'))

@app.route('/view-applications-submit')
def view_applications_submit():
    if 'user_email' not in session:
        return redirect('/login')  # or your user login route

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, j.designation, j.company
        FROM apply a
        JOIN job j ON a.job_id = j.id
        WHERE a.applicant_email = ?
        ORDER BY a.applied_at DESC
    """, (session['user_email'],))
    applications = cursor.fetchall()

    return render_template('view_application_submitted.html',
                           applications=[dict(row) for row in applications])


@app.route('/edit-application-inline/<int:app_id>', methods=['POST'])
def edit_application_inline(app_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    qualification = request.form['qualification']
    university = request.form['university']
    experience = request.form['experience']
    skills = request.form['skills']

    # Update the application
    cursor.execute("""
        UPDATE apply
        SET qualification = ?, university = ?, experience = ?, skills = ?
        WHERE id = ?
    """, (qualification, university, experience, skills, app_id))
    conn.commit()

    # Now fetch updated applications for the current user
    user_email = session.get('user_email')
    cursor.execute("SELECT * FROM apply WHERE applicant_email = ?", (user_email,))
    applications = cursor.fetchall()

    conn.close()

    return render_template("view_application_submitted.html", applications=applications, success_update=True)


@app.route('/delete-application-submit/<int:app_id>', methods=['POST'])
def delete_application_submit(app_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete the selected application
    cursor.execute("DELETE FROM apply WHERE id = ?", (app_id,))
    conn.commit()

    # Fetch updated applications for the logged-in user
    user_email = session.get('user_email')
    cursor.execute("SELECT * FROM apply WHERE applicant_email = ?", (user_email,))
    applications = cursor.fetchall()

    conn.close()

    return render_template("view_application_submitted.html", applications=applications, success_delete=True)




if __name__ == '__main__':
    app.run(debug=True)

