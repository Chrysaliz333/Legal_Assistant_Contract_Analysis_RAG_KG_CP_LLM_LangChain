# Getting Started - Contract Analysis System

## 🎯 What You Have

A complete **4-agent contract analysis pipeline** that:

1. **Diligent Reviewer** - Finds policy deviations with severity classification
2. **Neutral Rationale** - Generates objective, evidence-based explanations
3. **Personality Agent** - Transforms output based on communication style
4. **Editor Agent** - Creates track-change format suggested edits

**Plus:**
- ✅ SQLite database with 3 policies + 6 playbook rules
- ✅ LangGraph workflow orchestration
- ✅ Complete demo with sample SaaS contract
- ✅ Type-safe state management
- ✅ Caching support (Redis optional)
- ✅ Streaming execution support

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
pip install anthropic langchain langchain-anthropic langgraph textblob pydantic pydantic-settings
```

### Step 2: Set API Key

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Get your key from: https://console.anthropic.com/

### Step 3: Run Demo

```bash
python3 verify_setup.py  # Verify everything is ready
./run_demo.sh            # Run the full demo
```

---

## 📊 What the Demo Shows

The demo analyzes a **sample SaaS contract** with 6 clauses and finds:

- ❌ **SLA below requirement** (99.5% vs 99.9% required)
- ❌ **Liability cap too low** (1× vs 2× required)
- ❌ **Missing Data Processing Addendum** (critical for GDPR)
- ❌ **Wrong governing law** (Delaware vs England & Wales)
- ❌ **Payment terms too long** (60 days vs 30 days)
- ❌ **IP indemnity incomplete** (missing duty to defend)

For each issue, you get:
- **Finding** with evidence quote and severity
- **Neutral rationale** with objective explanation
- **Styled transformation** based on your communication preferences
- **Track-change edit** with exact positions for programmatic editing

---

## 📁 Key Files

### Core System
```
src/agents/
├── state.py                  # Shared context (TypedDict)
├── diligent_reviewer.py      # Policy compliance checking
├── neutral_rationale.py      # Objective explanations
├── personality.py            # Style transformation
├── editor.py                 # Track-change edits
└── workflow.py               # LangGraph orchestrator

config/
└── settings.py               # Configuration management

legal_assistant.db            # SQLite database (policies + rules)
get_policies.py               # Policy loading helper
```

### Demo & Setup
```
demo_workflow.py              # Complete end-to-end demo
verify_setup.py               # Pre-flight checks
run_demo.sh                   # Setup + execution script
DEMO_README.md                # Detailed demo documentation
```

### Database Schema
```
Supply Agreement Schema/
├── schema.sql                # PostgreSQL/SQLite schema
├── setup_sqlite.py           # SQLite initialization
├── policies_light.csv        # Sample policies (3)
└── playbook_rules_light.csv  # Sample rules (6)
```

---

## 🎨 Customization

### Change Communication Style

Edit `demo_workflow.py`:

```python
# Internal legal team (strict, concise)
style_params = {
    'tone': 'concise',
    'formality': 'legal',
    'aggressiveness': 'strict',
    'audience': 'internal'
}

# Counterparty negotiation (flexible, balanced)
style_params = {
    'tone': 'balanced',
    'formality': 'plain_english',
    'aggressiveness': 'flexible',
    'audience': 'counterparty'
}

# Executive summary (verbose, plain language)
style_params = {
    'tone': 'verbose',
    'formality': 'plain_english',
    'aggressiveness': 'balanced',
    'audience': 'internal'
}
```

### Use Your Own Contract

Replace the sample contract in `demo_workflow.py`:

```python
SAMPLE_CONTRACT = """
Your actual contract text here...
"""
```

### Integrate Your Clause Extraction

Replace the simulated extraction function:

```python
# In demo_workflow.py, replace:
def extract_clauses(contract_text):
    # Simulated extraction...

# With your actual service:
from your_extraction_service import extract_clauses
```

### Add Your Own Policies

```bash
# Edit CSV files
vi "Supply Agreement Schema/policies_light.csv"
vi "Supply Agreement Schema/playbook_rules_light.csv"

# Recreate database
cd "Supply Agreement Schema"
rm ../legal_assistant.db
python3 setup_sqlite.py
cd ..
```

Or add via Python:

```python
import sqlite3

conn = sqlite3.connect('legal_assistant.db')
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO policies (policy_text, policy_category, severity_default)
    VALUES (?, ?, ?)
""", (
    "All SaaS contracts must include disaster recovery provisions",
    "business_continuity",
    "high"
))

conn.commit()
conn.close()
```

---

## 🔧 Integration Points

### 1. Clause Extraction Service

You mentioned having an existing clause extraction service. Integrate it:

```python
from your_extraction_service import extract_clauses

clauses = extract_clauses(contract_text)
# Returns: [{'clause_id': ..., 'clause_text': ..., 'clause_type': ...}, ...]
```

### 2. Document Parsing Service

You mentioned having a document parsing service. Use it to get contract text:

```python
from your_parsing_service import parse_document

contract_text = parse_document(file_path)
# Returns: Full text of contract
```

### 3. Policy Database

Load policies from your existing system:

```python
from your_policy_system import get_policies_for_matter

policies = get_policies_for_matter(matter_id="M-12345")
# Returns: [{'policy_id': ..., 'policy_text': ..., 'severity_default': ...}, ...]
```

### 4. Complete Integration Example

```python
from src.agents.workflow import analyze_contract
from your_extraction_service import extract_clauses
from your_parsing_service import parse_document
from your_policy_system import get_policies_for_matter

# Parse document
contract_text = parse_document("contract.pdf")

# Extract clauses
clauses = extract_clauses(contract_text)

# Load applicable policies
policies = get_policies_for_matter(matter_id="M-12345")

# Run analysis
result = await analyze_contract(
    version_id="v1",
    session_id="session-123",
    contract_text=contract_text,
    clauses=clauses,
    policies=policies,
    style_params={'tone': 'concise', 'audience': 'internal'}
)

# Use results
for edit in result['suggested_edits']:
    print(f"Edit: {edit['change_summary']}")
    print(f"Policy: {edit['policy_anchor']['policy_id']}")
```

---

## 🎯 Next Steps

### Phase 1: Get Demo Working (Today)
1. ✅ Install dependencies
2. ✅ Set API key
3. ✅ Run `python3 verify_setup.py`
4. ✅ Run `./run_demo.sh`
5. ✅ Review output

### Phase 2: Integrate Your Services (This Week)
1. Replace simulated clause extraction with your service
2. Connect to your policy database
3. Test with real contracts
4. Adjust style parameters for your use cases

### Phase 3: Production Features (Next)
1. **Accept/Reject Workflow** - UI for reviewing suggested edits
2. **Redline Export** - Generate Word docs with track changes
3. **Version Control** - Use full PostgreSQL schema for multi-round tracking
4. **Batch Processing** - Analyze multiple contracts in parallel
5. **Caching** - Set up Redis for personality transformation caching
6. **Background Tasks** - Use Celery for long-running analyses

---

## 📚 Architecture Highlights

### State Management
- **TypedDict** for type safety and IDE autocomplete
- **Immutable inputs** (contract text, clauses, policies)
- **Progressive enhancement** (each agent adds outputs)
- **Complete audit trail** (all intermediate results preserved)

### Agent Pipeline
```
Input → [Reviewer] → [Rationale] → [Personality] → [Editor] → Output
        adds findings  adds rationales  adds styled    adds edits
```

Each agent:
1. Reads from shared context
2. Processes its part
3. Writes results to context
4. Returns updated context

### Error Handling
- Agents log errors but don't halt workflow
- Failed items skipped gracefully
- Complete error log in final results
- Partial results still usable

### Caching Strategy
- Personality transformations cached by (rationale_id, style_params)
- Avoids redundant LLM calls
- Redis backend (optional, falls back to in-memory)

---

## 🐛 Troubleshooting

### "No module named 'anthropic'"
```bash
pip install anthropic langchain langchain-anthropic langgraph textblob pydantic pydantic-settings
```

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

### "Database not found"
```bash
cd "Supply Agreement Schema"
python3 setup_sqlite.py
cd ..
```

### Rate Limit Errors
- Wait a few minutes between runs
- Use a higher-tier API key
- Reduce number of clauses in sample contract

### Import Errors
Make sure you're in the project directory:
```bash
cd /Users/liz/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain
python3 verify_setup.py
```

---

## 💡 Tips

### Run Streaming Mode
See real-time updates as each agent completes:
```bash
./run_demo.sh --stream
```

### Check What Policies Apply
```python
from get_policies import get_policies_for_contract

# See all buy-side SaaS policies
policies = get_policies_for_contract(
    contract_type='saas',
    model_orientation='buy'
)

for p in policies:
    print(f"{p['severity_default']}: {p['policy_text']}")
```

### Test Different Styles
Try all combinations:
```python
for tone in ['concise', 'balanced', 'verbose']:
    for aggr in ['strict', 'balanced', 'flexible']:
        for aud in ['internal', 'counterparty']:
            result = await analyze_contract(
                ...,
                style_params={
                    'tone': tone,
                    'aggressiveness': aggr,
                    'audience': aud
                }
            )
            # Compare results
```

---

## 📖 Learn More

- **DEMO_README.md** - Detailed demo documentation
- **docs/AGENT_CONTEXT_MANAGEMENT.md** - State management design
- **CONTEXT_MANAGEMENT_SUMMARY.md** - Quick reference
- **docs/IMPLEMENTATION_GUIDE.md** - Full system documentation
- **PROJECT_STATUS.md** - Current implementation status

---

## ✅ Verification Checklist

Before running the demo, verify:

- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] Dependencies installed (`pip list | grep anthropic`)
- [ ] API key set (`echo $ANTHROPIC_API_KEY`)
- [ ] Database exists (`ls -lh legal_assistant.db`)
- [ ] All checks pass (`python3 verify_setup.py`)

**All green?** → Run `./run_demo.sh` 🚀

---

## 🎉 You're Ready!

Your contract analysis system is **complete and ready to use**. The demo will show you:

1. How all 4 agents work together
2. What kind of issues they find
3. How personality transformation works
4. What the output looks like

After seeing the demo, you'll know exactly how to integrate with your existing services!

**Questions?** Check the documentation files or run `python3 verify_setup.py` for diagnostics.

---

**Made with ❤️ using Claude Sonnet 4.5**
