from flask import Flask, request, jsonify, render_template_string
import re
import os
import json
from collections import defaultdict
import math
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file):
    """Extract text from uploaded files"""
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    print(f"Extracting text from {filename}, extension: {file_ext}")
    
    try:
        if file_ext == 'txt':
            content = file.read()
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('utf-8', errors='ignore')
            print(f"TXT file processed: {len(text)} characters")
            return text
        
        elif file_ext == 'pdf':
            try:
                file_content = file.read()
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    print(f"PDF page {page_num + 1} processed")
                print(f"PDF file processed: {len(text)} characters")
                return text
            except Exception as e:
                print(f"PDF processing error: {str(e)}")
                return f"Error processing PDF {filename}: {str(e)}"
        
        elif file_ext == 'docx':
            try:
                file_content = file.read()
                doc = docx.Document(io.BytesIO(file_content))
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                print(f"DOCX file processed: {len(text)} characters")
                return text
            except Exception as e:
                print(f"DOCX processing error: {str(e)}")
                return f"Error processing DOCX {filename}: {str(e)}"
        
        elif file_ext == 'doc':
            try:
                content = file.read()
                # Try different encodings for .doc files
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        text = content.decode(encoding, errors='ignore')
                        # Basic cleanup for .doc files
                        text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)
                        text = re.sub(r'\s+', ' ', text)
                        print(f"DOC file processed with {encoding}: {len(text)} characters")
                        return text
                    except:
                        continue
                return f"Could not decode .doc file {filename}. Please convert to .docx format."
            except Exception as e:
                print(f"DOC processing error: {str(e)}")
                return f"Error processing DOC {filename}: {str(e)}"
        
        else:
            return f"Unsupported file format: {file_ext}"
    
    except Exception as e:
        print(f"General file processing error for {filename}: {str(e)}")
        return f"Error extracting text from {filename}: {str(e)}"

# HTML Template embedded in Python (no separate templates folder needed)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔬 VLSI & Embedded Resume Matcher</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .python-badge {
            background: #3776ab;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            margin-top: 10px;
            display: inline-block;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            padding: 30px;
        }
        
        .input-section {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            border: 2px dashed #dee2e6;
            transition: all 0.3s ease;
        }
        
        .input-section:hover {
            border-color: #667eea;
            background: #f1f3f4;
        }
        
        .input-section h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.3rem;
        }
        
        textarea {
            width: 100%;
            min-height: 200px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
            transition: border-color 0.3s ease;
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .analyze-btn {
            grid-column: 1 / -1;
            text-align: center;
            margin-top: 20px;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 1.1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .results { margin-top: 30px; display: none; }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .match-result {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 30px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
            border-left: 5px solid #28a745;
        }
        
        .match-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .match-score {
            font-size: 2rem;
            font-weight: bold;
            color: #28a745;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .score-badge {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            border-radius: 4px;
            transition: width 1s ease;
        }
        
        .match-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .detail-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .detail-card h4 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .skill-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        
        .skill-tag {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
            display: none;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 30px;
            border-left: 4px solid #dc3545;
            display: none;
        }
        
        .skill-breakdown {
            font-size: 0.9rem;
            line-height: 1.6;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
                gap: 20px;
                padding: 20px;
            }
            .header h1 { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 VLSI & Embedded Resume Matcher</h1>
            <p>Python-powered AI matching for VLSI Design & Embedded Systems roles</p>
            <div class="python-badge">🐍 Python Flask + Railway</div>
        </div>

        <div class="main-content">
            <div class="input-section">
                <h3>📋 Job Description</h3>
                <div class="file-upload" onclick="document.getElementById('jdFiles').click()" 
                     ondrop="handleFileDrop(event, 'jd')" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)">
                    <input type="file" id="jdFiles" accept=".txt,.pdf,.doc,.docx" multiple onchange="handleFileSelect(event, 'jd')">
                    <div>📁 <strong>Upload JD Files</strong></div>
                    <div class="upload-text">Drag & drop files here or click to browse</div>
                    <div class="upload-text">Supports: PDF, DOC, DOCX, TXT</div>
                </div>
                <div id="jdUploadedFiles" class="uploaded-files"></div>
                
                <div class="or-divider"><span>OR</span></div>
                
                <textarea id="jobDescription" placeholder="Paste your VLSI/Embedded job description here...

Example:
- 5+ years experience in VLSI design
- Strong knowledge of Verilog/SystemVerilog
- Experience with Synopsys tools (Design Compiler, ICC2)
- UVM verification methodology
- RTL design and synthesis
- ASIC/FPGA design experience"></textarea>
            </div>

            <div class="input-section">
                <h3>👥 Resumes</h3>
                <div class="file-upload" onclick="document.getElementById('resumeFiles').click()" 
                     ondrop="handleFileDrop(event, 'resume')" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)">
                    <input type="file" id="resumeFiles" accept=".txt,.pdf,.doc,.docx" multiple onchange="handleFileSelect(event, 'resume')">
                    <div>👤 <strong>Upload Resume Files</strong></div>
                    <div class="upload-text">Drag & drop multiple resumes here or click to browse</div>
                    <div class="upload-text">Supports: PDF, DOC, DOCX, TXT</div>
                </div>
                <div id="resumeUploadedFiles" class="uploaded-files"></div>
                
                <div class="or-divider"><span>OR</span></div>
                
                <textarea id="resumes" placeholder="Paste resumes here (separate multiple resumes with '---')...

Example:
John Doe
VLSI Design Engineer
5 years experience in digital design using Verilog and SystemVerilog.
Worked with Cadence and Synopsys tools including Vivado, Quartus.
Experience in RTL design, verification using UVM methodology.

---

Jane Smith  
Embedded Systems Engineer
3 years firmware development experience..."></textarea>
            </div>

            <div class="analyze-btn">
                <button class="btn" onclick="analyzeMatches()" id="analyzeBtn">
                    🚀 Analyze Matches
                </button>
            </div>
        </div>

        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Python AI analyzing VLSI/Embedded resumes...</p>
        </div>

        <div id="error" class="error"></div>

        <div id="results" class="results">
            <div class="stats" id="statsSection"></div>
            <div id="matchResults"></div>
        </div>
    </div>

    <script>
        // Global variables for file handling
        let uploadedJDFiles = [];
        let uploadedResumeFiles = [];

        // File drag and drop handlers
        function handleDragOver(event) {
            event.preventDefault();
            event.currentTarget.classList.add('dragover');
        }

        function handleDragLeave(event) {
            event.currentTarget.classList.remove('dragover');
        }

        function handleFileDrop(event, type) {
            event.preventDefault();
            event.currentTarget.classList.remove('dragover');
            
            const files = Array.from(event.dataTransfer.files);
            handleFiles(files, type);
        }

        function handleFileSelect(event, type) {
            const files = Array.from(event.target.files);
            handleFiles(files, type);
        }

        function handleFiles(files, type) {
            console.log(`Handling ${files.length} files for ${type}`);
            
            const validFiles = files.filter(file => {
                const ext = file.name.split('.').pop().toLowerCase();
                const isValid = ['txt', 'pdf', 'doc', 'docx'].includes(ext);
                console.log(`File ${file.name}: ${isValid ? 'valid' : 'invalid'}`);
                return isValid;
            });

            console.log(`${validFiles.length} valid files out of ${files.length}`);

            if (validFiles.length === 0) {
                showError('No valid files selected. Please upload PDF, DOC, DOCX, or TXT files.');
                return;
            }

            if (type === 'jd') {
                uploadedJDFiles = uploadedJDFiles.concat(validFiles);
                displayUploadedFiles(uploadedJDFiles, 'jdUploadedFiles', 'jd');
                console.log(`Total JD files: ${uploadedJDFiles.length}`);
            } else {
                uploadedResumeFiles = uploadedResumeFiles.concat(validFiles);
                displayUploadedFiles(uploadedResumeFiles, 'resumeUploadedFiles', 'resume');
                console.log(`Total resume files: ${uploadedResumeFiles.length}`);
            }

            if (validFiles.length < files.length) {
                showError(`${files.length - validFiles.length} file(s) were skipped (unsupported format). Only PDF, DOC, DOCX, and TXT files are supported.`);
            }
        }

        function displayUploadedFiles(files, containerId, type) {
            const container = document.getElementById(containerId);
            
            if (files.length === 0) {
                container.style.display = 'none';
                return;
            }

            container.style.display = 'block';
            container.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 8px;">
                    📎 ${files.length} file(s) uploaded:
                </div>
                ${files.map((file, index) => `
                    <div class="file-item">
                        <span>📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
                        <span class="remove-file" onclick="removeFile(${index}, '${type}')">&times;</span>
                    </div>
                `).join('')}
            `;
        }

        function removeFile(index, type) {
            if (type === 'jd') {
                uploadedJDFiles.splice(index, 1);
                displayUploadedFiles(uploadedJDFiles, 'jdUploadedFiles', 'jd');
            } else {
                uploadedResumeFiles.splice(index, 1);
                displayUploadedFiles(uploadedResumeFiles, 'resumeUploadedFiles', 'resume');
            }
        }

        async function extractTextFromFiles(files) {
            const formData = new FormData();
            files.forEach((file, index) => {
                formData.append('files', file);
            });

            try {
                const response = await fetch('/extract-text', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                if (data.success) {
                    return data.texts.join('\n---\n');
                } else {
                    throw new Error(data.error || 'Unknown error');
                }
            } catch (error) {
                console.error('File extraction error:', error);
                throw new Error('Failed to extract text from files: ' + error.message);
            }
        }

        async function analyzeMatches() {
            let jobDescription = document.getElementById('jobDescription').value.trim();
            let resumes = document.getElementById('resumes').value.trim();
            
            try {
                // Show loading early
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';
                document.getElementById('error').style.display = 'none';
                document.getElementById('analyzeBtn').disabled = true;

                // Extract text from uploaded JD files if any
                if (uploadedJDFiles.length > 0) {
                    console.log('Processing JD files:', uploadedJDFiles.length);
                    try {
                        const jdFromFiles = await extractTextFromFiles(uploadedJDFiles);
                        jobDescription = jdFromFiles + (jobDescription ? '\n' + jobDescription : '');
                        console.log('JD text extracted successfully');
                    } catch (error) {
                        console.error('JD file processing error:', error);
                        showError('Error processing JD files: ' + error.message);
                        return;
                    }
                }

                // Extract text from uploaded resume files if any
                if (uploadedResumeFiles.length > 0) {
                    console.log('Processing resume files:', uploadedResumeFiles.length);
                    try {
                        const resumesFromFiles = await extractTextFromFiles(uploadedResumeFiles);
                        resumes = resumesFromFiles + (resumes ? '\n---\n' + resumes : '');
                        console.log('Resume text extracted successfully');
                    } catch (error) {
                        console.error('Resume file processing error:', error);
                        showError('Error processing resume files: ' + error.message);
                        return;
                    }
                }

                if (!jobDescription || !resumes) {
                    showError('Please provide both job description and resumes (either upload files or paste text)!');
                    return;
                }

                console.log('Sending analysis request...');
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        job_description: jobDescription,
                        resumes: resumes
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                if (data.success) {
                    displayResults(data.results, data.statistics);
                } else {
                    showError(data.error || 'Analysis failed');
                }
            } catch (error) {
                console.error('Analysis error:', error);
                showError('Error: ' + error.message);
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('analyzeBtn').disabled = false;
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }

        function displayResults(results, stats) {
            const statsSection = document.getElementById('statsSection');
            const matchResults = document.getElementById('matchResults');
            
            // Display statistics
            statsSection.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${stats.total_resumes}</div>
                    <div>Total Resumes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.average_score}%</div>
                    <div>Average Match</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.top_score}%</div>
                    <div>Top Match</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.qualified_candidates}</div>
                    <div>Qualified (70%+)</div>
                </div>
            `;

            // Display individual results
            matchResults.innerHTML = results.map(result => `
                <div class="match-result">
                    <div class="match-header">
                        <h3>${result.candidate_name}</h3>
                        <div class="match-score">
                            ${result.overall_score}%
                            <span class="score-badge">${getMatchRating(result.overall_score)}</span>
                        </div>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${result.overall_score}%"></div>
                    </div>
                    
                    <div class="match-details">
                        <div class="detail-card">
                            <h4>📊 Score Breakdown</h4>
                            <p><strong>Skills Match:</strong> ${result.breakdown_scores.skills}%</p>
                            <p><strong>Semantic Match:</strong> ${result.breakdown_scores.semantic}%</p>
                            <p><strong>Experience:</strong> ${result.breakdown_scores.experience}%</p>
                            <p><strong>Education:</strong> ${result.breakdown_scores.education}%</p>
                        </div>
                        
                        <div class="detail-card">
                            <h4>🎯 Key Matches</h4>
                            <div class="skill-tags">
                                ${result.matched_keywords.slice(0, 8).map(keyword => 
                                    `<span class="skill-tag">${keyword}</span>`
                                ).join('')}
                            </div>
                        </div>
                        
                        <div class="detail-card">
                            <h4>🔧 VLSI/Embedded Skills</h4>
                            <div class="skill-breakdown">
                                <p><strong>Design:</strong> ${result.skill_details.vlsi_design.found.length}/${result.skill_details.vlsi_design.required.length} (${Math.round(result.skill_details.vlsi_design.score * 100)}%)</p>
                                <p><strong>EDA Tools:</strong> ${result.skill_details.eda_tools.found.length}/${result.skill_details.eda_tools.required.length} (${Math.round(result.skill_details.eda_tools.score * 100)}%)</p>
                                <p><strong>Verification:</strong> ${result.skill_details.verification.found.length}/${result.skill_details.verification.required.length} (${Math.round(result.skill_details.verification.score * 100)}%)</p>
                                <p><strong>Programming:</strong> ${result.skill_details.embedded_programming.found.length}/${result.skill_details.embedded_programming.required.length} (${Math.round(result.skill_details.embedded_programming.score * 100)}%)</p>
                            </div>
                        </div>
                        
                        <div class="detail-card">
                            <h4>🏆 Recommendation</h4>
                            <p>${getRecommendation(result.overall_score)}</p>
                        </div>
                    </div>
                </div>
            `).join('');

            document.getElementById('results').style.display = 'block';
        }

        function getMatchRating(score) {
            if (score >= 90) return 'Excellent';
            if (score >= 80) return 'Very Good';
            if (score >= 70) return 'Good';
            if (score >= 60) return 'Fair';
            return 'Poor';
        }

        function getRecommendation(score) {
            if (score >= 90) return 'Exceptional candidate for VLSI/Embedded role. Strong technical expertise across multiple domains. Recommend immediate technical interview.';
            if (score >= 80) return 'Excellent match for the position. Has required technical skills and tools experience. Schedule detailed technical discussion.';
            if (score >= 70) return 'Good candidate with relevant VLSI/Embedded background. Consider for interview to assess depth of experience.';
            if (score >= 60) return 'Moderate technical match. May be suitable for junior roles or with additional training in specific tools/methodologies.';
            return 'Limited match with job requirements. Consider only if expanding search criteria or for entry-level positions.';
        }
    </script>
</body>
</html>
"""

class VLSIResumeMatcherAI:
    def __init__(self):
        self.skills_database = self.load_skills_database()
        self.stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
    def load_skills_database(self):
        return {
            # VLSI & Digital Design Skills
            'vlsi_design': ['verilog', 'vhdl', 'systemverilog', 'system verilog', 'rtl design', 'rtl', 'logic design', 'digital design', 'asic design', 'fpga design', 'soc design', 'ip design', 'block design', 'chip design', 'ic design', 'vlsi design', 'analog design', 'mixed signal', 'ams', 'custom ic', 'standard cell', 'gate level', 'behavioral modeling', 'structural modeling', 'dataflow modeling'],
            
            # EDA Tools & Simulation
            'eda_tools': ['cadence', 'synopsys', 'mentor graphics', 'siemens eda', 'vivado', 'quartus', 'modelsim', 'questasim', 'vcs', 'ncsim', 'incisive', 'xcelium', 'design compiler', 'genus', 'innovus', 'encounter', 'icc', 'icc2', 'prime time', 'pt', 'redhawk', 'voltus', 'calibre', 'icv', 'hercules', 'virtuoso', 'spectre', 'hspice', 'eldo', 'ads', 'momentum', 'em', 'starrc', 'quantus', 'raphael'],
            
            # Verification & Testing
            'verification': ['uvm', 'ovm', 'vmm', 'testbench', 'verification', 'functional verification', 'formal verification', 'assertion based verification', 'coverage driven verification', 'cdv', 'constrained random', 'directed test', 'regression', 'lint', 'cdc', 'clock domain crossing', 'rdc', 'reset domain crossing', 'x-propagation', 'gate level simulation', 'gls', 'sdf', 'timing verification', 'sta', 'static timing analysis', 'dft', 'design for test', 'scan', 'atpg', 'bist', 'boundary scan', 'jtag'],
            
            # Physical Design & Backend
            'physical_design': ['physical design', 'backend', 'place and route', 'pnr', 'floorplanning', 'placement', 'routing', 'cts', 'clock tree synthesis', 'power planning', 'ir drop', 'em', 'electromigration', 'timing closure', 'crosstalk', 'noise analysis', 'rc extraction', 'parasitic extraction', 'lvs', 'drc', 'antenna', 'latch-up', 'well proximity', 'density', 'metal fill', 'via fill', 'double patterning', 'multi-patterning'],
            
            # Embedded Programming
            'embedded_programming': ['c', 'c++', 'embedded c', 'assembly', 'arm assembly', 'risc-v', 'python', 'matlab', 'perl', 'tcl', 'shell scripting', 'bash', 'makefile', 'cmake', 'git', 'svn', 'embedded systems', 'firmware', 'device drivers', 'rtos', 'freertos', 'bare metal', 'bootloader', 'u-boot', 'linux kernel', 'yocto', 'buildroot'],
            
            # Microcontrollers & Processors
            'microcontrollers': ['arm cortex', 'cortex-m', 'cortex-a', 'cortex-r', 'arm7', 'arm9', 'arm11', 'pic', 'avr', 'atmega', 'attiny', '8051', 'msp430', 'dsp', 'tms320', 'blackfin', 'risc-v', 'esp32', 'esp8266', 'stm32', 'nrf', 'nordic', 'ti', 'microchip', 'infineon', 'nxp', 'freescale', 'xilinx', 'altera', 'intel fpga', 'zynq', 'cyclone', 'stratix', 'kintex', 'virtex'],
            
            # Communication Protocols
            'protocols': ['spi', 'i2c', 'uart', 'usart', 'can', 'lin', 'ethernet', 'usb', 'pcie', 'axi', 'axi4', 'ahb', 'apb', 'amba', 'avalon', 'wishbone', 'ocp', 'tilelink', 'noc', 'network on chip', 'serdes', 'mipi', 'csi', 'dsi', 'lvds', 'jesd204b', 'sata', 'ddr', 'ddr3', 'ddr4', 'ddr5', 'lpddr', 'gddr', 'hbm'],
            
            # Standards & Methodologies
            'standards': ['iso 26262', 'automotive', 'do-178', 'aerospace', 'iec 61508', 'functional safety', 'misra c', 'autosar', 'agile', 'waterfall', 'v-model', 'scrum', 'six sigma', 'lean'],
            
            # Soft Skills
            'soft': ['problem solving', 'debugging', 'analytical thinking', 'attention to detail', 'teamwork', 'communication', 'documentation', 'project management', 'time management', 'leadership', 'mentoring'],
            
            # Certifications
            'certifications': ['arm certified', 'xilinx certified', 'intel fpga certified', 'cadence certified', 'synopsys certified', 'pmp', 'six sigma', 'agile certified'],
            
            # Application Domains
            'domains': ['automotive', 'aerospace', 'defense', 'telecommunications', 'consumer electronics', 'iot', 'medical devices', 'industrial automation', 'networking', 'ai accelerator', 'mobile', 'wireless']
        }
    
    def extract_keywords(self, text):
        words = re.sub(r'[^\w\s.-]', ' ', text.lower()).split()
        words = [word for word in words if len(word) > 2 and word not in self.stop_words]
        phrases = self.extract_phrases(text.lower())
        return list(set(words + phrases))
    
    def extract_phrases(self, text):
        phrases = []
        all_skills = []
        for category_skills in self.skills_database.values():
            all_skills.extend(category_skills)
        
        for skill in all_skills:
            if skill.lower() in text:
                phrases.append(skill.lower())
        
        return phrases
    
    def are_skills_similar(self, skill1, skill2):
        synonyms = {
            'verilog': ['hdl'],
            'systemverilog': ['system verilog', 'sv'],
            'rtl': ['rtl design'],
            'soc': ['system on chip'],
            'asic': ['application specific integrated circuit'],
            'fpga': ['field programmable gate array'],
            'uvm': ['universal verification methodology'],
            'sta': ['static timing analysis'],
            'pnr': ['place and route'],
            'cts': ['clock tree synthesis']
        }
        
        s1, s2 = skill1.lower(), skill2.lower()
        
        for key, values in synonyms.items():
            if ((key in s1 or any(v in s1 for v in values)) and 
                (key in s2 or any(v in s2 for v in values))):
                return True
        
        return False
    
    def calculate_skill_match(self, jd_skills, resume_skills):
        categories = list(self.skills_database.keys())
        match_details = {}
        weighted_score = 0
        
        category_weights = {
            'vlsi_design': 0.25, 'eda_tools': 0.20, 'verification': 0.15,
            'physical_design': 0.10, 'embedded_programming': 0.15,
            'microcontrollers': 0.05, 'protocols': 0.05, 'standards': 0.02,
            'soft': 0.05, 'certifications': 0.02, 'domains': 0.01
        }
        
        for category in categories:
            category_skills = self.skills_database[category]
            
            jd_category_skills = [skill for skill in jd_skills 
                                if any(cs.lower() in skill.lower() or skill.lower() in cs.lower() 
                                      or self.are_skills_similar(skill, cs) for cs in category_skills)]
            
            resume_category_skills = [skill for skill in resume_skills 
                                    if any(cs.lower() in skill.lower() or skill.lower() in cs.lower() 
                                          or self.are_skills_similar(skill, cs) for cs in category_skills)]
            
            matched_skills = [skill for skill in jd_category_skills 
                            if any(rs.lower() in skill.lower() or skill.lower() in rs.lower() 
                                  or self.are_skills_similar(skill, rs) for rs in resume_category_skills)]
            
            category_match = len(matched_skills) / len(jd_category_skills) if jd_category_skills else 1
            
            match_details[category] = {
                'required': jd_category_skills,
                'found': matched_skills,
                'score': category_match,
                'weight': category_weights.get(category, 0.01)
            }
            
            weighted_score += category_match * category_weights.get(category, 0.01)
        
        return {'overall_score': weighted_score, 'details': match_details}
    
    def extract_years_of_experience(self, text):
        patterns = [
            r'(\d+)\+?\s*years?\s*of?\s*experience',
            r'(\d+)\+?\s*year?\s*experience',
            r'experience.*?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*exp'
        ]
        
        max_years = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                years = int(match)
                max_years = max(max_years, years)
        
        return max_years
    
    def calculate_experience_match(self, jd_text, resume_text):
        jd_years = self.extract_years_of_experience(jd_text)
        resume_years = self.extract_years_of_experience(resume_text)
        
        if jd_years == 0 or resume_years == 0:
            return 0.5
        
        return min(resume_years / jd_years, 1)
    
    def calculate_education_match(self, jd_text, resume_text):
        education_levels = {
            'phd': 5, 'doctorate': 5, 'master': 4, 'masters': 4, 'mba': 4,
            'bachelor': 3, 'bachelors': 3, 'bs': 3, 'ba': 3, 'be': 3,
            'associate': 2, 'diploma': 2, 'certificate': 1
        }
        
        jd_education = max([education_levels.get(level, 0) for level in education_levels 
                           if level in jd_text.lower()] + [0])
        resume_education = max([education_levels.get(level, 0) for level in education_levels 
                               if level in resume_text.lower()] + [0])
        
        if jd_education == 0:
            return 0.8
        
        return min(resume_education / jd_education, 1)
    
    def calculate_semantic_similarity(self, keywords1, keywords2):
        set1, set2 = set(keywords1), set(keywords2)
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        return len(intersection) / len(union) if union else 0
    
    def analyze_resume(self, job_description, resume, resume_index):
        jd_keywords = self.extract_keywords(job_description)
        resume_keywords = self.extract_keywords(resume)
        
        semantic_score = self.calculate_semantic_similarity(jd_keywords, resume_keywords)
        skill_match = self.calculate_skill_match(jd_keywords, resume_keywords)
        experience_match = self.calculate_experience_match(job_description, resume)
        education_match = self.calculate_education_match(job_description, resume)
        
        # Weighted scoring for VLSI/Embedded
        weights = {'semantic': 0.25, 'skills': 0.55, 'experience': 0.15, 'education': 0.05}
        
        overall_score = (
            semantic_score * weights['semantic'] +
            skill_match['overall_score'] * weights['skills'] +
            experience_match * weights['experience'] +
            education_match * weights['education']
        ) * 100
        
        # Extract candidate name
        name_match = re.search(r'^([A-Z][a-z]+ [A-Z][a-z]+)', resume)
        candidate_name = name_match.group(1) if name_match else f"Candidate {resume_index + 1}"
        
        matched_keywords = [kw for kw in jd_keywords 
                           if any(rk for rk in resume_keywords 
                                 if kw.lower() in rk.lower() or rk.lower() in kw.lower())]
        
        return {
            'candidate_name': candidate_name,
            'overall_score': round(overall_score),
            'breakdown_scores': {
                'semantic': round(semantic_score * 100),
                'skills': round(skill_match['overall_score'] * 100),
                'experience': round(experience_match * 100),
                'education': round(education_match * 100)
            },
            'skill_details': skill_match['details'],
            'matched_keywords': matched_keywords[:20],
            'resume_preview': resume[:500] + '...' if len(resume) > 500 else resume
        }

# Initialize the matcher
matcher = VLSIResumeMatcherAI()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'OK', 'message': 'VLSI Resume Matcher is running!', 'python': True})

@app.route('/extract-text', methods=['POST'])
def extract_text():
    """Extract text from uploaded files"""
    try:
        print("Extract text endpoint called")  # Debug log
        
        if 'files' not in request.files:
            print("No 'files' key in request.files")
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        print(f"Number of files received: {len(files)}")
        
        if not files or all(file.filename == '' for file in files):
            print("All files are empty")
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        extracted_texts = []
        
        for i, file in enumerate(files):
            print(f"Processing file {i+1}: {file.filename}")
            
            if file and file.filename != '':
                if allowed_file(file.filename):
                    try:
                        text = extract_text_from_file(file)
                        print(f"Extracted {len(text)} characters from {file.filename}")
                        extracted_texts.append(f"=== {file.filename} ===\n{text}")
                    except Exception as e:
                        print(f"Error processing file {file.filename}: {str(e)}")
                        return jsonify({'success': False, 'error': f'Error processing {file.filename}: {str(e)}'}), 500
                else:
                    print(f"File type not supported: {file.filename}")
                    return jsonify({'success': False, 'error': f'File type not supported: {file.filename}'}), 400
        
        print(f"Successfully processed {len(extracted_texts)} files")
        return jsonify({
            'success': True,
            'texts': extracted_texts,
            'count': len(extracted_texts)
        })
        
    except Exception as e:
        print(f"Extract text error: {str(e)}")
        return jsonify({'success': False, 'error': f'File processing failed: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze_resumes():
    try:
        data = request.json
        job_description = data.get('job_description', '').strip()
        resumes_text = data.get('resumes', '').strip()
        
        if not job_description or not resumes_text:
            return jsonify({'success': False, 'error': 'Please provide both job description and resumes'}), 400
        
        # Split resumes
        resumes = [resume.strip() for resume in resumes_text.split('---') if resume.strip()]
        
        if not resumes:
            return jsonify({'success': False, 'error': 'No valid resumes found'}), 400
        
        # Analyze each resume
        results = []
        for i, resume in enumerate(resumes):
            result = matcher.analyze_resume(job_description, resume, i)
            results.append(result)
        
        # Sort by overall score
        results.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'results': results,
            'statistics': {
                'total_resumes': len(results),
                'average_score': round(sum(r['overall_score'] for r in results) / len(results)),
                'top_score': results[0]['overall_score'] if results else 0,
                'qualified_candidates': len([r for r in results if r['overall_score'] >= 70])
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
