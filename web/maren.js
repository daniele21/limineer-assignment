(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('scoring-data').textContent);
  const sites = new Map(data.sites.map(site => [site.site_id, site]));
  const baselineId = data.default_profile_id;
  const riskyId = data.presets.find(preset => preset.id === 'potential').profile_id;
  const storageKey = `limineer-maren-answers-v1-${data.metadata.exported_at}`;
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
  const number = value => Number(value).toLocaleString('en-GB', {maximumFractionDigits: 2});
  const shortNames = {grid: 'Grid capacity', sentiment: 'Local support', missing: 'Missing checks', conflicts: 'Land conflicts'};
  const typeNames = {brownfield: 'Brownfield', municipal_land: 'Municipal land', depot_yard: 'Depot yard', farm_edge: 'Farm edge'};
  const valueNames = {loi_signed: 'Letter of intent signed', in_talks: 'Owner in talks', not_contacted: 'Owner not contacted', refused: 'Owner refused', supportive: 'Support recorded', neutral: 'Neutral', opposed: 'Opposed', none: 'No mapped flood risk', low: 'Low flood risk', medium: 'Medium flood risk', high: 'High flood risk'};
  let answers = {};
  let compareScores = false;
  let comparisonTarget = riskyId;
  let alternativeGroup = 'contenders';
  let alternativeLimit = 3;
  let questionIndex = 0;
  let questionOpener = null;
  let breakdownOpener = null;
  let toastTimer;
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
    for (const question of data.questions) {
      if (question.options.some(option => option.id === saved?.[question.id])) answers[question.id] = saved[question.id];
    }
  } catch { /* The page also works when browser storage is unavailable. */ }

  function profileId() {
    return data.questions.map(question => answers[question.id] ?? question.default_answer).join('__');
  }
  function profile() { return data.profiles.find(item => item.id === profileId()); }
  function isCustom() { return profileId() !== baselineId; }
  function selection(site, field, id = profileId()) {
    return site.criterion_variants[field][site.scores[id].components[field]];
  }
  function formatValue(field, variant) {
    if (variant.value == null) return variant.basis === 'known_distance_bound' ? 'No substation within 10 km' : 'Unknown · no extra points';
    if (field === 'headroom_mw') return `${number(variant.value)} MW${variant.basis === 'vendor_estimate' ? ' · vendor estimate' : variant.basis === 'hypothesis' ? ' · assumed' : ' · official'}`;
    if (field === 'substation_distance_km') return `${number(variant.value)} km${variant.basis === 'hypothesis' ? ' · assumed' : ' to substation'}`;
    if (field === 'usable_area_m2') return `${number(variant.value)} m² · ${variant.basis === 'hypothesis' ? 'assumed' : variant.basis === 'remaining_plot_proxy' ? 'remaining plot proxy' : 'parcel proxy'}`;
    return `${valueNames[variant.value] || variant.value}${variant.basis === 'hypothesis' ? ' · assumed' : ''}`;
  }
  const baseReasons = {
    'S-003': '4.6 MW of official capacity, a signed letter of intent and recorded council support.',
    'S-018': 'The same strong grid and owner position as Kessby, with recorded council support.',
    'S-017': 'Strong grid capacity, a signed letter of intent and no mapped flood risk. Neighbours are neutral.',
    'S-027': '5.5 MW and a signed letter of intent. Local support is still conditional on a noise report.',
    'S-014': 'Strong grid capacity and recorded local support. The owner agreement is still in talks.',
    'S-007': 'Owner intent and local support are recorded; official grid capacity earns only 6 of 30 points.',
    'S-032': 'Strong grid capacity and no mapped flood risk. Owner talks and local support still need work.'
  };
  function reason(site) {
    const score = site.scores[profileId()];
    const base = site.scores[baselineId];
    const grid = selection(site, 'headroom_mw');
    if (score.components.headroom_mw !== 'baseline') {
      const gain = (grid.contribution || 0) - (selection(site, 'headroom_mw', baselineId).contribution || 0);
      return `${grid.basis === 'vendor_estimate' ? 'Vendor-estimated' : 'Assumed'} capacity adds ${number(gain)} points. The grid operator still needs to confirm it.`;
    }
    if (score.components.community_sentiment !== 'baseline') {
      return `Assuming confirmed local support adds ${number(score.score - base.score)} points. ${site.site_id === 'S-027' ? 'The noise-report condition still needs resolving.' : 'That support is still unverified.'}`;
    }
    if (baseReasons[site.site_id]) return baseReasons[site.site_id];
    const owner = selection(site, 'owner_status');
    const distance = selection(site, 'substation_distance_km');
    return `${grid.value == null ? 'Grid capacity needs checking' : `${number(grid.value)} MW of official capacity`}; ${distance.value == null ? 'connection distance unresolved' : `${number(distance.value)} km to the substation`}. ${owner.value === 'loi_signed' ? 'A letter of intent is signed.' : 'The owner agreement needs progressing.'}`;
  }
  function nextCheck(site) {
    const score = site.scores[profileId()];
    if (score.components.headroom_mw !== 'baseline') return 'Verify assumed capacity with the grid operator.';
    if (site.site_id === 'S-003') return 'Agree the requested 12% revenue share; assess low flood risk.';
    if (site.site_id === 'S-018') return 'Assess low flood risk and measure the installation footprint.';
    if (site.site_id === 'S-017') return 'Confirm cable route and installation footprint.';
    if (site.site_id === 'S-027') return 'Complete the noise report and confirm local support.';
    if (selection(site, 'owner_status').value !== 'loi_signed') return 'Secure a letter of intent and confirm lease terms.';
    if (score.unresolved_criteria.includes('community_sentiment') || score.components.community_sentiment !== 'baseline') return 'Confirm local support and any conditions.';
    return 'Confirm grid connection, usable land and lease terms.';
  }
  function rankExplanation(site) {
    const score = site.scores[profileId()];
    if (score.status !== 'eligible') return 'This site is outside the current recommendation pool until its critical checks are resolved.';
    const ordered = profile().rankings.eligible.map(id => sites.get(id));
    const tied = ordered.filter(other => other.scores[profileId()].score === score.score && other.site_id !== site.site_id);
    const above = ordered.filter(other => other.scores[profileId()].score > score.score).at(-1);
    const below = ordered.find(other => other.scores[profileId()].score < score.score);
    let text = tied.length ? `Joint #${score.rank} with ${tied.map(other => other.name).join(' and ')} at ${number(score.score)}/100. ` : `#${score.rank} at ${number(score.score)}/100. `;
    if (above) text += `${number(above.scores[profileId()].score - score.score)} ${above.scores[profileId()].score - score.score === 1 ? 'point' : 'points'} behind ${above.name}. `;
    else if (below) text += `${number(score.score - below.scores[profileId()].score)} ${score.score - below.scores[profileId()].score === 1 ? 'point' : 'points'} ahead of the next lower score. `;
    if (tied.length) text += 'Tied sites are displayed in site-ID order, with equal priority. ';
    if (score.score_kind === 'partial_lower') text += 'This is a lower-bound score: unknown local support earns no extra points.';
    if (score.conditions.length) text += 'This position depends on your selected assumptions passing verification.';
    return text;
  }
  function detailsContent(site) {
    const current = site.scores[profileId()];
    const conservative = site.scores[baselineId];
    const risky = site.scores[riskyId];
    const rows = data.rubric.criteria.map(criterion => {
      const selected = selection(site, criterion.id);
      return `<div class="criterion"><div><div class="criterion-name">${escape(criterion.label)} <span class="criterion-weight">· ${criterion.weight} pts</span></div><div class="criterion-value">${escape(formatValue(criterion.id, selected))}</div></div><span>${number(selection(site, criterion.id, baselineId).contribution || 0)}</span><span class="selected-points">${number(selected.contribution || 0)}</span><span class="risky-points">${number(selection(site, criterion.id, riskyId).contribution || 0)}</span></div>`;
    }).join('');
    const allConditions = [...new Set([...current.conditions, ...risky.conditions])];
    const notes = site.notes.length ? site.notes.map(note => `<div class="evidence-note"><blockquote>“${escape(note.text)}”</blockquote><cite>${escape(note.author)} · ${escape(note.date || 'Date not recorded')} · ${escape(note.note_id)}</cite></div>`).join('') : '<p class="detail-note">No field notes recorded. Missing evidence remains unknown.</p>';
    const gridSource = site.sources.gridmap;
    const landSource = site.sources.landreg;
    return `<div class="detail-content"><p class="rank-explanation">${escape(rankExplanation(site))}</p><h3 class="detail-subheading">Where the points come from</h3><div class="breakdown-head"><span>Criterion / maximum</span><span>Conser-<br>vative</span><span>Your<br>score</span><span>Risky<br>upside</span></div>${rows}<div class="score-totals"><span>${current.status === 'held' || current.status === 'excluded' ? 'Ranked score' : 'Total / 100'}</span><span>${conservative.score == null ? '—' : number(conservative.score)}</span><span>${current.score == null ? '—' : number(current.score)}</span><span>${risky.score == null ? '—' : number(risky.score)}</span></div><p class="detail-note">Score bands summarise rubric fit: High 80–100, Medium 60–79, Low below 60. They are not a measure of readiness. Values shown reflect your current answers. Unknown inputs add no points. ${site.source_site_ids.length > 1 ? `Duplicate records ${escape(site.source_site_ids.join(' / '))} count as one physical site. ` : ''}Area is a parcel proxy, not a measured installation footprint.</p>${allConditions.length ? `<div class="conditions"><p>What the upside depends on</p><ul>${allConditions.map(condition => `<li>${escape(condition)}</li>`).join('')}</ul></div>` : ''}<details class="evidence-disclosure"><summary>Read the source evidence <span aria-hidden="true">↗</span></summary><p class="source-line">Official grid: ${gridSource ? `data dated ${escape(gridSource.data_as_of)}${gridSource.fetched_at ? `, fetched ${escape(gridSource.fetched_at.slice(0, 10))}` : ''}` : 'not available'}.<br>Land registry: ${landSource ? `record dated ${escape(landSource.record_date)}` : 'not available'}. Parcel ${escape(site.parcel_id)}.</p>${site.sources.vendor_estimate ? `<p class="source-line">Vendor: ${number(site.sources.vendor_estimate.headroom_mw_est)} MW ±${number(site.sources.vendor_estimate.band_pct)}%, estimated ${escape(site.sources.vendor_estimate.estimated_at)}. Unvalidated estimate.</p>` : ''}${notes}</details></div>`;
  }
  function rankSummary(site) {
    const score = site.scores[profileId()];
    if (score.conditions.length) return 'This position depends on checks confirming your assumptions.';
    if (score.unresolved_criteria.includes('community_sentiment')) return 'Strong site; local support still needs confirmation.';
    if (selection(site, 'owner_status').value !== 'loi_signed') return 'Good candidate; the owner agreement is still outstanding.';
    return score.rank <= 3 ? 'Among the strongest options for site checks.' : 'A candidate for site checks, with the steps below.';
  }
  function scoreWord(variant, text) {
    const tone = variant.conditions.length || variant.tier == null ? 'caution' : ['refused', 'opposed', 'high'].includes(variant.value) ? 'negative' : variant.tier <= 2 ? 'caution' : variant.tier === 5 ? 'best' : variant.tier === 4 ? 'good' : 'neutral';
    return `<span class="score-word score-word-${tone}">${escape(text)}</span>`;
  }
  function aggregateContent(site) {
    const groups = [
      {label: 'Grid connection', fields: ['headroom_mw', 'substation_distance_km'], maximum: 45},
      {label: 'Agreements', fields: ['owner_status', 'community_sentiment'], maximum: 30},
      {label: 'Land & flood', fields: ['flood_zone', 'usable_area_m2'], maximum: 25}
    ];
    const rows = groups.map(group => {
      let explanation;
      if (group.label === 'Agreements') {
        const owner = selection(site, 'owner_status');
        const support = selection(site, 'community_sentiment');
        const ownerLabels = {loi_signed: 'Signed owner intent', in_talks: 'Owner in talks', not_contacted: 'Owner not contacted', refused: 'Owner refused'};
        const supportLabels = {supportive: 'local support recorded', neutral: 'neutral local stance', opposed: 'local opposition'};
        explanation = `${scoreWord(owner, owner.conditions.length ? 'Owner intent assumed' : ownerLabels[owner.value] || 'Owner status unknown')} · ${scoreWord(support, support.conditions.length ? 'support assumed' : supportLabels[support.value] || 'support unknown')}`;
      } else if (group.label === 'Grid connection') {
        const capacity = selection(site, 'headroom_mw');
        const distance = selection(site, 'substation_distance_km');
        const capacityLabel = capacity.conditions.length ? 'Capacity assumed' : capacity.value == null ? 'Capacity unknown' : capacity.value >= 4 ? 'Strong capacity' : capacity.value >= 2 ? 'Moderate capacity' : 'Limited capacity';
        const distanceLabel = distance.conditions.length ? 'distance assumed' : distance.value == null ? distance.basis === 'known_distance_bound' ? 'no nearby substation' : 'distance unknown' : distance.value <= 1 ? 'nearby substation' : 'longer connection';
        explanation = `${scoreWord(capacity, capacityLabel)} · ${scoreWord(distance, distanceLabel)}`;
      } else {
        const flood = selection(site, 'flood_zone');
        const area = selection(site, 'usable_area_m2');
        const floodLabels = {none: 'No mapped flood risk', low: 'Low flood risk', medium: 'Medium flood risk', high: 'High flood risk'};
        explanation = `${scoreWord(flood, flood.conditions.length ? 'Flood risk assumed' : floodLabels[flood.value] || 'Flood risk unknown')} · ${scoreWord(area, area.conditions.length ? 'area assumed' : area.value == null ? 'area unknown' : area.value >= 1200 ? 'large parcel' : 'small parcel')}`;
      }
      const conditional = group.fields.some(field => selection(site, field).conditions.length);
      const unknown = group.fields.some(field => selection(site, field).tier == null);
      return `<div class="aggregate-row"><span>${group.label}${conditional ? '<small>Assumed</small>' : unknown ? '<small>Incomplete</small>' : ''}</span><p class="aggregate-explanation">${explanation}</p></div>`;
    }).join('');
    return `<div class="aggregate-content"><p class="rank-summary">${escape(rankSummary(site))}</p><div class="aggregate-scores" aria-label="Evidence behind the recommendation">${rows}</div><p class="summary-check"><strong>Next check</strong>${escape(nextCheck(site))}</p>${breakdownButton(site)}</div>`;
  }
  function breakdownButton(site) {
    return `<button class="breakdown-button" type="button" data-open-breakdown="${site.site_id}" aria-haspopup="dialog" aria-controls="breakdown-dialog">See score breakdown <span aria-hidden="true">↗</span><span class="sr-only"> for ${escape(site.name)}</span></button>`;
  }
  function decision(site, id = profileId()) {
    const score = site.scores[id];
    if (score.status === 'excluded') return {label: 'Exclude from selection', reason: blocker(site), tone: 'negative'};
    if (score.status !== 'eligible') return {label: 'Resolve critical checks', reason: blocker(site), tone: 'caution'};
    if (score.components.headroom_mw !== 'baseline') return {label: 'Verify grid capacity', reason: 'Get operator confirmation before prioritising.', tone: 'caution'};
    if (score.components.community_sentiment !== 'baseline' || score.unresolved_criteria.includes('community_sentiment')) return {label: 'Confirm local support', reason: 'Resolve any conditions and obtain explicit support.', tone: 'caution'};
    if (selection(site, 'owner_status', id).value !== 'loi_signed') return {label: 'Secure owner intent', reason: 'Progress the owner talks before committing.', tone: 'caution'};
    return {label: 'Start site checks', reason: 'Check connection, footprint and commercial terms.', tone: 'positive'};
  }
  function priorityBand(site, id) {
    const score = site.scores[id];
    if (score.status === 'excluded') return {label: 'Excluded', tone: 'negative'};
    if (score.status !== 'eligible') return {label: 'Critical checks first', tone: 'caution'};
    if (score.rank > 5) return {label: 'Backup option', tone: 'neutral'};
    return {label: score.rank <= 3 ? 'Leading choice' : 'Shortlisted option', tone: 'positive'};
  }
  function comparisonReason(site) {
    const now = site.scores[profileId()];
    const target = site.scores[comparisonTarget];
    if (now.components.headroom_mw !== target.components.headroom_mw) {
      return comparisonTarget === baselineId ? 'Evidence only uses official grid capacity; the vendor estimate is left out. Get operator confirmation before acting.' : 'The potential outcome uses unverified grid capacity. Confirm it with the operator before acting.';
    }
    if (now.components.community_sentiment !== target.components.community_sentiment) {
      return (comparisonTarget === baselineId ? 'Unconfirmed local support is not counted.' : 'Confirmed local support would strengthen this site’s case.') + (site.site_id === 'S-027' ? ' The noise-report condition still needs resolving.' : ' Support still needs verification.');
    }
    if (now.score === target.score) {
      return target.rank > now.rank ? 'Other sites improve under these assumptions. This site’s fit and required checks stay the same.' : target.rank < now.rank ? 'Other sites lose assumed improvements. This site’s fit and required checks stay the same.' : 'Its fit, priority and required checks stay the same.';
    }
    return 'The outcome depends on verifying the missing site information.';
  }
  function comparisonContent(site) {
    const nowScore = site.scores[profileId()];
    const targetScore = site.scores[comparisonTarget];
    const now = priorityBand(site, profileId());
    const target = priorityBand(site, comparisonTarget);
    const nowFit = scoreBand(nowScore.score);
    const targetFit = scoreBand(targetScore.score);
    const targetName = comparisonTarget === riskyId ? 'Potential' : 'Evidence only';
    const sameAction = decision(site).label === decision(site, comparisonTarget).label;
    const sameOutcome = now.label === target.label && nowFit.label === targetFit.label && nowScore.score === targetScore.score && sameAction;
    if (sameOutcome) {
      return `<div class="comparison-unchanged" ${compareScores ? '' : 'hidden'}><span class="equal-mark" aria-hidden="true">=</span><span><span class="comparison-context">Now = ${targetName}</span><strong>No change in recommendation</strong><small>${escape(nowFit.label)} · ${escape(now.label.toLowerCase())}. Required checks stay the same.</small></span></div>`;
    }
    const sameFit = nowFit.label === targetFit.label;
    const state = (item, band, side, title) => `<div class="comparison-state ${side}"><span class="comparison-state-title">${title}</span><strong class="comparison-label recommendation-${item.tone}">${item.label}</strong>${sameFit ? '' : `<small class="comparison-fit fit-${band.tone}">${band.label}</small>`}</div>`;
    return `<div class="score-comparison" ${compareScores ? '' : 'hidden'} aria-label="Now compared with ${targetName.toLowerCase()} for ${escape(site.name)}"><p class="comparison-heading">${now.label === target.label ? 'Same priority, different assumptions' : 'Priority changes'}</p><div class="comparison-values">${state(now, nowFit, 'comparison-current', 'Now')}<span class="comparison-arrow" aria-hidden="true">→</span>${state(target, targetFit, comparisonTarget === riskyId ? 'comparison-risky' : 'comparison-base', targetName)}</div><div class="comparison-why"><strong>Why</strong><p>${escape(comparisonReason(site))}</p></div>${sameFit ? `<p class="comparison-fit-note">Fit stays ${escape(nowFit.label.toLowerCase())}.</p>` : ''}</div>`;
  }
  // Display bands summarise rubric fit; they do not change ranking or eligibility.
  function scoreBand(score) {
    return score >= 80 ? {label: 'High fit', tone: 'high'} : score >= 60 ? {label: 'Medium fit', tone: 'medium'} : {label: 'Low fit', tone: 'low'};
  }
  function siteMarkup(site) {
    const score = site.scores[profileId()];
    const tied = profile().rankings.eligible.some(id => id !== site.site_id && sites.get(id).scores[profileId()].rank === score.rank);
    const rankStrength = (5 - Math.min(score.rank, 5)) / 4;
    const scoreStrength = Math.max(0, Math.min(score.score, 100)) / 100;
    const wash = Number((0.01 + 0.26 * Math.pow(rankStrength, 1.25) * (0.7 + 0.3 * scoreStrength)).toFixed(4));
    const action = decision(site);
    const band = scoreBand(score.score);
    return `<li class="site-item" data-site-id="${site.site_id}" style="--rank-wash:${wash}"><article aria-labelledby="name-${site.site_id}"><div class="site-header"><span class="rank ${score.rank === 1 ? 'top-rank' : ''}" aria-label="${tied ? 'Joint ' : ''}Rank ${score.rank}">${String(score.rank).padStart(2, '0')}</span><div class="site-identity"><h3 class="site-name" id="name-${site.site_id}">${escape(site.name)}</h3><p class="site-meta">${escape(site.region)}</p><span class="decision-label decision-${action.tone}">${escape(action.label)}</span><span class="fit-band fit-${band.tone}" aria-label="Overall score band: ${band.label}"><small>Score band</small><strong>${band.label}</strong></span></div></div>${comparisonContent(site)}<details class="site-details" id="detail-${site.site_id}"><summary>Why this recommendation <span class="chevron" aria-hidden="true">›</span><span class="sr-only"> for ${escape(site.name)}</span></summary>${aggregateContent(site)}</details></article></li>`;
  }
  function holdReason(site) {
    const names = {
      unknown_protection_status: 'Protection status is unknown', unknown_flood_zone: 'Flood risk is unknown', unknown_area: 'Usable area needs verifying', unknown_owner_status: 'Owner position is unknown',
      unresolved_protection_overlap: 'A field note reports possible reserve overlap; legal clearance is unresolved', available_area_requires_verification: 'Newer notes report roughly 700 m² remaining; usable area needs checking',
      owner_refused: 'The latest dated owner note records a refusal', protected_nature_area: 'Confirmed protected nature area', missing_official_grid: 'Official grid data is missing',
      unknown_substation_distance: 'Connection distance is unknown', unknown_headroom: 'Official capacity is unknown', missing_official_headroom: 'Official capacity is missing', no_substation_within_10_km: 'No substation was found within 10 km', field_note_infrastructure_claim_requires_reconciliation: 'Conflicting grid evidence needs reconciling'
    };
    return site.base_status.reasons.map(reason => names[reason] || reason.replace(/_/g, ' ')).join('. ') + '.';
  }
  function blocker(site) {
    const reasons = site.base_status.reasons;
    if (reasons.includes('unresolved_protection_overlap')) return 'Possible nature-reserve overlap';
    if (reasons.includes('available_area_requires_verification')) return 'Only roughly 700 m² reportedly remains';
    if (reasons.includes('unknown_protection_status')) return 'Protection, flood risk, land and owner consent unverified';
    if (reasons.includes('owner_refused')) return 'Owner refused to lease';
    if (reasons.includes('protected_nature_area')) return 'Inside a protected nature area';
    if (reasons.includes('unknown_substation_distance')) return 'Official capacity and connection distance missing';
    if (reasons.includes('no_substation_within_10_km')) return 'Official capacity missing; no substation within 10 km';
    return holdReason(site);
  }
  function contenderReason(site, cutoff) {
    const score = site.scores[profileId()];
    const gap = cutoff - score.score;
    const limits = data.rubric.criteria.map(criterion => ({
      field: criterion.id, loss: criterion.weight - (selection(site, criterion.id).contribution || 0)
    })).filter(item => item.loss > 0).sort((a, b) => b.loss - a.loss);
    const labels = {headroom_mw: 'limited grid capacity', substation_distance_km: 'a longer grid connection', owner_status: 'an unfinished owner agreement', community_sentiment: selection(site, 'community_sentiment').value == null ? 'unconfirmed local support' : 'limited local support', flood_zone: 'mapped flood risk', usable_area_m2: 'a smaller land footprint'};
    return gap === 0 ? 'Equal priority at the shortlist cutoff; site-ID order determines the five displayed.' : `Stronger options made the five. Main limits: ${limits.slice(0, 2).map(item => labels[item.field]).join(' and ')}.`;
  }
  function potentialStrengths(site) {
    const values = site.observed_inputs;
    const strengths = [];
    if (values.headroom_mw >= 4) strengths.push(`${number(values.headroom_mw)} MW of official grid capacity`);
    else if (site.sources.vendor_estimate) strengths.push(`${number(site.sources.vendor_estimate.headroom_mw_est)} MW vendor estimate, unverified`);
    if (values.owner_status === 'loi_signed') strengths.push('signed owner intent');
    if (values.community_sentiment === 'supportive') strengths.push('recorded local support');
    return strengths.length ? strengths.slice(0, 2).join('; ') + '.' : 'Its potential depends on favourable results for the missing checks.';
  }
  function renderAlternatives(topIds) {
    const rankings = profile().rankings;
    const groups = {
      contenders: rankings.eligible.filter(id => !topIds.includes(id)),
      potential: [...rankings.conditional, ...rankings.held].sort((a, b) => (sites.get(b).scores[riskyId].score ?? -1) - (sites.get(a).scores[riskyId].score ?? -1) || a.localeCompare(b)),
      excluded: rankings.excluded
    };
    const labels = {contenders: 'Contenders', potential: 'Needs checks', excluded: 'Excluded'};
    const descriptions = {contenders: 'Closest alternatives under your selected assumptions.', potential: 'Potential only. Critical checks keep these sites outside the shortlist.', excluded: 'Firm exclusions. Changing assumptions cannot bring these sites back.'};
    const ids = groups[alternativeGroup];
    const visible = ids.slice(0, alternativeLimit);
    const cutoff = sites.get(topIds.at(-1)).scores[profileId()].score;
    $('alternative-list').innerHTML = `<div class="alternative-groups" aria-label="Browse sites outside the five">${Object.keys(groups).map(group => `<button type="button" data-alternative-group="${group}" aria-pressed="${group === alternativeGroup}">${labels[group]}<small>${groups[group].length}</small></button>`).join('')}</div><p class="alternative-intro">${descriptions[alternativeGroup]}</p><div class="alternative-results">${visible.map(id => {
        const site = sites.get(id);
        const score = site.scores[profileId()];
        const risky = site.scores[riskyId];
        const scoreText = alternativeGroup === 'contenders' ? 'Backup option' : alternativeGroup === 'potential' ? 'Potential only' : 'Excluded';
        const explanation = alternativeGroup === 'contenders' ? contenderReason(site, cutoff) : holdReason(site);
        const core = alternativeGroup === 'potential' ? `<div class="alternative-core"><strong>Why outside the five</strong><p>${escape(explanation)}</p></div><div class="alternative-core"><strong>Why explore it</strong><p>${escape(potentialStrengths(site))}</p></div>` : `<div class="alternative-core"><strong>${alternativeGroup === 'excluded' ? 'Why excluded' : 'Why below the cutoff'}</strong><p>${escape(explanation)}</p></div>`;
        return `<details class="alternative ${alternativeGroup === 'excluded' ? 'alternative-excluded' : ''}" name="outside-sites" id="alternative-${id}"><summary><span class="alternative-identity"><span class="alternative-name">${escape(site.name)}</span><span class="alternative-id">${escape(site.region)} · ${id}</span>${alternativeGroup === 'potential' ? `<span class="alternative-blocker"><strong>Blocked:</strong> ${escape(blocker(site))}</span>` : ''}</span><span class="alternative-score">${escape(scoreText)} <span aria-hidden="true">＋</span></span></summary>${core}${breakdownButton(site)}</details>`;
      }).join('') || '<p class="alternative-intro">No sites in this group under your current answers.</p>'}</div><div class="alternative-pagination"><span>Showing ${visible.length} of ${ids.length}</span>${visible.length < ids.length ? '<button class="text-button" type="button" id="more-alternatives">Show 3 more <span aria-hidden="true">↓</span></button>' : ''}</div>`;
  }
  function render() {
    const openIds = [...document.querySelectorAll('.site-details[open], .alternative[open]')].map(detail => detail.id);
    const topIds = profile().rankings.eligible.slice(0, 5);
    $('site-list').innerHTML = topIds.map(id => siteMarkup(sites.get(id))).join('');
    renderAlternatives(topIds);
    for (const id of openIds) { const element = $(id); if (element) element.open = true; }
    const answered = Object.keys(answers).length;
    const custom = isCustom();
    $('ranking-basis').textContent = custom ? 'Based on your selected assumptions' : 'Recommended from current evidence';
    $('assumption-state').textContent = custom ? `${answered} / 4 answered · your assumptions` : answered ? `${answered} / 4 answered · conservative` : 'Conservative defaults until you answer';
    $('refine-progress').textContent = answered ? `${answered} of 4 answered · ${answered === 4 ? 'Review your answers' : 'Keep tailoring your shortlist'}` : 'Answer 4 quick questions to make the recommendation fit your priorities';
    $('comparison-guide').hidden = !compareScores;
    $('comparison-target-name').textContent = comparisonTarget === riskyId ? 'Potential' : 'Evidence only';
    $('comparison-explanation').textContent = `Now uses ${custom ? 'your selected assumptions' : 'current evidence'}. ${comparisonTarget === riskyId ? 'Potential assumes favourable results for unverified checks.' : 'Evidence only uses official figures and recorded positions.'}`;
    document.querySelectorAll('[data-compare-target]').forEach(button => button.setAttribute('aria-pressed', String((button.dataset.compareTarget === 'potential' ? riskyId : baselineId) === comparisonTarget)));
    $('reset-main').hidden = answered === 0;
    $('reset-main').disabled = answered === 0;
    $('reset-questions').disabled = answered === 0;
    return topIds;
  }
  function save() { try { sessionStorage.setItem(storageKey, JSON.stringify(answers)); } catch {} }
  function announce(message, showToast = false) {
    $('live-status').textContent = message;
    if (showToast) {
      $('toast').textContent = message;
      $('toast').hidden = false;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
    }
  }
  function openQuestions(index, opener) {
    questionIndex = index;
    questionOpener = opener;
    renderQuestion();
    $('questions-dialog').showModal();
    document.body.style.overflow = 'hidden';
    $('close-dialog').focus();
  }
  function renderQuestion() {
    const question = data.questions[questionIndex];
    const selected = answers[question.id] ?? question.default_answer;
    $('question-progress').innerHTML = data.questions.map((_, index) => `<span class="progress-step ${index <= questionIndex ? 'active' : ''}"></span>`).join('');
    $('question-body').innerHTML = `<p class="question-step-label">Question ${questionIndex + 1} of ${data.questions.length} · ${shortNames[question.id]}</p><h2 id="question-title" tabindex="-1">${escape(question.prompt)}</h2><p class="question-explanation" id="question-explanation">${escape(question.help)}</p><fieldset class="question-options"><legend class="sr-only">${escape(question.prompt)}</legend>${question.options.map(option => `<label class="option"><input type="radio" name="${question.id}" value="${option.id}" ${selected === option.id ? 'checked' : ''}><span class="option-copy"><span class="option-title">${escape(option.label)}${option.id === question.default_answer ? '<span class="default-badge">Default</span>' : ''}</span><span class="option-description">${escape(option.description)}</span></span></label>`).join('')}</fieldset>`;
    $('question-impact').textContent = `${question.affected_site_ids.length} sites can be affected. ${answers[question.id] == null ? 'Using the conservative default until you choose.' : 'Your answer is applied to the shortlist.'}`;
    $('previous-question').hidden = questionIndex === 0;
    $('next-question').innerHTML = questionIndex === data.questions.length - 1 ? 'View your five <span aria-hidden="true">↗</span>' : 'Next question <span aria-hidden="true">→</span>';
  }
  document.addEventListener('click', event => {
    const comparisonTrigger = event.target.closest('[data-compare-target]');
    if (comparisonTrigger) {
      comparisonTarget = comparisonTrigger.dataset.compareTarget === 'potential' ? riskyId : baselineId;
      render();
      announce('Comparison updated: Now versus ' + (comparisonTarget === riskyId ? 'potential outcomes.' : 'evidence only.'));
    }
    const groupTrigger = event.target.closest('[data-alternative-group]');
    if (groupTrigger) {
      alternativeGroup = groupTrigger.dataset.alternativeGroup;
      alternativeLimit = 3;
      renderAlternatives(profile().rankings.eligible.slice(0, 5));
      document.querySelector(`[data-alternative-group="${alternativeGroup}"]`).focus();
    }
    if (event.target.closest('#more-alternatives')) {
      const previousLimit = alternativeLimit;
      const openId = document.querySelector('.alternative[open]')?.id;
      alternativeLimit += 3;
      renderAlternatives(profile().rankings.eligible.slice(0, 5));
      if (openId && $(openId)) $(openId).open = true;
      document.querySelectorAll('.alternative > summary')[previousLimit]?.focus();
    }
    const trigger = event.target.closest('[data-open-questions]');
    if (trigger) openQuestions(Number(trigger.dataset.openQuestions), trigger);
    const breakdownTrigger = event.target.closest('[data-open-breakdown]');
    if (breakdownTrigger) {
      const site = sites.get(breakdownTrigger.dataset.openBreakdown);
      breakdownOpener = breakdownTrigger;
      $('breakdown-title').textContent = site.name;
      $('breakdown-meta').textContent = `${site.region} · ${typeNames[site.site_type]} · ${site.site_id}`;
      $('breakdown-content').innerHTML = detailsContent(site);
      $('breakdown-content').scrollTop = 0;
      $('breakdown-dialog').showModal();
      document.body.style.overflow = 'hidden';
      $('close-breakdown').focus();
    }
  });
  $('close-breakdown').addEventListener('click', () => $('breakdown-dialog').close());
  $('breakdown-dialog').addEventListener('close', () => {
    document.body.style.overflow = '';
    if (breakdownOpener?.isConnected) breakdownOpener.focus();
    $('breakdown-content').replaceChildren();
  });
  $('breakdown-dialog').addEventListener('click', event => {
    if (event.target !== $('breakdown-dialog')) return;
    const bounds = $('breakdown-dialog').getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) $('breakdown-dialog').close();
  });
  $('question-body').addEventListener('change', event => {
    if (!event.target.matches('input[type="radio"]')) return;
    const beforeProfile = profileId();
    const before = profile().rankings.eligible.slice(0, 5);
    const question = data.questions[questionIndex];
    answers[question.id] = event.target.value;
    save();
    const after = render();
    const entering = after.filter(id => !before.includes(id));
    const leaving = before.filter(id => !after.includes(id));
    const changed = data.sites.filter(site => JSON.stringify(site.scores[beforeProfile]) !== JSON.stringify(site.scores[profileId()])).length;
    let message;
    if (entering.length) message = `${entering.map(id => sites.get(id).name).join(', ')} ${entering.length === 1 ? 'enters' : 'enter'} your five. ${leaving.map(id => sites.get(id).name).join(', ')} ${leaving.length === 1 ? 'moves' : 'move'} out.`;
    else if (before.join() !== after.join()) message = 'Your five have reordered. The same sites remain in the shortlist.';
    else message = changed ? 'Your top five stay the same. Assumptions or checks changed elsewhere.' : 'Your top five stay the same. Conservative assumptions still apply.';
    $('question-impact').textContent = message;
    announce(message);
  });
  // Choosing an already-selected default still counts as an explicit answer.
  $('question-body').addEventListener('click', event => {
    if (!event.target.matches('input[type="radio"]')) return;
    const question = data.questions[questionIndex];
    if (event.target.checked && answers[question.id] == null && event.target.value === question.default_answer) {
      answers[question.id] = event.target.value;
      save(); render();
      $('question-impact').textContent = 'Conservative answer saved. Your top five stay the same.';
    }
  });
  $('close-dialog').addEventListener('click', () => $('questions-dialog').close());
  $('questions-dialog').addEventListener('close', () => {
    document.body.style.overflow = '';
    if (questionOpener?.isConnected) questionOpener.focus();
    else document.querySelector('.assumption-bar [data-open-questions]').focus();
  });
  $('questions-dialog').addEventListener('click', event => {
    if (event.target !== $('questions-dialog')) return;
    const bounds = $('questions-dialog').getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) $('questions-dialog').close();
  });
  $('next-question').addEventListener('click', () => {
    if (questionIndex === data.questions.length - 1) { $('questions-dialog').close(); return; }
    questionIndex++; renderQuestion(); $('question-title').focus();
  });
  $('previous-question').addEventListener('click', () => { questionIndex--; renderQuestion(); $('question-title').focus(); });
  function resetAnswers() {
    answers = {}; save(); render();
    if ($('questions-dialog').open) {
      renderQuestion();
      $('question-impact').textContent = 'Reset to conservative. The original five are restored.';
      $('question-title').focus();
    }
    announce('Reset to conservative. The original five are restored.', !$('questions-dialog').open);
  }
  $('reset-main').addEventListener('click', resetAnswers);
  $('reset-questions').addEventListener('click', resetAnswers);
  $('compare-toggle').addEventListener('click', () => {
    compareScores = !compareScores;
    $('compare-toggle').setAttribute('aria-pressed', String(compareScores));
    $('comparison-guide').hidden = !compareScores;
    document.querySelectorAll('.score-comparison, .comparison-unchanged').forEach(element => { element.hidden = !compareScores; });
    announce(compareScores ? 'Showing current priority compared with the selected scenario.' : 'Showing the current recommendation only.');
  });
  $('rubric-list').innerHTML = data.rubric.criteria.map(criterion => `<div class="rubric-row"><span>${escape(criterion.label)}</span><strong>${criterion.weight} points</strong></div>`).join('');
  $('data-date').textContent = `Data exported ${new Date(`${data.metadata.exported_at}T12:00:00Z`).toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'})}`;
  render();
})();
