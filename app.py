from flask import Flask, request, jsonify, render_template_string
import PyPDF2
import docx
import re
from typing import Dict, List, Tuple
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory
os.makedirs('uploads', exist_ok=True)

class ResumeJDMatcher:
    def __init__(self):
        self.technical_keywords = {
            'programming': ['python', 'java', 'c++', 'javascript', 'react', 'node.js', 'angular'],
            'vlsi': ['verilog', 'systemverilog', 'rtl', 'asic', 'fpga', 'synthesis', 'verification', 'uvm'],
            'tools': ['synopsys', 'cadence', 'mentor', 'xilinx', 'altera', 'design compiler', 'icc2'],
            'domains': ['physical design', 'digital design', 'analog design', 'mixed signal'],
            'methodologies': ['agile', 'scrum', 'waterfall', 'devops', 'ci/cd']
        }
        
        # Domain differentiation - Critical for accurate matching
        self.domain_conflicts = {
            'vlsi_design_vs_physical': {
                'design_keywords': ['rtl design', 'verilog', 'systemverilog', 'design compiler', 'uvm', 'verification', 'testbench'],
                'physical_keywords': ['place and route', 'pnr', 'physical design', 'icc2', 'innovus', 'floorplan', 'timing closure', 'sta'],
                'conflict_message': 'VLSI Design (Frontend RTL) vs Physical Design (Backend Implementation)'
            },
            'frontend_vs_backend': {
                'design_keywords': ['react', 'angular', 'vue', 'html', 'css', 'javascript', 'ui/ux'],
                'physical_keywords': ['node.js', 'python', 'java', 'database', 'api', 'server', 'backend'],
                'conflict_message': 'Frontend Development vs Backend Development'
            },
            'software_vs_hardware': {
                'design_keywords': ['software', 'application', 'web development', 'mobile app', 'programming'],
                'physical_keywords': ['hardware', 'embedded', 'firmware', 'circuit design', 'pcb'],
                'conflict_message': 'Software Development vs Hardware Engineering'
            }
        }
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            return f"Error reading DOCX: {str(e)}"
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            return f"Error reading TXT: {str(e)}"
    
    def extract_text(self, file_path: str) -> str:
        """Extract text based on file extension"""
        _, ext = os.path.splitext(file_path.lower())
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return self.extract_text_from_docx(file_path)
        elif ext == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            return "Unsupported file format"
    
    def extract_experience(self, text: str) -> int:
        """Extract years of experience from text"""
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*yrs?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                return max([int(match) for match in matches])
        return 0
    
    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract technical skills from text"""
        found_skills = {}
        text_lower = text.lower()
        
        for category, keywords in self.technical_keywords.items():
            found_keywords = []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found_keywords.append(keyword)
            if found_keywords:
                found_skills[category] = found_keywords
        
        return found_skills
    
    def detect_domain_conflicts(self, resume_text: str, jd_text: str) -> Dict:
        """Detect domain mismatches like Design vs Physical Design"""
        conflicts = []
        resume_lower = resume_text.lower()
        jd_lower = jd_text.lower()
        
        for conflict_type, conflict_data in self.domain_conflicts.items():
            design_in_resume = any(keyword in resume_lower for keyword in conflict_data['design_keywords'])
            physical_in_resume = any(keyword in resume_lower for keyword in conflict_data['physical_keywords'])
            
            design_in_jd = any(keyword in jd_lower for keyword in conflict_data['design_keywords'])
            physical_in_jd = any(keyword in jd_lower for keyword in conflict_data['physical_keywords'])
            
            # Critical mismatch detection
            if (design_in_jd and physical_in_resume and not design_in_resume) or \
               (physical_in_jd and design_in_resume and not physical_in_resume):
                conflicts.append({
                    'type': conflict_type,
                    'message': conflict_data['conflict_message'],
                    'jd_domain': 'design' if design_in_jd else 'physical',
                    'resume_domain': 'design' if design_in_resume else 'physical'
                })
        
        return conflicts
    
    def calculate_match_score(self, resume_text: str, jd_text: str) -> Dict:
        """Calculate matching score between resume and JD with domain conflict detection"""
        resume_skills = self.extract_skills(resume_text)
        jd_skills = self.extract_skills(jd_text)
        resume_exp = self.extract_experience(resume_text)
        jd_exp = self.extract_experience(jd_text)
        
        # CRITICAL: Check for domain conflicts first
        domain_conflicts = self.detect_domain_conflicts(resume_text, jd_text)
        
        # Calculate skill overlap
        total_matches = 0
        total_required = 0
        detailed_matches = {}
        missing_critical = []
        
        for category, jd_keywords in jd_skills.items():
            resume_keywords = resume_skills.get(category, [])
            matches = set(jd_keywords) & set(resume_keywords)
            missing = list(set(jd_keywords) - matches)
            
            total_matches += len(matches)
            total_required += len(jd_keywords)
            
            if matches or missing:
                detailed_matches[category] = {
                    'matched': list(matches),
                    'missing': missing
                }
                
            # Track critical missing skills
            if category in ['vlsi', 'programming'] and missing:
                missing_critical.extend(missing)
        
        # Calculate base scores
        skill_score = (total_matches / total_required * 100) if total_required > 0 else 0
        exp_score = min(resume_exp / jd_exp * 100, 100) if jd_exp > 0 else 100
        overall_score = (skill_score * 0.7 + exp_score * 0.3)
        
        # Apply domain conflict penalties
        conflict_penalty = 0
        critical_issues = []
        
        if domain_conflicts:
            conflict_penalty = 50  # Major penalty for domain mismatch
            critical_issues = [conflict['message'] for conflict in domain_conflicts]
            overall_score = max(0, overall_score - conflict_penalty)
        
        # Check for critical missing skills
        if missing_critical and len(missing_critical) > 3:
            critical_issues.append(f"Missing critical skills: {', '.join(missing_critical[:5])}")
            overall_score = max(0, overall_score - 20)
        
        # Enhanced recommendation logic
        if domain_conflicts or len(critical_issues) > 0:
            recommendation = "DO NOT SEND"
            status = "❌"
            reason = "Critical domain mismatch or missing core skills"
        elif overall_score >= 80:
            recommendation = "SEND"
            status = "✅"
            reason = "Strong match across skills and experience"
        elif overall_score >= 65:
            recommendation = "MAYBE SEND"
            status = "⚠️"
            reason = "Moderate match, some gaps exist"
        else:
            recommendation = "DO NOT SEND"
            status = "❌"
            reason = "Insufficient match for role requirements"
        
        return {
            'overall_score': round(overall_score, 1),
            'skill_score': round(skill_score, 1),
            'experience_score': round(exp_score, 1),
            'recommendation': recommendation,
            'status': status,
            'reason': reason,
            'resume_experience': resume_exp,
            'required_experience': jd_exp,
            'detailed_matches': detailed_matches,
            'resume_skills': resume_skills,
            'jd_skills': jd_skills,
            'domain_conflicts': domain_conflicts,
            'critical_issues': critical_issues,
            'conflict_penalty': conflict_penalty
        }

# Initialize matcher
matcher = ResumeJDMatcher()

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume-JD Matcher</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        .upload-box {
            border: 2px dashed #3498db;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            background-color: #f8f9fa;
        }
        .upload-box h3 {
            color: #2c3e50;
            margin-bottom: 15px;
        }
        input[type="file"] {
            margin: 10px 0;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
        }
        textarea {
            width: 100%;
            height: 150px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
        }
        button {
            background-color: #3498db;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            display: block;
            margin: 20px auto;
        }
        button:hover {
            background-color: #2980b9;
        }
        .results {
            margin-top: 30px;
            padding: 20px;
            border-radius: 8px;
            display: none;
        }
        .send { background-color: #d4edda; border: 1px solid #c3e6cb; }
        .maybe { background-color: #fff3cd; border: 1px solid #ffeaa7; }
        .reject { background-color: #f8d7da; border: 1px solid #f5c6cb; }
        .score-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .score-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .score-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .details {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Resume-JD Matcher</h1>
        
        <form id="matchForm" enctype="multipart/form-data">
            <div class="upload-section">
                <div class="upload-box">
                    <h3>📄 Resume</h3>
                    <input type="file" id="resume" name="resume" accept=".pdf,.docx,.txt">
                    <p>Or paste text:</p>
                    <textarea id="resumeText" name="resumeText" placeholder="Paste resume content here..."></textarea>
                </div>
                
                <div class="upload-box">
                    <h3>📋 Job Description</h3>
                    <input type="file" id="jd" name="jd" accept=".pdf,.docx,.txt">
                    <p>Or paste text:</p>
                    <textarea id="jdText" name="jdText" placeholder="Paste job description here..."></textarea>
                </div>
            </div>
            
            <button type="submit">🔍 Analyze Match</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Analyzing match...</p>
        </div>
        
        <div class="results" id="results">
            <h2 id="recommendation"></h2>
            <div class="score-grid">
                <div class="score-card">
                    <div class="score-value" id="overallScore"></div>
                    <div>Overall Match</div>
                </div>
                <div class="score-card">
                    <div class="score-value" id="skillScore"></div>
                    <div>Skills Match</div>
                </div>
                <div class="score-card">
                    <div class="score-value" id="expScore"></div>
                    <div>Experience Match</div>
                </div>
            </div>
            <div class="details" id="details"></div>
        </div>
    </div>

    <script>
        document.getElementById('matchForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            
            loading.style.display = 'block';
            results.style.display = 'none';
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                // Update results
                document.getElementById('recommendation').textContent = 
                    data.status + ' ' + data.recommendation;
                document.getElementById('overallScore').textContent = data.overall_score + '%';
                document.getElementById('skillScore').textContent = data.skill_score + '%';
                document.getElementById('expScore').textContent = data.experience_score + '%';
                
                // Set result styling
                results.className = 'results';
                if (data.recommendation === 'SEND') {
                    results.classList.add('send');
                } else if (data.recommendation === 'MAYBE SEND') {
                    results.classList.add('maybe');
                } else {
                    results.classList.add('reject');
                }
                
                // Update details
                let detailsHtml = '<h3>Analysis Details:</h3>';
                detailsHtml += `<p><strong>Experience:</strong> Candidate has ${data.resume_experience} years, Required: ${data.required_experience} years</p>`;
                
                if (Object.keys(data.detailed_matches).length > 0) {
                    detailsHtml += '<h4>Skill Matches:</h4>';
                    for (const [category, matches] of Object.entries(data.detailed_matches)) {
                        detailsHtml += `<p><strong>${category}:</strong> `;
                        detailsHtml += `✅ ${matches.matched.join(', ')}`;
                        if (matches.missing.length > 0) {
                            detailsHtml += ` | ❌ Missing: ${matches.missing.join(', ')}`;
                        }
                        detailsHtml += '</p>';
                    }
                }
                
                document.getElementById('details').innerHTML = detailsHtml;
                results.style.display = 'block';
                
            } catch (error) {
                alert('Error analyzing match: ' + error.message);
            } finally {
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>
    """)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        resume_text = ""
        jd_text = ""
        
        # Handle resume input
        if 'resume' in request.files and request.files['resume'].filename:
            resume_file = request.files['resume']
            filename = secure_filename(resume_file.filename)
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(resume_path)
            resume_text = matcher.extract_text(resume_path)
            os.remove(resume_path)  # Clean up
        elif request.form.get('resumeText'):
            resume_text = request.form.get('resumeText')
        
        # Handle JD input
        if 'jd' in request.files and request.files['jd'].filename:
            jd_file = request.files['jd']
            filename = secure_filename(jd_file.filename)
            jd_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            jd_file.save(jd_path)
            jd_text = matcher.extract_text(jd_path)
            os.remove(jd_path)  # Clean up
        elif request.form.get('jdText'):
            jd_text = request.form.get('jdText')
        
        if not resume_text or not jd_text:
            return jsonify({'error': 'Please provide both resume and job description'})
        
        # Analyze match
        results = matcher.calculate_match_score(resume_text, jd_text)
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API endpoint for programmatic access"""
    try:
        data = request.get_json()
        
        if not data or 'resume' not in data or 'jd' not in data:
            return jsonify({'error': 'Please provide both resume and jd in JSON format'})
        
        results = matcher.calculate_match_score(data['resume'], data['jd'])
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)})

# Railway deployment optimization
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
