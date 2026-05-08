import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import streamlit as st
from ui_helpers import (
    inject_css, sidebar, parse_csv, breadcrumb, section,
    preview_matrix, results_panel, SAMPLE_POWERS_CSV,
)

st.set_page_config(
    page_title="Power Balance — PhysResidual",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
sidebar()

# ── header ────────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='color:#f1f5f9;font-size:1.85rem;font-weight:700;margin-bottom:2px;'>"
    "⚡  Power Balance Residual</h1>"
    "<p style='color:#64748b;margin:0 0 20px 0;'>"
    "r[i] = &Sigma;&#8336; powers[i, j] &nbsp;—&nbsp; "
    "row-sum of net bus injections per sample</p>",
    unsafe_allow_html=True,
)

# determine how many steps are done
_r_ready   = "pb_r" in st.session_state
_data_key  = "pb_source"

_steps = ["1  Load Data", "2  Configure", "3  Run Analysis", "4  Download Results"]
_done  = 3 if _r_ready else 0
breadcrumb(_steps, _done)

# ── step 1: data source ───────────────────────────────────────────────────────

with st.container():
    section("1", "Load your data")

    source = st.radio(
        "Choose a data source:",
        options=["Use built-in demo data", "Upload my own CSV"],
        horizontal=True,
        key=_data_key,
        help="The demo file contains 200 samples × 6 buses with 12 injected fault rows.",
    )

    pb_data = None

    if source == "Use built-in demo data":
        st.markdown(
            "<div class='sample-banner'>"
            "<b>power_balance_sample.csv</b> &nbsp;·&nbsp; "
            "200 samples × 6 buses &nbsp;·&nbsp; "
            "12 injected fault rows (large bus imbalances)"
            "</div>",
            unsafe_allow_html=True,
        )
        try:
            pb_data = parse_csv(SAMPLE_POWERS_CSV)
        except Exception as exc:
            st.error(f"Could not load demo file: {exc}")
            st.stop()

        with st.expander("Preview demo data (first 10 rows)"):
            preview_matrix(pb_data, col_prefix="Bus")

    else:
        uploaded = st.file_uploader(
            "Upload a CSV file — each row is one sample, each column is a bus net injection",
            type=["csv", "txt"],
            key="pb_upload",
        )
        if uploaded:
            try:
                pb_data = parse_csv(uploaded)
            except Exception as exc:
                st.error(f"Could not parse file: {exc}")
                st.stop()
            with st.expander(f"Preview: {uploaded.name} (first 10 rows)"):
                preview_matrix(pb_data, col_prefix="Bus")
        else:
            st.markdown(
                "<div style='background:#1e293b;border:1px dashed #334155;border-radius:10px;"
                "padding:20px;text-align:center;color:#64748b;font-size:0.9rem;margin-top:8px;'>"
                "Drag and drop a CSV here, or switch to demo data above."
                "</div>",
                unsafe_allow_html=True,
            )

# ── step 2: configure ─────────────────────────────────────────────────────────

if pb_data is not None:
    st.markdown("---")
    section("2", "Configure options")

    col_opt1, col_opt2 = st.columns([2, 3])
    with col_opt1:
        pb_abs = st.checkbox(
            "Apply absolute value  `|r[i]|`",
            value=False,
            key="pb_abs",
            help="Useful when you care only about the magnitude of the imbalance, not its sign.",
        )
    with col_opt2:
        st.markdown(
            "<p style='color:#64748b;font-size:0.85rem;margin-top:6px;'>"
            "All other settings are automatic — column count is inferred from the first row."
            "</p>",
            unsafe_allow_html=True,
        )

# ── step 3: run ───────────────────────────────────────────────────────────────

    st.markdown("---")
    section("3", "Run analysis")

    col_btn, col_hint = st.columns([2, 5])
    with col_btn:
        run = st.button("Run analysis", type="primary", key="run_pb", use_container_width=True)
    with col_hint:
        n_s, n_b = pb_data.shape
        st.markdown(
            f"<p style='color:#64748b;font-size:0.85rem;margin-top:10px;'>"
            f"Will compute {n_s:,} residuals across {n_b} buses.</p>",
            unsafe_allow_html=True,
        )

    if run:
        r = pb_data.sum(axis=1)
        if pb_abs:
            r = np.abs(r)
        st.session_state["pb_r"] = r
        st.rerun()

# ── step 4: results ───────────────────────────────────────────────────────────

if "pb_r" in st.session_state:
    section("4", "Results & download")
    results_panel(st.session_state["pb_r"], sess_key="pb", filename="power_balance_residuals.csv")

    st.markdown(
        "<p style='color:#475569;font-size:0.82rem;margin-top:8px;'>"
        "Enable the <b style='color:#94a3b8;'>Anomaly threshold</b> toggle above the chart "
        "to flag suspicious samples — drag the slider to adjust sensitivity in real time."
        "</p>",
        unsafe_allow_html=True,
    )
