@echo off

:: Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

:: Run the Flask app
python -m flask run --host=0.0.0.0

pause