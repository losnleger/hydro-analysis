# Changelog

## Unreleased

- Clarified that the skill targets WorkBuddy and other Agent development/runtime workflows.
- Added validated `agents/openai.yaml` metadata for Agent skill discovery and invocation UI.
- Added open-source packaging documentation, MIT licensing, dependency declarations, CI, contribution
  guidance, and explicit warnings for unavailable report/chart exporters.
- Added CN selection utilities based on USDA NRCS TR-55/NEH-630: land-use tables, HSG lookup,
  AMC conversion, area-weighted CN, urban impervious-area CN, cumulative SCS-CN runoff, and
  explicitly labeled Chinese local assumptions.
- Corrected scientific defects after independent reproduction against official NRCS sources:
  - replaced the uncited power/exponential hydrograph (whose peak occurred at `2.5Tp`) with direct
    interpolation of NEH-630 chapter 16 table 16-1, including the full recession to `5Tp`;
  - separated `Tc`, watershed `lag=0.6Tc`, unit-excess duration `ΔD=0.133Tc`, time to peak
    `Tp=ΔD/2+lag`, and numerical `dt`;
  - labels the `Tp`-only `ΔD≈0.2Tp` inference as an engineering bridge; strict NRCS timing requires
    `Tc` rather than claiming that the rounded inverse exactly reproduces both timing equations;
  - corrected rainfall intensity conversion from `mm/h` to interval depth using `dt_rain_h`;
  - separated the NRCS unit period from output sampling: the target `ΔD=0.133Tc` is aligned to an
    exact divisor of the rainfall interval, `Tp` is recomputed from the actual ΔD, and each excess
    increment shifts the ΔD-duration unit hydrograph by ΔD rather than by numerical `dt`;
  - made `dt` an output-only sampling interval that must divide ΔD and be no coarser than `0.1Tp`;
    incompatible explicit ΔD or `dt` values fail closed instead of drifting or being silently rounded;
  - removed arbitrary storm-peak rescaling and retained the complete recession in both CN and
    runoff-coefficient paths;
  - changed `peak_time`, rise duration, and recession duration from array indices to hours, while
    retaining `peak_index` explicitly;
  - made `runoff_coeff` optional when CN/land-use inputs are supplied;
  - stopped reporting an empirical pseudo-CN in the constant-runoff-coefficient path; `CN` is now
    `None` because that path does not use SCS-CN;
  - added finite/nonnegative/positive parameter validation and clear fail-closed behavior for unsupported
    alpine/frozen-soil use and Kirpich extrapolation.
- Corrected method boundaries:
  - HSG metadata now follows NEH-630 table 7-1 Ksat/depth context instead of legacy minimum-infiltration
    thresholds;
  - NEH-630 urban unconnected-impervious adjustment is limited to total impervious area below 30%;
  - the former blanket `crop_residue => CN-2` approximation is rejected;
  - regional `λ=0.05` is advisory only and is never applied automatically to CN tables developed for
    `Ia=0.2S`.
- Added `references/scientific_method.md` with source-to-code mapping, units, pre-fix counterexamples,
  fail-closed rules, and validation limits.
- Expanded the suite to 37 tests covering every published table 16-1 discharge ordinate, NEH chapter 16
  example 16-1, time relations, rainfall-duration conversion, ΔD-period hydrograph shifts, aligned output
  sampling, mass balance, invalid inputs, HSG/CN/AMC values, and documented method boundaries.

Passing tests establish official analytical reproduction and software/numerical consistency only; they do
not establish real-basin calibration, predictive accuracy, independent engineering review, or professional
acceptance.
