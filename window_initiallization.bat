@echo off

REM Create virtual environment
echo Creating Python virtual environment...
python -m venv .venv

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install required packages
echo Installing dependencies...
pip install pyqt5 pyvisa matplotlib numpy

REM Run the program
echo Launching Keithley Waveform Controller...
python main.py
