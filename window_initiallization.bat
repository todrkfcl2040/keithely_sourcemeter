@echo off
setlocal

REM Check for Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/downloads
    pause
    exit /b
)

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b
)

REM Clone the GitHub repository
echo Cloning repository from GitHub...
git clone https://github.com/todrkfcl2040/keithely_sourcemeter.git
if errorlevel 1 (
    echo [ERROR] Failed to clone repository.
    pause
    exit /b
)

REM Change to the cloned directory
cd keithely_sourcemeter

REM Create virtual environment
echo Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b
)

REM Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

REM Run the program
echo Launching Keithley Waveform Controller...
python main.py

endlocal
pause
