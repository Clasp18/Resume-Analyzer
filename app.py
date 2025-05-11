from flask import Flask, request, jsonify, render_template_string
import os
import PyPDF2
import spacy
from textblob import TextBlob
import logging
import re
import pandas as pd

app = Flask(__name__)


from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173","methods": ["POST"]}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    logger.error("Failed to load spaCy model. Please install it using: python -m spacy download en_core_web_sm")
    nlp = None

# Define TEMPLATES variable
TEMPLATES = """
<!DOCTYPE html>
<html>
<head>
    <title>Resume Analyzer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: #fff;
        }
        .section h3 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .form-group { margin: 20px 0; }
        .btn {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
        }
        .btn:hover {
            background: #0056b3;
        }
        .results { margin-top: 20px; }
        .score { color: #28a745; font-weight: bold; }
        .error {
            padding: 10px;
            background-color: #fee;
            border: 1px solid #fcc;
            border-radius: 4px;
            margin: 10px 0;
            color: #dc3545;
            display: none;
        }
        #loading {
            text-align: center;
            padding: 20px;
            font-weight: bold;
            color: #666;
            display: none;
        }
        ul { padding-left: 20px; }
        li { margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Resume Analyzer</h1>
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="form-group">
                <label for="resume">Upload Resume (PDF):</label><br>
                <input type="file" id="resume" name="resume" accept=".pdf" required>
                <button type="submit" class="btn">Analyze Resume</button>
            </div>
        </form>
        <div id="loading">Analyzing your resume... Please wait...</div>
        <div id="error" class="error"></div>
        <div id="results" class="results"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('uploadForm');
            const loadingDiv = document.getElementById('loading');
            const errorDiv = document.getElementById('error');
            const resultsDiv = document.getElementById('results');

            form.onsubmit = async function(e) {
                e.preventDefault();

                // Clear previous results
                errorDiv.textContent = '';
                errorDiv.style.display = 'none';
                resultsDiv.innerHTML = '';

                const formData = new FormData(this);

                try {
                    loadingDiv.style.display = 'block';

                    const response = await fetch('/analyze_resume', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to analyze resume');
                    }

                    // Format and display results
                    resultsDiv.innerHTML = `
                        <div class="section">
                            <h3>Word Count</h3>
                            <p>${data.word_count} words</p>
                        </div>
                        <div class="section">
                            <h3>Skills Found</h3>
                            <p><strong>Technical Skills:</strong> ${data.skills_analysis.technical_skills.join(', ') || 'None'}</p>
                            <p><strong>Soft Skills:</strong> ${data.skills_analysis.soft_skills.join(', ') || 'None'}</p>
                            <p><strong>Skills Score:</strong> ${data.skills_analysis.skills_score}</p>
                        </div>
                        <div class="section">
                            <h3>Job Recommendations</h3>
                            <ul>
                                ${data.job_recommendations.map(job =>
                                    `<li>${job.role} (${job.match_percentage}% match)</li>`
                                ).join('')}
                            </ul>
                        </div>
                        <div class="section">
                            <h3>Course Recommendations</h3>
                            <ul>
                                ${data.course_recommendations.map(course =>
                                    `<li>${course}</li>`
                                ).join('')}
                            </ul>
                        </div>
                        <div class="section">
                            <h3>Profile Summary Improvements</h3>
                            <ul>
                                ${data.profile_improvements.map(s => `<li>${s}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="section">
                            <h3>Improvement Suggestions</h3>
                            <ul>
                                ${data.improvement_suggestions.map(s => `<li>${s}</li>`).join('')}
                            </ul>
                        </div>
                    `;
                } catch (error) {
                    errorDiv.textContent = error.message;
                    errorDiv.style.display = 'block';
                    console.error('Error:', error);
                } finally {
                    loadingDiv.style.display = 'none';
                }
            };
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(TEMPLATES)


@app.route('/analyze_resume', methods=['POST'])
def analyze_resume():
    try:
        file = request.files['resume']
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Process the resume as needed
        # Assume extract_text_from_pdf and analyze_text are already defined to process the resume
        filepath = "temp_resume.pdf"
        file.save(filepath)
        text = extract_text_from_pdf(filepath)
        results = analyze_text(text)

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_text_from_pdf(filepath):
    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        raise

def analyze_text(text):
    try:
        word_count = len(text.split())

        blob = TextBlob(text)
        sentiment = blob.sentiment
        sentiment_interpretation = interpret_sentiment(sentiment.polarity, sentiment.subjectivity)

        sections = extract_sections(text)
        formatted_sections = format_sections(sections)

        skills = extract_skills(text)

        job_matches = get_job_recommendations(skills)

        courses = get_course_recommendations(job_matches)

        profile_summary = extract_profile_summary(text)
        profile_improvements = suggest_profile_improvements(profile_summary)

        suggestions = get_resume_suggestions(sections, skills, word_count)

        return {
            'word_count': word_count,
            'sentiment_analysis': {
                'raw_scores': {
                    'polarity': round(sentiment.polarity, 2),
                    'subjectivity': round(sentiment.subjectivity, 2)
                },
                'interpretation': sentiment_interpretation
            },
            
            'sections': formatted_sections,
            'skills_analysis': {
                'technical_skills': skills['technical'],
                'soft_skills': skills['soft'],
                'skills_score': calculate_skills_score(skills)
            },
            'job_recommendations': job_matches,
            'course_recommendations': courses,
            'profile_improvements': profile_improvements,
            'improvement_suggestions': suggestions
        }

    except Exception as e:
        logger.error(f"Error in text analysis: {str(e)}")
        raise

def extract_profile_summary(text):
    summary_pattern = re.compile(r"(summary|profile|objective)(.*?)(experience|skills|education|certifications|$)", re.IGNORECASE | re.DOTALL)
    match = summary_pattern.search(text)
    if match:
        return match.group(2).strip()
    return ""

def suggest_profile_improvements(summary):
    suggestions = []
    if not summary:
        suggestions.append("Consider adding a profile summary or objective statement.")
    else:
        if len(summary.split()) > 150:
            suggestions.append("Consider shortening your profile summary to be more concise.")
        if not re.search(r'(\d+ years|\d+%|\d+ projects)', summary):
            suggestions.append("Include quantifiable achievements or years of experience.")
    return suggestions

def extract_skills(text):
    """Extract technical and soft skills from resume"""
    technical_skills = {
        'programming_languages': [
            'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
            'typescript', 'scala', 'perl', 'r', 'matlab', 'sql', 'html', 'css'
        ],
        'frameworks': [
            'react', 'angular', 'vue', 'django', 'flask', 'spring', 'node.js', 'express',
            'tensorflow', 'pytorch', 'keras', 'pandas', 'numpy', 'scikit-learn'
        ],
        'databases': [
            'mysql', 'postgresql', 'mongodb', 'oracle', 'sqlite', 'redis', 'cassandra',
            'elasticsearch', 'dynamodb'
        ],
        'tools': [
            'git', 'docker', 'kubernetes', 'jenkins', 'aws', 'azure', 'gcp', 'jira',
            'confluence', 'slack', 'postman', 'webpack', 'npm', 'yarn'
        ],
        'concepts': [
            'agile', 'scrum', 'ci/cd', 'rest api', 'microservices', 'cloud computing',
            'machine learning', 'artificial intelligence', 'data science', 'blockchain'
        ]
    }

    soft_skills = [
        'leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking',
        'time management', 'project management', 'analytical skills', 'attention to detail',
        'creativity', 'adaptability', 'collaboration', 'organization', 'presentation',
        'negotiation', 'conflict resolution', 'decision making', 'mentoring', 'multitasking'
    ]

    found_skills = {
        'technical': [],
        'soft': []
    }

    text_lower = text.lower()

    # Find technical skills
    for category, skills in technical_skills.items():
        for skill in skills:
            if skill in text_lower:
                found_skills['technical'].append(skill)

    # Find soft skills
    for skill in soft_skills:
        if skill in text_lower:
            found_skills['soft'].append(skill)

    return found_skills

def calculate_skills_score(skills):
    """Calculate a score based on the number and variety of skills"""
    technical_weight = 0.6
    soft_weight = 0.4

    technical_score = min(len(skills['technical']) * 10, 100)
    soft_score = min(len(skills['soft']) * 20, 100)

    total_score = (technical_score * technical_weight) + (soft_score * soft_weight)
    return round(total_score, 1)

def get_job_recommendations(skills):
    """Recommend suitable job roles based on skills"""
    job_roles = {
        'Software Developer': {
            'required_skills': ['python', 'java', 'javascript', 'git', 'sql'],
            'weight': 0
        },
        'Data Scientist': {
            'required_skills': ['python', 'machine learning', 'sql', 'statistics', 'tensorflow', 'pandas'],
            'weight': 0
        },
        'DevOps Engineer': {
            'required_skills': ['docker', 'kubernetes', 'jenkins', 'aws', 'ci/cd', 'git'],
            'weight': 0
        },
        'Frontend Developer': {
            'required_skills': ['html', 'css', 'javascript', 'react', 'angular', 'typescript'],
            'weight': 0
        },
        'Backend Developer': {
            'required_skills': ['python', 'java', 'sql', 'node.js', 'rest api', 'microservices'],
            'weight': 0
        }
    }

    all_skills = skills['technical'] + skills['soft']
    recommendations = []

    for role, requirements in job_roles.items():
        matching_skills = sum(1 for skill in requirements['required_skills']
                            if skill in all_skills)
        match_percentage = (matching_skills / len(requirements['required_skills'])) * 100

        if match_percentage > 30:
            recommendations.append({
                'role': role,
                'match_percentage': round(match_percentage)
            })

    recommendations.sort(key=lambda x: x['match_percentage'], reverse=True)
    return recommendations[:3]

def get_course_recommendations(job_matches):
    """Recommend courses based on job matches"""
    courses_db = {
        'Software Developer': [
            'Complete Python Developer in 2024 (Udemy)',
            'Java Programming Masterclass (Coursera)',
            'Modern JavaScript from the Beginning (Udemy)'
        ],
        'Data Scientist': [
            'Data Science Specialization (Coursera)',
            'Machine Learning A-Z (Udemy)',
            'Statistics for Data Science (edX)'
        ],
        'DevOps Engineer': [
            'Docker & Kubernetes: The Complete Guide (Udemy)',
            'AWS Certified DevOps Engineer (AWS)',
            'Jenkins CI/CD Masterclass (Udemy)'
        ],
        'Frontend Developer': [
            'React - The Complete Guide (Udemy)',
            'Advanced CSS and Sass (Udemy)',
            'Modern Angular Bootcamp (Udemy)'
        ],
        'Backend Developer': [
            'Node.js Developer Course (Udemy)',
            'Python Django Masterclass (Udemy)',
            'Advanced SQL (Stanford Online)'
        ]
    }

    recommended_courses = set()
    for job in job_matches:
        if job['match_percentage'] > 40:
            role = job['role']
            if role in courses_db:
                recommended_courses.update(courses_db[role][:2])

    return list(recommended_courses)

def extract_sections(text):
    """Extract different sections from the resume"""
    sections = {}
    headers = ['education', 'experience', 'skills', 'projects', 'summary', 'objective']

    for header in headers:
        start = text.lower().find(header)
        if start != -1:
            next_header = float('inf')
            for h in headers:
                pos = text.lower().find(h, start + len(header))
                if pos != -1 and pos < next_header:
                    next_header = pos

            if next_header == float('inf'):
                sections[header] = text[start:].strip()
            else:
                sections[header] = text[start:next_header].strip()

    return sections

def format_sections(sections):
    """Format section content into bullet points"""
    formatted_sections = {}
    for section, content in sections.items():
        if content:
            bullets = re.split(r'[•\-\●\■\♦\◆\○\●]|\d+\.|[\n\r]+', content)
            bullets = [b.strip() for b in bullets if b.strip() and len(b.strip()) > 10]
            formatted_sections[section] = bullets
    return formatted_sections

def get_resume_suggestions(sections, skills, word_count):
    """Generate improvement suggestions for the resume"""
    suggestions = []

    if word_count < 300:
        suggestions.append("Your resume is quite brief. Consider adding more detailed information.")
    elif word_count > 1000:
        suggestions.append("Your resume is quite lengthy. Consider condensing it.")

    if len(skills['technical']) < 5:
        suggestions.append("Add more technical skills relevant to your target positions.")
    if len(skills['soft']) < 3:
        suggestions.append("Include more soft skills to demonstrate your capabilities.")

    required_sections = ['education', 'experience', 'skills']
    for section in required_sections:
        if section not in sections or not sections[section]:
            suggestions.append(f"Add a {section.title()} section to your resume.")

    return suggestions

def interpret_sentiment(polarity, subjectivity):
    """Interpret sentiment scores"""
    interpretation = {
        'tone_analysis': {
            'score': polarity,
            'description': '',
            'suggestion': ''
        },
        'objectivity_analysis': {
            'score': subjectivity,
            'description': '',
            'suggestion': ''
        }
    }

    # Interpret tone (polarity)
    if polarity > 0.5:
        interpretation['tone_analysis'].update({
            'description': 'Very positive',
            'suggestion': 'Consider maintaining a more balanced tone while keeping achievements highlighted.'
        })
    elif polarity > 0:
        interpretation['tone_analysis'].update({
            'description': 'Appropriately positive',
            'suggestion': 'Good balance of positive tone.'
        })
    elif polarity < -0.2:
        interpretation['tone_analysis'].update({
            'description': 'Negative',
            'suggestion': 'Use more positive language to highlight achievements and capabilities.'
        })
    else:
        interpretation['tone_analysis'].update({
            'description': 'Neutral',
            'suggestion': 'Consider adding more positive highlights of achievements.'
        })

    # Interpret objectivity (subjectivity)
    if subjectivity > 0.8:
        interpretation['objectivity_analysis'].update({
            'description': 'Very subjective',
            'suggestion': 'Include more factual statements and quantifiable achievements.'
        })
    elif subjectivity > 0.5:
        interpretation['objectivity_analysis'].update({
            'description': 'Moderately subjective',
            'suggestion': 'Balance subjective statements with more concrete achievements and metrics.'
        })
    else:
        interpretation['objectivity_analysis'].update({
            'description': 'Appropriately objective',
            'suggestion': 'Good balance of objective statements.'
        })

    return interpretation

if __name__ == '__main__':
    app.run(debug=True, port=5000)