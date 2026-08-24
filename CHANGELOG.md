# Changelog

## 0.2.0 - 2026-08-24

> 下文测试数量是开发阶段记录；v0.2.0 的公开发行审计独立验证了依赖安装、
> 完整链条演示、严格 JSON、CSV、PNG、离线 HTML、XLSX 与 DOCX 的生成及重开，
> 不把这些检查表述为流域率定或专业工程验收。

- Distribution compatibility:
  - corrected packaged module-loading paths in the legacy facade, report CLI, chart loader,
    and recommender;
  - CI and documented CLI examples enable Python UTF-8 mode so Chinese help text also works
    on non-CJK Windows runners;
  - the relocation-only patch leaves the 70-key full-chain JSON numerically identical and
    passes 40 retained public regressions plus 4 v0.2.0 release-contract tests under
    CPython 3.13.11.

- Phase 1 agent-callability hardening:
  - unknown `analyze_flood_hydrograph()` kwargs now fail closed instead of being silently ignored;
  - `allow_kirpich_extrapolation` and `crop_residue` now accept only real booleans, rejecting
    strings and numbers that were previously treated as truthy;
  - added `result_to_jsonable()` / `result_to_json()` with numpy-to-Python conversion and
    `allow_nan=False` defaults;
  - added result schema `1.1.0` with explicit-unit fields (`tc_min`, `watershed_lag_h`, `tp_h`,
    `recession_duration_h`, `recession_end_time_h`, `recession_criterion`), event totals
    (`total_rainfall_depth_mm`, `total_excess_depth_mm`, `event_runoff_coefficient`), CN-only
    `S_mm`/`Ia_mm`, and structured `cn_provenance`;
  - existing legal calls keep their previous numerical results and legacy field names.
- Phase 2 modular pipeline:
  - added `scripts/pipeline.py` with layered config schema `1.0`
    (`loss -> transform -> baseflow -> reach_routing -> reservoir`), strict method/parameter
    whitelists, and explicit `not_implemented` failures for future methods;
  - added `simulate_event()` unified pipeline and per-layer `layer_outputs` traceability;
  - converted `analyze_flood_hydrograph()` into a legacy facade that maps old kwargs to the
    pipeline while preserving the old signature, fields, numerical results, and error behavior;
  - added `scripts/scenario.py` with scenario description schema `1.0` and
    `validate_scenario(strict=True/False)` for later model recommendation;
  - added frozen equivalence baselines and config/scenario tests.
- Phase 3 output closure:
  - added `scripts/exporters.py` with JSON, grid-separated CSV, summary/long-format CSV,
    and a standalone offline HTML report (inline SVG, no CDN/external scripts);
  - added `export_report_package()` producing full/summary JSON, rainfall/hydrograph CSV,
    long CSV, summary CSV, HTML, and manifest;
  - added `scripts/export_report.py` CLI with `--result` and `--demo` modes;
  - added exporter tests including JSON round-trip, CSV precision, HTML independence,
    package manifest, and CLI smoke.
- Phase 4 alternative loss models:
  - added `scripts/loss_methods.py` with event-scale Green-Ampt (ponding time, implicit
    infiltration equation, impervious fraction) and Horton (analytic potential integral,
    impervious fraction) models;
  - added `scripts/loss_parameters.py` with soil-texture Green-Ampt priors
    (Rawls et al. 1983) and a SWMM-typical Horton preset, each carrying source,
    evidence level, and `requires_calibration`;
  - extended `pipeline.validate_config()` / `simulate_event()` with
    `loss.method = green_ampt | horton`, parameter whitelists, presets, provenance,
    and mass-balance checks; legacy API remains unchanged;
  - added analytic cross-validation, mass-balance, preset, and export tests.
- Phase 5 routing, baseflow, and observed metrics:
  - added `scripts/routing_methods.py` with volume-conserving `lag`,
    `linear_reservoir`, `lag_and_k`, and `muskingum` (X range, stability bounds,
    subreaches);
  - added `scripts/baseflow_methods.py` with `none` and `specified`
    constant/series baseflow;
  - added `scripts/performance.py` with NSE, PBIAS, peak/volume relative errors,
    peak-time error, and RMSE on overlapping observed time series;
  - extended pipeline config/execution for `baseflow` and `reach_routing`,
    added `direct_runoff_m3_s/baseflow_m3_s/routed_flow_m3_s` and optional
    `observed` comparison in results and HTML reports;
  - default five-layer `none` chain remains numerically identical to the legacy
    engine.
- Phase 6 NRCS method family expansion:
  - added `scripts/uh_tools.py` S-curve duration conversion with volume
    conservation, fractional-duration interpolation, and oscillation diagnostics;
  - added `scripts/tc_methods.py` Subpart F velocity method for
    sheet / shallow-concentrated / channel segments, with the official example
    as an analytical baseline;
  - added `scripts/cn_helpers.py` with AMC classification and NEH-630 Table 7-1
    HSG decision logic including dual HSG classes;
  - added `scripts/nrcs_prf_tables.py` with verbatim Appendix 16B ordinates for
    PRF 100-600 and `generate_unit_hydrograph_prf()`;
  - extended pipeline config with `nrcs_uh_prf`, `tc_method=velocity`,
    area-weighted and urban composite CN, and S-curve arbitrary unit duration.
- Phase 7 reservoir routing:
  - added `scripts/reservoir_methods.py` with `trial_level_pool`,
    `modified_puls`, and `semi_graphical` solvers sharing the level-pool
    continuity equation;
  - validated elevation/storage/discharge curves, initial storage/elevation,
    strict inflow time grid, mass-balance residual, and solver work tables;
  - extended pipeline `reservoir` layer and results with
    `reservoir_outflow_m3_s/reservoir_storage_m3/reservoir_elevation_m` and
    HTML reservoir section;
  - cross-solver agreement and steady-state analytical tests added.
- Phase 8 scenario screening and model recommendation:
  - added `scripts/recommender.py` with rule-based candidate generation,
    feasibility isolation, applicability/evidence ranking, result envelope,
    and optional observed-metric ranking;
  - `recommended_primary` is explicitly documented as the most preferred
    candidate for the current data, never a unique optimal model;
  - exporters gained a model-comparison section.
- Phase 9 WorkBuddy feedback merge and professional fixes:
  - fixed reservoir routing unit contract: low-level `route_reservoir()` now
    uses seconds (`dt_s`), pipeline converts hours<->seconds, with a physical
    magnitude regression test;
  - added Muskingum/linear-reservoir `auto_subreaches` and volume-conserving
    `routing_dt_h` resampling for independent routing time grids;
  - added DOCX/XLSX/PNG to `export_report_package()` and CLI flags;
  - added optional local-ECharts interactive HTML with offline SVG fallback;
  - added `scripts/full_chain.py` official full-chain orchestrator with
    `--demo` and `--config`; the upstream development suite was reported as 198 tests.
- Clarified that the skill targets WorkBuddy and other Agent development/runtime workflows.
- Added public packaging documentation, dependency declarations, CI, contribution guidance, and
  explicit output/validation boundaries.
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
- Added `prepare_precipitation_runoff_plot_data()` and a strict professional hyetograph/hydrograph
  contract: inverted rainfall, nested effective-rainfall bars, shared continuous time, consistent ΔD
  units, unmodified peak values, and no default smoothing.
- Added a tested Matplotlib PNG renderer whose rainfall axis is inverted, nested bars share interval
  centres, flow ordinates remain unmodified, and the complete recession is retained.
- Expanded the suite to 40 tests covering every published table 16-1 discharge ordinate, NEH chapter 16
  example 16-1, time relations, rainfall-duration conversion, ΔD-period hydrograph shifts, aligned output
  sampling, plot-data alignment and rendered geometry, mass balance, invalid inputs, HSG/CN/AMC values,
  and documented method boundaries.

Passing tests establish official analytical reproduction and software/numerical consistency only; they do
not establish real-basin calibration, predictive accuracy, independent engineering review, or professional
acceptance.
