"""
Flask API — serves deal data to the frontend dashboard.
Run with: python dashboard/app.py
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from core.database import get_recent_deals, init_db
from loguru import logger

app = Flask(__name__)
CORS(app)


@app.route("/api/deals", methods=["GET"])
def deals():
    """Return recent deals, optionally filtered."""
    limit     = int(request.args.get("limit", 50))
    min_score = int(request.args.get("min_score", 0))
    fire_only = request.args.get("fire_only", "false").lower() == "true"

    rows   = get_recent_deals(limit=limit * 3)   # over-fetch then filter
    result = []
    for r in rows:
        d = dict(r)
        if d["deal_score"] < min_score:
            continue
        if fire_only and not d["is_fire_deal"]:
            continue
        d["discount_pct_display"] = f"-{round(d['discount_pct'] * 100, 1)}%"
        result.append(d)

    return jsonify({"deals": result[:limit], "total": len(result)})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    logger.info("Dashboard API running → http://localhost:5000")
    app.run(debug=True, port=5000)
