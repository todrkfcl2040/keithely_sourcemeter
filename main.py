import sys
import time
import numpy as np
import pyvisa

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class KeithleyWaveformApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keithley 2400 Waveform Generator")
        self.simulation_mode = False

        self.rm = pyvisa.ResourceManager()
        try:
            self.instrument = self.rm.open_resource('ASRL4::INSTR')  # COM1 (윈도우), /dev/ttyS0 (리눅스)
            self.instrument.baud_rate = 9600
            self.instrument.write_termination = '\n'
            self.instrument.read_termination = '\n'
            self.instrument.timeout = 10000
            self.simulation_mode = False
        except Exception as e:
            QMessageBox.warning(self, "Simulation Mode", f"Keithley not connected. Running in demo mode.\n\n{e}")
            self.instrument = None
            self.simulation_mode = True

        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Waveform selection
        self.waveform_combo = QComboBox()
        self.waveform_combo.addItems(["Sine", "Cosine", "Square", "Sawtooth", "Custom"])
        self.waveform_combo.currentTextChanged.connect(self.update_waveform_visibility)
        self.layout.addWidget(QLabel("Waveform Type"))
        self.layout.addWidget(self.waveform_combo)

        # Square wave extra settings
        self.square_settings_layout = QHBoxLayout()

        start_level_layout = QVBoxLayout()
        start_level_layout.addWidget(QLabel("Square Start Level"))
        self.square_start_high = QComboBox()
        self.square_start_high.addItems(["High", "Low"])
        start_level_layout.addWidget(self.square_start_high)

        duty_layout = QVBoxLayout()
        duty_layout.addWidget(QLabel("Duty Cycle (%)"))
        self.square_duty_input = QLineEdit()
        self.square_duty_input.setText("50")
        duty_layout.addWidget(self.square_duty_input)

        self.square_settings_layout.addLayout(start_level_layout)
        self.square_settings_layout.addLayout(duty_layout)

        # Already moved above into square_settings_layout_widget
        self.square_settings_layout_widget = QWidget()
        self.square_settings_layout_widget.setLayout(self.square_settings_layout)
        self.layout.addWidget(self.square_settings_layout_widget)
        self.square_settings_layout_widget.hide()

        # Input fields
        self.input_layout = QHBoxLayout()

        amp_layout = QVBoxLayout()
        amp_layout.addWidget(QLabel("Amplitude (V)"))
        self.amplitude_input = QLineEdit()
        self.amplitude_input.setText("1.0")
        amp_layout.addWidget(self.amplitude_input)

        freq_layout = QVBoxLayout()
        freq_layout.addWidget(QLabel("Frequency (Hz)"))
        self.freq_input = QLineEdit()
        self.freq_input.setText("1.0")
        freq_layout.addWidget(self.freq_input)

        phase_layout = QVBoxLayout()
        phase_layout.addWidget(QLabel("Phase (deg)"))
        self.phase_input = QLineEdit()
        self.phase_input.setText("0.0")
        phase_layout.addWidget(self.phase_input)

        offset_layout = QVBoxLayout()
        offset_layout.addWidget(QLabel("Offset (V)"))
        self.offset_input = QLineEdit()
        self.offset_input.setText("0.0")
        offset_layout.addWidget(self.offset_input)
        self.input_layout.addLayout(offset_layout)

        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("Voltage Resolution (V)"))
        self.interval_input = QLineEdit()
        self.interval_input.setText("0.001")
        res_layout.addWidget(self.interval_input)

        repeat_layout = QVBoxLayout()
        repeat_layout.addWidget(QLabel("Pulse Repeat Count"))
        self.repeat_input = QLineEdit()
        self.repeat_input.setText("1")
        repeat_layout.addWidget(self.repeat_input)

        self.input_layout.addLayout(amp_layout)
        self.input_layout.addLayout(freq_layout)
        self.input_layout.addLayout(phase_layout)
        self.input_layout.addLayout(res_layout)
        self.input_layout.addLayout(repeat_layout)

        steady_layout = QVBoxLayout()
        steady_layout.addWidget(QLabel("Steady Voltage (V)"))
        self.steady_voltage_input = QLineEdit()
        self.steady_voltage_input.setText("0.0")
        steady_layout.addWidget(self.steady_voltage_input)
        self.input_layout.addLayout(steady_layout)

        self.total_time_label = QLabel("Total Duration: N/A")
        self.layout.addLayout(self.input_layout)

        # Custom waveform table
        self.layout.addWidget(QLabel("Custom Pulse (Time [s], Voltage [V])"))
        self.pulse_table = QTableWidget(5, 2)
        self.pulse_table.setHorizontalHeaderLabels(["Time", "Voltage"])
        self.layout.addWidget(self.pulse_table)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.run_button = QPushButton("Run on Keithley")
        self.button_layout.addWidget(self.preview_button)
        self.button_layout.addWidget(self.run_button)
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.button_layout.addWidget(self.pause_button)
        self.button_layout.addWidget(self.stop_button)

        self.steady_button = QPushButton("Apply Steady Voltage")
        self.pulse_button = QPushButton("Apply Pulse")
        self.button_layout.addWidget(self.steady_button)
        self.button_layout.addWidget(self.pulse_button)
        self.steady_button.clicked.connect(self.apply_steady_voltage)
        self.pulse_button.clicked.connect(self.apply_pulse_waveform)

        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.total_time_label)

        self.preview_button.clicked.connect(self.plot_waveform)
        self.run_button.clicked.connect(self.send_waveform_to_keithley)
        self.pause_button.clicked.connect(self.pause_waveform)
        self.stop_button.clicked.connect(self.stop_waveform)

        from PyQt5.QtWidgets import QScrollArea
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        self.scroll_area = QScrollArea()
        self.layout.addWidget(self.canvas)

    def update_waveform_visibility(self, waveform_name):
        if waveform_name == "Square":
            self.square_settings_layout_widget.show()
        else:
            self.square_settings_layout_widget.hide()

    def generate_waveform(self):
        waveform = self.waveform_combo.currentText()
        amp = float(self.amplitude_input.text() or 0)
        freq = float(self.freq_input.text() or 1)
        phase = float(self.phase_input.text() or 0)
        total_time = 1.0 / freq
        t = np.arange(0, total_time, 0.01)

        if waveform == "Sine":
            v = amp * np.sin(2 * np.pi * freq * t + np.deg2rad(phase))
        elif waveform == "Cosine":
            v = amp * np.cos(2 * np.pi * freq * t + np.deg2rad(phase))
        elif waveform == "Square":
            duty = float(self.square_duty_input.text() or 50) / 100.0
            start_high = self.square_start_high.currentText() == "High"
            period = 1.0 / freq
            v = np.zeros_like(t)
            high_time = duty * period
            for i, ti in enumerate(t):
                cycle_pos = (ti + (0 if start_high else high_time)) % period
                v[i] = amp if cycle_pos < high_time else -amp
        elif waveform == "Sawtooth":
            v = amp * 2 * (t * freq - np.floor(0.5 + t * freq))
        elif waveform == "Custom":
            t = []
            v = []
            for row in range(self.pulse_table.rowCount()):
                try:
                    t_val = float(self.pulse_table.item(row, 0).text())
                    v_val = float(self.pulse_table.item(row, 1).text())
                    t.append(t_val)
                    v.append(v_val)
                except:
                    continue
            t = np.array(t)
            v = np.array(v)
        offset = float(self.offset_input.text() or 0)
        v += offset
        return t, v

    def plot_waveform(self):
        t, v = self.generate_waveform()
        try:
            freq = float(self.freq_input.text() or 1.0)
            repeat_count = int(self.repeat_input.text() or 1)
            single_cycle_time = 1.0 / freq
        except:
            freq = 1.0
            repeat_count = 1
            single_cycle_time = 1.0

        total_time = (1.0 / freq) * repeat_count
        t_full = np.linspace(0, total_time, 1000 * repeat_count)

        waveform_type = self.waveform_combo.currentText()
        amp = float(self.amplitude_input.text() or 0)
        phase = float(self.phase_input.text() or 0)

        if waveform_type == "Sine":
            v_full = amp * np.sin(2 * np.pi * freq * t_full + np.deg2rad(phase))
        elif waveform_type == "Cosine":
            v_full = amp * np.cos(2 * np.pi * freq * t_full + np.deg2rad(phase))
        elif waveform_type == "Square":
            try:
                duty = float(self.square_duty_input.text() or 50) / 100.0
            except:
                duty = 0.5
            start_high = self.square_start_high.currentText() == "High"
            period = 1.0 / freq
            v_full = np.zeros_like(t_full)
            high_time = duty * period
            for i, ti in enumerate(t_full):
                cycle_pos = (ti + (0 if start_high else high_time)) % period
                v_full[i] = amp if cycle_pos < high_time else -amp
        elif waveform_type == "Sawtooth":
            v_full = amp * 2 * (t_full * freq - np.floor(0.5 + t_full * freq))
        elif waveform_type == "Custom":
            t_full = t
            v_full = v
        offset = float(self.offset_input.text() or 0)
        v_full += offset

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(t_full, v_full)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Waveform Preview")
        ax.set_xlim(t_full[0], t_full[-1])  # Zoomable area
        ax.set_autoscaley_on(True)
        try:
            steady_voltage = float(self.steady_voltage_input.text() or 0.0)
            ax.axhline(y=steady_voltage, color='red', linestyle='--', label=f"Steady Voltage ({steady_voltage:.2f} V)")
        except:
            pass
        ax.legend()
        try:
            total_duration = (1.0 / freq) * repeat_count
        except:
            total_duration = 0.0
        self.total_time_label.setText(f"Total Duration: {total_duration:.2f} s")
        self.canvas.draw()

    def send_waveform_to_keithley(self):
        self.triggered = False
        self.paused = False
        self.stopped = False

        _, voltages = self.generate_waveform()

        try:
            resolution = float(self.interval_input.text() or 0.001)
        except:
            resolution = 0.001

        try:
            repeat_count = int(self.repeat_input.text() or 1)
        except:
            repeat_count = 1

        try:
            freq = float(self.freq_input.text() or 1.0)
            total_duration = (1.0 / freq) * repeat_count
        except:
            total_duration = 0.0
        self.total_time_label.setText(f"Total Duration: {total_duration:.2f} s")

        if self.simulation_mode:
            QMessageBox.information(self, "Simulation", f"Simulated sending of waveform\nDuration: {total_duration:.2f}s")
            return

        try:
            self.instrument.write("*RST")  # 초기화
            self.instrument.write("*CLS")
            self.instrument.write("SOUR:FUNC VOLT")
            self.instrument.write("SOUR:VOLT:RANG 20")  # Adjust voltage range as needed
            self.instrument.write("SOUR:VOLT:MODE FIXED")
            self.instrument.write("SENS:CURR:PROT 0.1")
            self.instrument.write("OUTP ON")
            time.sleep(0.1)  # Wait for the instrument to stabilize

            try:
                status = self.instrument.query("OUTP?")
                print("Output status:", status)
            except Exception as e:
                print("Warning: Failed to read output status. Proceeding anyway.")

            # Debug print for interval and repeat info
            print(f"Interval: 0.02 s, Repeats: {repeat_count}, Total samples: {len(voltages)}")

            self.instrument.write("TRIG:SOUR BUS")
            self.instrument.write("TRIG:COUN 1")
            self.instrument.write("INIT")
            # Removed QMessageBox with "Trigger Ready"

            for _ in range(repeat_count):
                for v in voltages:
                    if self.stopped:
                        break
                    while self.paused:
                        QApplication.processEvents()
                        time.sleep(0.05)
                    if self.stopped:
                        break
                    v = round(v / resolution) * resolution
                    # Debug print for each voltage value
                    print(f"Sending voltage: {v:.4f}")
                    self.instrument.write(f"SOUR:VOLT {v:.4f}")
                    time.sleep(0.02)

            self.instrument.write("OUTP OFF")
        except Exception as e:
            QMessageBox.critical(self, "Communication Error", str(e))

    def pause_waveform(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_button.setText("Resume")
        else:
            self.pause_button.setText("Pause")

    def stop_waveform(self):
        self.stopped = True

    def apply_steady_voltage(self):
        if self.simulation_mode:
            QMessageBox.information(self, "Simulation", "Applying steady voltage (simulated).")
            return
        try:
            steady_v = float(self.steady_voltage_input.text() or 0.0)
            self.instrument.write("*RST")
            self.instrument.write("*CLS")
            self.instrument.write("SOUR:FUNC VOLT")
            self.instrument.write("SOUR:VOLT:RANG 20")
            self.instrument.write("SOUR:VOLT:MODE FIXED")
            self.instrument.write("SENS:CURR:PROT 0.1")
            self.instrument.write(f"SOUR:VOLT {steady_v:.4f}")
            self.instrument.write("OUTP ON")
            QMessageBox.information(self, "Steady Voltage", f"Steady voltage {steady_v:.2f} V applied.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def apply_pulse_waveform(self):
        if self.simulation_mode:
            QMessageBox.information(self, "Simulation", "Sending pulse waveform (simulated).")
            return

        self.paused = False
        self.stopped = False

        _, voltages = self.generate_waveform()

        try:
            resolution = float(self.interval_input.text() or 0.001)
            repeat_count = int(self.repeat_input.text() or 1)
            freq = float(self.freq_input.text() or 1.0)
        except:
            resolution = 0.001
            repeat_count = 1
            freq = 1.0

        interval = 1.0 / (freq * len(voltages))

        try:
            for _ in range(repeat_count):
                for v in voltages:
                    if self.stopped:
                        break
                    while self.paused:
                        QApplication.processEvents()
                        time.sleep(0.05)
                    if self.stopped:
                        break
                    v = round(v / resolution) * resolution
                    self.instrument.write(f"SOUR:VOLT {v:.4f}")
                    time.sleep(interval)
        except Exception as e:
            QMessageBox.critical(self, "Error during pulse", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = KeithleyWaveformApp()
    win.show()
    sys.exit(app.exec_())