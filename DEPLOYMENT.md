# Deployment Guide - Unified Agent to Streamlit Cloud

## Option 1: Update Existing Deployment (Recommended)

If you already have the app deployed, update it to use the unified agent:

### Step 1: Update Streamlit Cloud Settings

1. Go to your Streamlit Cloud dashboard
2. Click on your app settings (⚙️)
3. Under "Main file path", change from `app.py` to `app_unified.py`
4. Click "Save"

### Step 2: Add OpenAI API Key to Secrets

1. In app settings, go to "Secrets"
2. Add your OpenAI API key:

```toml
OPENAI_API_KEY = "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"
```

3. Click "Save"

### Step 3: Reboot the App

The app will automatically redeploy with the changes.

---

## Option 2: Replace app.py (Alternative)

If you prefer to keep the same filename:

### Step 1: Backup and Replace

```bash
# Backup old app
mv app.py app_old_multiagent.py

# Rename unified app
mv app_unified.py app.py
```

### Step 2: Commit and Push

```bash
git add app.py app_old_multiagent.py
git commit -m "Switch to unified agent for better performance"
git push
```

### Step 3: Add OpenAI Key (Same as Option 1, Step 2)

---

## What Will Work on Streamlit Cloud

✅ **Will Work:**
- Unified agent analysis
- Policy checking (from database)
- Contract upload (.txt, .pdf, .docx)
- Style parameters (tone, formality, aggressiveness, audience)
- Party selector (buyer/seller)
- Results display with track-change edits
- JSON/Markdown export

✅ **Performance:**
- ~10-30 seconds per contract (vs 60+ seconds with old multi-agent)
- Uses GPT-4o-mini ($0.15/1M tokens)
- Limited to 15 policies to prevent timeouts

⚠️ **Known Limitations:**
- Database file (`legal_assistant.db`) must be committed to repo
- No Redis caching on Streamlit Cloud (gracefully disabled)
- Large contracts (>10 pages) may timeout - truncate if needed

---

## Verification Steps

After deployment:

1. **Check Logs**: Go to "Manage app" → "Logs" to see if there are any errors
2. **Test Upload**: Upload `sample_msa.txt` to verify it works
3. **Test Audience**: Try both "internal" and "counterparty" modes
   - Internal should show policy IDs (e.g., "Policy LP-401")
   - Counterparty should hide policy IDs (e.g., "Our standard requirement")

---

## Rollback Plan

If something goes wrong, you can quickly rollback:

### Option 1 Users:
Change "Main file path" back to `app.py` in settings

### Option 2 Users:
```bash
mv app.py app_unified.py
mv app_old_multiagent.py app.py
git add app.py app_unified.py
git commit -m "Rollback to multi-agent"
git push
```

---

## Cost Estimate

**Old Multi-Agent System:**
- 56 findings × 4 agents = 224 API calls per contract
- ~$0.10 - $0.30 per contract
- 30-60 seconds processing time

**New Unified Agent:**
- 1 API call per contract
- ~$0.01 - $0.03 per contract (10× cheaper)
- 10-30 seconds processing time (2-3× faster)

---

## Troubleshooting

### Issue: "OPENAI_API_KEY not found"
**Solution**: Add the key to Streamlit Secrets (see Step 2 above)

### Issue: "Request timed out"
**Solution**: Contract is too large. The app limits to 15 policies for performance.
- Try with a smaller contract first
- Or reduce policy count in `app_unified.py` line 130 (change `[:15]` to `[:10]`)

### Issue: "No module named 'src.agents.unified_agent'"
**Solution**: Make sure `src/agents/unified_agent.py` is committed to your repo

### Issue: Database not found
**Solution**: Make sure `legal_assistant.db` is committed to git

---

## Next Steps

After successful deployment:

1. **Remove old agents** (optional cleanup):
   ```bash
   mkdir archive
   mv src/agents/diligent_reviewer.py archive/
   mv src/agents/neutral_rationale.py archive/
   mv src/agents/personality.py archive/
   mv src/agents/editor.py archive/
   ```

2. **Update README** with new architecture info

3. **Test with real contracts** from your workflow

4. **Gather user feedback** on the personality settings
