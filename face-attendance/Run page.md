# Run Guide (Windows PowerShell)

Use these exact terminal commands to start the website.

## First-Time Setup (one time only)

```powershell
cd "c:\Users\t-aftabkhan\OneDrive - Microsoft\Desktop\Aftab Khan - FinalYearProject\Teams com"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### What each command does

- `cd "...\Teams com"`:
	Changes the terminal location to the backend project folder where `app.py` and `requirements.txt` exist.
- `python -m venv .venv`:
	Creates a private Python environment named `.venv` for this project.
- `.\.venv\Scripts\Activate.ps1`:
	Activates that environment so `python` and `pip` use project-specific packages.
- `pip install -r requirements.txt`:
	Installs all required libraries (Flask, Flask-SocketIO, SQLAlchemy, etc.) from the requirements file.
- `python app.py`:
	Starts the Flask server for the whole website on port `5000`.

When you see the startup message, open:

`http://127.0.0.1:5000`

Login page:

`http://127.0.0.1:5000/auth/login`

Face Attendance page (after login):

`http://127.0.0.1:5000/face-attendance/`

## Daily Start (after first setup)

```powershell
cd "c:\Users\t-aftabkhan\OneDrive - Microsoft\Desktop\Aftab Khan - FinalYearProject\Teams com"
.\.venv\Scripts\Activate.ps1
python app.py
```

### Why only these 3 commands daily

- The virtual environment is already created.
- Packages are already installed.
- You only need to enter the project folder, activate the environment, and run the server.

## Stop Server

In the same terminal, press `Ctrl + C`.

### Why

- This safely stops the running Flask process.
- Close the terminal only after stopping the server to avoid hanging processes.

## If `python` does not work

Use `py` instead:

```powershell
py -m venv .venv
py -m pip install -r requirements.txt
py app.py
```

### What this means

- On some Windows setups, `python` is not added to PATH.
- `py` is the Windows Python launcher and runs the same tasks.
- These commands are direct alternatives to the `python ...` versions above.

## Important

- Keep the terminal running while using the site.
- The face-attendance page depends on the Flask server at port `5000`.
- Do not run this page with Live Server on port `5500`; use the Flask URL above.
- Student records are now persisted in SQLite at `Teams com/instance/team_collab.db`, so they remain after server restart.
- Records are user-specific: log into the same account to see the same saved students.

## Quick URL Purpose

- `http://127.0.0.1:5000`:
	Main app home when the server is running.
- `http://127.0.0.1:5000/auth/login`:
	Login page for your account.
- `http://127.0.0.1:5000/face-attendance/`:
	Face attendance feature page (works correctly only through Flask server).
