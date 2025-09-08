@echo off
REM Batch file to run the Dispensary Scraper Agent on Windows

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the scraper
python main.py %*

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat
