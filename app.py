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
        # Define clear domain patterns (KEEP EXISTING - WORKING)
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
        
        # Enhanced Skills and tools detection - Comprehensive list
        self.skill_categories = {
            'tools': [
                # Synopsys Tools
                'synopsys', 'design compiler', 'dc', 'icc2', 'ic compiler', 'primetime', 'pt', 
                'vcs', 'vcs mx', 'verdi', 'dve', 'spyglass', 'formality', 'star-rc', 'hspice',
                'custom compiler', 'sentaurus', 'proteus', 'raphael', 'tcad',
                
                # Cadence Tools
                'cadence', 'innovus', 'encounter', 'genus', 'conformal', 'incisive', 'xcelium',
                'virtuoso', 'allegro', 'pegasus', 'voltus', 'tempus', 'quantus', 'palladium',
                'protium', 'jasper', 'jaspergold', 'stratus', 'confrml',
                
                # Mentor Graphics/Siemens
                'mentor', 'calibre', 'modelsim', 'questasim', 'questa', 'tessent', 'catapult',
                'leonardo', 'precision', 'mbist', 'atpg', 'fastscan', 'testkompress',
                
                # Simulation Tools
                'ncsim', 'vcs-mx', 'questa sim', 'active-hdl', 'riviera', 'vivado simulator',
                
                # FPGA Tools
                'xilinx', 'vivado', 'ise', 'vitis', 'quartus', 'altera', 'intel quartus',
                'lattice diamond', 'libero', 'microsemi', 'radiant',
                
                # Programming/Scripting
                'python', 'perl', 'tcl', 'tk', 'shell', 'bash', 'csh', 'make', 'makefile',
                'matlab', 'octave', 'systemc', 'cpp', 'c++', 'verilog-a', 'verilog-ams',
                
                # Version Control & Collaboration
                'git', 'svn', 'perforce', 'cvs', 'clearcase', 'eclipse', 'emacs', 'vim'
            ],
            
            'protocols': [
                # Standard Protocols
                'axi', 'axi4', 'axi-lite', 'axi-stream', 'ahb', 'apb', 'amba', 'wishbone',
                'avalon', 'tilelink', 'chi', 'ace', 'acp',
                
                # High-Speed Interfaces
                'pcie', 'pci express', 'usb', 'usb2', 'usb3', 'usb4', 'thunderbolt',
                'sata', 'sas', 'nvme', 'ddr', 'ddr3', 'ddr4', 'ddr5', 'lpddr',
                'gddr', 'hbm', 'hmc',
                
                # Serial Interfaces
                'serdes', 'ethernet', '10gbe', '25gbe', '40gbe', '100gbe', 'tse',
                'uart', 'spi', 'i2c', 'i2s', 'i3c', 'can', 'flexray', 'lin',
                
                # Display & Graphics
                'mipi', 'dsi', 'csi', 'hdmi', 'displayport', 'dp', 'edp', 'lvds',
                'rgb', 'dvi', 'vga',
                
                # Memory Interfaces
                'jedec', 'onfi', 'toggle', 'cfi', 'qspi', 'ospi', 'hyperbus',
                
                # Network Protocols
                'tcp', 'udp', 'ip', 'ipv4', 'ipv6', 'mac', 'phy', 'rgmii', 'sgmii',
                'xgmii', 'interlaken', 'aurora',
                
                # Processor Interfaces
                'arm', 'risc-v', 'x86', 'mips', 'powerpc', 'cortex', 'neon',
                'trustzone', 'smmu', 'gic'
            ],
            
            'technologies': [
                # Chip Technologies
                'asic', 'fpga', 'soc', 'noc', 'chiplet', 'ip', 'soft ip', 'hard ip',
                'platform', 'subsystem', 'tile',
                
                # Design Methodologies
                'rtl', 'hdl', 'verilog', 'systemverilog', 'vhdl', 'systemc', 'tlm',
                'chisel', 'bluespec', 'hls', 'c-to-rtl',
                
                # Process Technologies
                '7nm', '5nm', '3nm', '10nm', '14nm', '16nm', '22nm', '28nm', '40nm',
                'finfet', 'planar', 'soi', 'bulk', 'gaafet',
                
                # Memory Technologies
                'sram', 'dram', 'flash', 'emmc', 'ufs', 'nvram', 'mram', 'rram',
                'cache', 'tcm', 'scratchpad',
                
                # Processor Architectures
                'cpu', 'gpu', 'dsp', 'mcu', 'dpu', 'npu', 'ai', 'ml', 'neural',
                'vector', 'simd', 'risc', 'cisc', 'superscalar', 'pipeline',
                
                # Design Concepts
                'clock domain crossing', 'cdc', 'reset domain crossing', 'rdc',
                'power gating', 'clock gating', 'dvfs', 'avs', 'retention',
                'low power', 'ultra low power', 'always on',
                
                # Security & Reliability
                'cryptography', 'aes', 'rsa', 'sha', 'ecc', 'puf', 'trng', 'prng',
                'secure boot', 'attestation', 'isolation', 'firewall',
                
                # Analog/Mixed Signal
                'analog', 'mixed signal', 'ams', 'pll', 'dll', 'adc', 'dac',
                'lvds', 'serdes phy', 'oscillator', 'bandgap', 'ldo', 'dcdc'
            ]
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
    
    def extract_experience(self, text: str) -> int:
        """Extract years of experience from text with enhanced patterns"""
        experience_years = []
        text_lower = text.lower()
        
        # Enhanced patterns - more comprehensive
        patterns = [
            # Direct experience mentions
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:work\s*)?experience',
            
            # Working/employment patterns
            r'(\d+)\+?\s*years?\s*(?:in|working|as|with)',
            r'working\s*(?:for\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*working',
            r'(\d+)\+?\s*years?\s*in\s+(?:the\s+)?(?:field|industry|domain)',
            
            # Career/professional patterns
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:professional|career|industry)',
            r'professional\s*(?:experience\s*(?:of\s*)?)?(\d+)\+?\s*years?',
            r'career\s*(?:spanning\s*)?(\d+)\+?\s*years?',
            r'total\s*(?:of\s*)?(\d+)\+?\s*years?',
            
            # Comparative patterns
            r'over\s*(\d+)\+?\s*years?',
            r'more\s*than\s*(\d+)\+?\s*years?',
            r'above\s*(\d+)\+?\s*years?',
            r'around\s*(\d+)\+?\s*years?',
            r'approximately\s*(\d+)\+?\s*years?',
            r'nearly\s*(\d+)\+?\s*years?',
            
            # Having/with patterns
            r'having\s*(\d+)\+?\s*years?',
            r'with\s*(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|expertise)',
            r'possess\s*(\d+)\+?\s*years?',
            r'bring\s*(\d+)\+?\s*years?',
            
            # Years mentioned with job titles
            r'(\d+)\+?\s*years?\s*(?:as\s*)?(?:a\s*)?(?:senior\s*)?(?:lead\s*)?(?:principal\s*)?(?:engineer|developer|designer|architect)',
            
            # Format: "5+ years of..."
            r'(\d+)\+\s*years?\s*of',
            
            # Education to work calculation - graduation patterns
            r'graduated?\s*(?:in\s*)?(\d{4})',
            r'(?:b\.?tech|be|bachelor|m\.?tech|me|master|mba).*?(?:in\s*)?(\d{4})',
            r'(?:b\.?tech|be|bachelor|m\.?tech|me|master|mba).*?(\d{4})',
            r'degree.*?(\d{4})',
            r'university.*?(\d{4})',
            r'college.*?(\d{4})',
        ]
        
        # Extract from direct experience patterns (excluding graduation patterns)
        direct_patterns = patterns[:-7]  # All except graduation patterns
        for pattern in direct_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    try:
                        years = int(match)
                        if 0 <= years <= 50:  # Reasonable range
                            experience_years.append(years)
                    except:
                        continue
        
        # Calculate from graduation year (assume they started working after graduation)
        current_year = 2025
        graduation_patterns = patterns[-7:]  # Last 7 patterns
        for pattern in graduation_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    try:
                        grad_year = int(match)
                        if 1990 <= grad_year <= current_year - 1:  # Must have graduated at least 1 year ago
                            calculated_years = current_year - grad_year
                            if calculated_years <= 35:  # Reasonable working years
                                experience_years.append(calculated_years)
                    except:
                        continue
        
        # Employment date ranges - present job
        date_patterns = [
            r'(\d{4})\s*-\s*(?:present|current|till\s*date|now)',
            r'(\d{4})\s*to\s*(?:present|current|till\s*date|now)',
            r'(?:since|from)\s*(\d{4})',
            r'from\s*(\d{4})\s*to\s*(?:present|current|now)',
            r'started\s*(?:in\s*)?(\d{4})',
            r'joining\s*(?:in\s*)?(\d{4})',
            r'employed\s*(?:since\s*)?(\d{4})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    try:
                        start_year = int(match)
                        if 1990 <= start_year <= current_year:
                            calculated_years = current_year - start_year
                            if calculated_years <= 40:
                                experience_years.append(calculated_years)
                    except:
                        continue
        
        # Return the maximum experience found
        return max(experience_years) if experience_years else 0
    
    def extract_skills(self, text: str) -> Dict:
        """Extract skills from text"""
        text_lower = text.lower()
        found_skills = {
            'tools': [],
            'protocols': [],
            'technologies': []
        }
        
        for category, skills_list in self.skill_categories.items():
            for skill in skills_list:
                if skill in text_lower:
                    found_skills[category].append(skill)
        
        return found_skills
    
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
        """Compare domains between resume and JD + enhanced analysis"""
        
        # STEP 1: Domain matching (KEEP EXISTING LOGIC)
        resume_domain = self.detect_domain(resume_text)
        jd_domain = self.detect_domain(jd_text)
        domains_match = resume_domain['primary_domain'] == jd_domain['primary_domain']
        
        # STEP 2: Experience comparison
        resume_exp = self.extract_experience(resume_text)
        jd_exp = self.extract_experience(jd_text)
        exp_match = resume_exp >= jd_exp if jd_exp > 0 else True
        exp_score = min(resume_exp / jd_exp * 100, 100) if jd_exp > 0 else 100
        
        # STEP 3: Skills comparison
        resume_skills = self.extract_skills(resume_text)
        jd_skills = self.extract_skills(jd_text)
        
        # Calculate skill match percentages
        skill_scores = {}
        overall_skill_score = 0
        total_categories = 0
        
        for category in ['tools', 'protocols', 'technologies']:
            jd_category_skills = set(jd_skills[category])
            resume_category_skills = set(resume_skills[category])
            
            if jd_category_skills:
                matches = jd_category_skills.intersection(resume_category_skills)
                score = (len(matches) / len(jd_category_skills)) * 100
                skill_scores[category] = {
                    'score': round(score, 1),
                    'matched': list(matches),
                    'missing': list(jd_category_skills - matches),
                    'total_required': len(jd_category_skills)
                }
                overall_skill_score += score
                total_categories += 1
        
        overall_skill_score = overall_skill_score / total_categories if total_categories > 0 else 0
        
        # STEP 4: Final recommendation
        if resume_domain['primary_domain'] == 'unknown' or jd_domain['primary_domain'] == 'unknown':
            recommendation = "MANUAL REVIEW"
            status = "⚠️"
            reason = "Unable to clearly identify domain from text"
            final_score = 0
        elif not domains_match:
            recommendation = "DOMAIN MISMATCH - DO NOT SEND"
            status = "❌"
            reason = f"Resume is {resume_domain['domain_name']} but JD requires {jd_domain['domain_name']}"
            final_score = 0
        else:
            # Domain matches, now check skills and experience
            final_score = (overall_skill_score * 0.7) + (exp_score * 0.3)
            
            if final_score >= 75 and exp_match:
                recommendation = "STRONG MATCH - SEND"
                status = "✅"
                reason = f"Domain match with {final_score:.1f}% overall compatibility"
            elif final_score >= 60 and exp_match:
                recommendation = "GOOD MATCH - SEND"
                status = "✅"
                reason = f"Domain match with {final_score:.1f}% compatibility"
            elif final_score >= 45:
                recommendation = "PARTIAL MATCH - MAYBE SEND"
                status = "⚠️"
                reason = f"Domain match but some skill gaps ({final_score:.1f}% match)"
            else:
                recommendation = "WEAK MATCH - DO NOT SEND"
                status = "❌"
                reason = f"Domain match but significant skill/experience gaps ({final_score:.1f}% match)"
        
        # Build complete analysis text for simple display
        analysis_text = f"""
Experience Analysis:
- Resume Experience: {resume_exp} years
- Required Experience: {jd_exp} years  
- Experience Match: {'✅ Meets requirement' if exp_match else '❌ Below requirement'}
- Experience Score: {round(exp_score, 1)}%

Skills Analysis:
- Overall Skills Score: {round(overall_skill_score, 1)}%
"""
        
        if skill_scores:
            analysis_text += "\nSkills Breakdown:\n"
            for category, data in skill_scores.items():
                category_display = category.replace('_', ' ').title()
                analysis_text += f"- {category_display}: {data['score']}% ({len(data['matched'])}/{data['total_required']})\n"
                if data['matched']:
                    matched_display = ', '.join(data['matched'][:8])  # Show first 8
                    if len(data['matched']) > 8:
                        matched_display += f" +{len(data['matched'])-8} more"
                    analysis_text += f"  ✅ Matched: {matched_display}\n"
                if data['missing']:
                    missing_display = ', '.join(data['missing'][:8])  # Show first 8  
                    if len(data['missing']) > 8:
                        missing_display += f" +{len(data['missing'])-8} more"
                    analysis_text += f"  ❌ Missing: {missing_display}\n"
        
        return {
            'recommendation': recommendation,
            'status': status,
            'reason': reason,
            'final_score': round(final_score, 1),
            'domains_match': domains_match,
            'resume_domain': resume_domain,
            'jd_domain': jd_domain,
            'analysis_text': analysis_text
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
    <title>Multi-Resume Matcher</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 10px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 20px;
            font-size: 24px;
        }
        
        /* Mobile responsive */
        @media (min-width: 768px) {
            .container { padding: 30px; }
            h1 { font-size: 28px; }
        }
        
        .upload-section {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        @media (min-width: 768px) {
            .upload-section { grid-template-columns: 1fr 1fr; }
        }
        
        .upload-box {
            border: 2px dashed #3498db;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            background-color: #f8f9fa;
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
            height: 120px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
            font-family: Arial, sans-serif;
        }
        
        @media (min-width: 768px) {
            textarea { height: 150px; }
        }
        
        button {
            background-color: #3498db;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
        }
        
        .results {
            margin-top: 20px;
            padding: 15px;
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
            height: 15px;
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
        
        .analysis-text {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            white-space: pre-line;
            font-family: monospace;
            font-size: 12px;
            overflow-x: auto;
        }
        
        @media (min-width: 768px) {
            .analysis-text { font-size: 14px; }
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
        <h1>📱 Multi-Resume Matcher</h1>
        
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
