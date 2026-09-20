# Milestone 4 — Mathematics and interpretation

Recorded 2026-09-20. Normative definitions: `docs/math_conventions.md` §3.14,
version 0.7. M3's amplitude residual and all earlier optical conventions remain
unchanged. Let T and R be corresponding target and reconstruction intensities
on one shared intensity scale, and N the number of pixels.

## Intensity errors

    MSE_I = (1/N) * sum((R-T)**2)
    NMSE_I = sum((R-T)**2) / sum(T**2)

MSE has squared-intensity units. NMSE is a squared relative L2 intensity error,
not its square root and not a universal normalization standard. Its denominator
is a squared intensity norm, not optical power. A zero T is valid for MSE but
makes NMSE undefined even when R is also zero.

If R=2T and T is nonzero, R-T=T, so NMSE=1. Independently normalizing each
image to its peak would conceal this brightness error and is not permitted.
Scaling both images by c>0 multiplies MSE by c² and leaves NMSE unchanged,
provided required float64 arithmetic remains usable.

    PSNR_I = 10*log10(data_range**2/MSE_I)
           = 20*log10(data_range) - 10*log10(MSE_I)

The implementation uses the second form to avoid unnecessarily overflowing a
squared data range or ratio. Range is an explicit positive finite intensity
quantity, not an observed maximum. For M2 design values the example explicitly
chooses one. Reconstruction overshoot is valid. MSE larger than range² produces
negative PSNR; neither score nor intensities are clipped. Exact numerical
equality after complete validation gives +infinity, including a zero pair.
Signed-zero representations compare equal. Underflow of a nonzero error is an
error condition, not permission to report infinity.

If T, R and range all scale by c, PSNR is invariant. At fixed range it shifts
by -20*log10(c). This is why changing display brightness must not silently
change the metric's declared reference range.

## Regional power

For uniform pixel area a=dx*dy and a supplied Boolean region M:

    fraction = [a*sum(R[M])] / [a*sum(R)] = sum(R[M])/sum(R)

The denominator is the full supplied reconstruction window. With usable
positive full power, an empty region gives zero and the complete region gives
one. Zero total power is undefined. A fixed region that excludes target tails
can give a fraction below one even for an exact target reconstruction.

    source-normalized simulated efficiency
        = fraction * P_destination_window / P_source

Power conservation over the complete modeled window makes the two equal.
M3's lossless periodic model provides that mathematical setting; it
does not establish measured device efficiency. Hardware interpretation requires
defined input/output powers, collection geometry, radiometric calibration and
device-loss accounting. Neither additional efficiency metric is implemented.

Common brightness scaling cancels, so the exact target and twice the target
can have identical fractions while their intensity errors differ substantially.

## Regional intensity variation

For n selected intensities and their mean mu:

    variance = sum((I_selected-mu)**2)/n
    CV = sqrt(variance)/mu

This is population standard deviation (`ddof=0`), treating all selected pixels
as the region being described. It is not a statistical estimator for unknown
unobserved pixels. The region must be nonempty with positive mean. CV is
dimensionless and may exceed one: [0,0,0,4] has mean 1, variance 3 and CV sqrt(3).
An exactly constant positive region has exact CV zero, including one pixel.
The implementation recognizes that identity before a reduction can introduce
spurious roundoff variance; it uses no tolerance or floor.

Common positive intensity scaling cancels. Changing valid values outside the
region leaves CV unchanged but may change its regional power fraction. Lower
CV means less variation, useful when flat brightness is intended. A prescribed
Gaussian falloff is not a defect. Neither CV nor 1-CV is an accuracy score.

## Relationship to M3

M3 stores rho=sum((abs(V)-A_target)**2)/sum(A_target**2). M4 evaluates
R=Re(V)**2+Im(V)**2 from the actual returned reconstruction, against the original
target intensity. These different mathematical questions have different values.
M4 does not modify the solver, optimize metrics, or require monotonic improvement.

## Independent evidence

Hand-calculated fractions and scaling identities are supplemented by 80-digit
Decimal references formed from the exact stored float inputs, and independent
scalar reductions on an actual M3 result. See `tests_and_evidence.md` for
measured errors, explicit tolerances, mutation detections and reproduction code.
Finite-case agreement validates these computations, not arbitrary optical
models or universal perception. NumPy's definition of population standard
deviation is documented at https://numpy.org/doc/stable/reference/generated/numpy.std.html.
