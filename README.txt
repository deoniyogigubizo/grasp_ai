# GRASP AI - Setup Guide
|removed something
## Install dependencies
pip install flask anthropic

## Set your API key
# Windows:
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Mac/Linux:
# export ANTHROPIC_API_KEY=your-key-here

## Run the app
python app.py

## Open in browser
http://localhost:5000

---

## Features Configured

### ✅ Sentiment Analysis
- Auto-detects frustrated / urgent / positive / neutral tone
- Adjusts AI response style based on mood
- Triggers human handoff prompt at high distress

### ✅ Multilingual
- Automatically detects user's language
- Replies in the same language (French, Swahili, Arabic, etc.)
- No configuration needed

### ✅ RAG (Knowledge Base)
- Drop any .txt file into the /knowledge/ folder
- OR upload via the Analytics panel in the UI
- AI will use your documents to answer questions

### ✅ Human Handoff
- Type "HUMAN" at any time to trigger escalation
- Full conversation history preserved
- In production: connect to Slack/email/Zendesk webhook

### ✅ Analytics Dashboard
- Click "📊 Analytics" in header
- See message count, sentiment breakdown, KB status

### ✅ 24/7 Availability
- No session timeout - runs as long as server is up
- For production: deploy to Railway, Render, or AWS

---

## Adding Your Own Knowledge Base

1. Create a .txt file with your company FAQs, product info, etc.
2. Drop it in the /knowledge/ folder
3. Restart the server OR upload via the UI panel
4. GRASP AI will now answer from your documents

## Production Deployment (optional)

Deploy to Railway.app (free tier):
1. Push code to GitHub
2. Connect repo to Railway
3. Set ANTHROPIC_API_KEY as environment variable
4. Done — public URL provided automatically
# Project Updated
