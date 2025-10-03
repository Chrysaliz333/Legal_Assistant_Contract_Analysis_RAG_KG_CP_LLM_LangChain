# Quick Reference Card

## 🚀 Run the Demo (3 Commands)

```bash
pip install anthropic langchain langchain-anthropic langgraph textblob pydantic pydantic-settings
export ANTHROPIC_API_KEY='your-key-here'
./run_demo.sh
```

---

## 📁 File Locations

| What | Where |
|------|-------|
| **Agents** | `src/agents/*.py` |
| **Workflow** | `src/agents/workflow.py` |
| **Database** | `legal_assistant.db` |
| **Policies** | `get_policies.py` |
| **Demo** | `demo_workflow.py` |
| **Verify** | `verify_setup.py` |

---

## 🤖 Agent Pipeline

```
Contract → [Reviewer] → [Rationale] → [Personality] → [Editor] → Edits
           finds issues  explains      styles text    creates changes
```

---

## 💻 Basic Usage

```python
from src.agents.workflow import analyze_contract
from get_policies import get_policies_for_contract

# Load policies
policies = get_policies_for_contract(
    contract_type='saas',
    model_orientation='buy'
)

# Analyze contract
result = await analyze_contract(
    version_id="v1",
    session_id="s1",
    contract_text="...",
    clauses=[...],
    policies=policies,
    style_params={'tone': 'concise', 'audience': 'internal'}
)

# Use results
print(f"Found {len(result['findings'])} issues")
for edit in result['suggested_edits']:
    print(edit['change_summary'])
```

---

## 🎨 Style Options

```python
style_params = {
    'tone': 'concise',           # concise | balanced | verbose
    'formality': 'legal',        # legal | plain_english
    'aggressiveness': 'strict',  # strict | balanced | flexible
    'audience': 'internal'       # internal | counterparty
}
```

### Common Presets

| Preset | Settings |
|--------|----------|
| **Strict Internal** | `concise + legal + strict + internal` |
| **Collaborative** | `balanced + plain_english + flexible + counterparty` |
| **Executive** | `verbose + plain_english + balanced + internal` |

---

## 📊 Output Structure

```python
result = {
    'findings': [...],                # From Diligent Reviewer
    'neutral_rationales': [...],      # From Neutral Rationale
    'transformed_rationales': [...],  # From Personality
    'suggested_edits': [...],         # From Editor
    'analysis_summary': {
        'total_findings': 5,
        'critical_count': 1,
        'high_count': 2
    }
}
```

---

## 🔧 Integration Points

### Your Clause Extraction
```python
from your_extraction_service import extract_clauses

clauses = extract_clauses(contract_text)
# Pass to analyze_contract(clauses=clauses)
```

### Your Document Parsing
```python
from your_parsing_service import parse_document

contract_text = parse_document("contract.pdf")
# Pass to analyze_contract(contract_text=contract_text)
```

### Your Policy System
```python
from your_policy_system import get_policies

policies = get_policies(matter_id="M-123")
# Pass to analyze_contract(policies=policies)
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `GETTING_STARTED.md` | ⭐ **Start here** |
| `DEMO_README.md` | Demo details |
| `WHAT_WE_BUILT.md` | System overview |
| `docs/IMPLEMENTATION_GUIDE.md` | Technical docs |

---

## 🐛 Troubleshooting

```bash
# Verify setup
python3 verify_setup.py

# Check database
ls -lh legal_assistant.db

# Test policy loading
python3 get_policies.py

# View sample contract
cat demo_workflow.py | grep -A 50 "SAMPLE_CONTRACT"
```

---

## 💡 Quick Tips

1. **Run streaming mode**: `./run_demo.sh --stream`
2. **See all policies**: `python3 get_policies.py`
3. **Verify before running**: `python3 verify_setup.py`
4. **Check database**: `sqlite3 legal_assistant.db "SELECT * FROM policies;"`

---

## 🎯 Next Steps

1. ✅ Run demo → see how it works
2. ✅ Integrate your clause extraction
3. ✅ Connect your policy database
4. ✅ Test with real contracts
5. ✅ Deploy to production

---

**Need help?** Check `GETTING_STARTED.md` or run `python3 verify_setup.py`
