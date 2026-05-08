import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import streamlit as st
from ui_helpers import (
    inject_css, sidebar, parse_csv, breadcrumb, section,
    preview_matrix, results_panel, SAMPLE_Y_CSV, SAMPLE_HX_CSV,
)

st.set_page_config(
    page_title="Measurement Residual — PhysResidual",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
sidebar()

# ── header ────────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='color:#f1f5f9;font-size:1.85rem;font-weight:700;margin-bottom:2px;'>"
    "📐  Measurement Residual (L2)</h1>"
    "<p style='color:#64748b;margin:0 0 20px 0;'>"
    "r[i] = &#8214; y[i] &minus; h&#x0302;(x)[i] &#8214;&#8322; &nbsp;—&nbsp; "
    "L2 norm of measurement minus model prediction per sample</p>",
    unsafe_allow_html=True,
)

_r_ready = "ml2_r" in st.session_state
_steps   = ["1  Load Data", "2  Run Analysis", "3  Download Results"]
_done    = 2 if _r_ready else 0
breadcrumb(_steps, _done)

# ── step 1: data source ───────────────────────────────────────────────────────

section("1", "Load your data")

source = st.radio(
    "Choose a data source:",
    options=["Use built-in demo data", "Upload my own CSV files"],
    horizontal=True,
    key="ml2_source",
    help="The demo files contain 200 samples × 5 channels with 10 injected anomaly rows.",
)

ml2_y = ml2_hx = None

if source == "Use built-in demo data":
    st.markdown(
        "<div class='sample-banner'>"
        "<b>measurement_y_sample.csv</b> + <b>measurement_hx_sample.csv</b>"
        " &nbsp;·&nbsp; 200 samples × 5 channels &nbsp;·&nbsp; "
        "10 injected anomaly rows (large sensor deviations)"
        "</div>",
        unsafe_allow_html=True,
    )
    try:
        ml2_y  = parse_csv(SAMPLE_Y_CSV)
        ml2_hx = parse_csv(SAMPLE_HX_CSV)
    except Exception as exc:
        st.error(f"Could not load demo files: {exc}")
        st.stop()

    with st.expander("Preview demo data (first 10 rows)"):
        n_m   = ml2_y.shape[1]
        tcols = [f"Ch {j+1}" for j in range(n_m)]
        t1, t2, t3 = st.tabs(["y  (sensor readings)", "ĥ(x)  (model predictions)", "Difference  y − ĥ(x)"])
        with t1:
            st.dataframe(pd.DataFrame(ml2_y[:10],           columns=tcols), use_container_width=True)
        with t2:
            st.dataframe(pd.DataFrame(ml2_hx[:10],          columns=tcols), use_container_width=True)
        with t3:
            st.dataframe(pd.DataFrame((ml2_y - ml2_hx)[:10], columns=tcols), use_container_width=True)

else:
    col_y, col_hx = st.columns(2, gap="medium")

    with col_y:
        st.markdown(
            "<p style='color:#94a3b8;font-size:0.88rem;margin-bottom:6px;font-weight:500;'>"
            "Actual measurements &nbsp;<code>y</code></p>",
            unsafe_allow_html=True,
        )
        y_file = st.file_uploader(
            "y CSV",
            type=["csv", "txt"],
            key="y_upload",
            label_visibility="collapsed",
        )

    with col_hx:
        st.markdown(
            "<p style='color:#94a3b8;font-size:0.88rem;margin-bottom:6px;font-weight:500;'>"
            "Model predictions &nbsp;<code>ĥ(x)</code> &nbsp;— same shape as y</p>",
            unsafe_allow_html=True,
        )
        hx_file = st.file_uploader(
            "hx CSV",
            type=["csv", "txt"],
            key="hx_upload",
            label_visibility="collapsed",
        )

    if y_file and hx_file:
        try:
            ml2_y  = parse_csv(y_file)
            ml2_hx = parse_csv(hx_file)
        except Exception as exc:
            st.error(f"Could not parse files: {exc}")
            st.stop()

        if ml2_y.shape != ml2_hx.shape:
            st.error(
                f"Shape mismatch — y is {ml2_y.shape} but ĥ(x) is {ml2_hx.shape}. "
                "Both files must have exactly the same number of rows and columns."
            )
            ml2_y = ml2_hx = None
        else:
            n_s, n_m = ml2_y.shape
            tcols = [f"Ch {j+1}" for j in range(n_m)]
            with st.expander(f"Preview: {y_file.name} and {hx_file.name} (first 10 rows)"):
                t1, t2, t3 = st.tabs(["y", "ĥ(x)", "y − ĥ(x)"])
                with t1:
                    st.dataframe(pd.DataFrame(ml2_y[:10],            columns=tcols), use_container_width=True)
                with t2:
                    st.dataframe(pd.DataFrame(ml2_hx[:10],           columns=tcols), use_container_width=True)
                with t3:
                    st.dataframe(pd.DataFrame((ml2_y - ml2_hx)[:10], columns=tcols), use_container_width=True)

    elif y_file or hx_file:
        missing = "ĥ(x)" if y_file else "y"
        st.warning(f"Also upload the **{missing}** file to continue.")
    else:
        st.markdown(
            "<div style='background:#1e293b;border:1px dashed #334155;border-radius:10px;"
            "padding:20px;text-align:center;color:#64748b;font-size:0.9rem;margin-top:8px;'>"
            "Upload both CSV files above, or switch to demo data."
            "</div>",
            unsafe_allow_html=True,
        )

# ── step 2: run ───────────────────────────────────────────────────────────────

if ml2_y is not None and ml2_hx is not None:
    st.markdown("---")
    section("2", "Run analysis")

    col_btn, col_hint = st.columns([2, 5])
    with col_btn:
        run = st.button("Run analysis", type="primary", key="run_ml2", use_container_width=True)
    with col_hint:
        n_s, n_m = ml2_y.shape
        st.markdown(
            f"<p style='color:#64748b;font-size:0.85rem;margin-top:10px;'>"
            f"Will compute {n_s:,} L2 residuals across {n_m} measurement channels.</p>",
            unsafe_allow_html=True,
        )

    if run:
        st.session_state["ml2_r"] = np.linalg.norm(ml2_y - ml2_hx, axis=1)
        st.rerun()

# ── step 3: results ───────────────────────────────────────────────────────────

if "ml2_r" in st.session_state:
    section("3", "Results & download")
    results_panel(st.session_state["ml2_r"], sess_key="ml2", filename="measurement_residuals_l2.csv")

    st.markdown(
        "<p style='color:#475569;font-size:0.82rem;margin-top:8px;'>"
        "Enable the <b style='color:#94a3b8;'>Anomaly threshold</b> toggle above the chart "
        "to flag suspicious samples — drag the slider to adjust sensitivity in real time."
        "</p>",
        unsafe_allow_html=True,
    )
