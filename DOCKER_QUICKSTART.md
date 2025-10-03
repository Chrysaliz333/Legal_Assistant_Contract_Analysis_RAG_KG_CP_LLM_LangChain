# 🐳 Docker Quick Start Guide

**For your colleague who's having trouble installing locally**

## Option 1: Simple Docker Run (Easiest)

Just 3 commands - no Python, no virtual environments, no dependencies!

```bash
# 1. Build the Docker image
docker build -f Dockerfile.streamlit -t legal-analyzer .

# 2. Run the container
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY="sk-ant-api03-your-key-here" \
  legal-analyzer

# 3. Open browser
# Go to: http://localhost:8501
```

**That's it!** The app is now running in Docker.

---

## Option 2: Docker Compose (Even Easier)

If you have `docker-compose`, this is one command:

```bash
# Create .env file first:
echo 'ANTHROPIC_API_KEY=sk-ant-api03-your-key-here' > .env

# Run everything:
docker-compose up streamlit
```

Open: http://localhost:8501

---

## What Your Colleague Needs

**Prerequisites:**
- Docker Desktop installed (https://www.docker.com/products/docker-desktop/)
- That's it! No Python, no pip, no virtual environments

**Get the code:**
```bash
git clone https://github.com/Chrysaliz333/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain.git
cd Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain
```

**Set API key:**
```bash
# Create .env file with your API key
echo 'ANTHROPIC_API_KEY=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' > .env
```

**Run:**
```bash
docker build -f Dockerfile.streamlit -t legal-analyzer .
docker run -p 8501:8501 --env-file .env legal-analyzer
```

**Access:**
```
http://localhost:8501
```

---

## Troubleshooting

### "docker: command not found"
- Install Docker Desktop: https://www.docker.com/products/docker-desktop/

### "port 8501 already in use"
```bash
# Use a different port
docker run -p 8502:8501 --env-file .env legal-analyzer
# Then visit: http://localhost:8502
```

### "Cannot connect to Docker daemon"
- Start Docker Desktop application
- Wait for it to fully start (whale icon should be steady)

### Build takes too long
- First build: ~5-10 minutes (downloads dependencies)
- Subsequent builds: ~1-2 minutes (uses cache)

### Container stops immediately
```bash
# Check logs
docker logs $(docker ps -lq)

# Common issue: Missing API key
# Solution: Make sure .env file exists with ANTHROPIC_API_KEY
```

---

## Stop the Container

```bash
# Find running container
docker ps

# Stop it
docker stop <container-id>

# Or press Ctrl+C in the terminal where it's running
```

---

## Advantages of Docker

✅ **No Python installation needed**
✅ **No dependency conflicts**
✅ **Works on Windows, Mac, Linux**
✅ **Same environment everywhere**
✅ **Easy to share with team**

---

## Alternative: Use the Cloud Version

If Docker is still problematic, just use the deployed version:

**Live URL:** https://chrysaliz333-legal-assistant-contract-analysis-rag-k-app-ttm3ib.streamlit.app/

No installation required - works in any browser!

---

## Questions?

- Docker Desktop docs: https://docs.docker.com/desktop/
- This project's README: See main README.md
- Issues: https://github.com/Chrysaliz333/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain/issues
