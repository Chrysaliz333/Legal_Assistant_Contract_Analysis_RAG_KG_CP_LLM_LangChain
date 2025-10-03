# 🎉 Setup Complete!

Your contract analysis system is **ready to use**!

---

## ✅ What's Installed

- ✅ **Python 3.13.5** (compatible)
- ✅ **Virtual environment** (`venv/`)
- ✅ **All dependencies** installed:
  - `anthropic` (Claude API)
  - `langchain` + `langchain-anthropic`
  - `langgraph` (workflow orchestration)
  - `textblob` (sentiment analysis)
  - `pydantic` + `pydantic-settings` (config)
- ✅ **SQLite database** with 3 policies + 6 playbook rules
- ✅ **4 AI agents** ready to analyze contracts
- ✅ **Complete demo** with sample SaaS contract

---

## 🚀 Ready to Run

### Option 1: Using the run script (recommended)
```bash
export ANTHROPIC_API_KEY='your-key-here'
./run_demo.sh
```

### Option 2: Manual activation
```bash
source venv/bin/activate
export ANTHROPIC_API_KEY='your-key-here'
python3 demo_workflow.py
```

### Option 3: Streaming mode
```bash
source venv/bin/activate
export ANTHROPIC_API_KEY='your-key-here'
python3 demo_workflow.py --stream
```

---

## 📝 Before You Run

**You need to set your Anthropic API key:**

```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
```

Get your key from: https://console.anthropic.com/

**Optional:** Save it permanently:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

---

## 🎯 What the Demo Will Do

When you run the demo, it will:

1. **Load 9 policies** from your database (3 general + 6 playbook rules)
2. **Analyze a sample SaaS contract** with 6 clauses
3. **Find ~5-6 policy deviations** (liability cap, SLA, missing DPA, etc.)
4. **Generate neutral explanations** (objective, evidence-based)
5. **Transform to your style** (concise + strict + internal by default)
6. **Create track-change edits** with exact character positions
7. **Show complete results** in ~30-60 seconds

---

## 📊 Expected Output

You'll see:

```
📋 STEP 1: Loading Policies and Playbook Rules
Loaded 9 applicable policies:
  1. [HIGH    ] [policy        ] All vendor contracts must include a liability cap of at least 200%...
  2. [CRITICAL] [policy        ] All vendor contracts processing personal data must include a Data...
  ...

📄 STEP 2: Extracting Clauses from Contract
Extracted 6 clauses:
  - Section 1        [service_levels              ] Provider shall use commercially reasonable...
  - Section 2        [limitation_of_liability     ] In no event shall Provider's total liability...
  ...

🤖 STEP 3: Running 4-Agent Analysis Pipeline
Style Configuration:
  - Tone: concise
  - Formality: legal
  - Aggressiveness: strict
  - Audience: internal

✅ Analysis complete in 45.2 seconds

📊 STEP 4: Analysis Results
Summary Statistics:
  - Total Findings: 5
  - Critical Issues: 1
  - High Priority Issues: 2
  - Suggested Edits: 5
  ...
```

---

## 🎨 Try Different Styles

The demo uses **strict internal** style by default. You can edit `demo_workflow.py` to try:

### Collaborative Negotiation
```python
style_params = {
    'tone': 'balanced',
    'formality': 'plain_english',
    'aggressiveness': 'flexible',
    'audience': 'counterparty'
}
```

### Executive Summary
```python
style_params = {
    'tone': 'verbose',
    'formality': 'plain_english',
    'aggressiveness': 'balanced',
    'audience': 'internal'
}
```

---

## 🔧 Integration Next Steps

After running the demo, integrate with your services:

```python
from src.agents.workflow import analyze_contract
from your_extraction_service import extract_clauses
from your_parsing_service import parse_document

# 1. Parse document
contract_text = parse_document("contract.pdf")

# 2. Extract clauses
clauses = extract_clauses(contract_text)

# 3. Load policies
from get_policies import get_policies_for_contract
policies = get_policies_for_contract(
    contract_type='saas',
    model_orientation='buy'
)

# 4. Run analysis
result = await analyze_contract(
    version_id="v1",
    session_id="s1",
    contract_text=contract_text,
    clauses=clauses,
    policies=policies,
    style_params={'tone': 'concise', 'audience': 'internal'}
)

# 5. Use results
for edit in result['suggested_edits']:
    print(f"Edit: {edit['change_summary']}")
```

---

## 📚 Documentation

- **QUICK_REFERENCE.md** - One-page cheat sheet
- **GETTING_STARTED.md** - Comprehensive guide
- **DEMO_README.md** - Demo details
- **WHAT_WE_BUILT.md** - Complete system overview

---

## 💡 Quick Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run demo
python3 demo_workflow.py

# Run in streaming mode
python3 demo_workflow.py --stream

# View policies
python3 get_policies.py

# Check database
sqlite3 legal_assistant.db "SELECT policy_text FROM policies;"

# Deactivate when done
deactivate
```

---

## 🎓 Virtual Environment Info

Your virtual environment is located at: `venv/`

**Activation commands:**
- macOS/Linux: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

**Deactivation:**
- All platforms: `deactivate`

**Packages installed:** 40+ packages including all dependencies

---

## ✨ You're All Set!

Just set your API key and run the demo:

```bash
export ANTHROPIC_API_KEY='your-key-here'
./run_demo.sh
```

Enjoy! 🚀

---

## 🐛 Troubleshooting

### "Command not found: ./run_demo.sh"
```bash
chmod +x run_demo.sh
```

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

### "ModuleNotFoundError"
Make sure venv is activated:
```bash
source venv/bin/activate
```

### Demo runs but no output
Check that your API key is valid and you have credits available at:
https://console.anthropic.com/

---

**Questions?** Check `GETTING_STARTED.md` or `QUICK_REFERENCE.md`
