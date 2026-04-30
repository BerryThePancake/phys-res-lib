"""
PhysResidual v0.1 - synthetic regime-shift experiment (research harness).

Formal definitions (toy generative model, not MATPOWER):
- Operating regime (train/cal): observations = true latent net injections x
  (approximately zero-sum per row) + i.i.d. Gaussian noise N(0, train_noise_std^2).
- Distribution shift (test): same latent process, but observations add
  (i) higher noise std test_noise_std and (ii) a fixed per-bus zero-sum sensor drift
  vector d (sum(d)=0), scaled by drift_scale. This is covariate shift on raw meters
  while the global sum feature remains defined on the same physical quantity layout.
- Anomaly label: subset of rows receive an additive fault_mag on one random bus without
  rebalancing, so the true injection sum becomes non-zero (imbalance).

Baselines:
- Classifier A (raw-only): logistic regression on visible bus channels only.
- Classifier B (residual-augmented): same visible channels plus |sum(observed)| over
  ALL buses (aggregate constraint channel).

Light model: sklearn.linear_model.LogisticRegression (L2, class_weight='balanced').
This is explicit, small, and CPU-only; not an embedded C export in v0.1.

For publication-grade work, replace this generator with MATPOWER/ORNL traces, define
shift on real covariates, and add significance tests across multiple seeds.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def try_load_physresidual():
    dll_path = os.environ.get("PHYSRESIDUAL_DLL")
    if not dll_path:
        root = Path(__file__).resolve().parents[1]
        for cand in (
            root / "build" / "Release" / "physresidual.dll",
            root / "build" / "physresidual.dll",
            root / "build" / "libphysresidual.so",
        ):
            if cand.is_file():
                dll_path = str(cand)
                break
    if not dll_path or not os.path.isfile(dll_path):
        return None
    lib = ctypes.CDLL(dll_path)
    lib.phys_power_balance_residual.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.c_void_p,
    ]
    lib.phys_power_balance_residual.restype = None
    return lib


def power_balance_numpy(powers: np.ndarray) -> np.ndarray:
    return np.sum(powers, axis=1)


def power_balance_c(lib, powers: np.ndarray) -> np.ndarray:
    n_samples, n_buses = powers.shape
    out = np.empty(n_samples, dtype=np.float64)
    powers_f = np.ascontiguousarray(powers, dtype=np.float64)
    lib.phys_power_balance_residual(
        powers_f.ctypes.data_as(ctypes.c_void_p),
        ctypes.c_size_t(n_samples),
        ctypes.c_size_t(n_buses),
        out.ctypes.data_as(ctypes.c_void_p),
    )
    return out


def make_dataset(
    rng: np.random.Generator,
    n_samples: int,
    n_buses: int,
    noise_std: float,
    noise_mean: float,
    anomaly_frac: float,
    fault_mag: float,
    sensor_drift: np.ndarray | None = None,
):
    x = rng.standard_normal((n_samples, n_buses))
    x -= x.mean(axis=1, keepdims=True)
    y = np.zeros(n_samples, dtype=np.int32)
    n_anom = max(1, int(n_samples * anomaly_frac))
    idx = rng.choice(n_samples, size=n_anom, replace=False)
    bus = rng.integers(0, n_buses, size=n_anom)
    x[idx, bus] += fault_mag
    y[idx] = 1
    obs = x + noise_mean + noise_std * rng.standard_normal(x.shape)
    if sensor_drift is not None:
        obs = obs + sensor_drift[np.newaxis, :]
    return obs.astype(np.float64), y


def threshold_at_fpr(scores: np.ndarray, y: np.ndarray, target_fpr: float) -> float:
    neg = scores[y == 0]
    if neg.size == 0:
        return float("inf")
    neg_sorted = np.sort(neg)[::-1]
    k = max(int(np.ceil(target_fpr * neg.size)), 1)
    return float(neg_sorted[min(k - 1, neg_sorted.size - 1)])


def eval_at_threshold(name: str, scores: np.ndarray, y: np.ndarray, thr: float):
    alarm = scores >= thr
    fp = int(np.sum(alarm & (y == 0)))
    tp = int(np.sum(alarm & (y == 1)))
    tn = int(np.sum((~alarm) & (y == 0)))
    fn = int(np.sum((~alarm) & (y == 1)))
    fpr = fp / max(fp + tn, 1)
    tpr = tp / max(tp + fn, 1)
    print(f"  [{name}] thr={thr:.4f}  FPR={fpr:.4f}  TPR={tpr:.4f}")


def report_metrics_block(name: str, clf, X, y):
    proba = clf.predict_proba(X)[:, 1]
    pred = clf.predict(X)
    auc = roc_auc_score(y, proba)
    ap = average_precision_score(y, proba)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    far = fp / max(fp + tn, 1)
    fnr = fn / max(fn + tp, 1)
    f1 = f1_score(y, pred, zero_division=0)
    prec = precision_score(y, pred, zero_division=0)
    rec = recall_score(y, pred, zero_division=0)
    print(
        f"  [{name}] ROC-AUC={auc:.4f}  AUC-PR={ap:.4f}  FAR={far:.4f}  FNR={fnr:.4f}  "
        f"P={prec:.4f}  R={rec:.4f}  F1={f1:.4f}"
    )
    return {
        "name": name,
        "roc_auc": float(auc),
        "auc_pr": float(ap),
        "far": float(far),
        "fnr": float(fnr),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
    }


def mcnemar_p_value(pred_a: np.ndarray, pred_b: np.ndarray, y: np.ndarray) -> tuple[float, int, int]:
    """
    McNemar (asymptotic chi^2 with continuity correction) on paired binary predictions.
    b01 = A correct & B wrong; b10 = A wrong & B correct (under 0/1 accuracy vs y).
    """
    ok_a = pred_a == y
    ok_b = pred_b == y
    b01 = int(np.sum(ok_a & ~ok_b))
    b10 = int(np.sum(~ok_a & ok_b))
    if b01 + b10 == 0:
        return 1.0, b01, b10
    chi = (abs(b10 - b01) - 1) ** 2 / (b10 + b01)
    p = float(chi2.sf(chi, 1))
    return p, b01, b10


def main():
    p = argparse.ArgumentParser(description="Synthetic regime-shift study (PhysResidual v0.1)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-train", type=int, default=8000)
    p.add_argument("--n-cal", type=int, default=4000)
    p.add_argument("--n-test", type=int, default=8000)
    p.add_argument("--n-buses", type=int, default=16)
    p.add_argument(
        "--visible-buses",
        type=int,
        default=3,
        help="raw classifier inputs: first k buses; residual uses full n-buses",
    )
    p.add_argument("--train-noise-std", type=float, default=0.12)
    p.add_argument("--test-noise-std", type=float, default=0.55)
    p.add_argument("--test-noise-mean", type=float, default=0.0)
    p.add_argument("--drift-scale", type=float, default=1.35)
    p.add_argument("--anomaly-frac", type=float, default=0.10)
    p.add_argument("--fault-mag", type=float, default=2.2)
    p.add_argument("--cal-fpr", type=float, default=0.02)
    p.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="optional path to write a JSON summary of printed metrics",
    )
    args = p.parse_args()

    rng = np.random.default_rng(args.seed)
    lib = try_load_physresidual()
    if lib:
        print("Using phys_power_balance_residual from C library.", file=sys.stderr)
    else:
        print("C DLL not found; using NumPy reference for residuals.", file=sys.stderr)

    k_vis = args.visible_buses
    if k_vis < 1 or k_vis > args.n_buses:
        p.error("--visible-buses must be in [1, n-buses]")

    print("=== Experiment protocol (record this block in lab notes) ===")
    print(json.dumps(vars(args), sort_keys=True, indent=2))
    print("================================================================")

    drift = rng.standard_normal(args.n_buses)
    drift -= drift.mean()
    drift *= args.drift_scale

    X_tr_f, y_tr = make_dataset(
        rng, args.n_train, args.n_buses, args.train_noise_std, 0.0, args.anomaly_frac, args.fault_mag, None
    )
    X_cal_f, y_cal = make_dataset(
        rng, args.n_cal, args.n_buses, args.train_noise_std, 0.0, args.anomaly_frac, args.fault_mag, None
    )
    X_te_f, y_te = make_dataset(
        rng,
        args.n_test,
        args.n_buses,
        args.test_noise_std,
        args.test_noise_mean,
        args.anomaly_frac,
        args.fault_mag,
        drift,
    )

    def slice_vis(full: np.ndarray) -> np.ndarray:
        if k_vis >= full.shape[1]:
            return full
        return full[:, :k_vis]

    X_tr, X_cal, X_te = slice_vis(X_tr_f), slice_vis(X_cal_f), slice_vis(X_te_f)

    pb = power_balance_c if lib else power_balance_numpy
    r_tr = np.abs(pb(X_tr_f)).reshape(-1, 1)
    r_cal = np.abs(pb(X_cal_f)).reshape(-1, 1)
    r_te = np.abs(pb(X_te_f)).reshape(-1, 1)

    X_aug_tr = np.hstack([X_tr, r_tr])
    X_aug_cal = np.hstack([X_cal, r_cal])
    X_aug_te = np.hstack([X_te, r_te])

    clf_raw = LogisticRegression(max_iter=400, class_weight="balanced", random_state=args.seed)
    clf_aug = LogisticRegression(max_iter=400, class_weight="balanced", random_state=args.seed)
    clf_raw.fit(X_tr, y_tr)
    clf_aug.fit(X_aug_tr, y_tr)

    s_raw_cal = clf_raw.predict_proba(X_cal)[:, 1]
    s_aug_cal = clf_aug.predict_proba(X_aug_cal)[:, 1]
    s_raw_te = clf_raw.predict_proba(X_te)[:, 1]
    s_aug_te = clf_aug.predict_proba(X_aug_te)[:, 1]

    thr_raw = threshold_at_fpr(s_raw_cal, y_cal, args.cal_fpr)
    thr_aug = threshold_at_fpr(s_aug_cal, y_cal, args.cal_fpr)

    mode = f"visible buses = {min(k_vis, args.n_buses)} (power-balance residual from all {args.n_buses} buses)"
    print(f"\nSetup: {mode}")

    artifact: dict = {"args": vars(args), "mode": mode, "metrics": {}}

    print("\nCalibration regime (same noise law as train):")
    artifact["metrics"]["cal_raw"] = report_metrics_block("raw-only", clf_raw, X_cal, y_cal)
    artifact["metrics"]["cal_aug"] = report_metrics_block("raw+|sum|", clf_aug, X_aug_cal, y_cal)
    print(f"\nThresholds on calibration normals targeting ~{args.cal_fpr:.0%} FAR:")
    eval_at_threshold("raw-only (cal)", s_raw_cal, y_cal, thr_raw)
    eval_at_threshold("aug (cal)", s_aug_cal, y_cal, thr_aug)

    print("\nShifted test regime (defined in module docstring):")
    artifact["metrics"]["test_raw"] = report_metrics_block("raw-only", clf_raw, X_te, y_te)
    artifact["metrics"]["test_aug"] = report_metrics_block("raw+|sum|", clf_aug, X_aug_te, y_te)
    print("Same calibration thresholds on shifted test:")
    eval_at_threshold("raw-only (test)", s_raw_te, y_te, thr_raw)
    eval_at_threshold("aug (test)", s_aug_te, y_te, thr_aug)

    pr = clf_raw.predict(X_te)
    pa = clf_aug.predict(X_aug_te)
    p_mc, b01, b10 = mcnemar_p_value(pr, pa, y_te)
    print("\nPaired significance (McNemar, default 0.5 decision threshold on shifted test):")
    print(f"  discordant: raw-only correct & aug wrong = {b01}, aug correct & raw wrong = {b10}")
    print(f"  McNemar p-value (asymptotic, continuity correction) = {p_mc:.6f}")

    print("\nOracle on shifted test (threshold fit to test normals; not deployable):")
    o_fpr = 0.05
    thr_raw_o = threshold_at_fpr(s_raw_te, y_te, o_fpr)
    thr_aug_o = threshold_at_fpr(s_aug_te, y_te, o_fpr)
    eval_at_threshold(f"raw-only @~{o_fpr:.0%} FAR on test normals", s_raw_te, y_te, thr_raw_o)
    eval_at_threshold(f"aug @~{o_fpr:.0%} FAR on test normals", s_aug_te, y_te, thr_aug_o)

    artifact["mcnemar"] = {"p_value": p_mc, "b01_raw_ok_aug_fail": b01, "b10_aug_ok_raw_fail": b10}

    if args.json_out:
        outp = Path(args.json_out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        print(f"\nWrote {outp}")


if __name__ == "__main__":
    main()
