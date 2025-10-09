from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, 
    QGroupBox, QComboBox, QLineEdit, QButtonGroup
)
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtCore import Qt
import random

# Import global T_r configuration
try:
    from t_r_config import get_global_t_r, set_global_t_r, reset_global_t_r
except ImportError:
    # Fallback functions if module not available
    get_global_t_r = lambda: random.uniform(6, 600)
    set_global_t_r = lambda x: None
    reset_global_t_r = lambda: random.uniform(6, 600)


class SimulationModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Simulation Mode Selection")
        # Initial setup - show manual mode by default
        self.setFixedSize(500, 650)
        self.setStyleSheet(self.get_dark_theme())
        self.selected_mode = None
        self.selected_bus = "Bus 5"
        self.selected_fault_type = "slg"
        self.fault_impedance = "0.0"
        self.comm_fault_type = None
        self.initUI()

    def get_dark_theme(self):
        return """
        QDialog {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #4a9eff;
            border-radius: 8px;
            margin: 5px;
            padding-top: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a2a, stop:1 #1a1a1a);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #4a9eff;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a9eff, stop:1 #2d5aa0);
            border: 2px solid #4a9eff;
            border-radius: 8px;
            padding: 8px;
            font-weight: bold;
            color: white;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5badff, stop:1 #3d6bb0);
            border: 2px solid #5badff;
        }
        QComboBox, QLineEdit {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a3a3a, stop:1 #2a2a2a);
            border: 2px solid #4a9eff;
            border-radius: 5px;
            padding: 5px;
            color: white;
        }
        QRadioButton {
            spacing: 8px;
            color: white;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        QRadioButton::indicator:unchecked {
            border: 2px solid #4a9eff;
            border-radius: 8px;
            background: #2a2a2a;
        }
        QRadioButton::indicator:checked {
            border: 2px solid #4a9eff;
            border-radius: 8px;
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, stop:0 #4a9eff, stop:1 #2d5aa0);
        }
        """

    def initUI(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Select Simulation Mode")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4a9eff; margin: 10px;")
        layout.addWidget(title)
        
        # Mode Selection
        mode_group = QGroupBox("Simulation Mode")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        self.manual_radio = QRadioButton("🎯 Manual Mode - Use specified parameters")
        self.random_radio = QRadioButton("🎲 Random Mode - Generate random faults")
        
        self.mode_group.addButton(self.manual_radio, 0)
        self.mode_group.addButton(self.random_radio, 1)
        self.manual_radio.setChecked(True)
        
        mode_layout.addWidget(self.manual_radio)
        mode_layout.addWidget(self.random_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Manual Mode Parameters Group
        self.params_group = QGroupBox("Manual Mode Parameters")
        params_layout = QVBoxLayout()
        
        # Case 1: Generation Loss
        case1_group = QGroupBox("Case 1: Generation Loss (SLG Faults)")
        case1_layout = QVBoxLayout()
        self.gen_radio = QRadioButton("Select Generation Bus")
        self.gen_combo = QComboBox()
        self.gen_combo.addItems(["Bus 1", "Bus 2", "Bus 6", "Bus 7"])
        self.gen_combo.setCurrentText("Bus 1")
        case1_layout.addWidget(self.gen_radio)
        case1_layout.addWidget(self.gen_combo)
        case1_group.setLayout(case1_layout)
        
        # Case 2: Load Buses Loss
        case2_group = QGroupBox("Case 2: Load Buses Loss (SLG Faults)")
        case2_layout = QVBoxLayout()
        self.load_radio = QRadioButton("Select Load Bus")
        self.load_combo = QComboBox()
        self.load_combo.addItems(["Bus 3", "Bus 4", "Bus 5"])
        self.load_combo.setCurrentText("Bus 3")
        case2_layout.addWidget(self.load_radio)
        case2_layout.addWidget(self.load_combo)
        case2_group.setLayout(case2_layout)
        
        # Case 3: Communication Loss
        case3_group = QGroupBox("Case 3: Communication Loss")
        case3_layout = QVBoxLayout()
        self.comm_radio = QRadioButton("Select Communication Bus")
        self.comm_combo = QComboBox()
        self.comm_combo.addItems(["Bus 1", "Bus 7"])
        self.comm_combo.setCurrentText("Bus 1")
        case3_layout.addWidget(self.comm_radio)
        case3_layout.addWidget(self.comm_combo)
        case3_group.setLayout(case3_layout)
        
        # Group radio buttons
        self.case_group = QButtonGroup()
        self.case_group.addButton(self.gen_radio, 0)
        self.case_group.addButton(self.load_radio, 1)
        self.case_group.addButton(self.comm_radio, 2)
        self.gen_radio.setChecked(True)  # Default selection
        
        # Fault Impedance (always user input)
        impedance_layout = QHBoxLayout()
        impedance_layout.addWidget(QLabel("Fault Impedance (Ω):"))
        self.impedance_input = QLineEdit()
        self.impedance_input.setText("0.0")
        self.impedance_input.setPlaceholderText("Enter impedance value")
        impedance_layout.addWidget(self.impedance_input)
        
        params_layout.addWidget(case1_group)
        params_layout.addWidget(case2_group)
        params_layout.addWidget(case3_group)
        params_layout.addLayout(impedance_layout)
        
        self.params_group.setLayout(params_layout)
        layout.addWidget(self.params_group)
        
        # Random Mode Info
        self.info_group = QGroupBox("Random Mode Distribution")
        info_layout = QVBoxLayout()
        info_label = QLabel("• Case 1 (Generation Loss): 15% (Bus 1, 2, 6, 7) - SLG\n• Case 2 (Load Buses Loss): 60% (Bus 3, 4, 5) - SLG\n• Case 3 (Communication Loss): 25% (Bus 1, 7) - COMM")
        info_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        info_layout.addWidget(info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("✅ Run Simulation")
        self.cancel_button = QPushButton("❌ Cancel")
        
        self.ok_button.clicked.connect(self.accept_simulation)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect mode change and set initial state
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        self.on_mode_changed()  # Set initial visibility
    
    def on_mode_changed(self):
        is_manual = self.manual_radio.isChecked()
        
        # Show/hide groups based on selected mode
        self.params_group.setVisible(is_manual)
        self.info_group.setVisible(not is_manual)
        
        # Adjust dialog size
        if is_manual:
            self.setFixedSize(500, 650)  # Larger for manual mode
        else:
            self.setFixedSize(500, 400)  # Smaller for random mode
    
    def accept_simulation(self):
        # Get fault impedance (always user input)
        try:
            impedance_text = self.impedance_input.text().strip()
            if impedance_text:
                self.fault_impedance = float(impedance_text)
            else:
                self.fault_impedance = 0.0
        except (ValueError, AttributeError):
            self.fault_impedance = 0.0
        
        if self.random_radio.isChecked():
            self.selected_mode = "random"
            self.generate_random_fault()
        else:
            self.selected_mode = "manual"
            # Get selected bus from appropriate case
            if self.gen_radio.isChecked():
                self.selected_bus = self.gen_combo.currentText()
                self.selected_fault_type = "slg"
                self.comm_fault_type = None
            elif self.load_radio.isChecked():
                self.selected_bus = self.load_combo.currentText()
                self.selected_fault_type = "slg"
                self.comm_fault_type = None
            else:  # Communication fault
                self.selected_bus = self.comm_combo.currentText()
                self.selected_fault_type = "comm"
                self.comm_fault_type = "Communication Loss"
        
        self.accept()
    
    def generate_random_fault(self):
        """Generate random fault based on distribution percentages"""
        # Generate T_r first to determine case probabilities
        reset_global_t_r()
        
        # 15% Case 1 (Generation), 60% Case 2 (Load), 25% Case 3 (Communication)
        fault_category = random.choices(
            ["generation", "load", "communication"], 
            weights=[15.0, 60.0, 25.0]
        )[0]
        
        if fault_category == "generation":
            # Random generation bus fault
            self.selected_bus = random.choice(["Bus 1", "Bus 2", "Bus 6", "Bus 7"])
            self.selected_fault_type = "slg"
            self.comm_fault_type = None
        elif fault_category == "load":
            # Random load bus fault
            self.selected_bus = random.choice(["Bus 3", "Bus 4", "Bus 5"])
            self.selected_fault_type = "slg"
            self.comm_fault_type = None
        else:
            # Random communication fault
            self.selected_bus = random.choice(["Bus 1", "Bus 7"])
            self.selected_fault_type = "comm"
            self.comm_fault_type = "Communication Loss"
    
    def get_simulation_parameters(self):
        """Return the selected simulation parameters"""
        return {
            "mode": self.selected_mode,
            "bus": self.selected_bus,
            "fault_type": self.selected_fault_type,
            "impedance": self.fault_impedance,
            "comm_fault": self.comm_fault_type
        }