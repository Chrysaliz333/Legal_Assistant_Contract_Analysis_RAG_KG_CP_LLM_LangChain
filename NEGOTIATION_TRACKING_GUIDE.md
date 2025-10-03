# Negotiation Tracking - Implementation Guide

## What's Been Built

✅ **Backend Complete**: `src/services/negotiation_tracker.py`
- Store multiple versions of same contract
- Compare any two versions with unified diff
- Track timeline of uploads (internal vs counterparty)
- Detect duplicate uploads (SHA-256 hash)
- JSON storage (no database needed)

✅ **Tested**: `test_negotiation_tracking.py`
- Version comparison working
- Timeline tracking working
- Diff generation working

## How It Works

### 1. Create a Negotiation

```python
from src.services.negotiation_tracker import NegotiationTracker

tracker = NegotiationTracker()
tracker.create_negotiation("acme_saas", "Acme Corp SaaS Agreement")
```

### 2. Add Versions

```python
# Version 1 (initial draft)
v1 = tracker.add_version(
    "acme_saas",
    contract_text="...",
    uploaded_by='internal',
    notes='Initial draft'
)

# Version 2 (counterparty response)
v2 = tracker.add_version(
    "acme_saas",
    contract_text="...",
    uploaded_by='counterparty',
    notes='Counterparty increased liability cap'
)
```

### 3. Compare Versions

```python
comparison = tracker.compare_versions(v1.version_id, v2.version_id)

print(f"Additions: {comparison['summary']['additions']}")
print(f"Deletions: {comparison['summary']['deletions']}")
print(comparison['diff_unified'])  # Unified diff format
```

### 4. View Timeline

```python
timeline = tracker.get_negotiation_timeline("acme_saas")

for entry in timeline:
    print(f"Version {entry['version_number']} ({entry['uploaded_by']})")
```

## Data Storage

Files are stored in `negotiations/` directory:

```
negotiations/
├── acme_saas_negotiation.json    # Negotiation metadata
├── acme_saas_v1.json             # Version 1 data
├── acme_saas_v2.json             # Version 2 data
└── acme_saas_v3.json             # Version 3 data
```

Each version file contains:
- `version_id`: Unique identifier
- `contract_text`: Full contract text
- `uploaded_at`: Timestamp
- `uploaded_by`: 'internal' or 'counterparty'
- `file_hash`: SHA-256 hash (for duplicate detection)
- `analysis_result`: Optional analysis from unified agent
- `notes`: Optional notes about this version

## Streamlit Integration (Partial - In Progress)

### What's Already Added to `app_unified.py`:

1. ✅ Import: `from src.services.negotiation_tracker import NegotiationTracker`
2. ✅ Session state initialization
3. ✅ Negotiation selector in sidebar (partially complete)

### What Still Needs to Be Done:

1. **Update analysis function** to save versions:
   ```python
   async def analyze_contract_async(contract_text, style_params, negotiation_id, uploaded_by, notes):
       # Run analysis
       result = await agent.analyze_contract(...)

       # Save version
       tracker.add_version(
           negotiation_id,
           contract_text,
           uploaded_by=uploaded_by,
           notes=notes,
           analysis_result=result
       )

       return result
   ```

2. **Add version timeline view** after results:
   ```python
   if st.session_state.current_negotiation_id:
       timeline = tracker.get_negotiation_timeline(st.session_state.current_negotiation_id)

       st.markdown("## 📋 Negotiation Timeline")
       for entry in timeline:
           with st.expander(f"Version {entry['version_number']} - {entry['uploaded_by']}"):
               st.write(f"Uploaded: {entry['uploaded_at']}")
               st.write(f"Notes: {entry.get('notes', 'None')}")

               if entry.get('analysis_summary'):
                   st.metric("Findings", entry['analysis_summary']['total_findings'])
   ```

3. **Add version comparison UI**:
   ```python
   st.markdown("## 🔀 Compare Versions")

   versions = [f"Version {e['version_number']}" for e in timeline]

   col1, col2 = st.columns(2)
   with col1:
       v1_selection = st.selectbox("Base Version", versions)
   with col2:
       v2_selection = st.selectbox("Compare To", versions)

   if st.button("Compare"):
       v1_id = timeline[int(v1_selection.split()[1]) - 1]['version_id']
       v2_id = timeline[int(v2_selection.split()[1]) - 1]['version_id']

       comparison = tracker.compare_versions(v1_id, v2_id)

       st.code(comparison['diff_unified'], language='diff')
   ```

4. **Add uploaded_by selector** when uploading:
   ```python
   uploaded_by = st.radio("This version is from:", ['internal', 'counterparty'])
   notes = st.text_input("Notes (optional)", value="")
   ```

## Example Workflow

### Round 1: Initial Upload
```
User Action:
1. Upload contract v1
2. Select "This is from: Internal"
3. Add note: "Initial draft from legal team"
4. Click "Analyze"

System:
1. Creates negotiation (if new)
2. Runs analysis
3. Saves as Version 1
4. Shows results + timeline (1 version)
```

### Round 2: Counterparty Response
```
User Action:
1. Same negotiation selected in sidebar
2. Upload contract v2
3. Select "This is from: Counterparty"
4. Add note: "Increased liability cap to 1.5×"
5. Click "Analyze"

System:
1. Runs analysis
2. Saves as Version 2
3. Shows results + timeline (2 versions)
4. Auto-displays diff: v1 → v2
```

### Round 3: Compare Versions
```
User Action:
1. Click "Compare Versions" tab
2. Select "Version 1" vs "Version 3"
3. View diff

System:
1. Loads both versions
2. Generates unified diff
3. Highlights changes:
   - Green: Additions
   - Red: Deletions
```

## Features Built But Not Yet in UI

✅ **Duplicate Detection**:
- If you upload identical text, system will warn you
- Uses SHA-256 hash comparison

✅ **Timeline Tracking**:
- Full chronological history
- Metadata for each version
- Analysis summaries

✅ **Flexible Comparison**:
- Compare any two versions (not just sequential)
- Unified diff format (standard)
- Change statistics (additions/deletions count)

## Next Steps to Complete Integration

1. **Finish Streamlit UI updates** (30 min):
   - Connect upload form to version saver
   - Add timeline view
   - Add comparison UI

2. **Test full workflow** (15 min):
   - Upload v1 → analyze → check timeline
   - Upload v2 → analyze → check timeline
   - Compare v1 vs v2

3. **Deploy** (5 min):
   - Commit changes
   - Push to Streamlit Cloud
   - Test cloud version

## File Locations

- Backend: `src/services/negotiation_tracker.py`
- Streamlit App: `app_unified.py`
- Test Script: `test_negotiation_tracking.py`
- Storage: `negotiations/` (auto-created)

## Benefits

✅ **No Database Required**: Uses JSON files
✅ **Simple API**: Easy to integrate
✅ **Git-Like Versioning**: Track every change
✅ **Duplicate Prevention**: SHA-256 hashing
✅ **Streamlit Compatible**: Works in session state
✅ **Cloud Deployable**: Files work on Streamlit Cloud

## Known Limitations

⚠️ **File-Based Storage**: Not ideal for teams (use database for multi-user)
⚠️ **No Locking**: Two simultaneous uploads could conflict
⚠️ **Linear History**: No branching (unlike Git)

For enterprise use, consider migrating to PostgreSQL or similar database.

## Testing

Run the test script:
```bash
python test_negotiation_tracking.py
```

Expected output:
- ✅ Created negotiation
- ✅ Added Version 1
- ✅ Added Version 2
- ✅ Comparison shows diff
- ✅ Timeline shows both versions
- ✅ Files saved in `negotiations/`
