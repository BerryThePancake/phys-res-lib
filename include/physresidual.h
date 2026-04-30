/**
 * @file physresidual.h
 * @brief Deterministic C kernels for scalar constraint residuals used as ML features.
 *
 * Scope (v0.1): This is a minimal numerical layer, not a full power-flow solver.
 * See docs/physresidual_api.txt for the physical interpretation, units contract,
 * and publication-oriented limitations.
 *
 * ABI: C99, nothrow (no exceptions). Functions do not allocate heap memory.
 * Thread safety: Reentrant if outputs do not overlap inputs and each thread uses
 * its own buffers. No mutable global state in the library implementation.
 *
 * Calling convention: Default C declaration on all supported platforms.
 * Windows DLL: define PHYSRESIDUAL_BUILD when compiling the shared library.
 * Static link: define PHYSRESIDUAL_STATIC when compiling consumers (or use CMake target).
 */
#ifndef PHYSRESIDUAL_H
#define PHYSRESIDUAL_H

#include <stddef.h>

#if defined(PHYSRESIDUAL_STATIC)
#define PHYSRESIDUAL_API
#elif defined(_WIN32)
#ifdef PHYSRESIDUAL_BUILD
#define PHYSRESIDUAL_API __declspec(dllexport)
#else
#define PHYSRESIDUAL_API __declspec(dllimport)
#endif
#else
#define PHYSRESIDUAL_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Per-sample signed scalar "power-balance" residual.
 *
 * Mathematical definition (no implicit network topology):
 *   r[i] = sum_j powers[i * n_buses + j]
 *
 * Row-major layout: sample index i is the outer dimension, bus j the inner.
 *
 * Physical interpretation (user must map data to this contract):
 * If @p powers holds consistent net active injections (or any variables that must
 * sum to zero at steady state under your model), then r[i] is near zero in nominal
 * operation and departs under imbalance. This library does NOT enforce KCL on a
 * graph, does NOT convert per-unit, and does NOT separate P/Q; it only sums the
 * provided doubles.
 *
 * Units: Dimensionless in API; values are whatever physical units the caller
 * stored in @p powers (MW, pu, etc.) as long as all columns are consistent.
 *
 * @param powers   Row-major matrix, length n_samples * n_buses. Must not alias @p out_residual.
 * @param n_samples Number of rows (time steps / scenarios).
 * @param n_buses   Number of columns (buses / channels).
 * @param out_residual Output array of length n_samples; r[i] as defined above.
 *                     Caller allocates; always written for i in [0, n_samples).
 */
PHYSRESIDUAL_API void phys_power_balance_residual(const double *powers,
                                                  size_t n_samples,
                                                  size_t n_buses,
                                                  double *out_residual);

/**
 * @brief Per-sample L2 norm of measurement innovation (y - Hx).
 *
 * For each sample i:
 *   r[i] = sqrt( sum_m ( y[i,m] - hx[i,m] )^2 )
 *
 * Row-major: y and hx are n_samples * n_meas contiguous doubles.
 * Typical use: hx is a predicted measurement from a state estimator; large r[i]
 * indicates inconsistency between measurement and model. The library does not
 * compute Hx; the caller supplies both y and hx.
 *
 * Units: Same as the squared sum of differences of the stored y and hx values.
 *
 * @param y         Measurements, row-major, length n_samples * n_meas.
 * @param hx        Predicted measurements, same layout and dimensions as y.
 * @param n_samples Number of rows.
 * @param n_meas    Number of columns (measurements per sample).
 * @param out_residual Output length n_samples; caller allocated.
 */
PHYSRESIDUAL_API void phys_measurement_residual_l2(const double *y,
                                                   const double *hx,
                                                   size_t n_samples,
                                                   size_t n_meas,
                                                   double *out_residual);

/**
 * @brief Horizontally stack one column to a row-major matrix.
 *
 * For each row i: out[i*(n_in+1) .. i*(n_in+1)+n_in-1] = matrix[i*n_in .. i*n_in+n_in-1],
 *                 out[i*(n_in+1)+n_in] = values[i].
 *
 * @param matrix        n_samples * n_in row-major; must not alias @p out_augmented.
 * @param values        Length n_samples.
 * @param n_samples     Rows.
 * @param n_in          Columns in matrix.
 * @param out_augmented Caller buffer, size n_samples * (n_in + 1). Must not alias @p matrix.
 */
PHYSRESIDUAL_API void phys_append_column(const double *matrix,
                                         const double *values,
                                         size_t n_samples,
                                         size_t n_in,
                                         double *out_augmented);

#ifdef __cplusplus
}
#endif

#endif /* PHYSRESIDUAL_H */
