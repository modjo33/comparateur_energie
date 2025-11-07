#!/usr/bin/env python3
# coding: utf-8

import os
import json
from datetime import datetime
from collections import Counter

from flask import Flask, render_template, request
import plotly.graph_objects as go
import plotly.io as pio

# Projet/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

app = Flask(__name__)


# ---------- Utilitaires ----------

def load_history():
    """Charge data/history.json et renvoie une liste propre d'entrées."""
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    cleaned = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        cleaned.append({
            "date": entry.get("date"),
            "fournisseur": entry.get("fournisseur", "Inconnu") or "Inconnu",
            "filename": entry.get("filename", "—"),
            "url": entry.get("url", "#"),
        })
    return cleaned


def parse_date(date_str):
    """Convertit une chaîne ISO en datetime, sinon None."""
    if not date_str:
        return None
    try:
        # format type 2025-11-06T15:13:36
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


def compute_status(last_dt, now=None):
    """Retourne (label, css_class) selon l'âge de la dernière maj."""
    if last_dt is None:
        return "Inconnu", "status-unknown"

    if now is None:
        now = datetime.now()

    delta_days = (now - last_dt).days

    if delta_days <= 7:
        return "Actif", "status-ok"
    elif delta_days <= 30:
        return "À surveiller", "status-warn"
    else:
        return "Inactif", "status-bad"


def build_daily_chart(entries):
    """Construit le graphique Plotly (HTML) de l'activité quotidienne."""
    if not entries:
        return None

    counts = Counter()
    for e in entries:
        dt = parse_date(e.get("date"))
        if dt is None:
            continue
        counts[dt.date()] += 1

    if not counts:
        return None

    dates = sorted(counts.keys())
    x = [d.strftime("%Y-%m-%d") for d in dates]
    y = [counts[d] for d in dates]

    fig = go.Figure(data=[go.Bar(x=x, y=y)])
    fig.update_layout(
        title="Nombre de nouvelles grilles par jour",
        xaxis_title="Date",
        yaxis_title="Nombre de grilles",
        template="plotly_white",
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    graph_html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs="cdn"
    )
    return graph_html


# ---------- Routes ----------

@app.route("/")
def dashboard():
    history = load_history()
    now = datetime.now()

    # Liste des fournisseurs pour le select
    fournisseurs_all = sorted(
        {e.get("fournisseur", "Inconnu") for e in history}
    )

    selected = request.args.get("fournisseur", "Tous")
    if selected != "Tous":
        filtered = [e for e in history if e.get("fournisseur", "Inconnu") == selected]
    else:
        filtered = history

    # Stats par fournisseur (sur le jeu filtré)
    per_provider = {}
    for e in filtered:
        f = e.get("fournisseur", "Inconnu") or "Inconnu"
        dt = parse_date(e.get("date"))

        if f not in per_provider:
            per_provider[f] = {"count": 0, "last_dt": None}

        per_provider[f]["count"] += 1
        if dt is not None:
            if per_provider[f]["last_dt"] is None or dt > per_provider[f]["last_dt"]:
                per_provider[f]["last_dt"] = dt

    # Construction des lignes de tableau
    rows = []
    for f, infos in sorted(per_provider.items()):
        last_dt = infos["last_dt"]
        last_str = last_dt.strftime("%Y-%m-%d %H:%M") if last_dt else "—"
        status_label, status_class = compute_status(last_dt, now)
        rows.append({
            "fournisseur": f,
            "count": infos["count"],
            "last_update": last_str,
            "status_label": status_label,
            "status_class": status_class,
        })

    # KPIs (sur le jeu filtré)
    total_grilles = sum(r["count"] for r in rows)
    total_fournisseurs = len(rows)

    if filtered:
        last_update_dt = max(
            (parse_date(e.get("date")) for e in filtered),
            key=lambda d: d or datetime.min,
        )
        last_update_str = (
            last_update_dt.strftime("%Y-%m-%d %H:%M")
            if last_update_dt and last_update_dt != datetime.min
            else "—"
        )
    else:
        last_update_str = "—"

    graph_html = build_daily_chart(filtered)

    return render_template(
        "dashboard.html",
        rows=rows,
        total_grilles=total_grilles,
        total_fournisseurs=total_fournisseurs,
        last_update_str=last_update_str,
        fournisseurs_all=fournisseurs_all,
        selected_fournisseur=selected,
        graph_html=graph_html,
    )


if __name__ == "__main__":
    # Oui, on lance ça en debug, tu vis dangereusement.
    app.run(host="127.0.0.1", port=5000, debug=True)
