# Contract Analysis Workflow Demo

Complete end-to-end demonstration of the 4-agent contract analysis pipeline.

## Quick Start

```bash
# 1. Set your Anthropic API key
export ANTHROPIC_API_KEY='your-key-here'

# 2. Run the demo
./run_demo.sh
```

## What This Demo Shows

### The Complete Pipeline

```
Sample SaaS Contract (6 clauses)
    ↓
[Diligent Reviewer Agent]
    → Checks 6 clauses against 5 policies
    → Finds policy deviations
    → Assigns severity (critical/high/medium/low)
    ↓
[Neutral Rationale Agent]
    → Generates objective, evidence-based explanations
    → Proposes specific changes
    → Validates neutrality (no tone/bias)
    ↓
[Personality Agent]
    → Transforms neutral text based on style settings
    → Applies: tone + formality + aggressiveness + audience
    → Caches transformations for reuse
    ↓
[Editor Agent]
    → Creates track-change format edits
    → Detects conflicts between overlapping edits
    → Anchors each edit to policy requirement
    ↓
Suggested Edits Ready for Review
```

## Demo Features

### 1. Sample Contract
- Realistic SaaS agreement with 6 clauses
- Contains intentional policy violations:
  - ❌ SLA below 99.9% requirement
  - ❌ Liability cap at 1× (policy requires 2×)
  - ❌ Missing Data Processing Addendum
  - ❌ Wrong governing law (Delaware instead of England & Wales)
  - ❌ Payment terms 60 days (policy requires 30 days)

### 2. Policy Database
- **3 general policies** (apply to all contracts)
- **6 playbook rules** (contract-type specific)
- **Buy-side vs Sell-side** filtering

### 3. Style Configurations

The demo uses **strict internal style**:
```python
style_params = {
    'tone': 'concise',           # Brief, direct
    'formality': 'legal',        # Legal terminology
    'aggressiveness': 'strict',  # Non-negotiable language
    'audience': 'internal'       # Internal legal team
}
```

Try different combinations:
- **Counterparty communication**: `{'tone': 'balanced', 'aggressiveness': 'flexible', 'audience': 'counterparty'}`
- **Verbose internal**: `{'tone': 'verbose', 'formality': 'legal', 'audience': 'internal'}`
- **Plain English**: `{'tone': 'concise', 'formality': 'plain_english', 'audience': 'counterparty'}`

### 4. Output Examples

**Neutral Rationale** (no tone):
> "This clause caps liability at 1× annual fees, which differs from Policy LP-401 requiring 2× minimum for vendor contracts."

**Styled (concise + strict + internal)**:
> "LoL cap at 1× must be revised to 2× per LP-401. Non-negotiable."

**Styled (verbose + flexible + counterparty)**:
> "The liability limitation is currently set at 1× annual fees. Our standard requirement for vendor agreements is 2× annual fees to ensure adequate risk coverage. We'd like to discuss increasing this cap to align with our standard terms."

## Running the Demo

### Standard Mode
Shows complete results after all agents finish:
```bash
./run_demo.sh
```

### Streaming Mode
Real-time updates as each agent completes:
```bash
./run_demo.sh --stream
```

### Direct Python Execution
```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 demo_workflow.py

# Or streaming:
python3 demo_workflow.py --stream
```

## Demo Output

The demo shows:

1. **📋 Policy Loading**
   - Lists all applicable policies and playbook rules
   - Shows buy-side vs sell-side filtering

2. **📄 Clause Extraction**
   - Displays 6 extracted clauses
   - Shows clause types and positions

3. **🤖 Agent Pipeline**
   - Runs all 4 agents in sequence
   - Shows execution time (~30-60 seconds)

4. **📊 Results Summary**
   - Statistics by severity
   - Total findings, rationales, edits
   - Conflict detection

5. **🔍 Detailed Findings**
   - Each policy deviation with evidence
   - Severity classification
   - Policy references

6. **📝 Neutral Rationales**
   - Objective explanations
   - Proposed changes
   - Fallback options

7. **🎨 Styled Transformations**
   - Personality-adjusted output
   - Shows effect of style parameters

8. **✏️ Suggested Edits**
   - Track-change format (deletions/insertions)
   - Character positions for programmatic editing
   - Policy anchors
   - Conflict warnings

9. **🔀 Comparison**
   - Side-by-side neutral vs styled output
   - Demonstrates personality transformation

## Expected Issues Found

The demo should find approximately **5-6 policy deviations**:

1. **[HIGH]** SLA below 99.9% (99.5% vs required 99.9%)
2. **[HIGH]** Liability cap too low (1× vs required 2×)
3. **[CRITICAL]** Missing Data Processing Addendum
4. **[MEDIUM]** Wrong governing law (Delaware vs England & Wales)
5. **[MEDIUM]** Payment terms too long (60 days vs 30 days)
6. **[HIGH]** IP indemnity missing duty to defend

## Customization

### Use Your Own Contract

Edit `demo_workflow.py`:
```python
SAMPLE_CONTRACT = """
Your contract text here...
"""
```

### Integrate Your Clause Extraction

Replace the simulated extraction:
```python
# Replace this:
def extract_clauses(contract_text):
    # Simulated...

# With your actual service:
from your_extraction_service import extract_clauses
```

### Change Style Settings

Modify `style_params` in the demo:
```python
style_params = {
    'tone': 'verbose',           # concise | balanced | verbose
    'formality': 'plain_english', # legal | plain_english
    'aggressiveness': 'flexible', # strict | balanced | flexible
    'audience': 'counterparty'   # internal | counterparty
}
```

### Filter Policies by Contract Type

```python
# Get policies for different contract types
msa_policies = get_policies_for_contract(
    contract_type='msa',
    model_orientation='sell'
)
```

## Files Involved

### Core Agents
- `src/agents/diligent_reviewer.py` - Policy compliance checking
- `src/agents/neutral_rationale.py` - Objective explanation generation
- `src/agents/personality.py` - Style transformation
- `src/agents/editor.py` - Track-change edit creation

### Orchestration
- `src/agents/workflow.py` - LangGraph workflow coordinator
- `src/agents/state.py` - Shared state management

### Data & Config
- `legal_assistant.db` - SQLite database with policies
- `get_policies.py` - Policy loading helper
- `config/settings.py` - Configuration management

### Demo
- `demo_workflow.py` - This demo script
- `run_demo.sh` - Setup and execution script

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### "No module named 'anthropic'"
```bash
pip install anthropic langchain langchain-anthropic langgraph textblob
```

### "legal_assistant.db not found"
```bash
cd "Supply Agreement Schema"
python3 setup_sqlite.py
cd ..
```

### API Rate Limits
The demo makes ~15-20 API calls. If you hit rate limits:
- Wait a few minutes
- Use a higher-tier API key
- Reduce the number of clauses in the sample contract

## Next Steps

After running the demo:

1. **Integrate your clause extraction service**
   - Replace simulated `extract_clauses()` with your actual service

2. **Connect to your policy database**
   - Import policies from your existing system
   - Add contract-specific playbook rules

3. **Customize personality settings**
   - Create presets for different use cases
   - "Strict internal review" vs "Collaborative negotiation"

4. **Implement accept/reject workflow**
   - UI for reviewing suggested edits
   - Track which edits were accepted/rejected

5. **Add redline export**
   - Generate Word documents with track changes
   - Export to PDF with annotations

6. **Set up version tracking**
   - Store analysis results in database
   - Track changes across negotiation rounds

## Performance Notes

- **Analysis time**: ~30-60 seconds for 6 clauses
- **API calls**: ~15-20 calls (varies by findings)
- **Caching**: Personality transformations are cached in Redis (if available)
- **Parallel processing**: Agents run sequentially (can be parallelized in future)

## Architecture Highlights

### State Management
- TypedDict-based shared context
- Each agent reads inputs, writes outputs
- Immutable history (append-only)

### Error Handling
- Agents log errors but don't halt workflow
- Graceful degradation (skip failed items)
- Complete error log in results

### Observability
- Track current agent and stage
- Timestamps for each step
- Detailed statistics from each agent

### Caching Strategy
- Personality transformations cached by (rationale_id, style_params)
- Avoids redundant LLM calls for same content
- Redis backend (falls back to in-memory if unavailable)

---

**Ready to run?**

```bash
export ANTHROPIC_API_KEY='your-key-here'
./run_demo.sh
```

Enjoy! 🚀
