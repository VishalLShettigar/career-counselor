import re
import fitz  # PyMuPDF
from career_mapping import SKILL_CAREER_MAP

def extract_resume_data(file):
    try:
        file.seek(0)
        text = ""
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        # 🧑 Name Extraction
        name = "Not Found"
        for i, line in enumerate(lines):
            if re.search(r'\b(cv|curriculum vitae|resume)\b', line, re.I):
                for next_line in lines[i+1:]:
                    if next_line.strip():
                        name = next_line.strip().title()
                        break
                break
        if name == "Not Found" and lines:
            name = lines[0].strip().title()

        # Email & Phone
        email_match = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        phone_match = re.findall(r'(?:\+91[-\s]?|0)?[6-9]\d{9}', text)
        email = email_match[0] if email_match else 'Not Found'
        phone = phone_match[0] if phone_match else 'Not Found'

        # Skills
        skill_keywords = list(SKILL_CAREER_MAP.keys())
        pattern = r'\b(?:' + '|'.join(re.escape(skill) for skill in skill_keywords) + r')\b'
        skills_found = re.findall(pattern, text, re.I)
        skills = list(set([s.lower() for s in skills_found]))

        # Education Extraction
        education_lines = []
        degree_keywords = [
    # UG & PG Common Abbreviations
    'b.tech', 'm.tech', 'b.e', 'm.e', 'b.sc', 'm.sc', 'bcom', 'mcom',
    'bca', 'mca', 'bba', 'mba', 'bpharm', 'mpharm', 'ba', 'ma',
    'b.arch', 'm.arch', 'bds', 'mbbs', 'llb', 'llm', 'b.ed', 'm.ed',

    # Full Forms
    'bachelor of technology', 'master of technology', 'bachelor of science', 'master of science',
    'bachelor of commerce', 'master of commerce', 'bachelor of arts', 'master of arts',
    'bachelor of computer application', 'master of computer applications',
    'bachelor of business administration', 'master of business administration',
    'bachelor of pharmacy', 'master of pharmacy', 'bachelor of education', 'master of education',

    # Diplomas & Certificates
    'diploma', 'pg diploma', 'postgraduate diploma', 'advanced diploma',

    # Medical
    'mbbs', 'bds', 'md', 'ms', 'bhms', 'bams', 'bpt', 'mpt', 'pharma d', 'mch',

    # Law
    'llb', 'llm', 'bachelor of law', 'master of law',

    # Research
    'phd', 'doctorate', 'doctor of philosophy', 'm.phil', 'msc by research',

    # Others (International / Misc.)
    'associate degree', 'honours degree', 'b.eng', 'm.eng', 'mae', 'bstat', 'mstat',
    'bfa', 'mfa', 'bdes', 'mdes', 'b.lib', 'm.lib', 'b.voc', 'm.voc',

    # Education Level (Fallback terms)
    'graduation', 'post graduation', 'undergraduate', 'postgraduate', 'degree','sslc','puc',
]

        for line in text.split('\n'):
            if any(re.search(rf"\b{kw}\b", line, re.I) for kw in degree_keywords):
                education_lines.append(line.strip())
        education = '\n'.join(sorted(set(education_lines))) if education_lines else 'Not Found'

        # Certification Extraction
        cert_lines = []
        cert_keywords = ['certification', 'certified', 'course', 'aws', 'azure', 'google cloud', 'scrum', 'pmp']
        for line in text.split('\n'):
            if any(re.search(rf"\b{kw}\b", line, re.I) for kw in cert_keywords):
                cert_lines.append(line.strip())
        certifications = '\n'.join(cert_lines) if cert_lines else 'Not Found'

        # Experience Extraction
        exp_lines = []
        exp_keywords = ['experience', 'intern', 'worked at', 'company', 'roles', 'responsibilities', 'designation']
        for line in text.split('\n'):
            if any(re.search(rf"\b{kw}\b", line, re.I) for kw in exp_keywords):
                exp_lines.append(line.strip())
        experience = '\n'.join(exp_lines) if exp_lines else 'Not Found'

        # Score Calculation
        score = 0
        if email != 'Not Found': score += 10
        if phone != 'Not Found': score += 10
        score += min(len(skills), 6) * 5
        if education != 'Not Found': score += 10
        if experience != 'Not Found': score += 10
        if re.search(r"(communication|team|leadership|creative|problem solving|adaptability)", text, re.I):
            score += 10
        word_count = len(text.split())
        if 500 <= word_count <= 1500: score += 10
        if re.search(r"(education|experience|skills|projects|certification)", text, re.I): score += 10
        if word_count < 100: score -= 10
        score = min(max(score, 0), 100)

        return {
            'name':name,
            'email': email,
            'phone': phone,
            'skills': skills,
            'score': score,
            'education': education,
            'certifications': certifications,
            'experience': experience
        }

    except Exception as e:
        return {'error': str(e)}


def recommend_career(skills):
    recommended = set()
    for skill in skills:
        if skill in SKILL_CAREER_MAP:
            recommended.add(SKILL_CAREER_MAP[skill])
    return list(recommended) if recommended else ['General Role Based on Resume']
