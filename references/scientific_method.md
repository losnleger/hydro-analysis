# Scientific method and evidence boundary

## Contents

- [Task classification](#task-classification)
- [Primary sources](#primary-sources)
- [Theory-to-code mapping](#theory-to-code-mapping)
- [Time-grid contract](#time-grid-contract)
- [Fail-closed rules](#fail-closed-rules)
- [Frozen pre-fix evidence](#frozen-pre-fix-evidence-2026-08-14)
- [Validation status](#validation-status)

## Task classification

- Type: bug fix + adaptation of an official method.
- Reproduced: NRCS PRF=484 dimensionless unit hydrograph table and NRCS timing/peak relations.
- Local adaptations: Chinese labels/CN supplements, optional constant-runoff-coefficient excess rainfall,
  discrete volume normalization, an explicitly labeled area-only Tc estimate, and a `Tp`-only
  `ΔD≈0.2Tp` engineering bridge. The latter does not claim exact simultaneous reproduction of
  `lag=0.6Tc` and `ΔD=0.133Tc`; strict NRCS timing uses an input Tc.
- Not professionally validated as an end-to-end field workflow: calibration for any real basin,
  spatial rainfall, dynamic/continuous baseflow, backwater or gate-controlled channel hydraulics,
  snow/frozen-soil runoff, controlled reservoir operations, uncertainty analysis, or
  design-standard approval.

## Primary sources

1. USDA NRCS, NEH Part 630, Chapter 16, *Hydrographs* (March 2007):
   <https://directives.nrcs.usda.gov/sites/default/files2/1712930620/7303.pdf>
   - Table 16-1: standard PRF=484 `q/qp` versus `t/Tp` ordinates.
   - Eq. 16A-6: `qp = 484 A Q / Tp` in customary units.
   - Eq. 16A-7 and 16A-13: `Tp = ΔD/2 + lag`, `ΔD = 0.133 Tc`.
   - Chapter 16 defines unit time as the duration of precipitation excess. Its incremental
     hydrograph construction shifts each unit-duration response by ΔD, not by an arbitrary
     numerical output step.
   - Example 16-1: `A=4.6 mi²`, `Tc=2.3 h`, `Tp≈1.53 h`, `qp≈1455 cfs`
     for one inch of unit runoff.
2. USDA NRCS, NEH Part 630, Subpart F, *Time of Concentration* (June 2025):
   <https://directives.nrcs.usda.gov/sites/default/files2/1749749287/Subpart%20F%20%E2%80%93%20Time%20of%20Concentration.pdf>
   - Eq. 630.15-3: `lag = 0.6 Tc`.
   - Eq. 630.15-12: Kirpich relation; developed from seven rural Tennessee watersheds
     with well-defined channels, steep slopes, and areas of 1.25–112 acres.
3. USDA NRCS, NEH Part 630, Chapter 7, *Hydrologic Soil Groups* (January 2009):
   <https://directives.nrcs.usda.gov/sites/default/files2/1720460843/Chapter%207%20-%20Hydrologic%20Soil%20Groups.pdf>
   - Table 7-1: HSG uses saturated hydraulic conductivity together with restrictive-layer
     depth, high-water-table depth, and dual HSG classes; it is not a single texture or
     legacy minimum-infiltration-rate lookup.
4. USDA NRCS, NEH Part 630, Subpart E, *Runoff Curve Numbers* (June 2025):
   <https://directives.nrcs.usda.gov/sites/default/files2/1749749646/Subpart%20E%20%E2%80%93%20Runoff%20Curve%20Numbers.pdf>
   - Eq. 630E-2 applies the unconnected-impervious adjustment only below 30% total
     imperviousness; at 30% or more, use the connected/area-weighted relation.
5. USDA NRCS, NEH Part 630, Subpart H, *Estimation of Direct Runoff from Storm Rainfall*
   (August 2025):
   <https://directives.nrcs.usda.gov/sites/default/files2/1754923466/Subpart%20H%20%E2%80%93%20Estimation%20of%20Direct%20Runoff%20from%20Storm%20Rainfall.pdf>
   - The tabulated CN system is developed for `Ia=0.2S`; a different `Ia/S` relation
     requires a newly developed/calibrated curve set.

## Theory-to-code mapping

| Scientific element | Code | Units and constraint |
|---|---|---|
| CN to retention | `cn_to_s_mm()` | `S=25400/CN-254`, mm; `0<CN<=100` |
| Cumulative direct runoff | `direct_runoff_mm()` | cumulative `P,Q,S,Ia` in mm; `P>=0`, `0<λ<=1` |
| Watershed lag | `calculate_lag_time()` | `lag=0.6Tc`; input Tc min, output h |
| Unit excess duration | `calculate_unit_duration()`, `_align_unit_duration()` | target `ΔD=0.133Tc`; actual ΔD is an exact rainfall-interval divisor, h |
| Time to peak | `calculate_time_to_peak()` | `Tp=ΔD/2+lag`; h; `ΔD<=0.25Tp` |
| Unit peak flow | `calculate_peak_flow()` | `0.208333 A Q/Tp`; A km², Q mm, output m³/s |
| PRF=484 shape | `NRCS_484_*`, `generate_unit_hydrograph()` | direct interpolation of table 16-1 over `0<=t/Tp<=5` |
| Rainfall conversion | `analyze_flood_hydrograph()` | intensity mm/h multiplied by `dt_rain_h`; interval-uniform intensity is then represented on the ΔD grid |
| Routing | `analyze_flood_hydrograph()`, `convolve_rainfall_runoff()` | net-depth increments occur every ΔD; the ΔD-duration UH is sampled at `dt` and shifted by ΔD |
| Plot-data mapping | `prepare_precipitation_runoff_plot_data()` | total/net rain share ΔD and units; bars use interval centers; flow preserves `time_h` and calculated peak |
| Mass balance | `analyze_flood_hydrograph()` | `Σq Δt = ΣPe A`; relative error must be `<=1e-10` |
| Result schema | result dict `schema_version=1.1.0` | explicit-unit aliases, event totals, recession termination, and `cn_provenance`; legacy keys unchanged |
| JSON export | `result_to_jsonable()`, `result_to_json()` | numpy arrays/scalars become Python types; NaN/Inf rejected by default |
| Input contract | `analyze_flood_hydrograph()` kwargs whitelist | unknown parameters fail closed; boolean flags accept only `bool` |
| Layered pipeline | `pipeline.validate_config()`, `pipeline.simulate_event()` | config schema `1.0`; loss/transform/baseflow/reach_routing/reservoir layers with method/parameter whitelists |
| Legacy facade | `analyze_flood_hydrograph()` | maps old kwargs to layered config and calls `simulate_event()`; frozen baselines enforce field-level numerical equivalence |
| Scenario schema | `scenario.validate_scenario()` | scenario schema `1.0`; strict validation and normalization only, no model recommendation yet |
| Green-Ampt loss | `loss_methods.run_green_ampt()` | event model; `f=Ks(ψΔθ/F+1)`, ponding point `Fp=Ks·ψΔθ/(i-Ks)`, implicit cumulative-infiltration equation solved by bounded bisection |
| Horton loss | `loss_methods.run_horton()` | `f=fc+(f0-fc)e^(-kt)`; per-ΔD analytic potential integral; no recovery between events |
| Parameter priors | `loss_parameters.get_green_ampt_preset()`, `get_horton_preset()` | literature defaults with source/evidence/`requires_calibration`; not field-calibrated values |
| Reach routing | `routing_methods.run_lag()`, `run_linear_reservoir()`, `run_lag_and_k()`, `run_muskingum()` | pure translation, linear reservoir, cascade, standard three-coefficient Muskingum with stability checks and volume balance |
| Baseflow | `baseflow_methods.run_baseflow()` | `none` or `specified` constant/series; added after transform and before reach routing |
| Observed metrics | `performance.evaluate_hydrograph()` | NSE, KGE-2009, KGE-2012, MAE, PBIAS, peak/volume relative error, peak-time error, RMSE; simulated values interpolated to observed times, overlap only; zero KGE denominators return `None + status` |
| Multi-event isolation | `event_dataset.prepare_event_dataset()`, `run_partition()`, `create_stage_lock()` | explicit UTC `[start,end)` boundaries; non-empty calibration/validation/blind roles; event-equal macro diagnostics; validation/blind require prior-stage dataset/split/config/area identity lock |
| S-curve duration conversion | `uh_tools.unit_hydrograph_for_duration()` | `UH_new=(D1/D2)[S(t)-S(t-D2)]`; volume conservation and negative-oscillation diagnostics |
| Velocity method Tc | `tc_methods.calculate_tc_velocity()` | NEH-630 Subpart F eq. 630.15-8 (sheet), fig. 630F-7 (shallow), eq. 630.15-10 (channel) |
| AMC/HSG helpers | `cn_helpers.classify_amc()`, `classify_hsg()` | TR-55 antecedent rainfall classes; NEH-630 Table 7-1 HSG decision incl. A/D, B/D, C/D |
| PRF 100-600 UH | `nrcs_prf_tables.generate_unit_hydrograph_prf()` | verbatim NEH-630 Chapter 16 Appendix 16B tables; PRF>=400 dt/Tp=0.1, PRF<=350 dt/Tp=0.2 |
| Reservoir routing | `reservoir_methods.route_reservoir()` | level-pool continuity `(I1+I2)/2·Δt-(O1+O2)/2·Δt=S2-S1`; trial, Modified Puls `N=S/Δt+O/2`, semi-graphical work table |
| Model recommendation | `recommender.recommend_models()` | physical/data/evidence screening, candidate isolation, applicability ranking, multi-model envelope; observed metrics only when independent observations are supplied |
| Reservoir unit contract | `reservoir_methods.route_reservoir()` | low-level time/dt in **seconds**; pipeline config uses hours and converts automatically |
| Routing grid contract | `routing_methods.resample_flow_volume_conserving()`, `auto_subreaches` | independent `routing_dt_h` maps interval-start mean flows by cumulative interval volume; the last source interval is retained and any final target overhang is zero-filled; native fine `dt` is handled by auto subreach splitting |
| Four-piece exports | `exporters.write_xlsx()`, `write_docx()`, `write_result_png()` | DOCX/XLSX/PNG joined into `export_report_package()` with HTML/JSON/CSV |
| JSON export | `exporters.write_result_json()`, `write_summary_json()` | UTF-8, indented, `allow_nan=False`, round-trip safe |
| CSV export | `exporters.write_rainfall_csv()`, `write_hydrograph_csv()`, `write_series_long_csv()`, `write_summary_csv()` | rainfall and flow retain their own time grids; UTF-8 BOM for Excel compatibility |
| HTML report | `exporters.generate_report_html()`, `build_four_piece.make_html()` | standalone offline HTML with inline SVG; optional ECharts requires an existing local UTF-8 file that is embedded, while URL/network paths fail closed |
| Output package | `exporters.export_report_package()`, `scripts/export_report.py` | full JSON + summary JSON + CSVs + HTML + manifest |

The published table is rounded. Its trapezoidal integral is about `1.33595`, so a dimensional
curve that preserves the tabulated shape and exact discrete runoff volume has a peak about 0.2%
below the continuous PRF=484 conversion. The implementation preserves the table shape and exact
volume and reports the theoretical PRF peak separately as `Qp_per_mm`/`Qp`.

## Time-grid contract

- Rainfall intervals are equal length and specified by `dt_rain_h`; each value is an intensity
  applying from that interval's start to its end.
- `ΔD=0.133Tc` is the target unit-excess duration. By default, the implementation selects the
  nearest exact divisor of `dt_rain_h` that also satisfies `ΔD<=0.25Tp`, records target and actual
  values, and recomputes `Tp=lag+ΔD/2` from the actual ΔD.
- In the legacy facade and the default `aligned` mode, a user-specified `unit_duration_h` must
  exactly divide `dt_rain_h`; incompatible durations fail closed. The unified pipeline also offers
  the explicit `unit_duration_resolution="s_curve"` path for arbitrary-duration conversion, with
  negative-oscillation and volume-conservation checks.
- When only interval intensity is available, it is assumed uniform inside the input interval.
  Cumulative SCS-CN runoff is recomputed at every actual ΔD boundary; interval runoff is not merely
  divided after applying the nonlinear cumulative CN equation.
- Each ΔD runoff-depth increment is applied once at its interval start. Copies of the same
  ΔD-duration unit hydrograph are shifted by ΔD. Applying that unit hydrograph at every finer `dt`
  would be a different and incorrect duration model even if total volume remained conserved.
- `dt` is output sampling only. It must exactly divide ΔD and be no greater than `0.1Tp`, retaining
  at least the published table 16-1 ordinate resolution. If omitted, it is selected automatically.
- `time_h=0` is the start of the first rainfall interval; every reported depth applies over the
  following interval. The output exposes this convention in `time_reference`.
- Reach-routing arrays use the existing discrete-volume contract `sum(Q_i) * dt`. When
  `routing_dt_h` differs from transform `dt`, every source sample represents the full interval
  beginning at its `time_h`; conservative resampling retains the last source interval. Reported
  routed volume, peak time, and recession times use the actual routed grid, not transform `dt`.
- The level-pool reservoir solver retains its node-flow trapezoidal continuity equation. It inherits
  the actual reach grid. An explicit reservoir `dt_h` is a grid-consistency assertion and must match
  the upstream grid; automatic interval-mean to node-flow resampling is not defined in this version.
- The unit hydrograph always includes the complete table 16-1 tail to `5Tp`; convolution retains
  that complete recession.
- Multi-event boundaries must match precipitation interval edges and use `[start,end)` semantics.
  No dry-gap duration, rainfall threshold, or pre/post-event window is inferred by the software.
  Every positive-rainfall interval must belong to exactly one event; observations are selected at
  instants `start <= t < end` and each event requires at least two observation points.

## Fail-closed rules

- Reject empty, multidimensional, negative, NaN, or infinite rainfall.
- Reject nonpositive/nonfinite area, timing, length, slope, CN, λ, and segment areas.
- A land-use lookup requires explicit HSG, hydrologic condition, AMC, and (for cultivated land)
  treatment; it does not silently assume B/good/straight/AMC II.
- Professional CN routing requires Tc, Tp, or both Kirpich length and slope.
- Kirpich use outside its original area sample requires the explicit
  `allow_kirpich_extrapolation=True` acknowledgement.
- Alpine/snow/frozen-soil application is rejected because this implementation has no such process.
- Regional `λ=0.05` advice is never applied automatically. An explicit nonstandard λ is returned
  with a warning assumption that CN and λ require joint local recalibration.
- The former blanket `crop_residue => CN-2` rule is rejected because TR-55 values vary by crop,
  treatment, and condition.

## Frozen pre-fix evidence (2026-08-14)

The old 15-test suite passed, but did not test the scientific invariants below:

- Custom UH peaked at `2.50 Tp`, while NRCS table 16-1 peaks at `1.00 Tp`.
- With rainfall `[100] mm/h`, CN 80, the old code returned the same `50.5391 mm` runoff depth
  for `dt_rain_h=0.5`, `1`, and `2 h`; rainfall intensity had not been converted to depth.
- `[100,-50]` produced a negative runoff-depth increment of `-36.7366 mm`.
- `region='alpine'` failed with a `TypeError` from multiplying by `None`, rather than a domain error.
- A 2 h legacy interval produced `6000 m³` instead of `12000 m³` for two `10 mm/h` intervals,
  coefficient 0.3, and area 1 km².
- `peak_time` returned array index `26` rather than `2.6 h` for `dt=0.1 h`.
- An intermediate mass-conserving correction applied a ΔD-duration unit hydrograph to every finer
  `dt` runoff increment. Chapter 16 requires incremental responses to be shifted by ΔD; the final
  implementation uses a sparse output grid and locks this invariant with a regression test.

These values are regression evidence for defects, not acceptable scientific baselines to preserve.

## Validation status

The automated suite covers:

- all published table 16-1 discharge ordinates and post-peak monotonicity;
- NEH chapter 16 example 16-1 peak discharge and timing;
- exact 1 mm unit-hydrograph volume and end-to-end mass balance;
- `dt_rain_h` values 0.5, 1, and 2 h plus fractional rainfall intervals, aligned ΔD periods,
  and a direct test that unit hydrographs are shifted by ΔD rather than by output `dt`;
- invalid/negative/nonfinite inputs and unsupported alpine use;
- CN/AMC table values, composite-CN boundaries, and explicit nonstandard-lambda warnings.
- professional plot-data invariants: same-unit nested rain bars, ΔD interval centres, continuous flow time,
  and unchanged calculated peak values.

### Deterministic sensitivity check (2026-08-14)

Reference case: rainfall intensity `[10,30,50,20] mm/h`, 1 h intervals, `A=5 km²`,
`CN=75`, `Tc=120 min`, `λ=0.2`, fixed `ΔD=0.25 h`, and fixed `dt=0.05 h`.
Holding ΔD and `dt` fixed isolates the listed parameter perturbations. With the interval-start
time convention, baseline outputs were `peak=27.0021 m³/s`, `peak time=4.05 h`, and
`volume=243662.9 m³`.

| Perturbation | Peak change | Peak-time change | Volume change |
|---|---:|---:|---:|
| CN −10% | −25.66% | +3.70% | −27.76% |
| CN +10% | +28.55% | −2.47% | +31.96% |
| Tc −10% | +4.67% | −4.94% | 0.00% |
| Tc +10% | −4.23% | +2.47% | 0.00% |
| λ −10% | +2.13% | −2.47% | +2.69% |
| λ +10% | −2.07% | 0.00% | −2.68% |

The +10% CN case changes runoff volume by more than 30%, so CN selection/calibration is a flagged
high-sensitivity input for this event. These values describe one synthetic case and are not transferable
uncertainty bounds for another watershed or storm.

Passing these tests means official analytical reproduction and software/numerical validation only.
It does not establish calibration, predictive skill, uncertainty bounds, or professional acceptance
for any real watershed.

### v0.3.1 multi-event metric and split-sample boundary

- KGE-2009 follows Gupta et al. (2009), DOI `10.1016/j.jhydrol.2009.08.003`, with
  `alpha=sigma_sim/sigma_obs` and `beta=mean_sim/mean_obs`.
- KGE-2012 follows Kling, Fuchs & Paulin (2012), DOI
  `10.1016/j.jhydrol.2012.01.011`, replacing the variability ratio with the coefficient-of-variation
  ratio `gamma=CV_sim/CV_obs`; both variants remain explicitly named.
- MAE follows the dimensional mean absolute error definition discussed by Willmott & Matsuura
  (2005), DOI `10.3354/cr030079`.
- Calibration/validation separation is an adaptation of split-sample testing principles in Klemes
  (1986), DOI `10.1080/02626668609491024`; the additional blind role and hash lock are local
  workflow safeguards, not terms or guarantees attributed to that paper.
- Metrics are aggregated with one equal weight per event and never used here to update parameters
  or automatically declare a best model. v0.3.1 synthetic tests can reach L2 only; independent
  multi-event basin evidence would be required for L4.
