v11 advanced build with timezone + whole-sign fixes



:: 1) Close any active venv
deactivate  2>nul

:: 2) Delete the broken venv
rmdir /s /q .venv

:: 3) Make a fresh one (use your installed version; 3.11 shown)
py -3.11 -m venv .venv

:: 4) Activate it
.\.venv\Scripts\activate

:: 5) Upgrade packaging tools
python -m pip install --upgrade pip setuptools wheel

:: 6) Install your deps
python -m pip install -r requirements.txt

:: 7) Run Streamlit using the current Python (avoid calling streamlit.exe directly)
python -m streamlit run streamlit_app.py
