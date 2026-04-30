#include "physresidual.h"
#include <stdio.h>

int main(void)
{
    /* Two samples, three buses: balanced then faulted sum */
    double powers[] = {
        10.0, -3.0, -7.0,
        10.0, -3.0, -5.0
    };
    const size_t n_samples = 2;
    const size_t n_buses = 3;
    double r[2];

    phys_power_balance_residual(powers, n_samples, n_buses, r);
    printf("power_balance_residual[0]=%.6f (expect ~0)\n", r[0]);
    printf("power_balance_residual[1]=%.6f (expect +2 imbalance)\n", r[1]);

    double y[] = {1.0, 0.0, 2.0, 0.0};
    double hx[] = {1.0, 0.1, 2.0, -0.1};
    double m[2];
    phys_measurement_residual_l2(y, hx, 2, 2, m);
    printf("measurement_l2[0]=%.6f\n", m[0]);
    printf("measurement_l2[1]=%.6f\n", m[1]);
    return 0;
}
