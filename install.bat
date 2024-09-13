@echo off

:: Install Python packages
pip install -r requirements.txt

:: Create templates directory if it doesn't exist
if not exist "templates" mkdir templates

:: Inform user about successful installation
echo Installation completed. You can now run your Flask app with: python app.py
pause