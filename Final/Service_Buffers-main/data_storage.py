import os
import json
from datetime import datetime
from typing import List, Dict, Any
import numpy as np

class DataStorage:
    def __init__(self, base_path="reports"):
        self.base_path = base_path
        self.ensure_directories()
        self.event_logs = []
        self.max_log_entries = 100
        
        # Statistical tracking variables (26 total: 13 T_r + 13 DA)
        self.simulation_count = 0
        self.case_counts = {
            'C1': 0, 'C2': 0, 'C3': 0, 'C1D': 0, 'C1R': 0, 'C1H': 0, 'C1C': 0,
            'C2T': 0, 'C2M': 0, 'C2R': 0, 'C3T': 0, 'C3F': 0, 'C3M': 0
        }
        self.t_r_averages = {
            'C1': 0, 'C2': 0, 'C3': 0, 'C1D': 0, 'C1R': 0, 'C1H': 0, 'C1C': 0,
            'C2T': 0, 'C2M': 0, 'C2R': 0, 'C3T': 0, 'C3F': 0, 'C3M': 0
        }
        self.da_averages = {
            'C1': 0, 'C2': 0, 'C3': 0, 'C1D': 0, 'C1R': 0, 'C1H': 0, 'C1C': 0,
            'C2T': 0, 'C2M': 0, 'C2R': 0, 'C3T': 0, 'C3F': 0, 'C3M': 0
        }
        
    def ensure_directories(self):
        """Create necessary directories"""
        os.makedirs(os.path.join(self.base_path, "events"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "logs"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "statistics"), exist_ok=True)
    
    def save_event_report(self, case_type: str, simulation_data: Dict[str, Any]):
        """Save event report with date and case information"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_Case{case_type}.json"
        filepath = os.path.join(self.base_path, "events", filename)
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "case": case_type,
            "simulation_data": simulation_data,
            "metadata": {
                "t_r": simulation_data.get("t_r", 0),
                "fault_bus": simulation_data.get("fault_bus", "N/A"),
                "fault_type": simulation_data.get("fault_type", "N/A")
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Update statistics
        self.simulation_count += 1
        case_info = simulation_data.get("case_info")
        subcategory = simulation_data.get("subcategory")
        t_r_value = simulation_data.get("t_r", 0)
        da_value = simulation_data.get("da_value", 0)
        
        if case_info and subcategory:
            self.update_statistics(case_info, subcategory, t_r_value, da_value)
        
        # Keep only last 3 event reports
        self._cleanup_old_events()
        return filepath
    
    def add_log_entry(self, log_message: str):
        """Add entry to event log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {log_message}"
        
        self.event_logs.append(log_entry)
        
        # Keep only last 100 entries
        if len(self.event_logs) > self.max_log_entries:
            self.event_logs = self.event_logs[-self.max_log_entries:]
    
    def save_event_log(self):
        """Save current event log to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"event_log_{timestamp}.txt"
        filepath = os.path.join(self.base_path, "logs", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for entry in self.event_logs:
                f.write(entry + '\n')
        
        return filepath
    
    def update_statistics(self, case_info, subcategory, t_r_value, da_value):
        """Update running averages for T_r and DA based on case and subcategory"""
        # Map case and subcategory to variable codes
        case_code = self._get_case_code(case_info, subcategory)
        if not case_code:
            return
        
        # Update counts
        self.case_counts[case_code] += 1
        n = self.case_counts[case_code]
        
        # Update running averages: new_avg = old_avg + (new_value - old_avg) / n
        self.t_r_averages[case_code] = self.t_r_averages[case_code] + (t_r_value - self.t_r_averages[case_code]) / n
        self.da_averages[case_code] = self.da_averages[case_code] + (da_value - self.da_averages[case_code]) / n
        
        # Update main case averages using weighted formula: T_r(C1) = w_C1D*t_r(C1D) + w_C1R*t_r(C1R) + ...
        main_case = case_code[:2] if len(case_code) > 2 else case_code
        if main_case in ['C1', 'C2', 'C3']:
            self._update_main_case_weighted_averages(main_case)
    
    def _update_main_case_weighted_averages(self, main_case):
        """Update main case averages using weighted formula based on subcategory probabilities"""
        # Define subcategory probabilities from t_r_config.py
        probabilities = {
            'C1': {'C1D': 0.40, 'C1R': 0.30, 'C1H': 0.20, 'C1C': 0.10},  # Case 1 subcategories
            'C2': {'C2T': 0.50, 'C2M': 0.30, 'C2R': 0.20},                # Case 2 subcategories  
            'C3': {'C3T': 0.60, 'C3F': 0.25, 'C3M': 0.15}                 # Case 3 subcategories
        }
        
        if main_case not in probabilities:
            return
            
        # Calculate weighted averages: T_r(C1) = w_C1D*t_r(C1D) + w_C1R*t_r(C1R) + w_C1H*t_r(C1H) + w_C1C*t_r(C1C)
        weighted_t_r = 0
        weighted_da = 0
        
        for subcase, weight in probabilities[main_case].items():
            if self.case_counts[subcase] > 0:  # Only include subcases with data
                weighted_t_r += weight * self.t_r_averages[subcase]
                weighted_da += weight * self.da_averages[subcase]
        
        # Update main case averages with weighted values
        self.t_r_averages[main_case] = weighted_t_r
        self.da_averages[main_case] = weighted_da
        
        # Update main case count (sum of all subcategory counts)
        total_count = sum(self.case_counts[subcase] for subcase in probabilities[main_case].keys())
        self.case_counts[main_case] = total_count
    
    def _get_case_code(self, case_info, subcategory):
        """Map case and subcategory to variable codes"""
        if "Case 1" in str(case_info):
            if subcategory == "clearance":
                return "C1D"  # Clearance/Despeje
            elif subcategory == "reconfig":
                return "C1R"  # Reconfig
            elif subcategory == "hot_restart":
                return "C1H"  # Hot restart
            elif subcategory == "cold_restart":
                return "C1C"  # Cold restart
            return "C1"
        elif "Case 2" in str(case_info):
            if subcategory == "transient":
                return "C2T"  # Transient
            elif subcategory == "sustained":
                return "C2M"  # Maniobra/Sustained
            elif subcategory == "repair":
                return "C2R"  # Repair
            return "C2"
        elif "Case 3" in str(case_info):
            if subcategory == "transient":
                return "C3T"  # Transient
            elif subcategory == "failover":
                return "C3F"  # Failover
            elif subcategory == "physical":
                return "C3M"  # Manual/Physical
            return "C3"
        return None
    
    def save_probability_statistics(self):
        """Save current statistical data as comprehensive PDF report"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            import matplotlib.pyplot as plt
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"probability_statistics_{timestamp}.pdf"
            pdf_filepath = os.path.join(self.base_path, "statistics", pdf_filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_filepath, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], 
                                       fontSize=18, spaceAfter=30, textColor=colors.HexColor('#4a9eff'))
            story.append(Paragraph("📊 Statistical Analysis Report - T_r and DA Variables", title_style))
            story.append(Spacer(1, 12))
            
            # Summary
            story.append(Paragraph("Executive Summary", styles['Heading2']))
            summary_text = f"""
            This report presents the statistical analysis of 26 variables tracking T_r (Recovery Time) and 
            DA (Delay Allowance) values across different fault cases and subcategories.<br/><br/>
            <b>Total Simulations:</b> {self.simulation_count}<br/>
            <b>Analysis Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
            <b>Variables Tracked:</b> 13 T_r variables + 13 DA variables = 26 total variables
            """
            story.append(Paragraph(summary_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Create statistics table
            story.append(Paragraph("Statistical Variables Table", styles['Heading2']))
            
            # Prepare table data
            table_data = [['Variable', 'Average Value', 'Simulation Count', 'Description']]
            
            # Add T_r variables
            for code in sorted(self.case_counts.keys()):
                if self.case_counts[code] > 0:
                    desc = self._get_variable_description(code)
                    table_data.append([
                        f'T_r({code})',
                        f'{self.t_r_averages[code]:.3f} min',
                        str(self.case_counts[code]),
                        desc
                    ])
                    table_data.append([
                        f'DA({code})',
                        f'{self.da_averages[code]:.6f}',
                        str(self.case_counts[code]),
                        f'Delay Allowance for {desc}'
                    ])
            
            # Create table
            table = Table(table_data, colWidths=[1.2*inch, 1.2*inch, 1*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a9eff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(table)
            story.append(Spacer(1, 20))
            
            # Create and include charts
            chart_path = self._create_statistics_charts_for_pdf(timestamp)
            if chart_path:
                story.append(Paragraph("Statistical Charts", styles['Heading2']))
                story.append(Image(chart_path, width=7*inch, height=5*inch))
                story.append(Spacer(1, 20))
            
            # Variable explanations
            story.append(Paragraph("Variable Definitions", styles['Heading2']))
            explanations = """
            <b>Case Categories:</b><br/>
            • C1: Generation Loss Cases<br/>
            • C2: Load Buses Loss Cases<br/>
            • C3: Communication Loss Cases<br/><br/>
            
            <b>Subcategories:</b><br/>
            • C1D: Clearance/Despeje, C1R: Reconfig, C1H: Hot Restart, C1C: Cold Restart<br/>
            • C2T: Transient, C2M: Maniobra/Sustained, C2R: Repair<br/>
            • C3T: Transient, C3F: Failover, C3M: Manual/Physical<br/><br/>
            
            <b>Update Formula:</b><br/>
            Variable = Variable_anterior + (New_Value - Variable_anterior) / n<br/>
            Where n is the count of simulations for each specific case/subcategory.
            """
            story.append(Paragraph(explanations, styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            # Clean up temp chart file
            if chart_path:
                try:
                    os.remove(chart_path)
                except:
                    pass
            
            return pdf_filepath
            
        except Exception as e:
            print(f"Error creating statistics PDF: {e}")
            return None
    
    def _create_statistics_charts_for_pdf(self, timestamp):
        """Create charts for T_r and DA statistics for PDF inclusion"""
        try:
            import matplotlib.pyplot as plt
            
            # Filter non-zero data
            active_codes = [code for code in self.case_counts.keys() if self.case_counts[code] > 0]
            
            if not active_codes:
                return None
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            fig.patch.set_facecolor('white')
            
            # T_r chart
            t_r_values = [self.t_r_averages[code] for code in active_codes]
            ax1.bar(active_codes, t_r_values, color='skyblue', edgecolor='black')
            ax1.set_title('Average T_r Values by Case/Subcategory', fontsize=14, fontweight='bold')
            ax1.set_ylabel('T_r (minutes)', fontsize=12)
            ax1.tick_params(axis='x', rotation=45, labelsize=10)
            ax1.grid(True, alpha=0.3)
            
            # DA chart
            da_values = [self.da_averages[code] for code in active_codes]
            ax2.bar(active_codes, da_values, color='lightcoral', edgecolor='black')
            ax2.set_title('Average DA Values by Case/Subcategory', fontsize=14, fontweight='bold')
            ax2.set_ylabel('DA (probability)', fontsize=12)
            ax2.tick_params(axis='x', rotation=45, labelsize=10)
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save chart for PDF
            chart_filename = f"temp_statistics_chart_{timestamp}.png"
            chart_filepath = os.path.join(self.base_path, "statistics", chart_filename)
            plt.savefig(chart_filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='black')
            plt.close()
            
            return chart_filepath
            
        except Exception as e:
            print(f"Error creating charts: {e}")
            return None
    
    def _get_variable_description(self, code):
        """Get description for variable code"""
        descriptions = {
            'C1': 'Generation Loss (Overall)',
            'C2': 'Load Buses Loss (Overall)', 
            'C3': 'Communication Loss (Overall)',
            'C1D': 'Generation - Clearance/Despeje',
            'C1R': 'Generation - Reconfig',
            'C1H': 'Generation - Hot Restart',
            'C1C': 'Generation - Cold Restart',
            'C2T': 'Load - Transient',
            'C2M': 'Load - Maniobra/Sustained',
            'C2R': 'Load - Repair',
            'C3T': 'Communication - Transient',
            'C3F': 'Communication - Failover',
            'C3M': 'Communication - Manual/Physical'
        }
        return descriptions.get(code, 'Unknown')
    
    def _get_case_description(self, case_num: int) -> str:
        """Get description for case number"""
        descriptions = {
            1: "Generation Loss - Generator or transmission line faults",
            2: "Load Buses Loss - Distribution system or load-side faults", 
            3: "Communication Loss - Control and communication system faults"
        }
        return descriptions.get(case_num, "Unknown Case")
    
    def _cleanup_old_events(self):
        """Keep only the 3 most recent event reports"""
        events_dir = os.path.join(self.base_path, "events")
        if not os.path.exists(events_dir):
            return
            
        files = [f for f in os.listdir(events_dir) if f.endswith('.json')]
        files.sort(reverse=True)  # Most recent first
        
        # Remove files beyond the first 3
        for file_to_remove in files[3:]:
            try:
                os.remove(os.path.join(events_dir, file_to_remove))
            except:
                pass
    
    def get_recent_events(self) -> List[str]:
        """Get list of recent event report files"""
        events_dir = os.path.join(self.base_path, "events")
        if not os.path.exists(events_dir):
            return []
            
        files = [f for f in os.listdir(events_dir) if f.endswith('.json')]
        files.sort(reverse=True)
        return files[:3]
    
    def clear_logs(self):
        """Clear current event logs"""
        self.event_logs = []