from flask import Flask, request, jsonify, render_template_string
import PyPDF2
import docx2txt
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
        # Stop words to ignore during matching
        self.stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'shall', 'a', 'an', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our',
            'their', 'experience', 'skills', 'knowledge', 'ability', 'candidate', 'required', 'must', 'should',
            'preferred', 'plus', 'good', 'excellent', 'strong', 'solid', 'proven', 'demonstrated'
        }
        
        # Weight different types of keywords
        self.keyword_weights = {
            'technical_tools': 3.0,    # Tools like "Synopsys", "Verilog"
            'technical_skills': 2.5,   # Skills like "RTL Design", "UVM"
            'technologies': 2.0,       # Technologies like "ASIC", "FPGA" 
            'general_skills': 1.0      # General terms
        }
    
    def clean_and_tokenize(self, text: str) -> List[str]:
        """Clean text and extract meaningful tokens"""
        try:
            # Convert to lowercase and remove extra whitespace
            text = re.sub(r'\s+', ' ', text.lower().strip())
            
            # Remove special characters but keep alphanumeric and spaces
            text = re.sub(r'[^\w\s\+\-\.]', ' ', text)
            
            # Split into words
            words = text.split()
            
            # Remove stop words and very short words
            meaningful_words = [word for word in words if word not in self.stop_words and len(word) > 2]
            
            return meaningful_words
        except Exception as e:
            print(f"Error in clean_and_tokenize: {e}")
            return []
    
    def extract_phrases(self, text: str, max_phrase_length: int = 3) -> List[str]:
        """Extract both individual words and meaningful phrases"""
        try:
            words = self.clean_and_tokenize(text)
            phrases = []
            
            # Add individual words
            phrases.extend(words)
            
            # Add 2-word phrases
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                phrases.append(phrase)
            
            # Add 3-word phrases 
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                phrases.append(phrase)
            
            return phrases
        except Exception as e:
            print(f"Error in extract_phrases: {e}")
            return []
    
    def extract_jd_requirements(self, jd_text: str) -> Dict[str, List[str]]:
        """Extract requirements from JD with scoring weights"""
        phrases = self.extract_phrases(jd_text)
        
        # Categorize keywords by type for different weights
        technical_tools = []
        technical_skills = []
        technologies = []
        general_skills = []
        
        # Technical tool patterns
        tool_patterns = [
            'synopsys', 'cadence', 'mentor', 'verilog', 'systemverilog', 'vcs', 'questasim', 'modelsim',
            'design compiler', 'icc2', 'primetime', 'innovus', 'calibre', 'python', 'perl', 'tcl',
            'matlab', 'xilinx', 'altera', 'vivado', 'quartus'
        ]
        
        # Technical skill patterns
        skill_patterns = [
            'rtl design', 'verification', 'uvm', 'functional verification', 'design verification',
            'testbench', 'coverage', 'assertion', 'debugging', 'simulation', 'synthesis',
            'timing analysis', 'static timing', 'power analysis', 'dft', 'scan', 'bist'
        ]
        
        # Technology patterns
        tech_patterns = [
            'asic', 'fpga', 'soc', 'ip', 'axi', 'ahb', 'apb', 'pcie', 'usb', 'ddr', 'serdes',
            'risc', 'arm', 'cpu', 'gpu', 'memory', 'cache', 'pipeline'
        ]
        
        for phrase in phrases:
            phrase_lower = phrase.lower()
            
            # Check if it's a technical tool
            if any(tool in phrase_lower for tool in tool_patterns):
                technical_tools.append(phrase)
            # Check if it's a technical skill
            elif any(skill in phrase_lower for skill in skill_patterns):
                technical_skills.append(phrase)
            # Check if it's a technology
            elif any(tech in phrase_lower for tech in tech_patterns):
                technologies.append(phrase)
            # Everything else is general
            else:
                general_skills.append(phrase)
        
        return {
            'technical_tools': list(set(technical_tools)),
            'technical_skills': list(set(technical_skills)),
            'technologies': list(set(technologies)),
            'general_skills': list(set(general_skills))
        }
    
    def extract_resume_keywords(self, resume_text: str) -> List[str]:
        """Extract all keywords/phrases from resume"""
        return self.extract_phrases(resume_text)
    
    def calculate_string_match_score(self, resume_text: str, jd_text: str) -> Dict:
        """Calculate match score based on string matching"""
        try:
            # Basic validation
            if not resume_text or not jd_text:
                return {
                    'overall_score': 0,
                    'skill_score': 0,
                    'experience_score': 0,
                    'recommendation': 'DO NOT SEND',
                    'status': '❌',
                    'reason': 'Missing resume or job description text',
                    'resume_experience': 0,
                    'required_experience': 0,
                    'category_breakdown': {},
                    'total_jd_requirements': 0,
                    'total_matches': 0
                }
            
            # Extract requirements from JD
            jd_requirements = self.extract_jd_requirements(jd_text)
            
            # Extract keywords from resume
            resume_keywords = self.extract_resume_keywords(resume_text)
            resume_keywords_lower = [kw.lower() for kw in resume_keywords]
            
            # Calculate matches for each category
            category_scores = {}
            total_weighted_score = 0
            total_possible_score = 0
            
            for category, requirements in jd_requirements.items():
                if not requirements:  # Skip empty categories
                    continue
                    
                weight = self.keyword_weights.get(category, 1.0)
                matches = []
                missing = []
                
                for req in requirements:
                    req_lower = req.lower()
                    # Check for exact match or partial match
                    if req_lower in resume_keywords_lower:
                        matches.append(req)
                    elif any(req_lower in resume_kw for resume_kw in resume_keywords_lower):
                        matches.append(req)
                    elif any(resume_kw in req_lower for resume_kw in resume_keywords_lower if len(resume_kw) > 3):
                        matches.append(req)
                    else:
                        missing.append(req)
                
                # Calculate category score
                category_match_rate = len(matches) / len(requirements) if requirements else 0
                category_score = category_match_rate * 100
                weighted_score = category_score * weight
                
                category_scores[category] = {
                    'score': round(category_score, 1),
                    'weight': weight,
                    'weighted_score': round(weighted_score, 1),
                    'matches': matches,
                    'missing': missing,
                    'total_requirements': len(requirements)
                }
                
                total_weighted_score += weighted_score
                total_possible_score += 100 * weight
            
            # Calculate overall score
            overall_score = (total_weighted_score / total_possible_score * 100) if total_possible_score > 0 else 0
            
            # Extract experience
            resume_exp = self.extract_experience(resume_text)
            jd_exp = self.extract_experience(jd_text)
            exp_score = min(resume_exp / jd_exp * 100, 100) if jd_exp > 0 else 100
            
            # Final combined score (80% skills, 20% experience)
            final_score = (overall_score * 0.8) + (exp_score * 0.2)
            
            # Determine recommendation based on final score
            if final_score >= 75:
                recommendation = "SEND"
                status = "✅"
                reason = "Strong keyword match with requirements"
            elif final_score >= 60:
                recommendation = "MAYBE SEND" 
                status = "⚠️"
                reason = "Moderate match, review specific gaps"
            elif final_score >= 45:
                recommendation = "MAYBE SEND"
                status = "⚠️" 
                reason = "Some important keywords missing, but potential fit"
            else:
                recommendation = "DO NOT SEND"
                status = "❌"
                reason = "Insufficient keyword match with requirements"
            
            return {
                'overall_score': round(final_score, 1),
                'skill_score': round(overall_score, 1),
                'experience_score': round(exp_score, 1),
                'recommendation': recommendation,
                'status': status,
                'reason': reason,
                'resume_experience': resume_exp,
                'required_experience': jd_exp,
                'category_breakdown': category_scores,
                'total_jd_requirements': sum(len(reqs) for reqs in jd_requirements.values()),
                'total_matches': sum(len(cat['matches']) for cat in category_scores.values())
            }
            
        except Exception as e:
            print(f"Error in calculate_string_match_score: {e}")
            return {
                'overall_score': 0,
                'skill_score': 0,
                'experience_score': 0,
                'recommendation': 'ERROR',
                'status': '❌',
                'reason': f'Analysis error: {str(e)}',
                'resume_experience': 0,
                'required_experience': 0,
                'category_breakdown': {},
                'total_jd_requirements': 0,
                'total_matches': 0
            }
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file with multiple fallback methods"""
        try:
            # Primary method with PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_error:
                        print(f"Error reading page: {page_error}")
                        continue
                
                if text.strip():
                    return text
                else:
                    return "No text found in PDF - might be image-based or encrypted"
                    
        except Exception as e1:
            print(f"PyPDF2 extraction failed: {e1}")
            
            # Fallback: Try alternative PDF reading method
            try:
                # Simple byte-level text extraction for basic PDFs
                with open(file_path, 'rb') as file:
                    content = file.read()
                    # Look for text streams in PDF
                    import re
                    text_pattern = re.compile(rb'BT\s*/F\d+\s+\d+\s+Tf\s+(.*?)ET', re.DOTALL)
                    matches = text_pattern.findall(content)
                    
                    extracted_text = ""
                    for match in matches:
                        try:
                            # Try to decode the text
                            text_str = match.decode('utf-8', errors='ignore')
                            extracted_text += text_str + " "
                        except:
                            continue
                    
                    if extracted_text.strip():
                        return extracted_text
                    else:
                        return f"PDF appears to be image-based or encrypted. Try converting to text format. Error: {str(e1)}"
                        
            except Exception as e2:
                return f"Could not read PDF file. Try converting to TXT format. Error: {str(e1)}"
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file using docx2txt (more robust)"""
        try:
            # Primary method: docx2txt (handles corrupt files better)
            text = docx2txt.process(file_path)
            if text and text.strip():
                return text
            else:
                return "No readable text found in DOCX file"
                
        except Exception as e1:
            print(f"docx2txt extraction failed: {e1}")
            
            # Fallback: Manual ZIP extraction
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                
                text_content = ""
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    try:
                        # Read document.xml directly
                        with zip_file.open('word/document.xml') as doc_xml:
                            content = doc_xml.read().decode('utf-8', errors='ignore')
                            
                            # Extract text using regex patterns
                            text_patterns = [
                                r'<w:t[^>]*>([^<]+)</w:t>',  # Standard text
                                r'<w:t>([^<]+)</w:t>',       # Simple text
                                r'>([^<]{3,})<'             # Any text between tags
                            ]
                            
                            for pattern in text_patterns:
                                matches = re.findall(pattern, content)
                                text_content += ' '.join(matches) + ' '
                                
                    except Exception as xml_error:
                        print(f"XML extraction failed: {xml_error}")
                        
                        # Last resort: try any readable files in the ZIP
                        for file_name in zip_file.namelist():
                            if file_name.endswith(('.xml', '.rels')) and not file_name.startswith('word/media'):
                                try:
                                    with zip_file.open(file_name) as f:
                                        content = f.read().decode('utf-8', errors='ignore')
                                        # Extract any readable text
                                        readable_text = re.findall(r'[a-zA-Z0-9\s]{10,}', content)
                                        text_content += ' '.join(readable_text[:20])  # Limit to avoid noise
                                except:
                                    continue
                
                if text_content.strip():
                    return text_content
                else:
                    return "DOCX file appears corrupted. Please convert to PDF or paste text directly."
                    
            except Exception as e2:
                return "Could not read DOCX file. Please try PDF format or paste text directly."
    
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
        """Extract years of experience from text with multiple patterns"""
        patterns = [
            # Standard patterns
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*yrs?',
            
            # Additional patterns for better detection
            r'(\d+)\+?\s*years?\s*in',
            r'(\d+)\+?\s*years?\s*working',
            r'(\d+)\+?\s*years?\s*as',
            r'(\d+)\+?\s*yrs?\s*in',
            r'(\d+)\+?\s*year\s*experience',
            r'total\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'over\s*(\d+)\+?\s*years?',
            r'more\s*than\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*of\s*professional',
            r'(\d+)\+?\s*years?\s*of\s*industry',
            r'(\d+)\+?\s*years?\s*of\s*work',
            r'professional\s*experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            
            # Date range patterns (calculate years)
            r'(\d{4})\s*-\s*(?:present|current|\d{4})',
            r'(\d{4})\s*to\s*(?:present|current|\d{4})',
            
            # Work history patterns
            r'working\s*since\s*(\d{4})',
            r'started\s*in\s*(\d{4})',
        ]
        
        experience_years = []
        text_lower = text.lower()
        
        # Extract years from patterns
        for pattern in patterns[:13]:  # First 13 are direct year patterns
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    try:
                        years = int(match)
                        if 0 <= years <= 50:  # Reasonable range
                            experience_years.append(years)
                    except:
                        continue
        
        # Calculate from date ranges
        current_year = 2025
        date_patterns = patterns[13:]
        for pattern in date_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                try:
                    start_year = int(match)
                    if 1990 <= start_year <= current_year:
                        calculated_years = current_year - start_year
                        if calculated_years <= 50:
                            experience_years.append(calculated_years)
                except:
                    continue
        
        # Return the maximum experience found, or 0 if none
        return max(experience_years) if experience_years else 0
    
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
        
        # Enhanced recommendation logic with more lenient scoring for good matches
        if domain_conflicts:
            recommendation = "DO NOT SEND"
            status = "❌"
            reason = f"Critical domain mismatch: {domain_conflicts[0]['message']}"
        elif len(critical_issues) > 2:  # More than 2 critical issues
            recommendation = "DO NOT SEND"
            status = "❌"
            reason = "Multiple critical missing skills"
        elif overall_score >= 70:  # Lowered from 80
            recommendation = "SEND"
            status = "✅"
            reason = "Strong match across skills and experience"
        elif overall_score >= 50:  # Lowered from 65
            recommendation = "MAYBE SEND"
            status = "⚠️"
            reason = "Moderate match, review specific requirements"
        else:
            recommendation = "DO NOT SEND"
            status = "❌"
            reason = "Insufficient match for role requirements"
        
        # Special case: If experience requirement is met and some core skills match, be more lenient
        if resume_exp >= jd_exp and skill_score >= 40 and not domain_conflicts:
            if recommendation == "DO NOT SEND":
                recommendation = "MAYBE SEND"
                status = "⚠️"
                reason = "Experience requirement met, some skill gaps exist"
        
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
        
        <div class="file-tip">
            <strong>📁 File Upload Tips:</strong>
            <ul style="margin: 5px 0; padding-left: 20px;">
                <li>If DOCX files fail to upload, try saving as PDF first</li>
                <li>For best results, copy-paste text directly into the text areas</li>
                <li>Supported formats: PDF, DOCX, TXT</li>
            </ul>
        </div>
        
        <form id="matchForm" enctype="multipart/form-data">
            <div class="upload-section">
                <div class="upload-box">
                    <h3>📄 Resume</h3>
                    <input type="file" id="resume" name="resume" accept=".pdf,.docx,.txt">
                    <p>Supported formats: PDF, DOCX, TXT</p>
                    <p><small><strong>Having file issues?</strong> Try copy-pasting the text instead!</small></p>
                    <textarea id="resumeText" name="resumeText" placeholder="Paste resume content here..."></textarea>
                </div>
                
                <div class="upload-box">
                    <h3>📋 Job Description</h3>
                    <input type="file" id="jd" name="jd" accept=".pdf,.docx,.txt">
                    <p>Supported formats: PDF, DOCX, TXT</p>
                    <p><small><strong>Having file issues?</strong> Try copy-pasting the text instead!</small></p>
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
        
        # Handle resume input with enhanced validation
        if 'resume' in request.files and request.files['resume'].filename:
            resume_file = request.files['resume']
            if resume_file.filename.strip() == '':
                return jsonify({'error': 'Resume file is empty'})
            filename = secure_filename(resume_file.filename)
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(resume_path)
            resume_text = matcher.extract_text(resume_path)
            os.remove(resume_path)  # Clean up
            
            # Check if extraction failed or returned an error message
            if not resume_text or resume_text.startswith('Error') or resume_text.startswith('Could not'):
                return jsonify({
                    'error': f'File processing issue: {resume_text}',
                    'suggestion': 'Try uploading the file in a different format (PDF → TXT, or DOCX → PDF), or copy-paste the text directly into the text area.'
                })
            
            # Check if extracted text is meaningful
            if len(resume_text.strip()) < 50:
                return jsonify({
                    'error': 'Very little text extracted from file. The file might be corrupted, image-based, or empty.',
                    'suggestion': 'Try copy-pasting the resume text directly into the text area below the file upload.'
                })
                
        elif request.form.get('resumeText'):
            resume_text = request.form.get('resumeText').strip()
        
        # Handle JD input with enhanced validation
        if 'jd' in request.files and request.files['jd'].filename:
            jd_file = request.files['jd']
            if jd_file.filename.strip() == '':
                return jsonify({'error': 'Job description file is empty'})
            filename = secure_filename(jd_file.filename)
            jd_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            jd_file.save(jd_path)
            jd_text = matcher.extract_text(jd_path)
            os.remove(jd_path)  # Clean up
            
            if not jd_text or jd_text.startswith('Error') or jd_text.startswith('Could not'):
                return jsonify({
                    'error': f'JD file processing issue: {jd_text}',
                    'suggestion': 'Try uploading the JD in a different format or copy-paste the text directly.'
                })
                
            if len(jd_text.strip()) < 20:
                return jsonify({
                    'error': 'Very little text extracted from JD file.',
                    'suggestion': 'Try copy-pasting the job description text directly.'
                })
                
        elif request.form.get('jdText'):
            jd_text = request.form.get('jdText').strip()
        
        # Final validation
        if not resume_text or len(resume_text.strip()) < 10:
            return jsonify({'error': 'Please provide a valid resume (at least 10 characters)'})
        
        if not jd_text or len(jd_text.strip()) < 10:
            return jsonify({'error': 'Please provide a valid job description (at least 10 characters)'})
        
        # Analyze match using string-based approach
        results = matcher.calculate_string_match_score(resume_text, jd_text)
        
        # Validate results before sending
        if not isinstance(results, dict):
            return jsonify({'error': 'Analysis failed - invalid results format'})
        
        # Ensure all required fields exist
        required_fields = ['overall_score', 'skill_score', 'experience_score', 'recommendation', 'status', 'reason']
        for field in required_fields:
            if field not in results:
                results[field] = 0 if 'score' in field else 'ERROR'
        
        return jsonify(results)
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in analyze endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'error': f'Server error during analysis: {str(e)}',
            'overall_score': 0,
            'skill_score': 0,
            'experience_score': 0,
            'recommendation': 'ERROR',
            'status': '❌',
            'reason': 'Analysis failed due to server error'
        })

@app.route('/debug', methods=['POST'])
def debug_analysis():
    """Debug endpoint to see detailed extraction"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Please provide text in JSON format'})
        
        text = data['text']
        
        # Extract and return all details
        experience = matcher.extract_experience(text)
        skills = matcher.extract_skills(text)
        
        # Show regex matches for experience
        exp_matches = []
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in',
            r'(\d+)\+?\s*years?\s*working'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                exp_matches.append({'pattern': pattern, 'matches': matches})
        
        return jsonify({
            'extracted_experience': experience,
            'extracted_skills': skills,
            'experience_regex_matches': exp_matches,
            'text_preview': text[:500] + '...' if len(text) > 500 else text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API endpoint for programmatic access"""
    try:
        data = request.get_json()
        
        if not data or 'resume' not in data or 'jd' not in data:
            return jsonify({'error': 'Please provide both resume and jd in JSON format'})
        
        results = matcher.calculate_string_match_score(data['resume'], data['jd'])
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)})

# Railway deployment optimization
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
