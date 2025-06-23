from flask import Flask, request, jsonify, render_template_string
import PyPDF2
import docx2txt
import re
from typing import Dict, List
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory
os.makedirs('uploads', exist_ok=True)

class DomainMatcher:
    def __init__(self):
        # Define clear domain patterns
        self.domains = {
            'design_verification': {
                'name': 'Design Verification (DV)',
                'keywords': [
                    'design verification', 'dv engineer', 'verification engineer', 'functional verification',
                    'uvm', 'testbench', 'coverage', 'assertion', 'constrained random', 'verification methodology',
                    'simulation', 'debugging', 'verification plan', 'test cases', 'coverage analysis',
                    'formal verification', 'lint', 'cdc', 'equivalence checking', 'verification ip',
                    'systemverilog', 'verilog', 'verification', 'rtl verification', 'block level verification',
                    'chip level verification', 'regression', 'test harness'
                ]
            },
            'physical_design': {
                'name': 'Physical Design (PD)',
                'keywords': [
                    'physical design', 'pd engineer', 'backend engineer', 'place and route', 'pnr',
                    'floorplan', 'floor planning', 'placement', 'routing', 'timing closure', 'sta',
                    'static timing analysis', 'icc2', 'innovus', 'primetime', 'timing constraints',
                    'power analysis', 'ir drop', 'signal integrity', 'cts', 'clock tree synthesis',
                    'post layout', 'parasitic extraction', 'physical verification', 'drc', 'lvs',
                    'antenna check', 'fill insertion', 'eco', 'metal layer', 'via optimization'
                ]
            },
            'rtl_design': {
                'name': 'RTL Design',
                'keywords': [
                    'rtl design', 'rtl engineer', 'design engineer', 'logic design', 'digital design',
                    'verilog', 'systemverilog', 'hdl', 'synthesis', 'design compiler', 'rtl coding',
                    'microarchitecture', 'architecture design', 'functional specification', 'design specification',
                    'rtl implementation', 'ip design', 'module design', 'interface design',
                    'protocol implementation', 'datapath design', 'control logic', 'state machine'
                ]
            }
        }
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception:
                        continue
                return text if text.strip() else "No text found in PDF"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            text = docx2txt.process(file_path)
            return text if text and text.strip() else "No readable text found in DOCX file"
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
    
    def detect_domain(self, text: str) -> Dict:
        """Detect the primary domain of a text"""
        text_lower = text.lower()
        domain_scores = {}
        matched_keywords = {}
        
        for domain_key, domain_info in self.domains.items():
            score = 0
            matches = []
            
            for keyword in domain_info['keywords']:
                if keyword in text_lower:
                    score += 1
                    matches.append(keyword)
            
            domain_scores[domain_key] = score
            matched_keywords[domain_key] = matches
        
        # Find the domain with highest score
        if not any(domain_scores.values()):
            return {
                'primary_domain': 'unknown',
                'domain_name': 'Unknown/Other',
                'confidence': 0,
                'all_scores': domain_scores,
                'matched_keywords': matched_keywords
            }
        
        primary_domain = max(domain_scores, key=domain_scores.get)
        max_score = domain_scores[primary_domain]
        total_possible = len(self.domains[primary_domain]['keywords'])
        confidence = (max_score / total_possible) * 100
        
        return {
            'primary_domain': primary_domain,
            'domain_name': self.domains[primary_domain]['name'],
            'confidence': round(confidence, 1),
            'score': max_score,
            'total_keywords': total_possible,
            'all_scores': domain_scores,
            'matched_keywords': matched_keywords
        }
    
    def compare_domains(self, resume_text: str, jd_text: str) -> Dict:
        """Compare domains between resume and JD"""
        
        resume_domain = self.detect_domain(resume_text)
        jd_domain = self.detect_domain(jd_text)
        
        # Determine if domains match
        domains_match = resume_domain['primary_domain'] == jd_domain['primary_domain']
        
        # Determine recommendation
        if resume_domain['primary_domain'] == 'unknown' or jd_domain['primary_domain'] == 'unknown':
            recommendation = "MANUAL REVIEW"
            status = "⚠️"
            reason = "Unable to clearly identify domain from text"
        elif domains_match:
            recommendation = "DOMAIN MATCH - PROCEED"
            status = "✅"
            reason = f"Both resume and JD are in {resume_domain['domain_name']} domain"
        else:
            recommendation = "DOMAIN MISMATCH - DO NOT SEND"
            status = "❌"
            reason = f"Resume is {resume_domain['domain_name']} but JD requires {jd_domain['domain_name']}"
        
        return {
            'recommendation': recommendation,
            'status': status,
            'reason': reason,
            'domains_match': domains_match,
            'resume_domain': resume_domain,
            'jd_domain': jd_domain
        }

# Initialize matcher
matcher = DomainMatcher()

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Domain Matcher - Phase 1</title>
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
        .phase-info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #2196f3;
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
            font-family: Arial, sans-serif;
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
        .match { background-color: #d4edda; border: 1px solid #c3e6cb; }
        .mismatch { background-color: #f8d7da; border: 1px solid #f5c6cb; }
        .review { background-color: #fff3cd; border: 1px solid #ffeaa7; }
        .domain-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .confidence-bar {
            background: #f0f0f0;
            height: 20px;
            border-radius: 10px;
            margin: 10px 0;
            overflow: hidden;
        }
        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #e74c3c, #f39c12, #27ae60);
            transition: width 0.3s ease;
        }
        .keywords {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 10px 0;
        }
        .keyword {
            background: #e8f4f8;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            border: 1px solid #bee5eb;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Domain Matcher - Phase 1</h1>
        
        <div class="phase-info">
            <strong>📋 Phase 1: Domain Detection Only</strong><br>
            This version focuses purely on identifying whether the resume and job description are in the same domain:
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Design Verification (DV):</strong> UVM, testbench, verification, coverage, assertions</li>
                <li><strong>Physical Design (PD):</strong> Place & route, floorplan, timing closure, ICC2, STA</li>
                <li><strong>RTL Design:</strong> Verilog, synthesis, architecture, logic design</li>
            </ul>
        </div>
        
        <form id="matchForm">
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
            
            <button type="submit">🔍 Check Domain Match</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Analyzing domains...</p>
        </div>
        
        <div class="results" id="results">
            <h2 id="recommendation"></h2>
            <p id="reason"></p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div class="domain-card">
                    <h4>📄 Resume Domain</h4>
                    <div id="resumeDomain"></div>
                </div>
                <div class="domain-card">
                    <h4>📋 JD Domain</h4>
                    <div id="jdDomain"></div>
                </div>
            </div>
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
                
                if (!response.ok) {
                    throw new Error(`Server error (${response.status})`);
                }
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                // Update recommendation
                document.getElementById('recommendation').textContent = data.status + ' ' + data.recommendation;
                document.getElementById('reason').textContent = data.reason;
                
                // Set result styling
                results.className = 'results';
                if (data.domains_match) {
                    results.classList.add('match');
                } else if (data.recommendation.includes('MANUAL')) {
                    results.classList.add('review');
                } else {
                    results.classList.add('mismatch');
                }
                
                // Update domain cards
                updateDomainCard('resumeDomain', data.resume_domain);
                updateDomainCard('jdDomain', data.jd_domain);
                
                results.style.display = 'block';
                
            } catch (error) {
                alert('Analysis failed: ' + error.message);
            } finally {
                loading.style.display = 'none';
            }
        });
        
        function updateDomainCard(elementId, domainData) {
            const element = document.getElementById(elementId);
            const confidence = domainData.confidence || 0;
            
            let html = `
                <div><strong>Detected Domain:</strong> ${domainData.domain_name}</div>
                <div><strong>Confidence:</strong> ${confidence}% (${domainData.score}/${domainData.total_keywords} keywords)</div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidence}%"></div>
                </div>
            `;
            
            if (domainData.matched_keywords && domainData.matched_keywords[domainData.primary_domain]) {
                const keywords = domainData.matched_keywords[domainData.primary_domain];
                if (keywords.length > 0) {
                    html += '<div><strong>Matched Keywords:</strong></div>';
                    html += '<div class="keywords">';
                    keywords.slice(0, 10).forEach(keyword => {
                        html += `<span class="keyword">${keyword}</span>`;
                    });
                    if (keywords.length > 10) {
                        html += `<span class="keyword">+${keywords.length - 10} more</span>`;
                    }
                    html += '</div>';
                }
            }
            
            element.innerHTML = html;
        }
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
            os.remove(resume_path)
            
            if resume_text.startswith('Error') or resume_text.startswith('No'):
                return jsonify({'error': f'Resume file issue: {resume_text}'})
                
        elif request.form.get('resumeText'):
            resume_text = request.form.get('resumeText').strip()
        
        # Handle JD input
        if 'jd' in request.files and request.files['jd'].filename:
            jd_file = request.files['jd']
            filename = secure_filename(jd_file.filename)
            jd_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            jd_file.save(jd_path)
            jd_text = matcher.extract_text(jd_path)
            os.remove(jd_path)
            
            if jd_text.startswith('Error') or jd_text.startswith('No'):
                return jsonify({'error': f'JD file issue: {jd_text}'})
                
        elif request.form.get('jdText'):
            jd_text = request.form.get('jdText').strip()
        
        # Validation
        if not resume_text or len(resume_text) < 20:
            return jsonify({'error': 'Please provide resume text (at least 20 characters)'})
        
        if not jd_text or len(jd_text) < 20:
            return jsonify({'error': 'Please provide job description text (at least 20 characters)'})
        
        # Analyze domains
        results = matcher.compare_domains(resume_text, jd_text)
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in analyze endpoint: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
