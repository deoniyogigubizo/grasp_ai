"""
GRASP AI - Advanced Chat Backend
Features:
 - Sentiment Analysis (detects frustration/urgency → escalation)
 - Multilingual (auto-detects + responds in user's language)
 - RAG (upload your own knowledge base .txt files)
 - Conversation Memory (full history per session)
 - Analytics (tracks message count, sentiments)
 - Human Handoff trigger
"""

from flask import Flask, request, jsonify, send_from_directory
import anthropic
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder=".")
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── In-memory stores ──────────────────────────────────────────────
sessions = {}
knowledge_base = []

KNOWLEDGE_DIR = Path("knowledge")
KNOWLEDGE_DIR.mkdir(exist_ok=True)

# ── Load knowledge base ───────────────────────────────────────────
def load_knowledge_base():
    global knowledge_base
    knowledge_base = []
    for f in KNOWLEDGE_DIR.glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        words = text.split()
        chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 250)]
        for chunk in chunks:
            knowledge_base.append({"source": f.name, "content": chunk})
    print(f"📚 Loaded {len(knowledge_base)} knowledge chunks")

load_knowledge_base()

# ── RAG retrieval ─────────────────────────────────────────────────
def retrieve_context(query: str, top_k=3) -> str:
    if not knowledge_base:
        return ""
    query_words = set(query.lower().split())
    scored = sorted(knowledge_base, key=lambda c: len(query_words & set(c["content"].lower().split())), reverse=True)
    top = [c for c in scored[:top_k] if len(query_words & set(c["content"].lower().split())) > 0]
    if not top:
        return ""
    return "\n\n".join([f"[From {c['source']}]\n{c['content']}" for c in top])

# ── Sentiment Analysis ────────────────────────────────────────────
def analyze_sentiment(text: str) -> dict:
    t = text.lower()
    frustration = sum(1 for w in ["angry","frustrated","terrible","awful","horrible","hate","worst","broken","not working","doesn't work"] if w in t)
    happy = sum(1 for w in ["thanks","thank you","great","awesome","perfect","love","amazing","excellent"] if w in t)
    urgency = sum(1 for w in ["urgent","asap","emergency","critical","immediately","right now"] if w in t)

    if urgency >= 1 or frustration >= 2:
        sentiment, emoji = "urgent", "🔴"
    elif frustration >= 1:
        sentiment, emoji = "frustrated", "🟠"
    elif happy >= 1:
        sentiment, emoji = "positive", "🟢"
    else:
        sentiment, emoji = "neutral", "⚪"

    return {
        "sentiment": sentiment,
        "emoji": emoji,
        "needs_handoff": frustration >= 3 or urgency >= 2
    }

# ── Session management ────────────────────────────────────────────
def get_session(sid: str) -> dict:
    if sid not in sessions:
        sessions[sid] = {
            "history": [],
            "analytics": {
                "message_count": 0,
                "session_start": datetime.now().isoformat(),
                "sentiments": [],
                "handoff_triggered": False
            }
        }
    return sessions[sid]

# ── System prompt ─────────────────────────────────────────────────
def build_system_prompt(sentiment: dict, rag_context: str) -> str:
    prompt = """You are GRASP AI — a sophisticated, empathetic, highly capable AI assistant.

RULES:
- Always respond in the SAME LANGUAGE the user writes in. If they write French, reply French. Swahili → Swahili. Always mirror their language.
- Understand intent even with typos, slang, or broken grammar
- Use bullet points, numbered lists, or code blocks when helpful
- Be concise but thorough"""

    if sentiment["sentiment"] == "urgent":
        prompt += "\n\n⚠️ USER IS URGENT: Be fast and direct. Get to the solution immediately."
    elif sentiment["sentiment"] == "frustrated":
        prompt += "\n\n⚠️ USER IS FRUSTRATED: Acknowledge their frustration warmly first, then solve their problem."
    elif sentiment["sentiment"] == "positive":
        prompt += "\n\nUser is happy. Match their positive energy."

    if sentiment["needs_handoff"]:
        prompt += "\n\n🚨 HIGH DISTRESS: End your response with: '--- Would you like to speak with a human agent? Type HUMAN to escalate. ---'"

    if rag_context:
        prompt += f"\n\nINTERNAL KNOWLEDGE BASE (use if relevant):\n{rag_context}"

    return prompt

# ── Routes ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if user_message.strip().upper() == "HUMAN":
        return jsonify({
            "reply": "🔄 **Escalating to human agent...**\n\nYour conversation history has been preserved. A human agent will join shortly.\n\n*(In production: this triggers a Slack/email alert to your support team)*",
            "sentiment": {"sentiment": "handoff", "emoji": "👤"},
            "handoff": True
        })

    session = get_session(session_id)
    sentiment = analyze_sentiment(user_message)
    rag_context = retrieve_context(user_message)
    system_prompt = build_system_prompt(sentiment, rag_context)

    session["analytics"]["message_count"] += 1
    session["analytics"]["sentiments"].append(sentiment["sentiment"])
    if sentiment["needs_handoff"]:
        session["analytics"]["handoff_triggered"] = True

    session["history"].append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=session["history"]
    )

    reply = response.content[0].text
    session["history"].append({"role": "assistant", "content": reply})

    return jsonify({
        "reply": reply,
        "sentiment": sentiment,
        "rag_used": bool(rag_context),
        "analytics": session["analytics"]
    })

@app.route("/reset", methods=["POST"])
def reset():
    sid = request.json.get("session_id", "default")
    if sid in sessions:
        del sessions[sid]
    return jsonify({"status": "cleared"})

@app.route("/analytics")
def analytics():
    sid = request.args.get("session_id", "default")
    session = get_session(sid)
    a = session["analytics"]
    sentiments = a["sentiments"]
    return jsonify({
        "message_count": a["message_count"],
        "session_start": a["session_start"],
        "sentiment_breakdown": {s: sentiments.count(s) for s in set(sentiments)},
        "handoff_triggered": a["handoff_triggered"],
        "knowledge_chunks": len(knowledge_base)
    })

@app.route("/upload-knowledge", methods=["POST"])
def upload_knowledge():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f.filename.endswith(".txt"):
        return jsonify({"error": "Only .txt files supported"}), 400
    f.save(KNOWLEDGE_DIR / f.filename)
    load_knowledge_base()
    return jsonify({"status": "uploaded", "chunks": len(knowledge_base), "file": f.filename})

@app.route("/knowledge-status")
def knowledge_status():
    return jsonify({
        "files": [f.name for f in KNOWLEDGE_DIR.glob("*.txt")],
        "total_chunks": len(knowledge_base)
    })

if __name__ == "__main__":
    print("🚀 GRASP AI running → http://localhost:5000")
    app.run(debug=True, port=5000)
