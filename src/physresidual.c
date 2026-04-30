#include "physresidual.h"
#include <math.h>

void phys_power_balance_residual(const double *powers,
                                 size_t n_samples,
                                 size_t n_buses,
                                 double *out_residual)
{
    for (size_t i = 0; i < n_samples; ++i) {
        double s = 0.0;
        const double *row = powers + i * n_buses;
        for (size_t j = 0; j < n_buses; ++j) {
            s += row[j];
        }
        out_residual[i] = s;
    }
}

void phys_measurement_residual_l2(const double *y,
                                  const double *hx,
                                  size_t n_samples,
                                  size_t n_meas,
                                  double *out_residual)
{
    for (size_t i = 0; i < n_samples; ++i) {
        const double *yi = y + i * n_meas;
        const double *hi = hx + i * n_meas;
        double acc = 0.0;
        for (size_t m = 0; m < n_meas; ++m) {
            double d = yi[m] - hi[m];
            acc += d * d;
        }
        out_residual[i] = sqrt(acc);
    }
}

void phys_append_column(const double *matrix,
                         const double *values,
                         size_t n_samples,
                         size_t n_in,
                         double *out_augmented)
{
    for (size_t i = 0; i < n_samples; ++i) {
        const double *src = matrix + i * n_in;
        double *dst = out_augmented + i * (n_in + 1);
        for (size_t j = 0; j < n_in; ++j) {
            dst[j] = src[j];
        }
        dst[n_in] = values[i];
    }
}
