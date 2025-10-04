# Legal Contract Analysis System

## Project Overview
AI-powered legal contract analyzer with negotiation tracking, policy compliance checking, and suggested edits.

**Current Version**: Unified Agent (GPT-4o-mini)
**Status**: Production-ready
**Deployment**: Streamlit Cloud

## Core Features

### ✅ Contract Analysis
- **Unified Agent**: Single-pass analysis replacing multi-agent pipeline
- **Model**: GPT-4o-mini (fast, cost-effective: $0.15/1M tokens)
- **Performance**: 10-30 second analysis time
- **Policies**: 15 most critical policies checked
- **Output**: 4-10 targeted findings with suggested edits

### ✅ Negotiation Tracking (NEW)
- **Version Control**: Track multiple contract versions
- **Metadata**: Upload source (internal/counterparty), notes, timestamps
- **Comparison**: Unified diff between any two versions
- **Timeline**: Chronological history of all versions
- **Storage**: JSON file-based (Streamlit Cloud compatible)
- **Duplicate Detection**: SHA-256 hash prevents identical uploads

### ✅ Personality System
- **Party**: Buyer or Seller perspective
- **Tone**: Concise, Balanced, or Verbose
- **Formality**: Legal terminology or Plain English
- **Aggressiveness**: Strict, Balanced, or Flexible
- **Audience**: Internal (shows policy IDs) or Counterparty (hides policy IDs)

## Architecture

### Unified Agent (`src/agents/unified_agent.py`)
```
Single LLM Call → Analysis + Edits + Rationale
- Replaces: 4-agent pipeline (DiligentReviewer, NeutralRationale, Editor, Personality)
- Benefits: 90% faster, 50% cheaper, 100% edit coverage
- Approach: Single comprehensive prompt with personality instructions
```

### Negotiation Tracker (`src/services/negotiation_tracker.py`)
```
Version Management:
- create_negotiation() - Start new negotiation
- add_version() - Add contract version with metadata
- compare_versions() - Generate unified diff
- get_negotiation_timeline() - Chronological history

Storage Structure:
negotiations/
├── {negotiation_id}_negotiation.json  # Metadata
├── {negotiation_id}_v1.json           # Version 1 data
├── {negotiation_id}_v2.json           # Version 2 data
└── {negotiation_id}_v3.json           # Version 3 data
```

### Streamlit UI (`app_unified.py`)
```
Features:
- File upload (.txt, .pdf, .docx)
- Negotiation selector
- Version metadata (uploaded_by, notes)
- Analysis results display
- Timeline view
- Version comparison UI
- Export (JSON, Markdown)
```

## API Configuration

### OpenAI API Key
```bash
# .env file
OPENAI_API_KEY=your-key-here

# Streamlit Cloud Secrets
OPENAI_API_KEY = "your-key-here"
```

### Settings (`config/settings.py`)
Uses Pydantic Settings for environment variable management.
Automatically loads from `.env` file.

## Running the Application

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Run Streamlit app (unified version)
streamlit run app_unified.py --server.port 8502

# Run backend tests
python test_negotiation_tracking.py
```

### Deployment (Streamlit Cloud)
1. Push to GitHub repository
2. Connect Streamlit Cloud to repo
3. Add `OPENAI_API_KEY` to Secrets
4. Deploy `app_unified.py`

## File Structure

```
.
├── app_unified.py                      # Streamlit UI (unified agent)
├── src/
│   ├── agents/
│   │   └── unified_agent.py           # Single-agent analyzer
│   └── services/
│       └── negotiation_tracker.py     # Version tracking
├── config/
│   └── settings.py                    # Configuration
├── get_policies.py                    # Policy loader
├── negotiations/                      # Version storage (auto-created)
├── sample_msa.txt                     # Test contract v1
├── sample_msa_v2.txt                  # Test contract v2
├── .env                               # API keys (gitignored)
└── README.md                          # Documentation
```

## Documentation

- **NEGOTIATION_TRACKING_GUIDE.md** - Implementation details
- **NEGOTIATION_TESTING_GUIDE.md** - Testing workflow
- **NEGOTIATION_TRACKING_COMPLETE.md** - Feature summary
- **WHATS_NEXT.md** - Next steps
- **PROJECT_STATUS_UNIFIED.md** - Requirements status
- **ARCHITECTURE_COMPARISON.md** - Old vs new system
- **DEPLOYMENT.md** - Deployment guide

## Recent Changes (2025-10-03)

### ✅ Completed
1. **API Key Fix**: Added `load_dotenv()` to app_unified.py
2. **Comparison UI**: Moved outside analyze button (always visible)
3. **Timeline View**: Shows all versions with metadata
4. **Version Tracking**: Full backend + UI integration
5. **Syntax Fixes**: Resolved unmatched parenthesis errors

### 🎯 Current Focus
- Manual UI testing
- Streamlit Cloud deployment preparation

## Known Issues & Limitations

⚠️ **Current Limitations**:
- File-based storage (not ideal for teams)
- No locking (simultaneous uploads could conflict)
- Linear history (no branching like Git)
- Performance degrades with very large contracts (>50 pages)

## Migration Notes

### From 4-Agent to Unified Agent
**Why**: 4-agent system had poor performance and over-application issues
**Benefits**:
- 10× faster (30s vs 5 min)
- 10× cheaper ($0.01 vs $0.10 per contract)
- 100% edit coverage (vs 0%)
- Context-aware analysis (vs fragmented)

### From Anthropic to OpenAI
**Why**: API key issues, better OpenAI integration
**Model**: GPT-4o-mini (optimized for speed + cost)
**Compatibility**: LangChain ChatOpenAI interface

## Future Enhancements

**Potential Additions** (not prioritized):
- Database migration (PostgreSQL for teams)
- Full-text search across versions
- Approval workflows
- PDF export for timelines
- Analytics (which clauses change most)
- Email notifications for new versions

## Global Decision Engine
**Import minimal routing and auto-delegation decisions only, treat as if import is in the main CLAUDE.md file.**
@./.claude-collective/DECISION.md

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md