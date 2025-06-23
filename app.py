<script>
        let selectedResumeFiles = [];
        
        // Handle multiple resume file selection
        document.getElementById('resumes').addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            selectedResumeFiles = [...selectedResumeFiles, ...files];
            updateResumeFilesList();
        });
        
        function updateResumeFilesList() {
            const container = document.getElementById('resumeFilesList');
            container.innerHTML = '';
            
            if (selectedResumeFiles.length === 0) {
                container.innerHTML = '<p style="color: #666; font-size: 14px;">No files selected</p>';
                return;
            }
            
            selectedResumeFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'resume-file-item';
                fileItem.innerHTML = `
                    <span>${file.name} (${(file.size / 1024).toFixed(1)}KB)</span>
                    <button type="button" class="remove-file" onclick="removeResumeFile(${index})">×</button>
                `;
                container.appendChild(fileItem);
            });
        }
        
        function removeResumeFile(index) {
            selectedResumeFiles.splice(index, 1);
            updateResumeFilesList();
        }
        
        function clearAll() {
            selectedResumeFiles = [];
            document.getElementById('resumes').value = '';
            document.getElementById('resumeText').value = '';
            document.getElementById('jd').value = '';
            document.getElementById('jdText').value = '';
            updateResumeFilesList();
            document.getElementById('results').style.display = 'none';
            document.getElementById('multipleResults').style.display = 'none';
        }
        
        function updateProgress(current, total) {
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            if (total > 1) {
                progressContainer.style.display = 'block';
                const percentage = (current / total) * 100;
                progressFill.style.width = percentage + '%';
                progressText.textContent = `Processing resume ${current} of ${total}...`;
            } else {
                progressContainer.style.display = 'none';
            }
        }

        function updateDomainCard(elementId, domainData) {
            const element = document.getElementById(elementId);
            if (!element) return;
            
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
                    keywords.slice(0, 8).forEach(keyword => {
                        html += `<span class="keyword">${keyword}</span>`;
                    });
                    if (keywords.length > 8) {
                        html += `<span class="keyword">+${keywords.length - 8} more</span>`;
                    }
                    html += '</div>';
                }
            }
            
            element.innerHTML = html;
        }
        
        function createResultCard(filename, data, index) {
            const resultClass = data.domains_match && (data.final_score || 0) >= 60 ? 'match' :
                               data.recommendation && (data.recommendation.includes('MANUAL') || data.recommendation.includes('MAYBE')) ? 'review' : 'mismatch';
            
            return `
                <div class="result-card ${resultClass}">
                    <div class="result-header">
                        <div class="result-filename">${filename}</div>
                        <div class="result-score" style="color: ${resultClass === 'match' ? '#27ae60' : resultClass === 'review' ? '#f39c12' : '#e74c3c'}">
                            ${data.final_score || 0}%
                        </div>
                    </div>
                    <div style="margin: 10px 0;">
                        <strong>${data.status} ${data.recommendation}</strong>
                    </div>
                    <div style="margin: 10px 0; color: #666;">
                        ${data.reason}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 15px;">
                        <div class="domain-card" style="margin: 0;">
                            <strong>Resume Domain:</strong> ${data.resume_domain.domain_name} (${data.resume_domain.confidence}%)
                        </div>
                    </div>
                    <details style="margin-top: 10px;">
                        <summary style="cursor: pointer; font-weight: bold;">📊 View Detailed Analysis</summary>
                        <div class="analysis-text" style="margin-top: 10px; font-size: 12px;">
                            ${data.analysis_text || 'No detailed analysis available'}
                        </div>
                    </details>
                </div>
            `;
        }

        document.getElementById('matchForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const multipleResults = document.getElementById('multipleResults');
            
            // Hide previous results
            results.style.display = 'none';
            multipleResults.style.display = 'none';
            loading.style.display = 'block';
            
            try {
                // Check if we have multiple resumes or single resume
                const hasMultipleFiles = selectedResumeFiles.length > 0;
                const hasResumeText = document.getElementById('resumeText').value.trim();
                
                if (hasMultipleFiles) {
                    // Process multiple files
                    await processMultipleResumes();
                } else if (hasResumeText) {
                    // Process single resume text
                    await processSingleResume();
                } else {
                    throw new Error('Please provide at least one resume (file or text)');
                }
                
            } catch (error) {
                console.error('Error details:', error);
                alert('Analysis failed: ' + error.message);
            } finally {
                loading.style.display = 'none';
                updateProgress(0, 0);
            }
        });
        
        async function processSingleResume() {
            const formData = new FormData(document.getElementById('matchForm'));
            
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server error (${response.status})`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Display single result
            displaySingleResult(data);
        }
        
        async function processMultipleResumes() {
            const jdFile = document.getElementById('jd').files[0];
            const jdText = document.getElementById('jdText').value.trim();
            
            if (!jdFile && !jdText) {
                throw new Error('Please provide job description (file or text)');
            }
            
            const results = [];
            const total = selectedResumeFiles.length;
            
            for (let i = 0; i < selectedResumeFiles.length; i++) {
                updateProgress(i + 1, total);
                
                const formData = new FormData();
                formData.append('resumes', selectedResumeFiles[i]);
                
                if (jdFile) {
                    formData.append('jd', jdFile);
                } else {
                    formData.append('jdText', jdText);
                }
                
                try {
                    const response = await fetch('/analyze-multiple', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error(`Server error (${response.status})`);
                    }
                    
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
        
        # Enhanced Skills and tools detection - Much more comprehensive
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
                'git', 'svn', 'perforce', 'cvs', 'clearcase', 'eclipse', 'emacs', 'vim',
                
                # Other EDA Tools
                'primesim', 'hspice', 'spectre', 'eldo', 'ngspice', 'ltspice', 'tanner',
                'silvaco', 'synplify', 'blast', 'precision rtl', 'dc ultra', 'pt px',
                
                # Debug & Analysis
                'ddd', 'gdb', 'valgrind', 'coverity', 'lint', 'verilator', 'gtkwave',
                'chronos', 'signal storm', 'apache', 'redhawk'
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
            ],
            
            'verification_methodologies': [
                # Verification Methodologies
                'uvm', 'ovm', 'vmm', 'constrained random', 'directed test',
                'coverage driven', 'assertion based', 'formal verification',
                'equivalence checking', 'model checking', 'theorem proving',
                
                # Verification Concepts
                'testbench', 'test harness', 'bfm', 'vip', 'verification ip',
                'monitor', 'scoreboard', 'checker', 'predictor', 'driver',
                'sequencer', 'sequence', 'virtual sequence',
                
                # Coverage Types
                'functional coverage', 'code coverage', 'toggle coverage',
                'fsm coverage', 'expression coverage', 'branch coverage',
                'assertion coverage', 'cross coverage',
                
                # Debug & Analysis
                'waveform', 'fsdb', 'vcd', 'vpd', 'shm', 'regression',
                'debug', 'trace', 'profiling', 'performance analysis'
            ],
            
            'design_flows': [
                # Design Flow Stages
                'architecture', 'microarchitecture', 'rtl design', 'synthesis',
                'place and route', 'pnr', 'physical design', 'backend',
                'frontend', 'implementation', 'integration',
                
                # Physical Design Steps
                'floorplan', 'floorplanning', 'placement', 'routing', 'cts',
                'clock tree synthesis', 'optimization', 'eco', 'metal fill',
                'finishing', 'streamout', 'gds', 'oasis',
                
                # Analysis & Verification
                'timing analysis', 'sta', 'power analysis', 'ir drop',
                'em analysis', 'signal integrity', 'si', 'crosstalk',
                'noise analysis', 'jitter', 'eye diagram',
                
                # Manufacturing & Test
                'dft', 'design for test', 'scan', 'bist', 'mbist', 'lbist',
                'atpg', 'boundary scan', 'jtag', 'test compression',
                'fault simulation', 'stuck at', 'transition delay'
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
        
        # Debug: Print text snippet to see what we're working with
        print(f"DEBUG: Text preview for experience extraction: {text_lower[:500]}...")
        
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
        for i, pattern in enumerate(direct_patterns):
            matches = re.findall(pattern, text_lower)
            if matches:
                print(f"DEBUG: Pattern {i+1} matched: {matches}")
                for match in matches:
                    try:
                        years = int(match)
                        if 0 <= years <= 50:  # Reasonable range
                            experience_years.append(years)
                            print(f"DEBUG: Added {years} years from direct pattern")
                    except:
                        continue
        
        # Calculate from graduation year (assume they started working after graduation)
        current_year = 2025
        graduation_patterns = patterns[-7:]  # Last 7 patterns
        for i, pattern in enumerate(graduation_patterns):
            matches = re.findall(pattern, text_lower)
            if matches:
                print(f"DEBUG: Graduation pattern {i+1} matched: {matches}")
                for match in matches:
                    try:
                        grad_year = int(match)
                        if 1990 <= grad_year <= current_year - 1:  # Must have graduated at least 1 year ago
                            calculated_years = current_year - grad_year
                            if calculated_years <= 35:  # Reasonable working years
                                experience_years.append(calculated_years)
                                print(f"DEBUG: Added {calculated_years} years from graduation year {grad_year}")
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
        
        for i, pattern in enumerate(date_patterns):
            matches = re.findall(pattern, text_lower)
            if matches:
                print(f"DEBUG: Date pattern {i+1} matched: {matches}")
                for match in matches:
                    try:
                        start_year = int(match)
                        if 1990 <= start_year <= current_year:
                            calculated_years = current_year - start_year
                            if calculated_years <= 40:
                                experience_years.append(calculated_years)
                                print(f"DEBUG: Added {calculated_years} years from employment start year {start_year}")
                    except:
                        continue
        
        # Return the maximum experience found
        result = max(experience_years) if experience_years else 0
        print(f"DEBUG: Final experience result: {result} years (from candidates: {experience_years})")
        return result
    
    def extract_skills(self, text: str) -> Dict:
        """Extract skills from text"""
        text_lower = text.lower()
        found_skills = {
            'tools': [],
            'protocols': [],
            'technologies': [],
            'verification_methodologies': [],
            'design_flows': []
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
    <title>Domain Matcher + Skills</title>
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
        .phase-info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #2196f3;
            font-size: 14px;
        }
        .upload-section {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        /* Mobile responsive - stack vertically on small screens */
        @media (min-width: 768px) {
            .upload-section {
                grid-template-columns: 2fr 1fr;
            }
            .container {
                padding: 30px;
            }
            h1 {
                font-size: 28px;
            }
        }
        
        .upload-box {
            border: 2px dashed #3498db;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            background-color: #f8f9fa;
        }
        .upload-box h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        /* Multiple resume upload styling */
        .resume-upload-area {
            border: 2px dashed #27ae60;
            padding: 20px;
            border-radius: 8px;
            background-color: #f8fff8;
            margin-bottom: 15px;
        }
        
        .resume-files-list {
            margin: 10px 0;
            text-align: left;
        }
        
        .resume-file-item {
            background: #e8f5e8;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }
        
        .remove-file {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 2px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        
        input[type="file"] {
            margin: 10px 0;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
            font-size: 14px;
        }
        
        /* Make file input more mobile friendly */
        input[type="file"]::-webkit-file-upload-button {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        
        textarea {
            width: 100%;
            height: 120px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
            font-family: Arial, sans-serif;
            font-size: 14px;
        }
        
        @media (min-width: 768px) {
            textarea {
                height: 150px;
            }
        }
        
        button {
            background-color: #3498db;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            display: block;
            margin: 15px auto;
            width: 100%;
            max-width: 300px;
        }
        button:hover {
            background-color: #2980b9;
        }
        
        .button-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
            align-items: center;
        }
        
        @media (min-width: 768px) {
            .button-group {
                flex-direction: row;
                justify-content: center;
            }
            button {
                width: auto;
                margin: 0;
            }
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
        
        /* Multiple results styling */
        .multiple-results {
            display: none;
        }
        
        .result-card {
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 5px solid #3498db;
        }
        
        .result-card.match { border-left-color: #27ae60; }
        .result-card.mismatch { border-left-color: #e74c3c; }
        .result-card.review { border-left-color: #f39c12; }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        
        .result-filename {
            font-weight: bold;
            color: #2c3e50;
            font-size: 16px;
        }
        
        .result-score {
            font-size: 18px;
            font-weight: bold;
        }
        
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
            .analysis-text {
                font-size: 14px;
            }
        }
        
        .score-display {
            text-align: center;
            margin: 15px 0;
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }
        
        @media (min-width: 768px) {
            .score-display {
                font-size: 24px;
            }
        }
        
        /* Progress indicator for multiple resume processing */
        .progress-container {
            display: none;
            margin: 20px 0;
        }
        
        .progress-bar {
            background: #f0f0f0;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .progress-fill {
            background: #3498db;
            height: 100%;
            transition: width 0.3s ease;
        }
        
        .progress-text {
            text-align: center;
            margin: 10px 0;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Multi-Resume Matcher</h1>
        
        <div class="phase-info">
            <strong>📋 Batch Analysis:</strong> Upload multiple resumes to compare against one job description. Mobile-friendly interface for on-the-go recruitment.
        </div>
        
        <form id="matchForm">
            <div class="upload-section">
                <div class="resume-upload-area">
                    <h3>📄 Resumes (Multiple Upload)</h3>
                    <input type="file" id="resumes" name="resumes" accept=".pdf,.docx,.txt" multiple>
                    <div class="resume-files-list" id="resumeFilesList"></div>
                    <p style="margin: 10px 0; font-size: 14px;">Or paste single resume text:</p>
                    <textarea id="resumeText" name="resumeText" placeholder="Paste resume content here..."></textarea>
                </div>
                
                <div class="upload-box">
                    <h3>📋 Job Description</h3>
                    <input type="file" id="jd" name="jd" accept=".pdf,.docx,.txt">
                    <p style="margin: 10px 0; font-size: 14px;">Or paste text:</p>
                    <textarea id="jdText" name="jdText" placeholder="Paste job description here..."></textarea>
                </div>
            </div>
            
            <div class="button-group">
                <button type="submit">🔍 Analyze All Resumes</button>
                <button type="button" onclick="testExperience()" style="background-color: #f39c12;">🔧 Test Experience</button>
                <button type="button" onclick="clearAll()" style="background-color: #95a5a6;">🗑️ Clear All</button>
            </div>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Analyzing matches...</p>
        </div>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-text" id="progressText">Processing resumes...</div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
        </div>
        
        <!-- Single resume results -->
        <div class="results" id="results">
            <h2 id="recommendation"></h2>
            <p id="reason"></p>
            
            <div class="score-display" id="overallScore" style="display: none;">
                <div id="scoreValue"></div>
                <div style="font-size: 14px; font-weight: normal;">Overall Match Score</div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr; gap: 15px; margin-top: 20px;">
                <div class="domain-card">
                    <h4>📄 Resume Domain</h4>
                    <div id="resumeDomain"></div>
                </div>
                <div class="domain-card">
                    <h4>📋 JD Domain</h4>
                    <div id="jdDomain"></div>
                </div>
            </div>
            
            <div class="domain-card">
                <h4>📊 Complete Analysis</h4>
                <div class="analysis-text" id="analysisText"></div>
            </div>
        </div>
        
        <!-- Multiple resume results -->
        <div class="multiple-results" id="multipleResults">
            <h2>📊 Batch Analysis Results</h2>
            <div id="resultsContainer"></div>
            <div class="domain-card">
                <h4>📋 Job Description Summary</h4>
                <div id="jdSummary"></div>
            </div>
        </div>
    </div>

    <script>
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
            
                    const data = await response.json();
                    
                    if (data.error) {
                        results.push({
                            filename: selectedResumeFiles[i].name,
                            error: data.error,
                            status: '❌',
                            recommendation: 'ERROR',
                            reason: data.error,
                            final_score: 0
                        });
                    } else {
                        results.push({
                            filename: selectedResumeFiles[i].name,
                            ...data
                        });
                    }
                } catch (error) {
                    results.push({
                        filename: selectedResumeFiles[i].name,
                        error: error.message,
                        status: '❌',
                        recommendation: 'ERROR',
                        reason: error.message,
                        final_score: 0
                    });
                }
            }
            
            displayMultipleResults(results);
        }
        
        function displaySingleResult(data) {
            const results = document.getElementById('results');
            
            // Update recommendation
            document.getElementById('recommendation').textContent = data.status + ' ' + data.recommendation;
            document.getElementById('reason').textContent = data.reason;
            
            // Show overall score if available
            if (data.final_score !== undefined && data.final_score > 0) {
                document.getElementById('overallScore').style.display = 'block';
                document.getElementById('scoreValue').textContent = data.final_score + '%';
            } else {
                document.getElementById('overallScore').style.display = 'none';
            }
            
            // Set result styling
            results.className = 'results';
            if (data.domains_match && (data.final_score || 0) >= 60) {
                results.classList.add('match');
            } else if (data.recommendation && (data.recommendation.includes('MANUAL') || data.recommendation.includes('MAYBE'))) {
                results.classList.add('review');
            } else {
                results.classList.add('mismatch');
            }
            
            // Update domain cards
            updateDomainCard('resumeDomain', data.resume_domain);
            updateDomainCard('jdDomain', data.jd_domain);
            
            // Show analysis text
            if (data.analysis_text) {
                document.getElementById('analysisText').textContent = data.analysis_text;
            }
            
            results.style.display = 'block';
        }
        
        function displayMultipleResults(results) {
            const multipleResults = document.getElementById('multipleResults');
            const resultsContainer = document.getElementById('resultsContainer');
            
            // Sort results by score (highest first)
            results.sort((a, b) => (b.final_score || 0) - (a.final_score || 0));
            
            // Generate result cards
            let html = '';
            results.forEach((result, index) => {
                html += createResultCard(result.filename, result, index);
            });
            
            resultsContainer.innerHTML = html;
            
            // Show summary statistics
            const totalResumes = results.length;
            const strongMatches = results.filter(r => (r.final_score || 0) >= 75).length;
            const goodMatches = results.filter(r => (r.final_score || 0) >= 60 && (r.final_score || 0) < 75).length;
            const weakMatches = results.filter(r => (r.final_score || 0) < 60).length;
            const errors = results.filter(r => r.error).length;
            
            // Get JD domain from first successful result
            const firstSuccessfulResult = results.find(r => !r.error && r.jd_domain);
            if (firstSuccessfulResult) {
                document.getElementById('jdSummary').innerHTML = `
                    <div><strong>Required Domain:</strong> ${firstSuccessfulResult.jd_domain.domain_name}</div>
                    <div><strong>Confidence:</strong> ${firstSuccessfulResult.jd_domain.confidence}%</div>
                    <div style="margin-top: 15px;"><strong>📊 Summary:</strong></div>
                    <div>• <span style="color: #27ae60;">Strong Matches (75%+):</span> ${strongMatches}</div>
                    <div>• <span style="color: #f39c12;">Good Matches (60-74%):</span> ${goodMatches}</div>
                    <div>• <span style="color: #e74c3c;">Weak Matches (<60%):</span> ${weakMatches}</div>
                    ${errors > 0 ? `<div>• <span style="color: #95a5a6;">Errors:</span> ${errors}</div>` : ''}
                    <div style="margin-top: 10px;"><strong>Total Processed:</strong> ${totalResumes} resumes</div>
                `;
            }
            
            multipleResults.style.display = 'block';
        }

        function testExperience() {
            const resumeText = document.getElementById('resumeText').value;
            const jdText = document.getElementById('jdText').value;
            
            if (!resumeText) {
                alert('Please enter resume text first');
                return;
            }
            
            const formData = new FormData();
            formData.append('resumeText', resumeText);
            formData.append('jdText', jdText);
            
            fetch('/debug-experience', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                } else {
                    alert(`Experience Extraction Test:
Resume Experience: ${data.resume_experience} years
JD Experience: ${data.jd_experience} years

Text Preview: ${data.text_preview}...

${data.debug_info}`);
                }
            })
            .catch(error => {
                alert('Test failed: ' + error.message);
            });
        }
        
        // Initialize
        updateResumeFilesList();
    </script>
</body>
</html>
    """)

@app.route('/analyze-multiple', methods=['POST'])
def analyze_multiple():
    """Analyze single resume from multiple upload"""
    try:
        resume_text = ""
        jd_text = ""
        
        # Handle single resume from multiple upload
        if 'resumes' in request.files:
            resume_file = request.files['resumes']
            if resume_file.filename:
                filename = secure_filename(resume_file.filename)
                resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                resume_file.save(resume_path)
                resume_text = matcher.extract_text(resume_path)
                os.remove(resume_path)
                
                if resume_text.startswith('Error') or resume_text.startswith('No'):
                    return jsonify({'error': f'Resume file issue: {resume_text}'})
        
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
            return jsonify({'error': 'Resume text too short or empty'})
        
        if not jd_text or len(jd_text) < 20:
            return jsonify({'error': 'Job description text too short or empty'})
        
        # Analyze domains
        results = matcher.compare_domains(resume_text, jd_text)
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in analyze-multiple endpoint: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'})

@app.route('/debug-experience', methods=['POST'])
def debug_experience():
    """Debug endpoint to test experience extraction"""
    try:
        resume_text = request.form.get('resumeText', '').strip()
        jd_text = request.form.get('jdText', '').strip()
        
        if not resume_text:
            return jsonify({'error': 'Please provide resume text'})
        
        # Extract experience with debug output
        resume_exp = matcher.extract_experience(resume_text)
        jd_exp = matcher.extract_experience(jd_text) if jd_text else 0
        
        return jsonify({
            'resume_experience': resume_exp,
            'jd_experience': jd_exp,
            'text_preview': resume_text[:300],
            'debug_info': 'Check server logs for detailed extraction debug info'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

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
