from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, 
    QGroupBox, QComboBox, QLineEdit, QButtonGroup
)
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtCore import Qt
import random


class SimulationModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Simulation Mode Selection")
        self.setFixedSize(500, 510)
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
        
        # Parameters Group
        params_group = QGroupBox("Simulation Parameters")
        params_layout = QVBoxLayout()
        
        # Bus Selection
        bus_layout = QHBoxLayout()
        bus_layout.addWidget(QLabel("Faulted Bus:"))
        self.bus_combo = QComboBox()
        self.bus_combo.addItems(["Bus 1", "Bus 2", "Bus 3", "Bus 4", "Bus 5", "Bus 6", "Bus 7"])
        self.bus_combo.setCurrentText("Bus 5")
        bus_layout.addWidget(self.bus_combo)
        params_layout.addLayout(bus_layout)
        
        # Fault Type
        fault_layout = QHBoxLayout()
        fault_layout.addWidget(QLabel("Fault Type:"))
        self.fault_combo = QComboBox()
        self.fault_combo.addItems(["slg"])
        fault_layout.addWidget(self.fault_combo)
        params_layout.addLayout(fault_layout)
        
        # Fault Impedance (always user input)
        impedance_layout = QHBoxLayout()
        impedance_layout.addWidget(QLabel("Fault Impedance (Ω):"))
        self.impedance_input = QLineEdit()
        self.impedance_input.setText("0.0")
        self.impedance_input.setPlaceholderText("Enter impedance value")
        impedance_layout.addWidget(self.impedance_input)
        params_layout.addLayout(impedance_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Random Mode Info
        info_group = QGroupBox("Random Mode Distribution")
        info_layout = QVBoxLayout()
        info_label = QLabel("• Power Flow Faults: 73.5%\n• Communication Faults: 26.5%")
        info_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
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
        
        # Connect mode change
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
    
    def on_mode_changed(self):
        is_manual = self.manual_radio.isChecked()
        self.bus_combo.setEnabled(is_manual)
        self.fault_combo.setEnabled(is_manual)
    
    def accept_simulation(self):
        # Get fault impedance (always user input)
        try:
            self.fault_impedance = float(self.impedance_input.text())
        except ValueError:
            self.fault_impedance = 0.0
        
        if self.random_radio.isChecked():
            self.selected_mode = "random"
            self.generate_random_fault()
        else:
            self.selected_mode = "manual"
            self.selected_bus = self.bus_combo.currentText()
            self.selected_fault_type = self.fault_combo.currentText()
        
        self.accept()
    
    def generate_random_fault(self):
        """Generate random fault based on distribution percentages"""
        # 73.5% Power Flow faults, 26.5% Communication faults
        fault_category = random.choices(
            ["power_flow", "communication"], 
            weights=[73.5, 26.5]
        )[0]
        
        if fault_category == "power_flow":
            # Random power flow fault
            self.selected_bus = random.choice(["Bus 1", "Bus 2", "Bus 3", "Bus 4", "Bus 5", "Bus 6", "Bus 7"])
            self.selected_fault_type = "slg"  # Only SLG for now
            self.comm_fault_type = None
        else:
            # Random communication fault
            self.selected_bus = random.choice(["Bus 1", "Bus 2", "Bus 3", "Bus 4", "Bus 5", "Bus 6", "Bus 7"])
            self.selected_fault_type = "slg"  # Still need power fault
            self.comm_fault_type = random.choice(["Latency", "Jitter", "Bandwidth"])
    
    def get_simulation_parameters(self):
        """Return the selected simulation parameters"""
        return {
            "mode": self.selected_mode,
            "bus": self.selected_bus,
            "fault_type": self.selected_fault_type,
            "impedance": self.fault_impedance,
            "comm_fault": self.comm_fault_type
        }