# Changelog

## Unreleased

## 0.3.2 - 2026-09-04

- Fixed the explicit `routing_dt_h` path so `(target_time, target_flow)` is consumed in the declared
  order; equal-step resampling is an exact pass-through and no longer risks treating time as flow.
- Aligned conservative flow resampling with the established interval-start `sum(Q) * dt` volume
  contract, retaining the final source interval and zero-filling only a partial target overhang.
- Propagated the actual routed grid through routed/reservoir volume, reservoir solver timestep,
  peak time, rise time, recession end, and recession duration calculations.
- Made an explicit reservoir `dt_h` a fail-closed consistency assertion against the upstream grid;
  removed reservoir inflow override fields that the layered pipeline previously accepted but ignored.
- Kept the hydrologic equations, pipeline/result schemas, default 70/73-field canonical outputs, and
  multi-event baseline unchanged. Validation is limited to L2 synthetic grid/conservation and runtime
  equivalence checks, not basin calibration or engineering review.

## 0.3.1 - 2026-09-01

- Added strict explicit multi-event datasets with stable event IDs, UTC-offset `[start,end)`
  boundaries aligned to precipitation interval edges, and non-empty calibration, validation, and
  blind partitions. Positive rainfall outside all events fails closed; zero-rain gaps are counted.
- Added auditable stage locks: validation requires a calibration run identity, blind requires a
  validation run identity, and dataset/split/config/area mismatches fail closed. These hashes guard
  workflow misuse; they are not signatures or access control.
- Added KGE-2009, KGE-2012, and MAE on the existing overlap/alignment contract. Exact zero means or
  variability return `None` with explicit status rather than NaN, Inf, or an invented epsilon.
- Added equal-weight per-event macro mean/median/min/max without concatenating event time series.
  No calibration optimizer or automatic best-model selector is introduced.
- Corrected the recommender so single-event NSE/KGE diagnostics cannot reorder physically ranked
  candidates; reports now label the output as a physical-applicability candidate, not a best model.
- Kept the pipeline schema, legacy 70-field result and hydrologic formula baseline unchanged. This
  release is limited to L2 formula/schema/conservation checks, not real-basin split-sample
  validation or engineering acceptance.

## 0.3.0 - 2026-09-01

- Added a strict structured hydrologic time-series contract for precipitation and observed
  discharge, with explicit offset-aware timestamps, interval reference, units, point quality,
  station/source metadata, QC policy, and canonical input hashes.
- Added exact normalization for supported rainfall intensity/depth and discharge units. Missing,
  non-finite or negative values, unknown fields, ambiguous/duplicate/reversed/irregular rainfall
  times, unaccepted quality classes, and explicit bound violations now fail closed; no imputation,
  resampling, timezone guessing, or default anomaly threshold is performed.
- Integrated structured rainfall/observed inputs into the pipeline and full-chain CLI while keeping
  the legacy positional input contract, 70-field result schema `1.1.0`, hydrologic formulas, and
  frozen numerical result unchanged. Structured runs use result schema `1.2.0` and add only data
  contract version, input hash, and normalized provenance.
- Made high-level JSON loading reject duplicate/non-finite values and unknown keys, restored
  scenario forwarding, and added input/file SHA-256 provenance to report summaries and output
  manifest schema `1.1`.
- Closed two report-callability gaps: advertised CLIs now run under isolated `python -I`, and the
  four-piece report displays arbitrary-duration S-curve runs on their actual common Delta-D
  total/net rainfall grid instead of failing or inventing a rebinning to source intervals.
- Made full-chain reporting method-aware: unsupported combinations use the generic professional
  four-piece instead of Muskingum/Modified-Puls labels, while the specialized reservoir report
  records its terminal storage/outflow and does not call an inflow-horizon boundary complete
  reservoir recession.
- Added unit, time-zone, interval, QC, provenance, JSON, runtime-equivalence, deterministic-package,
  and clean-extract regressions. This is an L2 software/units/conservation release, not measured-data
  certification, basin calibration, or engineering acceptance.

## 0.2.3 - 2026-09-01

- Replaced fixed sibling `*.py` execution with one fail-closed canonical module loader that works
  with the declared CPython 3.13 source or Windows x64 native runtime layout and prevents silent
  fallback or duplicate aliases.
- Added an ABI-tagged runtime manifest, numerical/error equivalence gates, and strict module-loading
  checks for the supported CPython 3.13 Windows x64 environment.
- Added Losn attribution in NOTICE, package metadata, CLI version output, and low-profile
  HTML/DOCX/XLSX/PNG metadata or footers without modifying CSV numerical structures.
- Kept all hydrologic formulas, parameters, schemas, time grids, the 70-field result, and numerical
  output unchanged; native equivalence does not establish basin calibration or engineering review.

## 0.2.2 - 2026-08-25

- Removed runtime ECharts downloads and CDN fallback from the full-chain HTML path; the default
  four-piece HTML is now a standalone document with an inline SVG chart.
- Unified PNG and inline-SVG chart construction on a professional hydrology layout: time axis on
  top, inverted rainfall axis on the left, flow axis on the right, nested net-rain bars, raw
  unsmoothed inflow/outflow series, and unchanged peak values.
- Corrected full-chain chart and tabular rainfall mapping to use the actual `dt_rain_h` for bar
  centres, widths, net-rain intensity, and time lookup instead of assuming one-hour input periods.
- Restricted optional ECharts reports to an existing local UTF-8 JavaScript file embedded into the
  document; URLs, network paths, missing files, and unknown backends fail closed. Its custom rain
  renderer now consumes the contract's actual total/net bar widths instead of assuming 1 h.
- Kept all hydrologic equations, schemas, time grids, parameters, and numerical outputs unchanged;
  these checks are not a claim of basin calibration.

## 0.2.1 - 2026-08-25

- Unified all 19 runtime modules, CLI examples, tests, and CI on one maintainable execution path.
- Verified the default 70-field full-chain JSON remains exactly equal to the previous runtime
  baseline, and retained all 44 public regression tests.
- Corrected the scientific-method documentation to distinguish the legacy aligned-duration rule
  from the unified pipeline's explicit S-curve arbitrary-duration path.
- Added a single root `VERSION`, `full_chain.py --version`, a package manifest with per-file
  SHA-256, and clean-unpack release-contract tests.
- Kept all hydrologic equations, parameter semantics, time grids, schemas, and numerical outputs
  unchanged.

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
