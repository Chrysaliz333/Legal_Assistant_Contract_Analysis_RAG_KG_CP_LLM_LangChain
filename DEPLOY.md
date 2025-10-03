# 🚀 Deployment Guide - Streamlit Cloud

## Local Testing (Already Working!)

Your app is running locally at: **http://localhost:8501**

To stop it:
```bash
pkill -f streamlit
```

---

## Deploy to Streamlit Cloud (Free Public Hosting)

### Step 1: Push to GitHub

✅ **Already done!** Use GitHub Desktop to push your latest commit.

### Step 2: Sign up for Streamlit Cloud

1. Go to: **https://share.streamlit.io/**
2. Click **"Sign up with GitHub"**
3. Authorize Streamlit to access your repositories

### Step 3: Deploy Your App

1. Click **"New app"**
2. Select your repository: `Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain`
3. Branch: `main`
4. Main file path: `app.py`
5. Click **"Deploy!"**

### Step 4: Add Your API Key (IMPORTANT!)

Streamlit Cloud needs your Anthropic API key:

1. In your deployed app, click **"⚙️ Settings"** (top right)
2. Go to **"Secrets"** tab
3. Add this content:
   ```toml
   ANTHROPIC_API_KEY = "your-actual-api-key-here"
   ```
4. Click **"Save"**
5. App will automatically restart

### Step 5: Share Your App!

Your app will be live at:
```
https://share.streamlit.io/[your-username]/legal_assistant_contract_analysis_rag_kg_cp_llm_langchain/main/app.py
```

Or use the custom URL Streamlit provides.

---

## Environment Variables

The app needs these environment variables (set in Streamlit Cloud Secrets):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
DATABASE_URL = "sqlite:///legal_assistant.db"
SECRET_KEY = "your-secret-key"
```

---

## Deployment Checklist

- ✅ Code pushed to GitHub
- ✅ `requirements.txt` up to date
- ✅ `.streamlit/config.toml` configured
- ✅ `app.py` ready
- ✅ Database file included (`legal_assistant.db`)
- ⏳ Streamlit Cloud account created
- ⏳ API key added to Secrets
- ⏳ App deployed and running

---

## Troubleshooting

### "Module not found" errors
- Check `requirements.txt` includes all dependencies
- Streamlit Cloud installs from requirements.txt automatically

### "API key not found"
- Add `ANTHROPIC_API_KEY` to Streamlit Cloud Secrets
- Make sure you click "Save" in the Secrets panel

### App crashes on startup
- Check Streamlit Cloud logs (available in dashboard)
- Verify database file is included in repo

### Slow performance
- First run may be slow (installing dependencies)
- Subsequent runs are faster
- Consider using smaller model for extraction if needed

---

## Alternative: Deploy Locally with Docker

If you prefer private deployment:

```bash
# Build Docker image
docker build -t legal-analyzer .

# Run container
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your-key-here \
  legal-analyzer
```

Access at: http://localhost:8501

---

## Cost Considerations

**Streamlit Cloud (Free Tier):**
- ✅ 1 private app OR unlimited public apps
- ✅ 1GB RAM
- ✅ 800 hours/month uptime
- ⚠️ Sleeps after 7 days of inactivity

**API Costs:**
- Claude Haiku: ~$0.25 per million tokens (cheap!)
- Claude Sonnet 3.5: ~$3 per million tokens
- Average contract: ~$0.10-0.50 per analysis

**Recommendation:** Start with free Streamlit Cloud, upgrade if you need more resources.

---

## Security Notes

⚠️ **NEVER commit API keys to Git!**
- Keys go in Streamlit Cloud Secrets only
- `.env` is gitignored
- `.streamlit/secrets.toml` is gitignored

✅ **Database security:**
- Database is read-only in the app
- No user data is stored
- All analysis is ephemeral

---

## Support

Questions? Check:
- Streamlit Docs: https://docs.streamlit.io/
- Streamlit Community: https://discuss.streamlit.io/
- Anthropic Docs: https://docs.anthropic.com/

Enjoy your deployed contract analyzer! 🎉
