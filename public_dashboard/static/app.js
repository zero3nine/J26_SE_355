'use strict';
const $ = (selector) => document.querySelector(selector);
const escapeHTML = (value) =>
  String(value ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
const fmt = (n) => Number(n).toLocaleString('en-US');
const pct = (n) => `${Number(n).toFixed(1)}%`;
const icons = {
  overview:
    '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  careers: '<path d="M4 8h16v12H4zM9 8V4h6v4M4 12h16M10 12v3h4v-3"/>',
  trends: '<path d="M3 4v16h18M6 15l5-5 4 3 6-8M16 5h5v5"/>',
  markets:
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c6 5 6 13 0 18M12 3c-6 5-6 13 0 18"/>',
  connections:
    '<circle cx="5" cy="12" r="3"/><circle cx="18" cy="5" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8 10 7-4M8 14l7 4"/>',
  methods: '<path d="M9 3h6M10 3v6L4 19c-.5 1 .5 2 1.5 2h13c1 0 2-1 1.5-2L14 9V3M7 15h10"/>',
  jobs: '<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 5V3h8v2M8 10h8M8 14h8M8 18h4"/>',
  skills: '<path d="m8 5-6 7 6 7M16 5l6 7-6 7M14 3l-4 18"/>',
};
const icon = (name) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.skills}</svg>`;
const views = [
  ['overview', 'Overview'],
  ['careers', 'Skills & careers'],
  ['trends', 'Demand over time'],
  ['markets', 'Compare markets'],
  ['connections', 'Skill connections'],
  ['methods', 'Data & methods'],
];
const state = {
  view: 'overview',
  data: null,
  options: null,
  skill: '',
  search: '',
  sort: 'demand',
  controller: null,
};
const parameters = new URLSearchParams(location.search);
state.view = views.some((v) => v[0] === parameters.get('view'))
  ? parameters.get('view')
  : 'overview';
state.skill = parameters.get('skill') || '';

function toast(text) {
  const el = $('#toast');
  el.textContent = text;
  el.classList.add('visible');
  clearTimeout(state.toast);
  state.toast = setTimeout(() => el.classList.remove('visible'), 2800);
}
function filters() {
  const result = Object.fromEntries(new FormData($('#filters')));
  if (state.skill) result.skill = state.skill;
  return result;
}
function query() {
  return new URLSearchParams(Object.entries(filters()).filter(([, v]) => v !== ''));
}
function syncURL() {
  const params = query();
  params.set('view', state.view);
  history.replaceState(null, '', `${location.pathname}?${params}`);
}
function setView(view) {
  state.view = view;
  render();
  syncURL();
  $('#sidebar').classList.remove('open');
  $('#menu-toggle').setAttribute('aria-expanded', 'false');
}
function navigation() {
  $('#navigation').innerHTML = views
    .map(
      ([key, label]) =>
        `<button class="nav-button ${state.view === key ? 'active' : ''}" data-view="${key}" ${state.view === key ? 'aria-current="page"' : ''}>${icon(key)}${label}${state.view === key ? '<span class="nav-arrow">↗</span>' : ''}</button>`,
    )
    .join('');
}
function tabs() {
  return `<div class="tabs" role="navigation" aria-label="Explore findings">${views
    .slice(0, 5)
    .map(
      ([key, label]) =>
        `<button class="tab ${key === state.view ? 'active' : ''}" data-view="${key}" ${key === state.view ? 'aria-current="page"' : ''}>${label}</button>`,
    )
    .join('')}</div>`;
}
function delta(change) {
  return change === null || change === undefined
    ? '<span class="pill neutral">Limited history</span>'
    : `<span class="pill ${change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'}">${change > 0 ? '↗ +' : change < 0 ? '↘ ' : ''}${change.toFixed(1)} pp</span>`;
}
function cardTitle(title, sub, label = '') {
  return `<div class="card-heading"><div><h3>${title}</h3><p>${sub}</p></div>${label ? `<span class="label">${label}</span>` : ''}</div>`;
}
function bars(rows, nameKey = 'skill', limit = 8, action = true) {
  const max = Math.max(1, ...rows.map((r) => r.rate));
  return `<div class="bar-list">${rows
    .slice(0, limit)
    .map(
      (r) =>
        `<${action ? 'button' : 'div'} class="bar-row ${r[nameKey] === state.data.selected_skill ? 'selected' : ''}" ${action ? `data-skill="${escapeHTML(r[nameKey])}" aria-label="Explore ${escapeHTML(r[nameKey])}, ${pct(r.rate)} demand"` : ''}><span class="bar-name" title="${escapeHTML(r[nameKey])}">${escapeHTML(r[nameKey])}</span><span class="bar-track"><span class="bar-fill" style="display:block;width:${(r.rate / max) * 100}%"></span></span><span class="bar-value">${pct(r.rate)}</span></${action ? 'button' : 'div'}>`,
    )
    .join('')}</div>`;
}
function chart(points, skills) {
  if (!points.length || !skills.length)
    return '<div class="empty small">No dated observations match these filters.</div>';
  const width = 600,
    height = 240,
    left = 38,
    right = 15,
    top = 15,
    bottom = 33;
  const rates = points.flatMap((p) =>
    skills.map((s) => p.rates[s]).filter((v) => v !== null && v !== undefined),
  );
  if (!rates.length)
    return '<div class="empty small">Not enough jobs per month to draw this chart. Try a broader scope or lower the minimum sample in More filters.</div>';
  const max = Math.min(100, Math.max(10, Math.ceil(Math.max(...rates) / 10) * 10));
  const x = (i) => left + ((width - left - right) * i) / Math.max(1, points.length - 1),
    y = (v) => height - bottom - ((height - top - bottom) * v) / max;
  const colors = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)'];
  const grid = [0, 1, 2, 3, 4]
    .map((i) => {
      const v = (max * i) / 4;
      return `<line class="chart-grid" x1="${left}" y1="${y(v)}" x2="${width - right}" y2="${y(v)}"/><text class="chart-label" x="${left - 9}" y="${y(v) + 3}" text-anchor="end">${Math.round(v)}%</text>`;
    })
    .join('');
  const labels = [
    ...new Set([
      0,
      Math.round((points.length - 1) / 3),
      Math.round((2 * (points.length - 1)) / 3),
      points.length - 1,
    ]),
  ]
    .map(
      (i) =>
        `<text class="chart-label" x="${x(i)}" y="${height - 8}" text-anchor="middle">${new Date(points[i].period + '-02').toLocaleDateString('en', { month: 'short', year: '2-digit' })}</text>`,
    )
    .join('');
  const lines = skills
    .map((skill, j) => {
      let active = false;
      const path = points
        .map((p, i) => {
          const rate = p.rates[skill];
          if (rate === null || rate === undefined) {
            active = false;
            return '';
          }
          const segment = `${active ? 'L' : 'M'}${x(i).toFixed(1)},${y(rate).toFixed(1)}`;
          active = true;
          return segment;
        })
        .join(' ');
      return (
        `<path d="${path}" fill="none" stroke="${colors[j]}" stroke-width="2.4" stroke-linejoin="round"/>` +
        points
          .map((p, i) =>
            p.rates[skill] === null || p.rates[skill] === undefined
              ? ''
              : `<circle cx="${x(i)}" cy="${y(p.rates[skill])}" r="3" fill="var(--card)" stroke="${colors[j]}" stroke-width="1.5"><title>${escapeHTML(skill)} · ${p.period}: ${pct(p.rates[skill])} (${fmt(p.eligible)} eligible jobs)</title></circle>`,
          )
          .join('')
      );
    })
    .join('');
  return `<svg class="line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Monthly skill demand. A gap means the month is below the minimum sample. Exact values are available in the data table."><title>Monthly demand for ${escapeHTML(skills.join(', '))}</title>${grid}${labels}${lines}</svg><div class="chart-legend">${skills.map((s, i) => `<span><i class="legend-dot" style="background:${colors[i]}"></i>${escapeHTML(s)}</span>`).join('')}</div>`;
}
function kpis(d) {
  const top = d.skills[0];
  return `<div class="kpi-grid"><div class="kpi featured"><div class="kpi-label">Advertisements in view ${icon('jobs')}</div><div class="kpi-value">${fmt(d.summary.jobs)}</div><div class="kpi-note">Matched cohort · both extraction methods</div></div><div class="kpi"><div class="kpi-label">Technical skills ${icon('skills')}</div><div class="kpi-value">${d.summary.skills}</div><div class="kpi-note">Distinct skills in this selection</div></div><div class="kpi"><div class="kpi-label">Most requested ${icon('trends')}</div><div class="kpi-value">${escapeHTML(top?.skill || '—')}</div><div class="kpi-note">${top ? `In <b>${pct(top.rate)}</b> of advertisements` : 'No skill mentions in this selection'}</div></div><div class="kpi"><div class="kpi-label">Sources represented ${icon('markets')}</div><div class="kpi-value">${d.summary.sources}</div><div class="kpi-note">${d.summary.months} calendar months in view</div></div></div>`;
}
function focus(d) {
  const selected = d.skills.find((r) => r.skill === d.selected_skill);
  return `<div class="focus-strip"><div><div class="eyebrow">TAKE A CLOSER LOOK</div><h3>${escapeHTML(d.selected_skill || 'Choose a skill')}</h3><p>One skill, connected across careers, time, and markets.</p></div><div class="focus-stat"><strong>${pct(selected?.rate || 0)}</strong><span>of selected advertisements</span></div><label>Explore another skill<select id="focus-skill">${state.options.skills.map((s) => `<option ${s === d.selected_skill ? 'selected' : ''}>${escapeHTML(s)}</option>`).join('')}</select></label></div>`;
}
function overview(d) {
  const selected = d.skills.find((r) => r.skill === d.selected_skill);
  const growing = d.skills.filter((r) => r.change !== null).sort((a, b) => b.change - a.change)[0];
  const role = [...d.roles].sort((a, b) => b.rate - a.rate)[0];
  const pair = d.relationships[0];
  const skillNames = [
    ...new Set([d.selected_skill, ...d.skills.slice(0, 3).map((r) => r.skill)]),
  ].slice(0, 3);
  return `<div class="section-heading"><div><h2>Your market at a glance</h2><p>A connected picture of demand, beyond the job title.</p></div><button class="text-link" data-view="methods">About this data ↗</button></div>${tabs()}<div class="two-col"><section class="card">${cardTitle('The skills employers ask for', 'Share of advertisements mentioning each skill', 'MOST REQUESTED')}${bars(d.skills)}<div class="card-footer"><span>Each advertisement counts once per skill.</span><button class="text-link" data-view="careers">Explore all skills →</button></div></section><section class="card">${cardTitle('A moving picture of demand', 'Monthly share of eligible advertisements', 'OVER TIME')}${chart(d.timeline, skillNames)}<div class="card-footer"><span>${d.summary.low_sample_months ? `${d.summary.low_sample_months} month(s) below the sample threshold` : 'Consistent calendar grid · missing months stay missing'}</span><button class="text-link" data-view="trends">Explore trends →</button></div></section></div>${focus(d)}<div class="mini-card-grid"><section class="mini-card"><span class="mini-icon">↗</span><h3>A skill on the move</h3><p>${growing && growing.change > 0 ? `<strong>${escapeHTML(growing.skill)}</strong> gained <strong>${growing.change.toFixed(1)} percentage points</strong> in the latest three months versus the preceding three.` : 'There is not enough recent evidence to identify a growing skill in this view.'}</p></section><section class="mini-card"><span class="mini-icon">⌘</span><h3>Where ${escapeHTML(d.selected_skill)} fits</h3><p>${role ? `It appears in <strong>${pct(role.rate)}</strong> of <strong>${escapeHTML(role.role)}</strong> advertisements in your selection.` : 'Choose a wider selection to explore career connections.'}</p></section><section class="mini-card insight-card"><span class="mini-icon">↔</span><h3>Better understood together</h3><p>${pair ? `<strong>${escapeHTML(pair.skill)}</strong> appears alongside ${escapeHTML(d.selected_skill)} in <strong>${pct(pair.confidence)}</strong> of advertisements that mention it.` : 'Select a skill with co-mentions to see its technology connections.'}</p></section></div><section class="card">${cardTitle('A few skills worth exploring', 'Demand is a share of the selected job sample, not the entire labour market.')} ${skillTable(d.skills.slice(0, 5))}</section>`;
}
function skillTable(rows) {
  return `<div class="table-wrap"><table><thead><tr><th>TECHNICAL SKILL</th><th>ADVERTISEMENTS</th><th>DEMAND</th><th>RECENT CHANGE</th><th>SIGNAL</th></tr></thead><tbody>${rows.length ? rows.map((r) => `<tr><td><button class="skill-button" data-skill="${escapeHTML(r.skill)}">${escapeHTML(r.skill)} ↗</button></td><td class="number">${fmt(r.count)}</td><td><div class="table-meter"><span class="bar-track"><span class="bar-fill" style="display:block;width:${r.rate}%"></span></span><span>${pct(r.rate)}</span></div></td><td>${delta(r.change)}</td><td><span class="small muted">${escapeHTML(r.label)}</span></td></tr>`).join('') : '<tr><td colspan="5">No skills match your search.</td></tr>'}</tbody></table></div>`;
}
function searchedSkills() {
  const rows = state.data.skills.filter((r) =>
    r.skill.toLowerCase().includes(state.search.toLowerCase()),
  );
  if (state.sort === 'growth')
    rows.sort((a, b) => (b.change ?? -Infinity) - (a.change ?? -Infinity));
  if (state.sort === 'name') rows.sort((a, b) => a.skill.localeCompare(b.skill));
  return rows;
}
function careers(d) {
  return `${tabs()}${focus(d)}<section class="card">${cardTitle('Find the skills that fit your direction', 'Search, sort, and select a skill to explore it across every view.')}<div class="table-search"><input id="skill-search" type="search" placeholder="Search technical skills…" aria-label="Search skills" value="${escapeHTML(state.search)}"><select id="skill-sort" aria-label="Sort skills"><option value="demand">Most requested</option><option value="growth" ${state.sort === 'growth' ? 'selected' : ''}>Fastest growing</option><option value="name" ${state.sort === 'name' ? 'selected' : ''}>Alphabetical</option></select><button class="button secondary" data-export="skills">↓ CSV</button></div><div id="skill-table">${skillTable(searchedSkills())}</div></section><div class="section-heading"><div><h2>Different paths. Different skill sets.</h2><p>Within-career demand uses all eligible advertisements in that career area.</p></div></div><div class="mini-card-grid">${d.roles.map((r) => `<section class="mini-card"><span class="mini-icon">${icon('careers')}</span><h3><button class="skill-button" data-role="${escapeHTML(r.role)}">${escapeHTML(r.role)} ↗</button></h3><p>${fmt(r.jobs)} advertisements · <strong>${pct(r.rate)} request ${escapeHTML(d.selected_skill)}</strong></p><div>${r.skills.map((s) => `<button class="tag" data-skill="${escapeHTML(s.skill)}">${escapeHTML(s.skill)} · ${pct(s.rate)}</button>`).join('')}</div></section>`).join('')}</div><div class="explanation"><strong>A practical starting point:</strong> these are technologies mentioned together within career areas, not a required curriculum or a guarantee of employment. Skill selection explores a detail; it never removes zero-skill jobs from the denominator.</div>`;
}
function forecastCard(d) {
  const forecast = d.forecast;
  if (!forecast?.rows?.length)
    return `<div class="explanation"><strong>Short-term outlook:</strong> ${escapeHTML(forecast?.note || 'No forecast has been published for this selection.')}</div>`;
  const first = forecast.rows[0];
  return `<section class="card" style="margin-top:20px">${cardTitle('A cautious look ahead', 'Prepared offline from this published sample, not generated during browsing.', 'EXPLORATORY BASELINE')}<div class="forecast-grid">${forecast.rows.map((r) => `<div class="forecast-point"><span>${new Date(r.period + '-02').toLocaleDateString('en', { month: 'long', year: 'numeric' })}</span><strong>${pct(r.rate)}</strong><div class="small">estimated demand rate</div></div>`).join('')}</div><div class="card-footnote">${escapeHTML(first.model)} · one-step historical MAE: ${first.mae.toFixed(2)} pp · ${first.evaluated_periods} evaluation targets. ${escapeHTML(forecast.note)}</div><div class="card-footer"><span>Forecast scope matches this publication.</span><button class="text-link" data-export="forecasts">Download outlook ↓</button></div></section>`;
}
function trends(d) {
  const rows = [...d.skills].sort((a, b) => (b.change ?? -Infinity) - (a.change ?? -Infinity));
  return `${tabs()}${focus(d)}<section class="card">${cardTitle(`How ${escapeHTML(d.selected_skill)} demand is changing`, 'Demand rate by calendar month · hover over a point for the sample size', `${escapeHTML(d.filters.method)} matching`)}${chart(d.timeline, [d.selected_skill])}<div class="card-footnote">A gap means fewer than ${d.filters.min_jobs || 5} eligible jobs in that month. Zero means eligible jobs existed but none mentioned the skill. Partial first/last months may affect comparisons.</div><details class="data-details"><summary>View accessible monthly data table</summary><div class="table-wrap"><table><thead><tr><th>MONTH</th><th>ELIGIBLE JOBS</th><th>DEMAND RATE</th></tr></thead><tbody>${d.timeline.map((p) => `<tr><td>${p.period}</td><td>${p.eligible}</td><td>${p.rates[d.selected_skill] === null ? 'Insufficient sample' : pct(p.rates[d.selected_skill] ?? 0)}</td></tr>`).join('')}</tbody></table></div></details><div class="card-footer"><span>Rates share one calendar grid and denominator policy.</span><button class="text-link" data-export="timeline">Download monthly data ↓</button></div></section><div class="section-heading"><div><h2>Momentum, with context</h2><p>Latest three calendar months versus the preceding three. Changes are percentage points.</p></div></div><section class="card">${skillTable(rows)}</section>${forecastCard(d)}<div class="explanation"><strong>Signals, not certainties.</strong> A change above +2 pp is marked Growing; below −2 pp, Declining. An Emerging candidate also starts below 5% and exceeds that baseline in each recent month. Both complete three-month windows must meet the sample threshold. These transparent screening rules do not establish new technology emergence or source stability.</div>`;
}
function markets(d) {
  return `${tabs()}${focus(d)}<div class="explanation"><strong>A fairer comparison:</strong> this view compares ${escapeHTML(d.selected_skill)} across all published markets, retaining your career, source, method, and date filters. Only the Market filter is lifted. Each market uses its own eligible-job denominator. India is a South Asian comparator.</div><div class="two-col"><section class="card">${cardTitle(`Where ${escapeHTML(d.selected_skill)} is requested`, 'Share of eligible advertisements within each market', 'MARKET COMPARISON')}${bars(d.markets, 'country', 10, false)}<div class="card-footnote">Different portal coverage and sample sizes can affect comparisons. These samples do not represent complete national job markets.</div></section><section class="card">${cardTitle('The numbers behind the comparison', 'Always read the rate alongside its sample size.')}<div class="table-wrap"><table><thead><tr><th>MARKET</th><th>ELIGIBLE JOBS</th><th>MENTIONS</th><th>DEMAND</th></tr></thead><tbody>${d.markets.map((r) => `<tr><td><button class="skill-button" data-country="${escapeHTML(r.country)}">${escapeHTML(r.country)} ↗</button></td><td>${fmt(r.jobs)}</td><td>${fmt(r.count)}</td><td>${pct(r.rate)}</td></tr>`).join('')}</tbody></table></div><div class="card-footer"><span>Select a market to update the whole view.</span><button class="text-link" data-export="markets">Download comparison ↓</button></div></section></div><div class="section-heading"><div><h2>A different mix in every market</h2><p>Leading technical skills in the same comparison scope.</p></div></div><div class="mini-card-grid">${d.markets.map((r) => `<section class="mini-card"><h3>${escapeHTML(r.country)}</h3><p>${fmt(r.jobs)} eligible advertisements</p><div>${r.skills.map((s) => `<button class="tag" data-skill="${escapeHTML(s.skill)}">${escapeHTML(s.skill)} · ${pct(s.rate)}</button>`).join('')}</div></section>`).join('')}</div>`;
}
function connections(d) {
  return `${tabs()}${focus(d)}<div class="two-col"><section class="card">${cardTitle(`The company ${escapeHTML(d.selected_skill)} keeps`, 'Skills co-mentioned in the same advertisement', 'TECHNOLOGY CONNECTIONS')}${
    d.relationships.length
      ? d.relationships
          .slice(0, 8)
          .map(
            (r, i) =>
              `<div class="stack-row"><span class="stack-number">${String(i + 1).padStart(2, '0')}</span><div><button class="skill-button" data-skill="${escapeHTML(r.skill)}">${escapeHTML(d.selected_skill)} <span class="muted">+</span> ${escapeHTML(r.skill)} ↗</button><p>${fmt(r.count)} co-mentions · ${pct(r.confidence)} of ${escapeHTML(d.selected_skill)} ads</p></div><span class="pill positive">${r.lift.toFixed(2)}× lift</span></div>`,
          )
          .join('')
      : '<p class="muted">No co-mentioned skills in this selection.</p>'
  }</section><section class="card">${cardTitle('Read the relationship, not just the line', 'A connection means co-occurrence, not a prerequisite.')}<dl class="provenance"><dt>Support</dt><dd>Share of all eligible advertisements mentioning both skills.</dd><dt>Confidence</dt><dd>Among advertisements mentioning the selected skill, the share also mentioning its partner.</dd><dt>Lift</dt><dd>How often the pair appears relative to independent mentions. Above 1 means they co-occur more than independence would predict.</dd><dt>Jaccard similarity &amp; PMI</dt><dd>Additional overlap/association measures in the table below. Rare pairs can produce striking values from very little evidence.</dd></dl><div class="explanation">Use this as a way to discover adjacent technologies, then inspect the counts. Co-mentions do not establish causation, proficiency, or a required learning order.</div></section></div><section class="card">${cardTitle('Connection evidence', 'Counts and normalized measures for your current selection.')}<div class="table-wrap"><table><thead><tr><th>PAIRED SKILL</th><th>CO-MENTIONS</th><th>SUPPORT</th><th>CONFIDENCE</th><th>LIFT</th><th>JACCARD</th><th>PMI</th></tr></thead><tbody>${d.relationships.map((r) => `<tr><td><button class="skill-button" data-skill="${escapeHTML(r.skill)}">${escapeHTML(r.skill)}</button></td><td>${r.count}</td><td>${pct(r.support)}</td><td>${pct(r.confidence)}</td><td>${r.lift.toFixed(2)}</td><td>${r.jaccard.toFixed(3)}</td><td>${r.pmi.toFixed(3)}</td></tr>`).join('')}</tbody></table></div><div class="card-footer"><span>Each job contributes once per skill pair.</span><button class="text-link" data-export="relationships">Download evidence ↓</button></div></section>`;
}
function methods(d) {
  const p = d.publication;
  return `<div class="section-heading"><div><h2>Know what sits behind the numbers</h2><p>Transparent methods. Shared samples. Clear limitations.</p></div></div><div class="method-grid"><section class="card">${cardTitle('One cohort, two ways to find skills', 'These methods are compared on the same advertisements.')}<dl class="provenance"><dt>Keyword (lexical) matching</dt><dd>Finds explicit terms and aliases from the technical-skill vocabulary.</dd><dt>Semantic matching</dt><dd>Uses meaning-based similarity to identify skills from that same vocabulary. It can miss or add skills; higher demand is not proof of higher accuracy.</dd><dt>What stays the same</dt><dd>Dates, career areas, sources, and all eligible advertisements—including completed extractions with zero skills. Demand is distinct skill-bearing jobs ÷ eligible jobs × 100.</dd></dl></section><section class="card">${cardTitle('Publication details', 'A traceable dataset, separate from collection tools.')}<dl class="provenance"><dt>Dataset</dt><dd>${escapeHTML(p.title)}</dd><dt>Observation window</dt><dd>${escapeHTML(p.date_start)} — ${escapeHTML(p.date_end)}</dd><dt>Published</dt><dd>${escapeHTML(new Date(p.generated_at).toLocaleString())}</dd><dt>Provenance</dt><dd>${escapeHTML(p.provenance)}</dd><dt>Snapshot</dt><dd>${escapeHTML(p.snapshot_id)} · ${p.is_synthetic ? 'Synthetic demonstration' : 'Reviewed research publication'}</dd><dt>Configuration</dt><dd>${escapeHTML(p.configuration || 'See publisher metadata')}</dd></dl></section></div><section class="card">${cardTitle('Does extraction change the picture?', 'Difference is semantic minus keyword demand, in percentage points.', 'SAME COHORT')}<div class="table-wrap"><table><thead><tr><th>SKILL</th><th>KEYWORD DEMAND</th><th>SEMANTIC DEMAND</th><th>DIFFERENCE</th></tr></thead><tbody>${d.comparison.map((r) => `<tr><td><button class="skill-button" data-skill="${escapeHTML(r.skill)}">${escapeHTML(r.skill)}</button></td><td>${pct(r.lexical)}</td><td>${pct(r.semantic)}</td><td>${delta(r.difference)}</td></tr>`).join('')}</tbody></table></div><div class="card-footer"><span>Downstream sensitivity is different from extraction accuracy.</span><button class="text-link" data-export="comparison">Download comparison ↓</button></div></section><div class="explanation"><strong>What this cannot tell you:</strong> the collected sample is not the whole labour market. Sources, job mix, vocabulary, and date quality influence results. The public app calculates transparent counts, proportions, and association summaries from a published cohort; it does not run scraping, train models, or score extraction accuracy. No forecasts are fabricated when reviewed results are absent.${p.is_synthetic ? '<br><strong>This dataset is entirely synthetic.</strong> Its patterns were designed to demonstrate the interface and are not findings about actual employers.' : ''}</div>`;
}
function render() {
  navigation();
  if (!state.data) return;
  const d = state.data;
  const content = d.summary.jobs
    ? { overview, careers, trends, markets, connections, methods }[state.view](d)
    : `${tabs()}<section class="empty"><h2>A little too specific?</h2><p>No advertisements match this combination. Try a different market, a broader career area, or a longer date range.</p><button class="button primary" data-reset>Reset filters</button></section>`;
  $('#analysis').innerHTML = kpis(d) + content;
  $('#analysis').setAttribute('aria-busy', String(Boolean(state.loading)));
  const market = $('#country').value || 'All markets',
    role = $('#role').value || 'All career areas';
  $('#scope-description').textContent =
    `${market} · ${role} · ${fmt(d.summary.jobs)} advertisements · ${$('#method').value === 'semantic' ? 'Semantic' : 'Keyword'} matching`;
  $('#download').disabled = Boolean(state.loading) || !d.summary.jobs;
}
async function loadAnalysis() {
  if (!$('#filters').reportValidity()) return;
  if ($('#start').value > $('#end').value) {
    $('#feedback').innerHTML =
      '<div class="error">Choose a start date on or before the end date.</div>';
    return;
  }
  state.controller?.abort();
  const controller = new AbortController();
  state.controller = controller;
  state.loading = true;
  $('#analysis').setAttribute('aria-busy', 'true');
  $('#feedback').textContent = 'Updating your view…';
  $('#download').disabled = true;
  try {
    const response = await fetch(`/api/analysis?${query()}`, { signal: controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not load analysis.');
    state.loading = false;
    state.data = data;
    state.skill = data.selected_skill;
    $('#feedback').textContent = '';
    render();
    syncURL();
  } catch (error) {
    if (error.name === 'AbortError') return;
    state.loading = false;
    state.data = null;
    $('#analysis').setAttribute('aria-busy', 'false');
    $('#feedback').innerHTML =
      `<div class="error">${escapeHTML(error.message)} <button class="button secondary" data-retry>Retry</button> <button class="button secondary" data-reset>Reset filters</button></div>`;
    $('#analysis').innerHTML =
      '<div class="empty"><h2>No published analysis available</h2><p>The data publisher may not have supplied a snapshot yet. Please try again later.</p></div>';
  }
}
function reset() {
  $('#country').value = state.options.countries.includes('Sri Lanka') ? 'Sri Lanka' : '';
  $('#role').value = '';
  $('#source').value = '';
  $('#method').value = 'semantic';
  $('#min_jobs').value = '5';
  $('#start').value = state.options.publication.date_start;
  $('#end').value = state.options.publication.date_end;
  state.skill = '';
  state.search = '';
  state.sort = 'demand';
  loadAnalysis();
}
function download(view) {
  const params = query();
  params.set('view', view);
  const a = document.createElement('a');
  a.href = `/api/export?${params}`;
  a.download = `skillscope-${view}.csv`;
  a.click();
}
document.addEventListener('click', (event) => {
  const target = event.target.closest('button');
  if (!target) return;
  if (target.dataset.view) setView(target.dataset.view);
  if (target.dataset.skill) {
    state.skill = target.dataset.skill;
    loadAnalysis();
  }
  if (target.dataset.role) {
    $('#role').value = target.dataset.role;
    loadAnalysis();
  }
  if (target.dataset.country) {
    $('#country').value = target.dataset.country;
    loadAnalysis();
  }
  if (target.hasAttribute('data-reset')) reset();
  if (target.hasAttribute('data-retry')) loadAnalysis();
  if (target.dataset.export) download(target.dataset.export);
});
$('#filters').addEventListener('submit', (event) => {
  event.preventDefault();
  loadAnalysis();
});
$('#filters').addEventListener('change', () => loadAnalysis());
document.addEventListener('change', (event) => {
  if (event.target.id === 'focus-skill') {
    state.skill = event.target.value;
    loadAnalysis();
  }
  if (event.target.id === 'skill-sort') {
    state.sort = event.target.value;
    $('#skill-table').innerHTML = skillTable(searchedSkills());
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    $('#sidebar').classList.remove('open');
    $('#menu-toggle').setAttribute('aria-expanded', 'false');
  }
});
document.addEventListener('input', (event) => {
  if (event.target.id === 'skill-search') {
    state.search = event.target.value;
    $('#skill-table').innerHTML = skillTable(searchedSkills());
  }
});
$('#reset').addEventListener('click', () => state.options && reset());
$('#menu-toggle').addEventListener('click', () => {
  const open = $('#sidebar').classList.toggle('open');
  $('#menu-toggle').setAttribute('aria-expanded', String(open));
});
$('#method-link').addEventListener('click', () => setView('methods'));
$('#footer-method').addEventListener('click', () => setView('methods'));
$('#download').addEventListener('click', () =>
  download(
    {
      careers: 'skills',
      trends: 'timeline',
      markets: 'markets',
      connections: 'relationships',
      methods: 'comparison',
    }[state.view] || 'skills',
  ),
);
$('#share').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    toast('View link copied. Your filters are included.');
  } catch {
    toast('Copy the address from your browser to share this view.');
  }
});
navigation();
$('#download').disabled = true;
async function start() {
  try {
    const response = await fetch('/api/options');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    state.options = data;
    for (const key of ['country', 'role', 'source']) {
      const values =
        data[`${key === 'country' ? 'countries' : key === 'role' ? 'roles' : 'sources'}`];
      const el = $('#' + key);
      el.innerHTML += values
        .map((v) => `<option value="${escapeHTML(v)}">${escapeHTML(v)}</option>`)
        .join('');
    }
    const p = data.publication;
    for (const key of ['start', 'end']) {
      const el = $('#' + key);
      el.min = p.date_start;
      el.max = p.date_end;
      el.value = parameters.get(key) || (key === 'start' ? p.date_start : p.date_end);
    }
    for (const key of ['country', 'role', 'source', 'method', 'min_jobs'])
      if (parameters.has(key)) $('#' + key).value = parameters.get(key);
    if (!parameters.has('country'))
      $('#country').value = data.countries.includes('Sri Lanka') ? 'Sri Lanka' : '';
    $('#dataset-notice').classList.toggle('real', !p.is_synthetic);
    $('#dataset-notice').innerHTML =
      `<span><span class="notice-icon">${p.is_synthetic ? '◉' : '✓'}</span> <strong>${p.is_synthetic ? 'Demo dataset' : 'Published research'}</strong> · ${p.is_synthetic ? 'Synthetic advertisements for exploration. These are not real labour-market findings.' : escapeHTML(p.title)}</span><span>${escapeHTML(p.date_start.slice(0, 4))}–${escapeHTML(p.date_end.slice(0, 4))} &nbsp; · &nbsp; ${fmt(p.job_count)} advertisements</span>`;
    await loadAnalysis();
  } catch (error) {
    $('#dataset-notice').textContent = 'No published dataset available';
    $('#feedback').innerHTML =
      `<div class="error">${escapeHTML(error.message)} <button class="button secondary" id="reload-data">Try again</button></div>`;
    $('#analysis').innerHTML =
      '<div class="empty"><h2>Fresh insights are on their way</h2><p>No readable publication is available yet. The research tools and private database are not exposed here.</p></div>';
    $('#analysis').setAttribute('aria-busy', 'false');
    $('#reload-data').addEventListener('click', () => location.reload());
  }
}
start();
