# At the top with your other imports
import logging
from tracer import new_trace, get_trace_id

logger = logging.getLogger("app")
import os, re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# ── Startup sequence (order matters) ────────────────────────────
from logging_setup import setup_logging
setup_logging()

from database import init_db, clear_conv_history, save_conv_turn
from database import is_pending_reset, set_pending_reset, touch_last_active

from scheduler import scheduler, register_jobs
from logging_setup import get_all_logs, get_recent_logs

# ── AI ───────────────────────────────────────────────────────────
from ai.classifier import classify_intent
from ai.chat       import ai_chat
from ai.brainstorm import ai_brainstorm

# ── Features ────────────────────────────────────────────────────
from features.reminders import parse_reminder_with_ai, save_reminder, get_reminders_list, delete_reminder
from features.notes     import save_note,  get_notes,  delete_note,  edit_note
from features.ideas     import save_idea,  get_ideas,  delete_idea,  edit_idea
from features.tasks     import save_task,  get_tasks,  complete_task, delete_task, edit_task
from features.calendar  import (
    parse_event_with_ai, parse_date_from_message,
    save_event, get_events, delete_event, edit_event,
)
from features.news    import get_news
from features.quotes  import generate_daily_quote
from features.budget  import calculate_budget
from features.memory  import semantic_search

# ── Flask app ────────────────────────────────────────────────────
app = Flask(__name__)
@app.after_request
def log_response(response):
    logger.info(f"[{get_trace_id()}] ◀ RESPONSE: HTTP {response.status_code}")
    return response
# ── DB + Scheduler ───────────────────────────────────────────────
init_db()
register_jobs()
scheduler.start()

# ── tracer log ───────────────────────────────────────────────
from tracer import new_trace, trace, logger, get_trace_id


# ================================================================
# WEBHOOK
# ================================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    tid = new_trace()
    incoming = request.form.get("Body", "").strip()
    lower = incoming.lower()
    resp = MessagingResponse()
    msg = resp.message()

    # Pending reset confirmation (keep this)
    if is_pending_reset():
        set_pending_reset(False)
        touch_last_active()
        yes_words = {"yes", "ya", "reset", "clear", "iya", "ok", "okay", "sure"}
        if any(w in lower for w in yes_words):
            clear_conv_history()
            msg.body("🔄 Session reset! Fresh start — what's on your mind?")
        else:
            msg.body("👍 Continuing your previous session. What's up?")
        return str(resp)

    touch_last_active()

    # Logs shortcut (keep this)
    if lower.startswith("/logs"):
        import re
        n = 20
        nums = re.findall(r"\d+", incoming)
        if nums:
            n = min(int(nums[0]), 50)
        msg.body(f"🖥️ *Last {n} log lines:*\n\n{get_recent_logs(n)[-1400:]}")
        return str(resp)

    # ✅ Everything else — let the agent handle it
    from ai.agent import run_agent
    reply = run_agent(incoming)
    msg.body(reply)
    return str(resp)

# ================================================================
# /logs — browser log viewer (auto-refreshes every 10s)
# ================================================================
@app.route("/logs")
def logs_endpoint():
    secret = os.environ.get("LOG_SECRET", "")
    if secret and request.args.get("secret") != secret:
        return "Unauthorized — add ?secret=YOUR_LOG_SECRET to the URL", 401
    n    = min(int(request.args.get("n", 100)), 300)
    logs = get_all_logs(n).replace("<", "&lt;").replace(">", "&gt;")
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bot Logs</title>
  <meta http-equiv="refresh" content="10">
  <style>
    body {{ background:#0d1117; color:#c9d1d9; font-family:monospace; font-size:13px; padding:16px; margin:0 }}
    h2   {{ color:#58a6ff; margin-bottom:8px }}
    pre  {{ white-space:pre-wrap; word-break:break-all; line-height:1.6 }}
  </style>
</head>
<body>
  <h2>🖥️ Bot Logs <span style="font-size:11px;color:#8b949e">(auto-refresh 10s · last {n} lines)</span></h2>
  <pre>{logs}</pre>
</body>
</html>"""
    return html, 200, {"Content-Type": "text/html"}

# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=False,
        use_reloader=False,
        port=int(os.environ.get("PORT", 5000)),
    )
