# 🪟 Windows Installation Guide

**Step-by-step for local installation on Windows**

## Prerequisites

1. **Python 3.11 or 3.12** (NOT 3.13 - some dependencies aren't compatible yet)
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Verify: Open Command Prompt and run `python --version`

2. **Git** (to clone the repository)
   - Download: https://git-scm.com/download/win
   - Use default settings during installation

---

## Installation Steps

### 1. Clone the Repository

Open **Command Prompt** or **PowerShell**:

```cmd
git clone https://github.com/Chrysaliz333/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain.git
cd Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain
```

### 2. Create Virtual Environment

```cmd
python -m venv venv
```

### 3. Activate Virtual Environment

**In Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

**In PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

If PowerShell gives an error about execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

You should see `(venv)` at the start of your command line.

### 4. Install Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

This will take 3-5 minutes.

### 5. Set Up API Key

Create a file called `.env` in the project folder:

```cmd
notepad .env
```

Add this line:
```
ANTHROPIC_API_KEY=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
```

Save and close Notepad.

### 6. Run the App

```cmd
streamlit run app.py
```

The app will open automatically in your browser at: **http://localhost:8501**

---

## Common Windows Issues & Fixes

### Issue 1: "python is not recognized"

**Fix:**
1. Reinstall Python
2. **Check** "Add Python to PATH" during installation
3. Restart Command Prompt

### Issue 2: "pip install" fails with compilation errors

**Fix - Install Visual C++ Build Tools:**
1. Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++"
3. Restart computer
4. Try `pip install -r requirements.txt` again

**Or use precompiled wheels:**
```cmd
pip install --only-binary :all: -r requirements.txt
```

### Issue 3: PowerShell script execution blocked

**Error:** "running scripts is disabled on this system"

**Fix:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again:
```powershell
venv\Scripts\Activate.ps1
```

### Issue 4: "No module named 'XXX'"

**Fix:**
```cmd
# Make sure virtual environment is activated (you see (venv))
pip install -r requirements.txt --force-reinstall
```

### Issue 5: Port 8501 already in use

**Fix:**
```cmd
# Find what's using the port
netstat -ano | findstr :8501

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different port
streamlit run app.py --server.port 8502
```

### Issue 6: Slow installation

**Fix:**
```cmd
# Use a faster mirror
pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## Verify Installation

After installation, verify everything works:

```cmd
# Check Python version (should be 3.11 or 3.12)
python --version

# Check pip is working
pip --version

# Check Streamlit is installed
streamlit --version

# List installed packages
pip list
```

---

## Running the App

### Every time you want to run the app:

1. **Open Command Prompt** in the project folder
2. **Activate virtual environment:**
   ```cmd
   venv\Scripts\activate.bat
   ```
3. **Run Streamlit:**
   ```cmd
   streamlit run app.py
   ```
4. **Access:** http://localhost:8501

### To stop the app:
- Press **Ctrl + C** in the terminal

---

## Recommended: Use Windows Terminal

Windows Terminal is much better than Command Prompt:

1. Install from Microsoft Store (free)
2. Open Windows Terminal
3. Navigate to project folder:
   ```cmd
   cd C:\path\to\Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain
   ```
4. Follow the steps above

---

## Alternative: Docker (Easier!)

If you're still having issues, Docker is simpler:

1. **Install Docker Desktop for Windows:**
   - Download: https://www.docker.com/products/docker-desktop/
   - Install and restart computer

2. **Run the app:**
   ```cmd
   docker build -f Dockerfile.streamlit -t legal-analyzer .
   docker run -p 8501:8501 -e ANTHROPIC_API_KEY=your-key-here legal-analyzer
   ```

3. **Open:** http://localhost:8501

Docker handles all dependencies automatically!

---

## Need Help?

### Check these first:
- ✅ Python 3.11 or 3.12 installed (NOT 3.13)
- ✅ Virtual environment activated (see `(venv)`)
- ✅ `.env` file created with API key
- ✅ All dependencies installed successfully

### Still stuck?
- See detailed logs: `streamlit run app.py --logger.level debug`
- Check GitHub issues: https://github.com/Chrysaliz333/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain/issues
- Or use the cloud version (no installation): https://chrysaliz333-legal-assistant-contract-analysis-rag-k-app-ttm3ib.streamlit.app/
