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
        
        # Skills and tools detection (EXPANDED FROM YOUR WORKING VERSION)
        self.skill_categories = {
            'tools': [
                # Synopsys Tools
                'synopsys', 'design compiler', 'dc', 'icc2', 'ic compiler', 'primetime', 'pt', 
                'vcs', 'vcs mx', 'verdi', 'dve', 'spyglass', 'formality', 'star-rc', 'hspice',
                
                # Cadence Tools
                'cadence', 'innovus', 'encounter', 'genus', 'conformal', 'incisive', 'xcelium',
                'virtuoso', 'allegro', 'pegasus', 'voltus', 'tempus', 'quantus', 'palladium',
                
                # Mentor Graphics/Siemens
                'mentor', 'calibre', 'modelsim', 'questasim', 'questa', 'tessent', 'catapult',
                
                # FPGA Tools
                'xilinx', 'vivado', 'ise', 'vitis', 'quartus', 'altera', 'intel quartus',
                
                # Programming/Scrip
