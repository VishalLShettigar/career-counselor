from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify
from utils.resume_parser import extract_resume_data, recommend_career
from io import BytesIO
from reportlab.pdfgen import canvas
import json
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

@app.route('/')
def root():
    return redirect('/home')
@app.route('/home')
def home():
    return render_template('home.html')



@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])  # Your animated resume uploader page
    else:
        flash("Please login to continue.", "warning")
        return redirect('/login')


from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import bcrypt

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="career_counselor"
)
cursor = db.cursor()

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                           (username, email, hashed_pw))
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect('/login')
        except mysql.connector.errors.IntegrityError:
            flash("Username already exists!", "danger")

    return render_template('register.html')

@app.route('/recruiter-register', methods=['GET', 'POST'])
def recruiter_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            cursor.execute("INSERT INTO recruiter (username, email, password) VALUES (%s, %s, %s)",
                           (username, email, hashed_pw))
            db.commit()
            flash("Recruiter registration successful! Please login.", "success")
            return redirect('/recruiter-login')
        except mysql.connector.errors.IntegrityError:
            flash("Username already exists!", "danger")

    return render_template('recruiter_register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[0].encode('utf-8')):
            session['username'] = username
            flash("Login successful!", "success")  # ✅ Show only after login
            return redirect('/index')
        else:
            flash("Invalid username or password!", "danger")
    return render_template('login.html')

@app.route('/recruiter-login', methods=['GET', 'POST'])
def recruiter_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id,password FROM recruiter WHERE username = %s", (username,))
        recruiter = cursor.fetchone()

        if recruiter and bcrypt.checkpw(password.encode('utf-8'), recruiter['password'].encode('utf-8')):
            session['recruiter_id'] = recruiter['id']
            flash("Login successful!", "success")
            return redirect('/job-postings')
        else:
            flash("Invalid username or password!", "danger")


    return render_template('recruiter_login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    # ❌ Don't flash login success here
    flash("You have been logged out.", "info")
    return redirect('/login')

@app.route('/logout1')
def logout1():
    session.pop('username', None)
    # ❌ Don't flash login success here
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

@app.route('/generate-resume-template', methods=["GET"])
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
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.form
        job_id = data.get('job_id')

        if job_id:
            # Update existing job
            cursor.execute("""
                UPDATE job SET company=%s, designation=%s, experience_required=%s, qualification=%s, 
                    skills_required=%s, contact_number=%s, email=%s
                WHERE id=%s AND recruiter_id=%s
            """, (
                data['company'], data['designation'], data['experience_required'], data['qualification'],
                data['skills_required'], data['contact_number'], data['email'], job_id, recruiter_id
            ))
            session['job_message'] = "Job updated successfully!"
        else:
            # Insert new job
            cursor.execute("""
                INSERT INTO job (recruiter_id, company, designation, experience_required, qualification, 
                    skills_required, contact_number, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                recruiter_id, data['company'], data['designation'], data['experience_required'],
                data['qualification'], data['skills_required'], data['contact_number'], data['email']
            ))
            session['job_message'] = "Job posted successfully!"

        db.commit()
        return redirect('/job-postings')

    # Show all jobs posted by the recruiter
    cursor.execute("SELECT * FROM job WHERE recruiter_id = %s ORDER BY posted_at DESC", (recruiter_id,))
    jobs = cursor.fetchall()
    return render_template("job_postings.html", jobs=jobs, job_data=None)

@app.route('/edit-job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    if 'recruiter_id' not in session:
        return redirect('/recruiter-login')

    recruiter_id = session['recruiter_id']
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle update via form submission
        data = request.form
        cursor.execute("""
            UPDATE job SET company=%s, designation=%s, experience_required=%s, qualification=%s, 
                skills_required=%s, contact_number=%s, email=%s
            WHERE id=%s AND recruiter_id=%s
        """, (
            data['company'], data['designation'], data['experience_required'], data['qualification'],
            data['skills_required'], data['contact_number'], data['email'], job_id, recruiter_id
        ))
        db.commit()
        session['job_message'] = "Job updated successfully!"
        return redirect('/job-postings')

    # For GET, pre-fill form with job data
    cursor.execute("SELECT * FROM job WHERE id = %s AND recruiter_id = %s", (job_id, recruiter_id))
    job_data = cursor.fetchone()

    if not job_data:
        return redirect('/job-postings')  # Prevent access to other recruiter's job

    cursor.execute("SELECT * FROM job WHERE recruiter_id = %s ORDER BY posted_at DESC", (recruiter_id,))
    jobs = cursor.fetchall()
    return render_template("job_postings.html", jobs=jobs, job_data=job_data)

@app.route('/delete-job/<int:job_id>')
def delete_job(job_id):
    
    if 'recruiter_id' not in session:
        return redirect('/recruiter-login')

    recruiter_id = session['recruiter_id']
    cursor = db.cursor()
    cursor.execute("DELETE FROM job WHERE id = %s AND recruiter_id = %s", (job_id, recruiter_id))
    db.commit()
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

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM owner WHERE username = %s", (username,))
        owner = cursor.fetchone()

        if owner and bcrypt.checkpw(password.encode('utf-8'), owner['password'].encode('utf-8')):
            session['owner_id'] = owner['id']
            #flash('Successfully Logged in as Owner!', 'success')
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
    cursor = db.cursor(dictionary=True)

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

            cursor.execute("SELECT * FROM owner WHERE username = %s", (old_username,))
            owner = cursor.fetchone()
            
            if owner and bcrypt.checkpw(old_password.encode('utf-8'), owner['password'].encode('utf-8')):
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
            cursor.execute("INSERT INTO owner (username, password) VALUES (%s, %s)", (new_username, hashed_password))
            db.commit()

            return render_template('set_owner.html', stage='change_success')

@app.route('/job-search', methods=['GET', 'POST'])
def job_search():
    if request.method == 'POST':
        skill_input = request.form.get('skill', '').lower()
        qualification_input = request.form.get('qualification', '').lower()
        experience_input = request.form.get('experience', '0')

        try:
            experience_val = int(experience_input)
        except ValueError:
            experience_val = 0

        cursor = db.cursor(dictionary=True)

        query = """
        SELECT * FROM job
        WHERE 
            LOWER(skills_required) LIKE %s OR
            LOWER(qualification) LIKE %s OR
            (
              experience_required REGEXP %s
              OR experience_required LIKE %s
            )
        """
        exp_regex = f"^{experience_val}([-+])?"  # matches '2', '2+', '2-3'
        cursor.execute(query, (
            f"%{skill_input}%",
            f"%{qualification_input}%",
            exp_regex,
            f"{experience_val}%",
        ))

        jobs = cursor.fetchall()
        return render_template("job_finder.html", stage="results", jobs=jobs)

    return render_template("job_finder.html", stage="initial")

@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    cursor = db.cursor(dictionary=True)
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_password = request.form['password']

        query = "UPDATE users SET username=%s, email=%s, password=%s WHERE id=%s"
        cursor.execute(query, (new_username, new_email, new_password, user_id))
        db.commit()
        return redirect(url_for('view_users', status='edit'))
    
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    return render_template('edit_user.html', user=user)

@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()
    return redirect(url_for('view_users', status='delete'))


@app.route('/view-users', methods=['GET'])
def view_users():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'username')
    page = int(request.args.get('page', 1))
    per_page = 6

    cursor = db.cursor(dictionary=True)

    # Handle optional search
    base_query = "SELECT * FROM users"
    params = []

    if search:
        base_query += " WHERE username LIKE %s OR email LIKE %s"
        params.extend([f"%{search}%", f"%{search}%"])

    base_query += f" ORDER BY {sort}"
    cursor.execute(base_query, params)
    all_users = cursor.fetchall()

    total_users = len(all_users)
    total_pages = (total_users + per_page - 1) // per_page
    start = (page - 1) * per_page
    users = all_users[start:start + per_page]

    # ✅ Check for edit_id in query and fetch user
    edit_user = None
    edit_id = request.args.get('edit_id')
    if edit_id:
        cursor.execute("SELECT * FROM users WHERE id = %s", (edit_id,))
        edit_user = cursor.fetchone()

    action_status = request.args.get("status")  # 'edit' or 'delete'

    return render_template("view_users.html",
                           users=users,
                           page=page,
                           total_pages=total_pages,
                           total_users=total_users,
                           action_status=action_status,
                           edit_user=edit_user)  # ✅ Pass this to template


@app.route('/view-recruiters')
def view_recruiters():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'username')
    page = int(request.args.get('page', 1))
    per_page = 6

    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM recruiter"
    filters = []

    if search:
        filters.append("(username LIKE %s OR email LIKE %s)")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" ORDER BY {sort}"

    params = (f"%{search}%", f"%{search}%") if search else ()
    cursor.execute(query, params)
    all_recruiters = cursor.fetchall()

    total = len(all_recruiters)
    total_pages = (total + per_page - 1) // per_page
    recruiters = all_recruiters[(page - 1) * per_page : page * per_page]

    edit_id = request.args.get("edit_id")
    edit_recruiter = None
    if edit_id:
        cursor.execute("SELECT * FROM recruiter WHERE id = %s", (edit_id,))
        edit_recruiter = cursor.fetchone()

    return render_template("view_recruiters.html", recruiters=recruiters, edit_recruiter=edit_recruiter,
                           page=page, total_pages=total_pages, total_recruiters=total, action_status=request.args.get("status"))

@app.route('/edit-recruiter/<int:id>', methods=['POST'])
def edit_recruiter(id):
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    cursor = db.cursor()
    cursor.execute("UPDATE recruiter SET username=%s, email=%s, password=%s WHERE id=%s",
                   (username, email, password, id))
    db.commit()
    return redirect(url_for('view_recruiters', status='edit'))

@app.route('/delete-recruiter/<int:id>', methods=['POST'])
def delete_recruiter(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM recruiter WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('view_recruiters', status='delete'))

@app.route('/view-jobs')
def view_jobs():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'designation')  # Default sort
    page = int(request.args.get('page', 1))
    per_page = 6

    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM job"
    filters = []

    if search:
        filters.append("(company LIKE %s OR designation LIKE %s OR skills_required LIKE %s)")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" ORDER BY {sort}"

    params = (f"%{search}%", f"%{search}%", f"%{search}%") if search else ()
    cursor.execute(query, params)
    all_jobs = cursor.fetchall()

    total = len(all_jobs)
    total_pages = (total + per_page - 1) // per_page
    jobs = all_jobs[(page - 1) * per_page : page * per_page]

    return render_template("view_jobs.html",
                           jobs=jobs,
                           page=page,
                           total_pages=total_pages,
                           total_jobs=total,
                           request=request,
                           action_status=request.args.get("status"))

@app.route('/delete-jobs/<int:id>', methods=['POST'])
def delete_jobs(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM job WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('view_jobs', status='delete'))

@app.route('/analytics')
def analytics():
    cursor = db.cursor()

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

from flask import request, render_template, jsonify

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

        cursor = db.cursor()
        cursor.execute("INSERT INTO feedback (name, email, experience, user_type, suggestions, rating) VALUES (%s, %s, %s, %s, %s, %s)",
                       (name, email, experience, user_type, suggestions, rating))
        db.commit()
        return jsonify({"status": "success"})

    return render_template("feedback.html")

@app.route('/view-feedback')
def view_feedback():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'name')
    page = int(request.args.get('page', 1))
    per_page = 6

    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM feedback"
    filters = []
    params = []

    if search:
        filters.append("(name LIKE %s OR email LIKE %s OR user_type LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" ORDER BY {sort}"

    cursor.execute(query, tuple(params))
    all_feedback = cursor.fetchall()

    total = len(all_feedback)
    total_pages = (total + per_page - 1) // per_page
    feedbacks = all_feedback[(page - 1) * per_page : page * per_page]

    return render_template('view-feedback.html',
        feedbacks=feedbacks,
        total_feedback=total,
        total_pages=total_pages,
        page=page,
        action_status=request.args.get('status')
    )

@app.route('/delete-feedback/<int:id>', methods=['POST'])
def delete_feedback(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM feedback WHERE id = %s", (id,))
    db.commit()
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
    footer = "Smart Career Guidance System"  # This line fixes the error

    return render_template(
        "system_settings.html",
        scoring=scoring,
        ai=ai,
        owner_name=owner_name,
        footer=footer
    )
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from collections import defaultdict
from datetime import datetime
import os
import math

UPLOAD_FOLDER = 'static/resumes/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        try:
            applicant_name = request.form.get('applicant_name', '').strip()
            applicant_email = request.form.get('applicant_email', '').strip()
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

            filename = secure_filename(resume.filename)
            resume_path = f"resumes/{filename}"
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            query = """
                INSERT INTO apply (
                    applicant_name, applicant_email, qualification, university,
                    experience, skills, resume_path, recruiter_id, job_id, applied_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                applicant_name, applicant_email, qualification, university,
                experience, skills, resume_path, recruiter_id, job_id, datetime.now()
            )
            cursor.execute(query, values)
            db.commit()

            job = {
                'designation': request.form.get('designation'),
                'company': request.form.get('company'),
                'skills_required': request.form.get('skills_required'),
                'qualification': qualification,
                'job_id': job_id,
                'recruiter_id': recruiter_id
            }
            return render_template('apply.html', job=job, application_status='success')

        except Exception as e:
            return f"Unexpected Error: {str(e)}", 500

    job = {
        'designation': request.args.get('designation'),
        'company': request.args.get('company'),
        'skills_required': request.args.get('skills_required'),
        'qualification': request.args.get('qualification'),
        'job_id': request.args.get('job_id'),
        'recruiter_id': request.args.get('recruiter_id')
    }
    return render_template('apply.html', job=job, application_status=None, resume_error=None)

@app.route('/view-applications')
def view_applications():
    recruiter_id = session.get('recruiter_id')
    if not recruiter_id:
        return redirect('/login')

    action_status = request.args.get('action_status')
    page = request.args.get('page', 1, type=int)
    per_page = 3

    query = """
        SELECT a.*, j.designation, j.company
        FROM apply a
        JOIN job j ON a.job_id = j.id
        WHERE a.recruiter_id = %s
        ORDER BY j.company ASC, j.designation ASC, a.applied_at DESC
    """
    cursor.execute(query, (recruiter_id,))
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    applications = [dict(zip(columns, row)) for row in rows]

    company_groups = defaultdict(lambda: defaultdict(list))
    for app in applications:
        company = app['company']
        designation = app['designation']
        company_groups[company][designation].append(app)

    all_companies = list(company_groups.keys())
    total_pages = math.ceil(len(all_companies) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    selected_companies = all_companies[start:end]
    grouped_applications = {company: company_groups[company] for company in selected_companies}

    return render_template('view_applicants.html',
                           grouped_applications=grouped_applications,
                           page=page,
                           total_pages=total_pages,
                           action_status=action_status)

@app.route('/delete-application/<int:app_id>', methods=['POST'])
def delete_application(app_id):
    recruiter_id = session.get('recruiter_id')
    if not recruiter_id:
        return redirect('/login')

    cursor.execute("DELETE FROM apply WHERE id = %s AND recruiter_id = %s", (app_id, recruiter_id))
    db.commit()
    return redirect(url_for('view_applications', action_status='delete'))





if __name__ == '__main__':
    app.run(debug=True)
