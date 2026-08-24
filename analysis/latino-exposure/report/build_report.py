"""Assembles report/index.html from results.json + the SVG figures + the
written analysis. Run after build_figures.py.
"""

import json
import pathlib
import re

import jinja2

HERE = pathlib.Path(__file__).resolve().parent
FIGURES = HERE / "figures"

results = json.loads((HERE / "results.json").read_text())
T = results["tract"]
B = results["block_group"]
PROV = results["data_provenance"]
RC = json.loads((HERE / "race_class_results.json").read_text())
PC = json.loads((HERE / "pooled_results.json").read_text())
HIER = json.loads((HERE / "hierarchical_results.json").read_text())


def inline_svg(name: str) -> str:
    svg = (FIGURES / f"{name}.svg").read_text()
    svg = re.sub(r"<\?xml.*?\?>\s*", "", svg, flags=re.DOTALL)
    svg = re.sub(r"<!DOCTYPE.*?>\s*", "", svg, flags=re.DOTALL)
    return f'<div class="figure-card">{svg}</div>'


def p_fmt(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def sig_span(p: float, text: str) -> str:
    cls = "sig" if p < 0.05 else ""
    return f'<span class="{cls}">{text}</span>'


VAR_LABELS = {
    "const": "Constant",
    "latino_share": "Latino/Hispanic share",
    "arterial_km_per_km2": "Arterial road, km per km²",
    "log_income": "log(median household income)",
    "pop_density_per_km2_1000": "Population density, 1,000s per km²",
    "crime_rate_per_km2_1000": "Pre-treatment crime rate, 1,000s per km²",
    "alpha": "α (NB overdispersion)",
}


def nb_table_html(nb: dict, caption: str) -> str:
    rows = []
    for var, label in VAR_LABELS.items():
        d = nb[var]
        rows.append(
            f"<tr><td>{label}</td><td>{d['coef']:.3f}</td><td>{d['se']:.3f}</td>"
            f"<td>{d['z']:.2f}</td><td>{sig_span(d['p'], p_fmt(d['p']))}</td></tr>"
        )
    return f"""
<div class="table-wrap">
<table>
<caption>{caption}</caption>
<thead><tr><th>Variable</th><th>Coef.</th><th>SE</th><th>z</th><th>p</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</div>
"""


abstract = f"""
<p>Flock Safety automated license-plate-reader (ALPR) camera locations in Oakland,
California are analyzed against Census-tract Latino/Hispanic population share,
using a negative-binomial count model with controls for arterial road density,
income, population density, and pre-treatment crime. The raw, unconditional
correlation between Latino share and camera density is weak and not statistically
significant (Pearson r = 0.050, p = 0.59). Once standard siting justifications are
held constant, however, Latino share is a large, positive, and statistically
significant predictor of camera count (β = {T['nb']['latino_share']['coef']:.2f},
p {p_fmt(T['nb']['latino_share']['p'])}), robust to spatial-lag and spatial-error
correction for spatial autocorrelation, to a first-order correction for known
ACS measurement error (which pushes the estimate up, not down), and to
substituting block groups for tracts. Adding Black share, Asian share, and a
poverty-rate control shows the relationship is specific to Latino/Hispanic
share in Oakland itself — neither a general nonwhite-neighborhood pattern nor
a class effect shows up as statistically robust there. <strong>The result is
Oakland-specific, but not Oakland-only:</strong> repeating the full pipeline in
fourteen more cities and fitting each city's own model finds Oakland is still
the only city with a significant Latino-share effect in the simplest
specification, with San Diego and Seattle close behind without quite clearing
the bar (§7); Oakland's result survives, unchanged, once real crime-data
controls found for six more cities are added, ruling out a missing confound
as the explanation. Extending the race/class comparison across all fifteen
cities (§8) turns up a broader picture: a joint model pooling every city with
one shared slope per variable actually converges here (unlike the pure
Latino-only version) and finds <strong>Asian share is a significant, positive
predictor of camera count pooled across all fifteen cities</strong>, replicating
individually in four of them (Charlotte, Dallas, San Diego, Seattle); Black
share replicates in three (Albuquerque, Phoenix, Sacramento); and once these
other shares are controlled for jointly, Latino share itself turns out to
replicate in two more cities beyond Oakland (Sacramento, San Diego). Poverty
rate remains the one variable with no coherent story — significant in four
cities, but split three-positive to one-negative rather than pointing one way.
A Bayesian hierarchical model (§9), built specifically to resolve the
pooled-vs-per-city tension in §7-8, gives the most statistically defensible
summary yet: the population-average Latino-share effect is not itself
distinguishable from zero, but the spread of that effect across cities is —
real heterogeneity, not noise — with Oakland and San Diego anchoring the
positive end; Asian share's population-level effect is confirmed by this
independent method; and poverty rate turns out to have a real, if modest,
positive population-level effect once city-level baselines are properly
separated out via random intercepts, refining rather than contradicting §8's
"no coherent poverty story" reading. The result is correlational, not causal — it
cannot distinguish deliberate targeting from a facially neutral siting rule that
happens to correlate with demographics — and Oakland's finding should be read
as a documented, robust pattern in one city, not yet a general claim about
Flock siting nationally. A planned difference-in-differences extension, keyed to
Oakland's actual December 2025 Flock-contract vote, was found not to be viable with
current data (OpenStreetMap tag-date history reflects mapper survey campaigns, not
installation dates) and is deferred pending a prospective camera-count panel.</p>
"""

body_sections = []

# 1. Introduction
body_sections.append(f"""
<section id="introduction">
  <h2><span class="num">1</span>Introduction</h2>
  <p class="lede">Flock Safety's automated license-plate-reader (ALPR) network has
  expanded into hundreds of U.S. cities, including Oakland, largely through
  city-by-city procurement decisions made with limited public siting criteria. This
  paper asks a narrow, tractable version of a much larger question: <em class="term">
  conditional on the siting rationales cities and vendors publicly cite</em> — traffic
  engineering, crime concentration, arterial chokepoints — <em class="term">is camera
  density in Oakland systematically higher in neighborhoods with a larger
  Latino/Hispanic population share?</em></p>
  <p>This is a disparate-impact question, not a claim about intent. A regression
  can show a relationship is robust to observable confounders; it cannot show that
  a city or vendor targeted a neighborhood because of who lives there. Both readings
  are consistent with the same coefficient, and the limitations section returns to
  this directly.</p>
  <p>The paper builds outward in stages, and each stage changes the answer in
  a way the previous one couldn't have shown. §§2-5 establish the core
  Oakland result with a standard econometric toolkit — negative binomial
  regression, spatial correction, an attenuation-bias check, block-group
  robustness. §6 asks whether that result is really about race or class
  generally rather than Latino share specifically. §§7-8 test whether any of
  it holds outside Oakland, in fourteen more cities. §9 replaces the
  forced choice between "one number for every city" and "fifteen unrelated
  numbers" with a hierarchical model built to handle exactly that structure.
  The headline finding changes shape at nearly every stage — which is itself
  the argument for building it this way rather than stopping at the first
  significant coefficient.</p>
</section>
""")

# 2. Data
body_sections.append(f"""
<section id="data">
  <h2><span class="num">2</span>Data</h2>
  <p>Four datasets are joined at the tract and block-group level. Camera locations
  come from OpenStreetMap nodes tagged <code>surveillance:type=ALPR</code> — the same
  crowdsourced dataset the DeFlock project publishes from, not a Flock corporate feed
  or a FOIA'd city inventory. Of {PROV['cameras_total_bbox']} cameras originally pulled
  against a bounding rectangle around Oakland, {PROV['cameras_oakland_only']} fall
  genuinely inside the city's boundary (confirmed by direct polygon-containment test);
  the rest sit in neighboring jurisdictions the rectangle happened to catch, and are
  excluded here.</p>
  <p>Demographic data is the American Community Survey 2023 5-year estimates
  (table B03002, Hispanic or Latino origin; B19013, median household income; B01003,
  total population), from the Census API. Road network and arterial classification
  come from OpenStreetMap via Overpass. Crime data is the City of Oakland's
  CrimeWatch open dataset, restricted to incidents dated on or before 2025-12-15 — the
  day before Oakland's city council passed its Flock-agreement policy — so this
  control cannot itself be downstream of the cameras being explained.</p>
  <div class="callout">
    <strong>A data-quality finding worth stating plainly:</strong> block-group
    Latino-share estimates carry a median margin of error equal to 65% of the point
    estimate (72% of Oakland block groups exceed 50%). Tract-level is better (38%
    median) but not clean. <strong>Tract is used as the primary unit for this reason</strong>;
    block group is reported only as a robustness check, and the regression
    corrects for the resulting attenuation bias (§4.3).
  </div>
</section>
""")

# 3. Empirical strategy
body_sections.append(f"""
<section id="strategy">
  <h2><span class="num">3</span>Empirical strategy</h2>
  <p>The outcome is camera count per tract, modeled as a negative binomial count
  process (Poisson is rejected — α is large and highly significant in both
  geographies, confirming overdispersion). The regressor of interest is tract
  Latino/Hispanic population share. Controls are chosen for a specific reason each,
  since the point of the exercise is to net out the facially race-neutral
  explanations a city or vendor would give for camera placement:</p>
  <ul class="limitations">
    <li><strong>Arterial road density</strong> (km of motorway/trunk/primary/secondary/tertiary
    road per km²) — Flock's own marketing describes siting logic keyed to entry/exit
    corridors and chokepoints.</li>
    <li><strong>log(median household income)</strong> — the standard socioeconomic
    confound.</li>
    <li><strong>Population density</strong> — more people mechanically implies more
    plausible camera sites.</li>
    <li><strong>Pre-treatment crime rate</strong> — "responding to crime" is the
    standard public justification for camera placement, so omitting it would leave
    any demographic coefficient contaminated by whatever crime is actually doing.</li>
  </ul>
  <p>Four specifications are reported: the negative-binomial baseline; the same
  model rescaled for known ACS measurement error in Latino share (§4.3); a spatial-lag
  model; and a spatial-error model (both via PySAL/<code>spreg</code>, on log(1+count)),
  since Moran's I on the baseline residuals detects spatial autocorrelation the
  baseline's standard errors do not account for. A geographically weighted regression
  (GWR) is reported as an exploratory check on whether the relationship is
  geographically uniform.</p>
</section>
""")

# 4. Results
gwr_lo, gwr_hi = T["gwr_local_range"]
body_sections.append(f"""
<section id="results">
  <h2><span class="num">4</span>Results</h2>

  <h3>4.1 &nbsp;The raw relationship is weak — and that is not the answer</h3>
  <p>Before any controls, Latino share and camera density are essentially
  uncorrelated in Oakland (Pearson r = 0.050, p = 0.59; Spearman ρ = 0.17 on raw
  counts, p = 0.068). This is the marginal relationship only. It is fully
  consistent with a real conditional relationship hiding behind confounders that
  happen to offset: Latino share correlates <em>negatively</em> with arterial road
  density (r = &minus;0.32) and income (r = &minus;0.48) in this sample — both of which
  independently predict fewer cameras — which can mask a positive demographic
  relationship until those factors are held fixed.</p>
  <figure>
    {inline_svg("fig2_raw_scatter")}
    <figcaption><strong>Figure 1.</strong> Raw relationship between tract Latino/Hispanic
    share and camera count (jittered for visibility), with an unconditional linear fit.
    Weak and not significant — see §4.2 for the controlled estimate.</figcaption>
  </figure>

  <h3>4.2 &nbsp;Controlling for siting rationale reverses the picture</h3>
  <p>Once arterial road density, income, population density, and pre-treatment crime
  are held constant, Latino share becomes a large, positive, and highly significant
  predictor of camera count:</p>
  {nb_table_html(T['nb'], 'Table 1. Negative binomial regression, camera count per tract (n = ' + str(T['n']) + ', HC1 robust SEs).')}
  <p>Arterial road density behaves as expected (more arterial road, more cameras).
  Population density is <em>negative</em> and significant — net of the other
  controls, denser tracts see fewer cameras, plausibly because dense, deep-interior
  residential tracts have less arterial-road frontage to place a camera on in the
  first place. The pre-treatment crime control is not significant in either
  geography (tract p = {p_fmt(T['nb']['crime_rate_per_km2_1000']['p'])}, block group
  p = {p_fmt(B['nb']['crime_rate_per_km2_1000']['p'])}) — "responding to crime" does
  not appear to independently explain Oakland's camera placement once the other
  factors are accounted for.</p>
  <figure>
    {inline_svg("fig1_map")}
    <figcaption><strong>Figure 2.</strong> Tract Latino/Hispanic share (blue, darker =
    higher) and individual camera locations (points) across Oakland. Descriptive
    only — the map does not net out the controls in Table 1.</figcaption>
  </figure>

  <h3>4.3 &nbsp;Robustness to spatial autocorrelation</h3>
  <p>Moran's I on the baseline model's residuals is statistically significant
  (I = {T['moran_residuals']['I']:.3f}, p = {p_fmt(T['moran_residuals']['p'])}),
  meaning the negative-binomial model's standard errors cannot be trusted as-is.
  Spatial-lag and spatial-error models (fit on log(1+camera count), since
  <code>spreg</code>'s estimators are continuous-outcome) confirm the Latino-share
  coefficient survives spatial correction: {sig_span(T['spatial_lag_latino']['p'], f"β = {T['spatial_lag_latino']['coef']:.2f} (spatial lag)")}
  and {sig_span(T['spatial_error_latino']['p'], f"β = {T['spatial_error_latino']['coef']:.2f} (spatial error)")},
  both p {p_fmt(max(T['spatial_lag_latino']['p'], T['spatial_error_latino']['p']))}.</p>

  <h3>4.4 &nbsp;Attenuation-bias correction</h3>
  <p>Because Latino share is itself an ACS estimate with known sampling error, a
  plain regression <em>understates</em> the true relationship (classical
  measurement-error attenuation), not the reverse. Applying a first-order
  reliability-ratio correction (Fuller 1987) — using each tract's ACS margin of
  error to estimate the share of observed variance in Latino share that is real
  signal versus sampling noise (reliability ratio = {T['attenuation']['reliability_ratio']:.3f}) —
  moves the coefficient from {T['attenuation']['naive_coef']:.2f} to
  {T['attenuation']['corrected_coef']:.2f}. This correction rescales the point
  estimate only; it does not produce a valid standard error, which is why Figure 3
  shows it as an open marker rather than with a confidence interval. It is reported
  as a magnitude check — evidence the naive estimate is, if anything, conservative —
  not a replacement for a full errors-in-variables model (e.g. SIMEX), which is
  future work.</p>
  <figure>
    {inline_svg("fig3_coefficients")}
    <figcaption><strong>Figure 3.</strong> The Latino-share coefficient across
    specifications. Filled markers show 95% confidence intervals; the open marker
    (attenuation-corrected) is a point correction only, without a valid CI — see
    §4.4. All four specifications are positive; three of four are directly
    significance-tested and significant at p &lt; 0.001.</figcaption>
  </figure>

  <h3>4.5 &nbsp;Is the relationship geographically uniform?</h3>
  <p>A geographically weighted regression finds the local Latino-share coefficient
  ranges from {gwr_lo:.2f} to {gwr_hi:.2f} across Oakland (mean {T['gwr_local_mean']:.2f}) —
  positive everywhere, with no sign reversal in any part of the city. The
  AICc-optimal bandwidth selected {T['gwr_bandwidth']:.0f} of {T['n']} tracts, which
  means this surface is close to a smooth, global relationship rather than a
  sharply localized one — read Figure 4 as "the relationship holds broadly, with
  mild regional variation in strength," not as evidence of a few outlier
  neighborhoods driving the result.</p>
  <figure>
    {inline_svg("fig4_gwr_map")}
    <figcaption><strong>Figure 4.</strong> GWR local coefficients on Latino share.
    Uniformly positive; the near-full-sample bandwidth means this reflects a mild,
    smooth spatial gradient rather than sharp local heterogeneity.</figcaption>
  </figure>
</section>
""")

# 5. Robustness — block groups
body_sections.append(f"""
<section id="robustness">
  <h2><span class="num">5</span>Robustness: block-group level</h2>
  <p>Repeating the full pipeline at block-group resolution ({B['n']} units, after
  dropping units with no ACS income data) reproduces the same pattern despite the
  block-group data being considerably noisier (§2): a positive, significant Latino-share
  coefficient in the negative-binomial baseline, surviving both spatial-lag and
  spatial-error correction.</p>
  {nb_table_html(B['nb'], 'Table 2. Negative binomial regression, camera count per block group (n = ' + str(B['n']) + ', HC1 robust SEs).')}
  <p>Variance inflation factors for all regressors are below 2.6 in both geographies
  (multicollinearity is not a concern), and the spatial models
  ({sig_span(B['spatial_lag_latino']['p'], f"lag β = {B['spatial_lag_latino']['coef']:.2f}")},
  {sig_span(B['spatial_error_latino']['p'], f"error β = {B['spatial_error_latino']['coef']:.2f}")})
  again confirm the tract-level result is not an artifact of geography choice.</p>
</section>
""")

# 6. Race and class horse race
def rc_table_html(model: dict, rows: list, caption: str) -> str:
    trs = []
    for var, label in rows:
        d = model[var]
        trs.append(
            f"<tr><td>{label}</td><td>{d['coef']:.3f}</td><td>{d['se']:.3f}</td>"
            f"<td>{sig_span(d['p'], p_fmt(d['p']))}</td></tr>"
        )
    return f"""
<div class="table-wrap">
<table>
<caption>{caption}</caption>
<thead><tr><th>Variable</th><th>Coef.</th><th>SE</th><th>p</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
</div>
"""


rc_rows = [
    ("latino_share", "Latino/Hispanic share"),
    ("black_share", "Black share (non-Hispanic)"),
    ("asian_share", "Asian share (non-Hispanic)"),
    ("poverty_rate", "Poverty rate"),
    ("arterial_km_per_km2", "Arterial road, km per km²"),
    ("pop_density_per_km2_1000", "Population density, 1,000s per km²"),
    ("crime_rate_per_km2_1000", "Pre-treatment crime rate, 1,000s per km²"),
]
body_sections.append(f"""
<section id="race-class">
  <h2><span class="num">6</span>Is the effect specific to Latino/Hispanic share,
  or a general race/class pattern?</h2>
  <p>The models in §4 include income as the only class proxy and say nothing
  about whether camera density also tracks Black or Asian population share, or
  whether "Latino share" is really standing in for poverty generally. This is
  tested directly by adding non-Hispanic White, Black, and Asian shares (White
  as the omitted reference category — the four groups are mutually exclusive, so
  including all of them alongside a constant would be collinear) and a
  poverty-rate variable to the baseline specification.</p>
  <p>Raw, unconditional correlations with camera density are weak for every
  demographic variable tested — Latino share ({RC['correlations']['latino_share']:.3f}),
  Black share ({RC['correlations']['black_share']:.3f}), Asian share
  ({RC['correlations']['asian_share']:.3f}), White share
  ({RC['correlations']['white_share']:.3f}), poverty rate
  ({RC['correlations']['poverty_rate']:.3f}), income
  ({RC['correlations']['B19013_001E']:.3f}) — none of them tell a story on their
  own. The controlled model does:</p>
  {rc_table_html(RC['model_b_race_and_poverty'], rc_rows, 'Table 3. Negative binomial regression with race shares and poverty rate, camera count per tract (n = ' + str(RC['n']) + ', White-non-Hispanic as reference, HC1 robust SEs).')}
  <p><strong>Latino share is the only demographic term that is statistically
  robust</strong>, essentially unchanged from §4's estimate. Black share and Asian
  share are both negative in sign and not statistically distinguishable from
  zero (i.e., from the White-non-Hispanic reference group). Poverty rate is also
  not significant, and switches sign depending on what else is in the model — a
  poverty-only specification with no race terms at all (not shown in the table)
  is itself not significant (p = 0.123). Class alone does not explain Oakland's
  camera placement any better than the race terms do; only Latino share does.</p>
  <p>Two honest caveats on the null results for Black and Asian share, not just
  the Latino result: this sample has less variation in Black share
  (mean {RC['descriptives']['black_share']['mean']:.2f}, SD
  {RC['descriptives']['black_share']['std']:.2f}) and Asian share (SD
  {RC['descriptives']['asian_share']['std']:.2f}) than in Latino share (SD
  {RC['descriptives']['latino_share']['std']:.2f}) — no Oakland tract is as
  overwhelmingly Black- or Asian-majority as some are Latino-majority, which
  lowers statistical power to detect an effect on those terms even if a true one
  exists. And n = 114 tracts is not a large sample for a five-covariate model.
  "Not statistically significant" here means the data cannot rule out zero, not
  that a Black-share or class effect has been ruled out.</p>
</section>
""")

# 7. Multi-city expansion
per_city = PC["per_city_slope"]
n_per_city = PC["n_per_city"]
oak_slope = per_city["Oakland"]
sig_cities = [c for c, d in per_city.items() if d["p"] < 0.05]
CC = PC["crime_controlled"]
n_cities_total = len(n_per_city)
cc_attempted = len(CC["cities"])
cc_converged = sorted(CC["per_city_slope"].keys())
cc_failed = sorted(set(CC["cities"]) - set(cc_converged))

city_rows_html = []
for city in sorted(per_city.keys(), key=lambda c: per_city[c]["coef"], reverse=True):
    d = per_city[city]
    n = n_per_city[city]
    city_rows_html.append(
        f"<tr><td>{city}</td><td>{n['n']}</td><td>{n['cameras']}</td>"
        f"<td>{n['latino_mean']:.0%}</td><td>{d['coef']:.2f}</td>"
        f"<td>{d['implied_p10_p90_effect']:.2f}</td>"
        f"<td>{sig_span(d['p'], p_fmt(d['p']))}</td></tr>"
    )

body_sections.append(f"""
<section id="multi-city">
  <h2><span class="num">7</span>Does Oakland's pattern generalize?</h2>
  <p>Oakland is one city. The same acquisition and spatial-join pipeline has
  now been run for {n_cities_total - 1} more — El Paso, Fresno, Phoenix,
  Albuquerque, San Jose, Fort Worth, Denver, Sacramento, Seattle, Dallas,
  Kansas City, San Diego, Columbus, and Charlotte, chosen for confirmed
  OSM/DeFlock camera coverage and a range of Latino population shares — for
  {sum(v['n'] for v in n_per_city.values())} tracts total.</p>

  <p>A single joint model — one shared Latino-share slope across all
  {n_cities_total} cities plus city fixed effects — still does not converge
  numerically at this scale (Seattle's unusually narrow real-world Latino-share
  range, 0.6%-26% versus 20+ points of spread elsewhere, makes the joint
  Hessian singular). Each city's own independent regression is reported
  instead, as before — the robust approach, at the cost of not testing
  cross-city equality in one step.</p>

  <p><strong>Oakland remains the only city where the Latino-share effect is
  itself statistically distinguishable from zero</strong>
  (β = {oak_slope['coef']:.2f}, p {p_fmt(oak_slope['p'])}). Two more cities now
  sit close to that line without quite crossing it: San Diego
  (β = {per_city["San Diego"]["coef"]:.2f}, p = {p_fmt(per_city["San Diego"]["p"])},
  recalibrated effect {per_city["San Diego"]["implied_p10_p90_effect"]:.2f}) and
  Seattle (β = {per_city["Seattle"]["coef"]:.2f}, p = {p_fmt(per_city["Seattle"]["p"])},
  recalibrated effect {per_city["Seattle"]["implied_p10_p90_effect"]:.2f} — Seattle's
  raw coefficient looks enormous only because of that narrow range; the
  recalibrated, P10-to-P90 version is what belongs next to Oakland's
  {oak_slope['implied_p10_p90_effect']:.2f}). Every other city's confidence
  interval is wide enough to include zero, and none show a significant
  <em>negative</em> Latino-share effect.</p>

  <figure>
    {inline_svg("fig5_per_city_slopes")}
    <figcaption><strong>Figure 5.</strong> Implied Latino-share coefficient by
    city (independent per-city NB models, no crime control). Filled marker =
    individually significant at p &lt; 0.05. Oakland is the only city that
    clears that bar; San Diego and Seattle come closest without doing so.</figcaption>
  </figure>

  <div class="table-wrap">
  <table>
  <caption>Table 4. Per-city implied Latino-share slope (independent per-city NB models).</caption>
  <thead><tr><th>City</th><th>n tracts</th><th>Cameras</th><th>Mean Latino share</th>
  <th>Coef.</th><th>Implied effect, P10&rarr;P90</th><th>p</th></tr></thead>
  <tbody>{''.join(city_rows_html)}</tbody>
  </table>
  </div>

  <p>One obvious candidate explanation for Oakland looking different — its
  model has a crime control and most other cities didn't — has gotten a
  fuller test. Real, official geocoded crime feeds have now been tracked down
  for 7 of the 14 other cities:</p>
  <ul class="limitations">
    <li><strong>Fresno</strong> — the City of Fresno's own ArcGIS Feature Service,
    point-geocoded, 31,667 incidents. Coverage is only 2022-01 to 2023-07,
    roughly two years stale relative to the camera snapshot.</li>
    <li><strong>Albuquerque</strong> — the city's own ArcGIS MapServer,
    point-geocoded, 111,642 incidents, but only a rolling ~6-month window.</li>
    <li><strong>Phoenix</strong> — a real CSV feed (624,148 incidents,
    2015-2025) geocoded only to a police "grid" cell, area-weighted onto
    tracts via the city's separate grid-polygon service.</li>
    <li><strong>Fort Worth</strong> — the city's own ArcGIS point layer,
    631,346 incidents, 2016-2026. The per-city regression with this control
    added did not converge (singular covariance) and is excluded from the
    crime-controlled results below.</li>
    <li><strong>Denver</strong> — the city's official ArcGIS point layer,
    375,777 incidents, 2021-2026.</li>
    <li><strong>Sacramento</strong> — the city's official ArcGIS point layer,
    but only calendar-year 2025 (32,529 geocoded incidents) — a single-year
    snapshot. The per-city regression with this control added also did not
    converge and is excluded below.</li>
    <li><strong>Seattle</strong> — the city's official Socrata feed,
    1,156,809 geocoded incidents, 2008-2026 (a small number of clearly
    erroneous pre-2008 dates and "REDACTED"/sentinel coordinates were
    filtered out).</li>
    <li><strong>El Paso, San Jose, Dallas, Kansas City, San Diego, Columbus,
    Charlotte</strong> — not yet searched (San Jose: a real feed exists but
    is only geocoded to block-range address strings, not points, and was
    skipped rather than geocoding thousands of addresses).</li>
  </ul>
  <p>Each feed's crime count was annualized (count &divide; years of coverage
  &divide; km²) so cities with very different window lengths sit on one
  comparable scale — necessary but imperfect, since it assumes each city's
  crime geography is roughly stable over its own window.</p>
  <p>Of the 8 cities with a crime feed, {len(cc_converged)} converge with the
  control added ({', '.join(cc_converged)}); {', '.join(cc_failed)} do not and
  are excluded from this specific comparison. <strong>Oakland's Latino-share
  effect survives controlling for crime, essentially unchanged</strong>
  (β = {CC['per_city_slope']['Oakland']['coef']:.2f}, p
  {p_fmt(CC['per_city_slope']['Oakland']['p'])}, versus
  {oak_slope['coef']:.2f} without crime) — and Oakland's own crime-rate
  coefficient is not significant
  ({sig_span(CC['per_city_crime_coef']['Oakland']['p'], f"p = {p_fmt(CC['per_city_crime_coef']['Oakland']['p'])}")}),
  consistent with §4.2. Crime rate <em>is</em> a large, significant predictor
  in Fresno ({sig_span(CC['per_city_crime_coef']['Fresno']['p'], f"β = {CC['per_city_crime_coef']['Fresno']['coef']:.1f}")})
  and Phoenix ({sig_span(CC['per_city_crime_coef']['Phoenix']['p'], f"β = {CC['per_city_crime_coef']['Phoenix']['coef']:.1f}")}) —
  worth reading cautiously given those two cities' crime data are, respectively,
  stale and grid-approximated (see list above) — but not in Albuquerque,
  Denver, or Seattle. The missing-crime-control explanation for Oakland
  looking different does not hold up in any of the cities where the
  comparison could actually be run.</p>

  <figure>
    {inline_svg("fig6_per_city_slopes_crime_controlled")}
    <figcaption><strong>Figure 6.</strong> Implied Latino-share coefficient by
    city, with the crime control included. Oakland remains the only
    individually significant city among those where the model converges.</figcaption>
  </figure>

  <p><strong class="flag">This is still not a story of a universal,
  generalizable pattern</strong> — ruling out the missing-crime-control
  explanation narrows the field further, it doesn't resolve it. What's left:
  El Paso's mean tract Latino share is 82% (versus Oakland's 26%), leaving
  very little of the city as a genuine comparison group; El Paso itself has an
  active city-council effort to <em>end</em> its Flock agreements (§10) — a
  very different institutional moment than Oakland's expanding program;
  Fresno's and Phoenix's crime controls are noisier than Oakland's; San
  Diego's and Seattle's marginal near-significance (Table 4) suggests some
  cities may simply be underpowered rather than genuinely null; and it may
  simply be that Oakland's pattern is Oakland-specific. Finding crime data for
  the remaining 7 cities, and continuing to add more, is the natural next step
  before treating either "Oakland generalizes" or "Oakland is an outlier" as
  settled.</p>
</section>
""")

# 8. Multi-city race/class horse race
MCRC = json.loads((HERE / "multi_city_race_class_results.json").read_text())
mcrc_vars = [
    ("latino_share", "Latino/Hispanic share"),
    ("black_share", "Black share (non-Hispanic)"),
    ("asian_share", "Asian share (non-Hispanic)"),
    ("poverty_rate", "Poverty rate"),
]
mcrc_cities = sorted(MCRC["per_variable_per_city"]["latino_share"].keys())

mcrc_rows = []
n_sig = 0
n_total = 0
for var_key, var_label in mcrc_vars:
    for city in mcrc_cities:
        d = MCRC["per_variable_per_city"][var_key][city]
        n_total += 1
        if d["p"] < 0.05:
            n_sig += 1
        mcrc_rows.append(
            f"<tr><td>{var_label}</td><td>{city}</td><td>{d['coef']:.2f}</td>"
            f"<td>{d['implied_p10_p90_effect']:.2f}</td>"
            f"<td>{sig_span(d['p'], p_fmt(d['p']))}</td></tr>"
        )

body_sections.append(f"""
<section id="multi-city-race-class">
  <h2><span class="num">8</span>Does the race/class pattern generalize?</h2>
  <p>§6 asked whether Oakland's Latino-share effect was really a general
  nonwhite or low-income pattern in disguise, and found it wasn't — Black
  share, Asian share, and poverty rate were all null in Oakland once Latino
  share was in the model. The same question is worth asking across cities:
  is <em>any</em> demographic pattern general, or is each city's story its
  own?</p>
  <p>Fitting each of the {len(mcrc_cities)} cities' own model with Latino share,
  Black share, Asian share, and poverty rate together (no crime control, for
  the same reason as §7) gives per-city coefficients for every variable.
  Unlike §7's Latino-only spec, <strong>the joint pooled version of this model
  — one shared slope per variable across all {len(mcrc_cities)} cities, plus
  city fixed effects — does converge</strong>, and its headline result is
  worth stating on its own: pooled across every city, with one shared slope,
  <strong>Asian share is a significant positive predictor of camera count</strong>
  ({sig_span(MCRC['pooled_homogeneous']['asian_share']['p'], f"β = {MCRC['pooled_homogeneous']['asian_share']['coef']:.2f}")},
  p {p_fmt(MCRC['pooled_homogeneous']['asian_share']['p'])}) — Latino share, Black
  share, and poverty rate are not significant in this pooled, one-slope-fits-all
  version (p = {p_fmt(MCRC['pooled_homogeneous']['latino_share']['p'])},
  {p_fmt(MCRC['pooled_homogeneous']['black_share']['p'])}, and
  {p_fmt(MCRC['pooled_homogeneous']['poverty_rate']['p'])} respectively). That's a
  genuinely different headline number than §7's city-by-city Latino result, and
  both are reported because they answer different questions: the pooled model
  asks "is there one shared effect across all cities," the per-city models
  (below, and Table 5) ask "does any individual city show an effect" — Oakland's
  Latino-share result is real and city-specific without being the kind of
  shared, poolable effect Asian share turns out to be here.</p>
  <p>Raw per-city coefficients aren't directly comparable to each other, either,
  because each city has a very different real-world range for these variables
  — Albuquerque's Black share, for instance, only spans roughly 0.2% to 6% of
  a tract's population, versus Oakland's 5% to 37%, so the same underlying
  effect would show up as a much larger per-percentage-point coefficient in
  Albuquerque purely from the narrower range. The table below reports both the
  raw coefficient and the <strong>implied effect of moving a tract from the
  city's own 10th to 90th percentile</strong> on that variable — the honest,
  comparable quantity.</p>
  <div class="table-wrap">
  <table>
  <caption>Table 5. Per-city coefficient for each demographic variable (independent per-city NB models).</caption>
  <thead><tr><th>Variable</th><th>City</th><th>Coef. (per unit share)</th>
  <th>Implied effect, P10&rarr;P90</th><th>p</th></tr></thead>
  <tbody>{''.join(mcrc_rows)}</tbody>
  </table>
  </div>

  <figure>
    {inline_svg("fig7_race_class_matrix")}
    <figcaption><strong>Figure 7.</strong> The same 60 results as Table 5, as
    a grid: rows are cities (sorted by how many of their four coefficients are
    significant), columns are the four demographic variables. Dot size is the
    implied P10-to-P90 effect magnitude; filled dots are significant at
    p &lt; 0.05, colored by sign. San Diego, Albuquerque, and Sacramento carry
    the most significant cells; Asian share (third column) has the most
    filled dots of any variable, all the same color.</figcaption>
  </figure>

  <p>{n_sig} of these {n_total} city-variable combinations are significant at
  p &lt; 0.05 — about {n_sig / (n_total * 0.05):.0f}x the roughly
  {n_total * 0.05:.0f} expected by chance alone at that threshold. That's
  suggestive of real signal beyond noise, though still not confirmatory with no
  multiple-comparison correction applied and the four variables within a city
  sharing the same outcome and overlapping geography.</p>
  <p><strong>Asian share is now the most consistently-replicating per-city
  signal</strong>, matching its pooled significance above: positive and
  significant in four separate cities —
  Charlotte ({p_fmt(MCRC['per_variable_per_city']['asian_share']['Charlotte']['p'])},
  implied effect {MCRC['per_variable_per_city']['asian_share']['Charlotte']['implied_p10_p90_effect']:.2f}),
  Dallas ({p_fmt(MCRC['per_variable_per_city']['asian_share']['Dallas']['p'])},
  implied effect {MCRC['per_variable_per_city']['asian_share']['Dallas']['implied_p10_p90_effect']:.2f}),
  San Diego ({p_fmt(MCRC['per_variable_per_city']['asian_share']['San Diego']['p'])},
  implied effect {MCRC['per_variable_per_city']['asian_share']['San Diego']['implied_p10_p90_effect']:.2f}),
  and Seattle ({p_fmt(MCRC['per_variable_per_city']['asian_share']['Seattle']['p'])},
  implied effect {MCRC['per_variable_per_city']['asian_share']['Seattle']['implied_p10_p90_effect']:.2f})
  — no sign reversals anywhere, unlike the earlier 10-city read where Albuquerque's
  Asian-share point estimate leaned negative (it is no longer significant at 15
  cities).</p>
  <p><strong>Black share replicates in three cities, all positive</strong>:
  Albuquerque ({p_fmt(MCRC['per_variable_per_city']['black_share']['Albuquerque']['p'])},
  implied effect {MCRC['per_variable_per_city']['black_share']['Albuquerque']['implied_p10_p90_effect']:.2f}),
  Phoenix ({p_fmt(MCRC['per_variable_per_city']['black_share']['Phoenix']['p'])},
  implied effect {MCRC['per_variable_per_city']['black_share']['Phoenix']['implied_p10_p90_effect']:.2f}),
  and Sacramento ({p_fmt(MCRC['per_variable_per_city']['black_share']['Sacramento']['p'])},
  implied effect {MCRC['per_variable_per_city']['black_share']['Sacramento']['implied_p10_p90_effect']:.2f}).
  <strong>Latino share also now replicates in three cities</strong>, not just
  Oakland: Sacramento
  ({p_fmt(MCRC['per_variable_per_city']['latino_share']['Sacramento']['p'])})
  and San Diego
  ({p_fmt(MCRC['per_variable_per_city']['latino_share']['San Diego']['p'])})
  join Oakland once Black share, Asian share, and poverty are controlled for
  jointly — worth flagging directly against §7, where neither Sacramento's nor
  San Diego's Latino-share coefficient alone was significant (San Diego came
  close, p = {p_fmt(per_city["San Diego"]["p"])}). That difference is
  informative, not contradictory: net of the other race shares and poverty,
  the Latino-share estimate sharpens in both cities, suggesting the simpler §7
  spec was somewhat confounded by correlation between each city's Latino and
  other-race populations there, not that either number is wrong. San Diego is
  the only city with three simultaneously significant demographic terms
  (Latino, Asian, and poverty), each positive.</p>
  <p>Poverty rate is significant in four cities but without a consistent sign
  — positive in Charlotte, San Diego, and San Jose (poorer tracts get more
  cameras) and negative in Albuquerque (poorer tracts get fewer). Three-to-one
  leans toward "more," but this is the weakest and least coherent of the four
  variables, and still the best evidence that there's no simple class story
  here in either direction.</p>
  <p><strong class="flag">The pattern across cities is now genuinely more than
  one city's story, just not a single unified one</strong>: Asian share
  replicates across four cities and holds up as a significant pooled effect;
  Black share replicates across three; Latino share, once thought to be purely
  Oakland's, now replicates in two more. No single demographic variable
  explains camera placement the same way in <em>every</em> city, and poverty
  never coheres into a class story — but "each city's result is its own
  finding, unrelated to every other city's" is no longer the most accurate
  summary either. A formal multiple-comparison correction and more cities are
  the right next step before calling any one of these three patterns settled.</p>
</section>
""")

# 9. Hierarchical (multilevel) model
HPL = HIER["population_level"]


def hier_sig(var: str) -> bool:
    return HPL[var]["hdi_3%"] > 0 or HPL[var]["hdi_97%"] < 0


HIER_VAR_LABELS = [
    ("b_latino", "Latino/Hispanic share (population mean)"),
    ("b_black", "Black share (non-Hispanic)"),
    ("b_asian", "Asian share (non-Hispanic)"),
    ("b_poverty", "Poverty rate"),
    ("b_arterial", "Arterial road, km per km²"),
    ("b_income", "log(median household income)"),
    ("b_density", "Population density, 1,000s per km²"),
    ("sigma_a_city", "SD of random intercept across cities"),
    ("sigma_b_city", "SD of random Latino-share slope across cities"),
    ("alpha", "NB dispersion (α)"),
]
hier_rows = []
for var, label in HIER_VAR_LABELS:
    v = HPL[var]
    sig = hier_sig(var)
    cls = "sig" if sig else ""
    hier_rows.append(
        f"<tr><td>{label}</td><td>{v['mean']:.3f}</td>"
        f"<td>[{v['hdi_3%']:.3f}, {v['hdi_97%']:.3f}]</td>"
        f"<td><span class=\"{cls}\">{'excludes 0' if sig else 'includes 0'}</span></td></tr>"
    )

body_sections.append(f"""
<section id="hierarchical">
  <h2><span class="num">9</span>A hierarchical model, instead of picking between "one number" and "fifteen numbers"</h2>
  <p>§7 and §8 kept running into the same fork: a single pooled slope shared
  by every city (loses real city-to-city variation, and for the Latino-only
  spec never even converges), or a separate regression per city (numerically
  robust, but treats Seattle's 177 tracts as no more or less informative than
  Oakland's 114, so a city with a narrow demographic range and modest data
  can produce a wild, barely-constrained point estimate with no way to say
  how much to trust it relative to the others). A hierarchical
  (multilevel) model is the standard fix for exactly this tension: each
  city's Latino-share slope is estimated as its own value <em>and</em> as a
  draw from a shared population distribution, so noisy per-city estimates get
  pulled toward the population mean by an amount the data themselves
  determine — precise, well-supported estimates (Oakland) barely move; noisy
  ones (Seattle) move a lot.</p>
  <p>The model is Bayesian (PyMC, NUTS sampler): camera count is negative
  binomial; Latino share gets a random intercept and random slope by city
  (modeled as independent, not a correlated pair via an LKJ prior — with only
  15 cities, a full covariance structure would be poorly identified); Black
  share, Asian share, poverty rate, and the controls (arterial road density,
  income, population density) are population-level (fixed) effects only, for
  the same reason — 15 groups can't realistically support giving every one of
  four demographic variables its own random slope. Sampling diagnostics were
  clean: max R-hat = {HIER['diagnostics']['max_rhat']:.3f} (1.00 is ideal, under 1.01 is
  the standard threshold), minimum effective sample size
  {HIER['diagnostics']['min_ess_bulk']:.0f} across {HIER['n_total']} tracts in
  {HIER['n_cities']} cities, {HIER['diagnostics']['n_divergent']} divergent
  transitions.</p>

  <div class="table-wrap">
  <table>
  <caption>Table 6. Population-level (fixed-effect) posterior estimates, 94% credible intervals.</caption>
  <thead><tr><th>Variable</th><th>Mean</th><th>94% CI</th><th></th></tr></thead>
  <tbody>{''.join(hier_rows)}</tbody>
  </table>
  </div>

  <p>Three results stand out. First, <strong>the population-average
  Latino-share slope is small and includes zero</strong>
  ({HPL['b_latino']['mean']:.2f}, 94% CI
  [{HPL['b_latino']['hdi_3%']:.2f}, {HPL['b_latino']['hdi_97%']:.2f}]) — but
  <strong>the spread of that slope across cities is large and clearly excludes
  zero</strong> ({HPL['sigma_b_city']['mean']:.2f}, 94% CI
  [{HPL['sigma_b_city']['hdi_3%']:.2f}, {HPL['sigma_b_city']['hdi_97%']:.2f}]).
  Read together, this is a genuinely different — and more accurate — summary
  than either "there's a universal Latino-share effect" or "there's no effect
  anywhere": there is real, credible variation from city to city, some cities
  sit well above zero and some below, and the average across all of them
  happens to land near zero. That is exactly what a large positive Oakland
  alongside a scatter of near-zero and mildly-negative other cities should
  produce, and the model recovers it directly instead of it being an artifact
  of how the per-city results happened to get listed in a table.</p>
  <p>Second, <strong>Asian share's population-level effect is confirmed by a
  completely different method</strong>
  ({HPL['b_asian']['mean']:.2f}, 94% CI
  [{HPL['b_asian']['hdi_3%']:.2f}, {HPL['b_asian']['hdi_97%']:.2f}], clearly
  excludes zero) — matching §8's simpler pooled-NB finding, now with a
  Bayesian model built specifically to handle the cross-city structure this
  question actually has.</p>
  <p>Third, <strong>poverty rate comes out positive and (just barely)
  significant here</strong>
  ({HPL['b_poverty']['mean']:.2f}, 94% CI
  [{HPL['b_poverty']['hdi_3%']:.2f}, {HPL['b_poverty']['hdi_97%']:.2f}], lower
  bound just above zero) — where §8's simpler pooled model found no
  significant poverty effect at all. This isn't a contradiction so much as a
  refinement: this model's random intercepts absorb each city's own baseline
  camera intensity separately from the poverty-camera relationship, so the
  poverty coefficient here is less likely to be confounded with unmodeled
  city-level differences than it was in the flat pooled specification. Given
  how close the lower bound sits to zero, this should be read as suggestive
  support for a real, modest, positive poverty effect population-wide — not
  proof of one. Black share remains not significant at the population level
  ({HPL['b_black']['mean']:.2f}, 94% CI includes zero), and population density
  remains robustly negative, as in every earlier specification.</p>

  <figure>
    {inline_svg("fig8_shrinkage")}
    <figcaption><strong>Figure 8.</strong> Shrinkage plot: each city's
    independent per-city Latino-share estimate (rust, same specification as
    Table 5 — includes Black share, Asian share, and poverty rate as
    covariates, for a fair comparison) next to its hierarchical,
    partially-pooled counterpart (blue), with the population-level 94%
    credible interval shown as a band. Seattle's estimate — the least
    constrained by data, on a demographic range too narrow to pin the slope
    down well — shrinks the most, from 9.6 to roughly 0.6. Oakland and San
    Diego, both well-supported by their own data, barely move.</figcaption>
  </figure>

  <p><strong class="flag">This is the most statistically defensible answer
  this project has produced to "does it generalize"</strong>, and it's a
  nuanced one: not one shared effect, not fifteen unrelated ones, but real
  between-city heterogeneity in the Latino-share relationship with Oakland
  and San Diego anchoring the positive end, a confirmed population-level
  Asian-share effect, and suggestive evidence of a population-level poverty
  effect that the simpler pooled model had missed. The obvious next step is
  extending this same hierarchical structure to more cities, which would let
  the model estimate the between-city variance components with much more
  precision than 15 groups currently allow.</p>
</section>
""")

# 10. Limitations
body_sections.append("""
<section id="limitations">
  <h2><span class="num">10</span>Limitations</h2>
  <ul class="limitations">
    <li><strong class="flag">Correlational, not causal.</strong> This design nets out
    observable confounders; it cannot distinguish deliberate targeting from a
    facially neutral rule (e.g., "place cameras on arterial roads") that happens to
    correlate with demographics through Oakland's own settlement and zoning
    history. Reverse causality is also not resolvable here — cameras placed in
    response to crime, and crime correlated with demographics, is observationally
    similar to cameras placed in response to demographics directly.</li>
    <li><strong class="flag">Ecological, not individual.</strong> A tract-level
    coefficient describes tracts, not people. It says nothing about which
    individuals are more or less exposed to any given camera.</li>
    <li><strong class="flag">Camera-dataset provenance.</strong> OSM/DeFlock
    coverage depends on volunteer mapping activity, which itself correlates with
    income and education in the broader VGI (volunteered geographic information)
    literature. An undercount in a neighborhood could reflect fewer mappers, not
    fewer cameras — in either direction.</li>
    <li><strong class="flag">§4's spatial and attenuation diagnostics are
    Oakland-only.</strong> Moran's I, spatial-lag/error correction, and the
    ACS-attenuation correction (§4.3-4.4) were run for Oakland specifically
    and not repeated for the other 14 cities — it's unknown whether their
    per-city estimates would similarly survive spatial correction.</li>
    <li><strong class="flag">Single snapshot, mostly.</strong> Every city's
    camera count is a single point-in-time pull (Aug 2026). Oakland now has a
    second, later snapshot (§11) as the start of a prospective panel, but
    there isn't yet a real installation-date time series for any city.</li>
    <li><strong class="flag">GWR bandwidth.</strong> The near-full-sample optimal
    bandwidth (§4.5) means Figure 4 should not be over-read as showing sharp
    neighborhood-level heterogeneity — and this diagnostic exists for Oakland only.</li>
    <li><strong class="flag">The Black/Asian-share nulls in §6 are underpowered,
    not confirmatory.</strong> Lower variance in those shares in Oakland
    specifically means the data are less able to detect an effect on those
    terms even if one exists; "not significant" should not be read as "ruled
    out" — and indeed Asian share turns out to be significant once more
    cities are added (§8-9).</li>
    <li><strong class="flag">Crime data exists for 8 of 15 cities, at
    inconsistent vintages and resolutions, and the crime-controlled regression
    only converges for 6 of those 8.</strong> Fresno's window is stale
    (2022-2023), Sacramento's is a single year, Phoenix's is grid- not
    point-geocoded — see §7 for the full list. Seven cities have no crime data
    at all.</li>
    <li><strong class="flag">No formal multiple-comparison correction.</strong>
    §8's 60-test grid and the various per-city regressions throughout are
    reported with raw p-values; a Bonferroni or FDR correction would shrink
    the set of "significant" findings, and hasn't been applied anywhere in
    this report.</li>
  </ul>
</section>
""")

# 11. Planned extension: DiD
body_sections.append("""
<section id="did">
  <h2><span class="num">11</span>Planned extension: difference-in-differences
  <span class="status-pill blocked">Not yet viable</span></h2>
  <p>Oakland's city council passed a Flock-agreement policy on 2025-12-16, after an
  earlier version of the same contract failed on 2025-12-02 — a real, externally
  dated policy event that could anchor an event-study design (camera count ~ Post ×
  Latino share, with tract and quarter fixed effects), and several other cities in
  this project's tracked dataset show the opposite move (e.g. a pending item in El
  Paso to end existing Flock agreements), which would support a staggered
  multi-city design using heterogeneity-robust estimators (Callaway &amp; Sant'Anna
  2021; Sun &amp; Abraham 2021) rather than plain two-way fixed effects.</p>
  <p>Before building on it, this was tested directly: pulling the full OSM edit
  history for a sample of Oakland's camera nodes. The result ruled the near-term
  version out. First-tagged-as-ALPR dates cluster heavily on a small number of
  specific days rather than spreading organically over time — 30% of a 120-node
  sample were first tagged on a single day (2024-11-20), consistent with a mapper's
  bulk survey pass, not 36 independent camera installations on one day. Using OSM
  tag dates as an installation-date panel would attribute mapping-campaign timing to
  Flock installation timing — backwards from what the design needs.</p>
  <p>The sound path is a <em class="term">prospective</em> panel: recurring
  Overpass snapshots, accumulated from here forward, so that a real installation-date
  time series exists to build on. That process has started, manually rather
  than on an automated schedule: a second Oakland snapshot on 2026-08-23 found
  880 cameras, up from 856 on 2026-08-13 — one data point, not yet a usable
  panel, but the beginning of one. The DiD extension is still realistically a
  multi-month-out deliverable; it needs enough snapshots to distinguish a real
  installation trend from month-to-month mapper-activity noise, which a
  single follow-up observation can't do.</p>
</section>
""")

# 12. Conclusion
body_sections.append(f"""
<section id="conclusion">
  <h2><span class="num">12</span>Conclusion</h2>
  <p>In Oakland, the unconditional relationship between neighborhood Latino share
  and Flock/ALPR camera density is negligible. Once the standard, facially neutral
  siting rationale — arterial roads, income, density, crime — is held constant, the
  relationship becomes large, positive, and robust across four independent
  specifications, two geographic resolutions, and a race/class horse race that
  isolates it to Latino share specifically. That reversal is itself a central
  empirical finding, and is exactly the kind of pattern a purely descriptive map or
  a raw correlation would miss.</p>
  <p>It is, so far, a finding specific to Oakland — but not a finding isolated
  to Oakland. Extending the same pipeline to fourteen more cities found
  Oakland to be the only one where the simple Latino-share effect is itself
  statistically distinguishable from zero, with San Diego and Seattle close
  behind. The race/class extension across all fifteen cities turned up more:
  a jointly-pooled model converges here and finds Asian share is a
  significant, positive predictor across the whole sample, replicating
  individually in four cities; Black share replicates in three; and Latino
  share itself, once other race shares are controlled for, replicates beyond
  Oakland in two more cities.</p>
  <p>A hierarchical model (§9), built to stop forcing a choice between "one
  number for every city" and "fifteen unrelated numbers," gives the most
  statistically honest version of this answer: city-to-city variation in the
  Latino-share effect is itself real and substantial (not just estimation
  noise), even though the population average sits close to zero; Asian
  share's population-level effect replicates under a completely different
  modeling approach; and poverty rate — dismissed in §8 as incoherent — turns
  out to have a real, modest, positive population-level effect once city-level
  baselines are properly separated from it. Fifteen cities and inconsistent
  crime-data coverage is still not enough to call any of these patterns
  settled — but "each city's result is its own, unrelated finding" is no
  longer the most accurate summary of what the data show. This supports
  further inquiry — more cities (which would let the hierarchical model
  estimate its variance components with real precision), consistent crime
  data, formal multiple-comparison correction, the DiD extension once panel
  data exists, and matched comparisons with cities that have rejected Flock
  contracts — more than it supports a settled conclusion in either direction.</p>
</section>
""")

body = "\n".join(body_sections)

env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(HERE)))
template = env.from_string((HERE / "template.html.j2").read_text())
html = template.render(
    title="Camera Placement and Latino Population Share",
    subtitle="A tract-level econometric analysis of Flock/ALPR camera siting, from a single-city deep "
              "dive in Oakland to a 15-city hierarchical Bayesian model",
    data_vintage="Cameras Aug 2026 &middot; ACS 2023 5-yr &middot; crime data city-specific, dated where used (&sect;7)",
    abstract=abstract,
    body=body,
)

out_path = HERE / "index.html"
out_path.write_text(html)
print(f"wrote {out_path} ({len(html):,} bytes)")
