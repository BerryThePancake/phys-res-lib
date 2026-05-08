"""
PhysResidual — Home page
Run with:  python -m streamlit run python/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from ui_helpers import inject_css, sidebar

st.set_page_config(
    page_title="PhysResidual",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
sidebar()

# ── hero ──────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align:center;padding:56px 0 44px 0;">
      <div style="display:inline-block;background:#1d4ed820;border:1px solid #3b82f644;
                  border-radius:20px;padding:4px 16px;font-size:0.8rem;color:#93c5fd;
                  margin-bottom:16px;letter-spacing:0.05em;">
        POWER GRID · ANOMALY DETECTION · PHYSICS-INFORMED
      </div>
      <h1 style="font-size:3rem;font-weight:800;color:#f1f5f9;margin:0 0 14px 0;
                 letter-spacing:-0.02em;">
        PhysResidual Analysis
      </h1>
      <p style="font-size:1.05rem;color:#94a3b8;max-width:560px;margin:0 auto;line-height:1.75;">
        Upload power-grid CSV data and compute physics-informed constraint residuals
        to surface anomalies — no code required.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── feature cards ─────────────────────────────────────────────────────────────

col_l, col_r = st.columns(2, gap="large")

with col_l:
    st.markdown(
        """
        <div class="feat-card">
          <h3>⚡  Power Balance Residual</h3>
          <div class="formula-pill">r[i] = &Sigma;&#8336; powers[i, j]</div>
          <p>
            Sums the net bus injections for each sample.
            A non-zero result means the sample violates the power-balance constraint —
            a strong signal for faults, bad data, or model mismatch.
          </p>
          <ul style="color:#94a3b8;font-size:0.86rem;margin:14px 0 0 0;padding-left:18px;
                     line-height:2;">
            <li>One CSV — rows = samples, columns = buses</li>
            <li>Built-in demo data included (12 injected faults)</li>
            <li>Optional absolute-value mode</li>
            <li>Interactive anomaly threshold</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Power_Balance.py", label="Open Power Balance →", use_container_width=True)

with col_r:
    st.markdown(
        """
        <div class="feat-card">
          <h3>📐  Measurement Residual (L2)</h3>
          <div class="formula-pill">r[i] = &#8214; y[i] &minus; h&#x0302;(x)[i] &#8214;&#8322;</div>
          <p>
            Computes the L2 distance between actual sensor readings and
            state-estimator predictions per sample.
            Large values flag inconsistency between observations and the model.
          </p>
          <ul style="color:#94a3b8;font-size:0.86rem;margin:14px 0 0 0;padding-left:18px;
                     line-height:2;">
            <li>Two CSVs — y and ĥ(x), must have the same shape</li>
            <li>Built-in demo data included (10 injected anomalies)</li>
            <li>Per-sample scalar L2 norm output</li>
            <li>Interactive anomaly threshold</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Measurement_Residual.py", label="Open Measurement Residual →", use_container_width=True)

# ── how it works ──────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<h2 style='color:#f1f5f9;font-size:1.35rem;font-weight:700;margin-bottom:18px;'>"
    "How it works</h2>",
    unsafe_allow_html=True,
)

steps = [
    ("1", "Load Data",
     "Pick the built-in demo or upload your own CSV. "
     "A live preview shows the first rows so you can verify the format."),
    ("2", "Configure",
     "Set analysis options — absolute value, threshold — using plain controls. "
     "No parameters are required."),
    ("3", "Run Analysis",
     "Click Run. Residuals are computed instantly in Python using "
     "the same kernels as the C library."),
    ("4", "Download",
     "Export the residual column as a single-column CSV, "
     "ready to drop into any downstream pipeline."),
]

scols = st.columns(4, gap="medium")
for col, (num, title, desc) in zip(scols, steps):
    col.markdown(
        f"""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:14px;
                    padding:22px 18px;height:100%;">
          <div style="font-size:1.9rem;font-weight:800;color:#3b82f6;
                      margin-bottom:8px;line-height:1;">{num}</div>
          <div style="font-weight:600;color:#f1f5f9;margin-bottom:8px;
                      font-size:0.97rem;">{title}</div>
          <div style="color:#94a3b8;font-size:0.84rem;line-height:1.6;">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── sample data note ──────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.info(
    "**No data?  No problem.**  Both analysis pages load built-in demo CSV files "
    "by default so you can explore the full workflow immediately.",
    icon="ℹ️",
)
