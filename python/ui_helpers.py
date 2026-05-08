"""Shared CSS, constants, and helper functions for all pages."""

import io
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ── paths ─────────────────────────────────────────────────────────────────────

_HERE         = os.path.dirname(os.path.abspath(__file__))
_EXAMPLES     = os.path.normpath(os.path.join(_HERE, "..", "examples"))

SAMPLE_POWERS_CSV = os.path.join(_EXAMPLES, "power_balance_sample.csv")
SAMPLE_Y_CSV      = os.path.join(_EXAMPLES, "measurement_y_sample.csv")
SAMPLE_HX_CSV     = os.path.join(_EXAMPLES, "measurement_hx_sample.csv")

# ── palette ───────────────────────────────────────────────────────────────────

BLUE  = "#3b82f6"
RED   = "#f87171"
AMBER = "#f59e0b"
GRID  = "#334155"
BG    = "#0f172a"
PANEL = "#1e293b"
TEXT  = "#e2e8f0"
MUTED = "#94a3b8"

# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.4rem;}

/* ── metric cards ── */
[data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 18px;
}
[data-testid="stMetricLabel"] p {
    color: #94a3b8 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
}

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #1e293b;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #334155;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    padding: 7px 22px;
    color: #94a3b8;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #3b82f6 !important;
    color: #fff !important;
}

/* ── expander ── */
[data-testid="stExpander"] details {
    background: #1e293b;
    border: 1px solid #334155 !important;
    border-radius: 10px;
}

/* ── download button ── */
[data-testid="stDownloadButton"] button {
    border: 1px solid #334155;
    border-radius: 8px;
    background: #1e293b;
    color: #e2e8f0;
    font-weight: 500;
    padding: 8px 20px;
}
[data-testid="stDownloadButton"] button:hover {
    border-color: #3b82f6;
    color: #3b82f6;
    background: #1e293b;
}

/* ── section card ── */
.section-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 22px 24px 18px 24px;
    margin-bottom: 16px;
}
.section-num {
    display: inline-block;
    background: #1d4ed8;
    color: #fff;
    font-weight: 700;
    font-size: 0.78rem;
    border-radius: 20px;
    padding: 2px 10px;
    margin-bottom: 10px;
    letter-spacing: 0.04em;
}
.section-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 14px;
}

/* ── feature cards (home page) ── */
.feat-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 28px 26px 22px 26px;
    height: 100%;
    transition: border-color 0.2s;
}
.feat-card:hover { border-color: #3b82f6; }
.feat-card h3  { color: #f1f5f9; margin: 0 0 8px 0; font-size: 1.15rem; }
.feat-card p   { color: #94a3b8; font-size: 0.88rem; line-height: 1.65; margin: 0; }
.formula-pill {
    display: inline-block;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 3px 10px;
    font-family: monospace;
    font-size: 0.83rem;
    color: #60a5fa;
    margin: 8px 0 12px 0;
}

/* ── step breadcrumb ── */
.breadcrumb {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 22px;
    flex-wrap: wrap;
}
.bc-step {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 4px 13px;
    font-size: 0.76rem;
    color: #64748b;
    font-weight: 500;
}
.bc-step.done {
    border-color: #22c55e33;
    color: #22c55e;
    background: #14532d22;
}
.bc-step.active {
    border-color: #3b82f6;
    background: #1d4ed820;
    color: #93c5fd;
}
.bc-sep { color: #334155; font-size: 0.85rem; }

/* ── info banner ── */
.sample-banner {
    background: #1e3a5f;
    border: 1px solid #2563eb44;
    border-radius: 10px;
    padding: 12px 16px;
    color: #93c5fd;
    font-size: 0.88rem;
    margin: 8px 0 4px 0;
}
.sample-banner b { color: #bfdbfe; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


# ── sidebar ───────────────────────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown(
            "<h2 style='margin:0 0 2px 0;color:#f1f5f9;font-size:1.25rem;'>PhysResidual</h2>"
            "<p style='color:#64748b;font-size:0.8rem;margin:0 0 16px 0;'>v0.1 · MIT · Austin Riha</p>",
            unsafe_allow_html=True,
        )
        st.page_link("app.py",                         label="Home",                    icon="🏠")
        st.page_link("pages/1_Power_Balance.py",       label="Power Balance Residual",  icon="⚡")
        st.page_link("pages/2_Measurement_Residual.py",label="Measurement Residual",    icon="📐")
        st.divider()
        with st.expander("CSV format"):
            st.markdown(
                "- **Rows** = samples, **columns** = channels\n"
                "- Comma, space, or semicolon delimited\n"
                "- Lines starting with `#` are ignored\n"
                "- UTF-8 with or without BOM\n"
            )


# ── data parsing ──────────────────────────────────────────────────────────────

def parse_csv(source) -> np.ndarray:
    if isinstance(source, (str, os.PathLike)):
        with open(source, encoding="utf-8-sig") as fh:
            raw = fh.read()
    else:
        raw = source.read().decode("utf-8-sig")
    lines = [ln for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        raise ValueError("File contains no data rows.")
    return pd.read_csv(io.StringIO("\n".join(lines)), header=None).values.astype(np.float64)


# ── breadcrumb ────────────────────────────────────────────────────────────────

def breadcrumb(steps: list[str], done_up_to: int):
    """steps = list of labels; done_up_to = number of completed steps (0-indexed)."""
    parts = []
    for i, label in enumerate(steps):
        if i < done_up_to:
            cls = "bc-step done"
        elif i == done_up_to:
            cls = "bc-step active"
        else:
            cls = "bc-step"
        parts.append(f'<div class="{cls}">{label}</div>')
        if i < len(steps) - 1:
            parts.append('<span class="bc-sep">›</span>')
    st.markdown(f'<div class="breadcrumb">{"".join(parts)}</div>', unsafe_allow_html=True)


def section(num: str, title: str):
    st.markdown(
        f'<div class="section-num">Step {num}</div>'
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )


# ── data preview ─────────────────────────────────────────────────────────────

def preview_matrix(data: np.ndarray, col_prefix: str = "Col"):
    n_rows, n_cols = data.shape
    cols = [f"{col_prefix} {j+1}" for j in range(n_cols)]
    st.dataframe(pd.DataFrame(data[:10], columns=cols), use_container_width=True)
    st.caption(f"{n_rows:,} total rows shown above: first 10")


# ── results ───────────────────────────────────────────────────────────────────

def metric_row(r: np.ndarray, threshold: float | None = None):
    above = int((np.abs(r) > threshold).sum()) if threshold is not None else None
    cols  = st.columns(6)
    items = [
        ("Samples",   f"{len(r):,}"),
        ("Mean",      f"{r.mean():.4g}"),
        ("Std dev",   f"{r.std():.4g}"),
        ("p95 |r|",   f"{np.percentile(np.abs(r), 95):.4g}"),
        ("Max |r|",   f"{np.abs(r).max():.4g}"),
        (
            "Flagged" if threshold is not None else "Median",
            f"{above} ({above / len(r) * 100:.1f}%)" if above is not None else f"{np.median(r):.4g}",
        ),
    ]
    for col, (label, val) in zip(cols, items):
        col.metric(label, val)


def residual_chart(r: np.ndarray, threshold: float | None = None) -> go.Figure:
    idx = np.arange(len(r))
    hi  = (np.abs(r) > threshold) if threshold is not None else np.zeros(len(r), bool)
    lo  = ~hi

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.65, 0.35],
        subplot_titles=["<b>Time Series</b>", "<b>Distribution</b>"],
        horizontal_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=idx[lo], y=r[lo], mode="lines+markers",
        line=dict(color=BLUE, width=1.3), marker=dict(size=3, color=BLUE),
        name="Normal",
        hovertemplate="Sample %{x}<br>r = %{y:.5g}<extra></extra>",
    ), row=1, col=1)

    if hi.any():
        fig.add_trace(go.Scatter(
            x=idx[hi], y=r[hi], mode="markers",
            marker=dict(size=9, color=RED, line=dict(color="#dc2626", width=1.2)),
            name="Flagged",
            hovertemplate="Sample %{x}<br>r = %{y:.5g}<extra></extra>",
        ), row=1, col=1)

    fig.add_hline(y=0, line=dict(color=GRID, width=1, dash="dash"), row=1, col=1)

    if threshold is not None:
        for sign in (1, -1):
            fig.add_hline(
                y=sign * threshold,
                line=dict(color=AMBER, width=1.5, dash="dot"),
                annotation_text=f"±{threshold:.3g}" if sign == 1 else "",
                annotation_font_color=AMBER,
                row=1, col=1,
            )
            fig.add_vline(x=sign * threshold,
                          line=dict(color=AMBER, width=1.5, dash="dot"),
                          row=1, col=2)

    fig.add_trace(go.Histogram(
        x=r,
        nbinsx=min(60, max(10, len(r) // 20)),
        marker=dict(color=BLUE, opacity=0.75, line=dict(color=PANEL, width=0.5)),
        name="Distribution",
        hovertemplate="Bin: %{x}<br>Count: %{y}<extra></extra>",
    ), row=1, col=2)

    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        font=dict(color=MUTED, size=12),
        height=390,
        showlegend=bool(hi.any()),
        legend=dict(bgcolor=PANEL, bordercolor=GRID, borderwidth=1,
                    font=dict(color=TEXT), x=0.01, y=0.99),
        margin=dict(l=8, r=8, t=48, b=8),
    )
    for ax in ("xaxis", "yaxis", "xaxis2", "yaxis2"):
        fig.update_layout(**{ax: dict(gridcolor=GRID, zerolinecolor=GRID,
                                      linecolor=GRID, tickfont=dict(color=MUTED))})
    fig.update_annotations(font_color=MUTED)
    fig.update_xaxes(title_text="Sample index",  title_font_color=MUTED, row=1, col=1)
    fig.update_yaxes(title_text="Residual",       title_font_color=MUTED, row=1, col=1)
    fig.update_xaxes(title_text="Residual value", title_font_color=MUTED, row=1, col=2)
    fig.update_yaxes(title_text="Count",          title_font_color=MUTED, row=1, col=2)
    return fig


def results_panel(r: np.ndarray, sess_key: str, filename: str):
    st.markdown("---")
    col_l, col_r = st.columns([5, 1])
    col_l.markdown("#### Results")
    thresh_on = col_r.toggle("Anomaly threshold", key=f"{sess_key}_thresh_on")

    thresh = None
    if thresh_on:
        abs_max = float(np.abs(r).max())
        thresh = st.slider(
            "Flag samples where |residual| exceeds:",
            min_value=0.0,
            max_value=abs_max,
            value=float(np.percentile(np.abs(r), 90)),
            step=max(abs_max / 300, 1e-6),
            key=f"{sess_key}_thresh_val",
            format="%.4g",
        )

    metric_row(r, threshold=thresh)
    st.plotly_chart(residual_chart(r, threshold=thresh), use_container_width=True)

    col_dl, col_note = st.columns([2, 5])
    col_dl.download_button(
        label=f"Download  {filename}",
        data=pd.DataFrame({"residual": r}).to_csv(index=False, header=False).encode(),
        file_name=filename,
        mime="text/csv",
        key=f"{sess_key}_dl",
    )
    col_note.caption(f"One residual value per row · {len(r):,} rows · plain CSV")
