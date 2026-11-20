/* ShopKart India dashboard — all metrics recomputed in the browser from order/line arrays. */
(() => {
  const D = window.SHOPKART;
  const O = D.o, L = D.l;
  const NO = O.m.length, NL = L.o.length, NC = Math.max(...O.cust) + 1;
  const ST = Object.fromEntries(D.statuses.map((s, i) => [s, i]));
  const COD = D.payments.indexOf('COD');
  const MONTH_LBL = D.months.map(m => { const [y, mm] = m.split('-'); return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][+mm - 1] + ' ' + y.slice(2); });

  // total orders per customer (all time) for "did they come back"
  const custTotal = new Int32Array(NC);
  for (let i = 0; i < NO; i++) custTotal[O.cust[i]]++;

  const F = { year: 'all', reg: 'all', cat: 'all', pay: 'all', ch: 'all' };

  // ---------- formatting ----------
  const inr = v => {
    const a = Math.abs(v);
    if (a >= 1e7) return '₹' + (v / 1e7).toFixed(2) + ' Cr';
    if (a >= 1e5) return '₹' + (v / 1e5).toFixed(1) + ' L';
    return '₹' + Math.round(v).toLocaleString('en-IN');
  };
  const n0 = v => Math.round(v).toLocaleString('en-IN');
  const pct = (v, d = 1) => (isFinite(v) ? v.toFixed(d) : '0') + '%';
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  // ---------- core aggregation ----------
  function compute(f) {
    const yr = f.year === 'all' ? -1 : (f.year === '2023' ? 0 : 1);
    const reg = f.reg === 'all' ? -1 : +f.reg, pay = f.pay === 'all' ? -1 : +f.pay,
          ch = f.ch === 'all' ? -1 : +f.ch, cat = f.cat === 'all' ? -1 : +f.cat;
    const om = new Uint8Array(NO);
    for (let i = 0; i < NO; i++) {
      if (yr >= 0 && ((O.m[i] / 12) | 0) !== yr) continue;
      if (reg >= 0 && O.reg[i] !== reg) continue;
      if (pay >= 0 && O.pay[i] !== pay) continue;
      if (ch >= 0 && O.ch[i] !== ch) continue;
      om[i] = 1;
    }
    const nm = D.months.length, ncat = D.categories.length;
    const R = {
      rev: 0, profit: 0, lines: 0, ret: 0, disc: 0,
      mRev: new Float64Array(nm), mProfit: new Float64Array(nm),
      cRev: new Float64Array(ncat), cProfit: new Float64Array(ncat), cLines: new Float64Array(ncat), cRet: new Float64Array(ncat), cDisc: new Float64Array(ncat),
      fRev: [new Float64Array(ncat), new Float64Array(ncat)], fProfit: [new Float64Array(ncat), new Float64Array(ncat)],
      regRev: new Float64Array(D.regions.length), pRev: new Float64Array(D.products.length), pUnits: new Float64Array(D.products.length),
      chRev: new Float64Array(D.channels.length),
    };
    const inSet = new Uint8Array(NO), netOrd = new Uint8Array(NO);
    for (let j = 0; j < NL; j++) {
      const o = L.o[j];
      if (!om[o] || (cat >= 0 && L.cat[j] !== cat)) continue;
      inSet[o] = 1;
      const c = L.cat[j];
      R.lines++; R.ret += L.ret[j]; R.disc += L.disc[j];
      R.cLines[c]++; R.cRet[c] += L.ret[j]; R.cDisc[c] += L.disc[j];
      if (O.st[o] === ST.Delivered && !L.ret[j]) {
        const rv = L.rev[j], pf = rv - L.cogs[j], m = O.m[o];
        netOrd[o] = 1;
        R.rev += rv; R.profit += pf; R.mRev[m] += rv; R.mProfit[m] += pf;
        R.cRev[c] += rv; R.cProfit[c] += pf; R.regRev[O.reg[o]] += rv;
        R.pRev[L.p[j]] += rv; R.pUnits[L.p[j]] += L.q[j]; R.chRev[O.ch[o]] += rv;
        R.fRev[O.fest[o]][c] += rv; R.fProfit[O.fest[o]][c] += pf;
      }
    }
    // order level
    let orders = 0, netOrders = 0, newCust = 0, cancel = 0, rto = 0, codN = 0, ddSum = 0, ddN = 0;
    const custOrders = new Int32Array(NC), custCh = new Int16Array(NC).fill(-1);
    const payN = new Float64Array(D.payments.length), payCancel = new Float64Array(D.payments.length), payRto = new Float64Array(D.payments.length);
    const tierDd = [0, 0, 0, 0], tierN = [0, 0, 0, 0];
    const mNew = new Float64Array(nm), mRet = new Float64Array(nm), seenM = new Int16Array(NC).fill(-1);
    const bucket = [[0, 0], [0, 0], [0, 0], [0, 0]];
    for (let i = 0; i < NO; i++) {
      if (!inSet[i]) continue;
      orders++; if (netOrd[i]) netOrders++;
      const cu = O.cust[i], s = O.st[i], p = O.pay[i];
      custOrders[cu]++; custCh[cu] = O.ch[i];
      payN[p]++;
      if (s === ST.Cancelled) { cancel++; payCancel[p]++; }
      if (s === ST.RTO) { rto++; payRto[p]++; }
      if (p === COD) codN++;
      if (s === ST.Delivered && O.dd[i] >= 0) { ddSum += O.dd[i]; ddN++; tierDd[O.tier[i]] += O.dd[i]; tierN[O.tier[i]]++; }
      if (seenM[cu] !== O.m[i]) { seenM[cu] = O.m[i]; O.first[i] ? mNew[O.m[i]]++ : mRet[O.m[i]]++; }
      else if (O.first[i]) { mRet[O.m[i]]--; mNew[O.m[i]]++; }
      if (O.first[i]) {
        newCust++;
        if (O.dd[i] >= 0) {
          const b = O.dd[i] <= 2 ? 0 : O.dd[i] <= 4 ? 1 : O.dd[i] <= 6 ? 2 : 3;
          bucket[b][0]++; if (custTotal[cu] >= 2) bucket[b][1]++;
        }
      }
    }
    let active = 0, repeaters = 0;
    const chCust = new Float64Array(D.channels.length);
    for (let c = 0; c < NC; c++) if (custOrders[c]) { active++; if (custOrders[c] >= 2) repeaters++; chCust[custCh[c]]++; }
    Object.assign(R, { orders, netOrders, newCust, cancel, rto, codN, ddSum, ddN, payN, payCancel, payRto, tierDd, tierN,
                       mNew, mRet, bucket, active, repeaters, chCust,
                       aov: netOrders ? R.rev / netOrders : 0, margin: R.rev ? 100 * R.profit / R.rev : 0,
                       retRate: R.lines ? 100 * R.ret / R.lines : 0 });
    return R;
  }

  // ---------- filters ----------
  const sel = id => document.getElementById(id);
  const fill = (id, label, list) => {
    sel(id).innerHTML = `<option value="all">All ${label}</option>` + list.map((v, i) => `<option value="${i}">${v}</option>`).join('');
  };
  fill('f-region', 'regions', D.regions); fill('f-cat', 'categories', D.categories);
  fill('f-pay', 'payments', D.payments); fill('f-ch', 'channels', D.channels);
  const map = { 'f-year': 'year', 'f-region': 'reg', 'f-cat': 'cat', 'f-pay': 'pay', 'f-ch': 'ch' };
  Object.entries(map).forEach(([id, k]) => sel(id).addEventListener('change', e => { F[k] = e.target.value; render(); }));
  sel('f-reset').addEventListener('click', () => { Object.keys(F).forEach(k => F[k] = 'all'); syncFilters(); render(); });
  function syncFilters() {
    Object.entries(map).forEach(([id, k]) => { sel(id).value = F[k]; sel(id).classList.toggle('active', F[k] !== 'all'); });
  }

  // ---------- tabs ----------
  let tab = 'overview';
  document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => {
    tab = b.dataset.tab;
    document.querySelectorAll('.tabs button').forEach(x => x.setAttribute('aria-selected', x === b));
    document.querySelectorAll('.view').forEach(v => v.hidden = v.id !== 'v-' + tab);
    render();
  }));

  // ---------- charts ----------
  const charts = {};
  Chart.defaults.font.family = "'General Sans', system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  function base(extra = {}) {
    const grid = css('--color-divider'), tick = css('--color-text-muted');
    Chart.defaults.color = tick;
    return Object.assign({
      responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, color: tick } },
                 tooltip: { backgroundColor: css('--color-text'), titleColor: css('--color-surface'), bodyColor: css('--color-surface'), padding: 10, cornerRadius: 6 } },
      scales: { x: { grid: { display: false }, ticks: { color: tick }, border: { color: grid } },
                y: { grid: { color: grid }, ticks: { color: tick }, border: { display: false } } },
    }, extra);
  }
  function draw(id, cfg) {
    if (charts[id]) { charts[id].data = cfg.data; charts[id].options = cfg.options; charts[id].update(); return; }
    charts[id] = new Chart(sel(id), cfg);
  }
  const festShade = {
    id: 'festShade',
    beforeDatasetsDraw(c) {
      const x = c.scales.x, { top, bottom } = c.chartArea, ctx = c.ctx;
      const labels = c.data.labels;
      ctx.save(); ctx.fillStyle = css('--color-accent') + '1f';
      labels.forEach((l, i) => {
        if (!/^(Oct|Nov)/.test(l)) return;
        const w = x.getPixelForValue(1) - x.getPixelForValue(0);
        const cx = x.getPixelForValue(i);
        const isNov = l.startsWith('Nov');
        ctx.fillRect(cx - w / 2, top, isNov ? w / 2 : w, bottom - top);
      });
      ctx.restore();
    }
  };

  // ---------- KPI cards ----------
  function spark(vals, color) {
    const v = vals.filter(x => x !== null);
    if (v.length < 2) return '';
    const mx = Math.max(...v), mn = Math.min(...v), r = mx - mn || 1;
    const pts = v.map((x, i) => `${(i / (v.length - 1) * 72).toFixed(1)},${(24 - (x - mn) / r * 22).toFixed(1)}`).join(' ');
    return `<svg class="spark" viewBox="0 0 72 26" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  }
  function kpiCards(el, items, cur, prev) {
    sel(el).innerHTML = items.map(k => {
      const v = k.get(cur);
      let delta = '';
      if (prev) {
        const a = k.get(prev.now), b = k.get(prev.before);
        const d = k.pp ? a - b : (b ? 100 * (a / b - 1) : 0);
        const good = k.invert ? d < 0 : d > 0;
        const cls = Math.abs(d) < 0.05 ? 'flat' : good ? 'up' : 'down';
        delta = `<span class="delta ${cls}">${d > 0 ? '▲' : d < 0 ? '▼' : '■'} ${Math.abs(d).toFixed(1)}${k.pp ? ' pp' : '%'}</span><span class="vs">2024 vs 2023</span>`;
      } else delta = `<span class="vs" style="margin:0">No prior year</span>`;
      return `<div class="kpi" data-testid="kpi-${k.id}"><div class="label">${k.label}</div><div class="value">${k.fmt(v)}</div>${delta}${k.spark ? spark(k.spark(cur), css('--color-primary')) : ''}</div>`;
    }).join('');
  }
  const monthsIn = R => Array.from(R.mRev).map((v, i) => (F.year === 'all' || ((i / 12) | 0) === (F.year === '2023' ? 0 : 1)) ? i : -1).filter(i => i >= 0);

  // ---------- table helper with sorting ----------
  const sortState = {};
  function table(id, cols, rows, opts = {}) {
    const st = sortState[id] || (sortState[id] = { k: opts.sortKey, asc: false });
    if (st.k != null) rows = [...rows].sort((a, b) => (a[st.k] > b[st.k] ? 1 : -1) * (st.asc ? 1 : -1));
    const t = sel(id);
    t.innerHTML = `<thead><tr>${cols.map(c => `<th class="${c.r ? 'r' : ''}" data-k="${c.k}" ${st.k === c.k ? `aria-sort="${st.asc ? 'ascending' : 'descending'}"` : ''}>${c.label}</th>`).join('')}</tr></thead>
      <tbody>${rows.map((r, i) => `<tr class="${opts.onRow ? 'clickable' : ''} ${opts.selected && opts.selected(r) ? 'selected' : ''}" data-i="${i}" data-testid="row-${id}-${i}">${cols.map(c => `<td class="${c.r ? 'r' : ''}">${c.fmt ? c.fmt(r[c.k], r) : r[c.k]}</td>`).join('')}</tr>`).join('')}</tbody>`;
    t.querySelectorAll('th').forEach(th => th.onclick = () => {
      const k = th.dataset.k; st.asc = st.k === k ? !st.asc : false; st.k = k; table(id, cols, rows, opts);
    });
    if (opts.onRow) t.querySelectorAll('tbody tr').forEach(tr => tr.onclick = () => opts.onRow(rows[+tr.dataset.i]));
  }
  const marginPill = v => `<span class="pill ${v < 15 ? 'bad' : v < 25 ? 'mid' : 'good'}">${pct(v)}</span>`;

  // ---------- render ----------
  function render() {
    syncFilters();
    const R = compute(F);
    const prev = F.year !== '2023' ? { now: compute({ ...F, year: '2024' }), before: compute({ ...F, year: '2023' }) } : null;
    const active = Object.entries(F).filter(([, v]) => v !== 'all').length;
    sel('scope').textContent = `${n0(R.orders)} orders · ${n0(R.lines)} order lines${active ? ` · ${active} filter${active > 1 ? 's' : ''} applied` : ''}`;
    const idx = monthsIn(R);
    const primary = css('--color-primary'), accent = css('--color-accent'), grey = css('--color-grey'),
          success = css('--color-success'), error = css('--color-error');

    if (tab === 'overview') {
      kpiCards('kpi-overview', [
        { id: 'revenue', label: 'Net revenue', get: r => r.rev, fmt: inr, spark: r => idx.map(i => r.mRev[i]) },
        { id: 'profit', label: 'Gross profit', get: r => r.profit, fmt: inr, spark: r => idx.map(i => r.mProfit[i]) },
        { id: 'margin', label: 'Gross margin', get: r => r.margin, fmt: v => pct(v), pp: true },
        { id: 'orders', label: 'Orders', get: r => r.orders, fmt: n0 },
        { id: 'aov', label: 'Avg order value', get: r => r.aov, fmt: inr },
        { id: 'returns', label: 'Item return rate', get: r => r.retRate, fmt: v => pct(v), pp: true, invert: true },
      ], R, prev);

      draw('c-trend', { type: 'bar', plugins: [festShade], data: {
        labels: idx.map(i => MONTH_LBL[i]),
        datasets: [
          { type: 'line', label: 'Gross margin %', data: idx.map(i => R.mRev[i] ? 100 * R.mProfit[i] / R.mRev[i] : null), borderColor: accent, backgroundColor: accent, yAxisID: 'y1', tension: .3, pointRadius: 3, borderWidth: 2 },
          { label: 'Net revenue', data: idx.map(i => R.mRev[i]), backgroundColor: primary, borderRadius: 3, maxBarThickness: 28, yAxisID: 'y' },
        ] }, options: base({
          plugins: { ...base().plugins, tooltip: { ...base().plugins.tooltip, callbacks: { label: c => c.dataset.yAxisID === 'y1' ? ` Margin ${pct(c.raw)}` : ` Revenue ${inr(c.raw)}` } } },
          scales: { x: base().scales.x,
            y: { ...base().scales.y, ticks: { ...base().scales.y.ticks, callback: v => inr(v) } },
            y1: { position: 'right', min: 0, max: 40, grid: { display: false }, border: { display: false }, ticks: { color: css('--color-text-muted'), callback: v => v + '%' } } } }) });

      const catRows = D.categories.map((c, i) => ({ i, name: c, rev: R.cRev[i], share: R.rev ? 100 * R.cRev[i] / R.rev : 0,
        margin: R.cRev[i] ? 100 * R.cProfit[i] / R.cRev[i] : 0, ret: R.cLines[i] ? 100 * R.cRet[i] / R.cLines[i] : 0,
        disc: R.cLines[i] ? R.cDisc[i] / R.cLines[i] / 10 : 0 })).filter(r => r.rev > 0);
      const maxRev = Math.max(...catRows.map(r => r.rev), 1);
      table('t-cat', [
        { k: 'name', label: 'Category' },
        { k: 'rev', label: 'Net revenue', fmt: (v) => `<div class="bar-cell"><i style="width:${(v / maxRev * 90).toFixed(0)}px"></i>${inr(v)}</div>` },
        { k: 'share', label: 'Share', r: 1, fmt: v => pct(v) },
        { k: 'margin', label: 'Margin', r: 1, fmt: marginPill },
        { k: 'ret', label: 'Returns', r: 1, fmt: v => pct(v) },
        { k: 'disc', label: 'Avg disc.', r: 1, fmt: v => pct(v) },
      ], catRows, { sortKey: 'rev', selected: r => F.cat === String(r.i),
        onRow: r => { F.cat = F.cat === String(r.i) ? 'all' : String(r.i); render(); } });

      const regOrder = D.regions.map((r, i) => [r, R.regRev[i]]).sort((a, b) => b[1] - a[1]);
      draw('c-region', { type: 'bar', data: { labels: regOrder.map(r => r[0]),
        datasets: [{ label: 'Net revenue', data: regOrder.map(r => r[1]), backgroundColor: regOrder.map((r) => F.reg !== 'all' && D.regions[+F.reg] === r[0] ? accent : primary), borderRadius: 4, maxBarThickness: 26 }] },
        options: base({ indexAxis: 'y', plugins: { legend: { display: false }, tooltip: { ...base().plugins.tooltip, callbacks: { label: c => ' ' + inr(c.raw) } } },
          scales: { x: { ...base().scales.y, ticks: { ...base().scales.y.ticks, callback: v => inr(v) } }, y: { ...base().scales.x } } }) });

      const prods = Array.from(R.pRev).map((v, i) => ({ i, name: D.products[i][0], cat: D.categories[D.products[i][1]], rev: v, units: R.pUnits[i] }))
        .sort((a, b) => b.rev - a.rev).slice(0, 10).map((p, k) => ({ ...p, rank: k + 1, share: R.rev ? 100 * p.rev / R.rev : 0 }));
      table('t-prod', [
        { k: 'rank', label: '#', fmt: v => `<span class="muted">${v}</span>` }, { k: 'name', label: 'Product' }, { k: 'cat', label: 'Category' },
        { k: 'units', label: 'Units', r: 1, fmt: n0 }, { k: 'rev', label: 'Net revenue', r: 1, fmt: inr }, { k: 'share', label: 'Share', r: 1, fmt: v => pct(v, 2) },
      ], prods, { sortKey: 'rev' });
    }

    if (tab === 'customers') {
      kpiCards('kpi-customers', [
        { id: 'active', label: 'Active customers', get: r => r.active, fmt: n0 },
        { id: 'new', label: 'New customers', get: r => r.newCust, fmt: n0, spark: r => idx.map(i => r.mNew[i]) },
        { id: 'repeat', label: 'Repeat customer rate', get: r => r.active ? 100 * r.repeaters / r.active : 0, fmt: v => pct(v), pp: true },
        { id: 'rpc', label: 'Revenue per customer', get: r => r.active ? r.rev / r.active : 0, fmt: inr },
        { id: 'opc', label: 'Orders per customer', get: r => r.active ? r.orders / r.active : 0, fmt: v => v.toFixed(2) },
      ], R, prev);

      draw('c-newret', { type: 'bar', data: { labels: idx.map(i => MONTH_LBL[i]), datasets: [
        { label: 'Returning', data: idx.map(i => R.mRet[i]), backgroundColor: primary, borderRadius: 2, maxBarThickness: 28 },
        { label: 'New', data: idx.map(i => R.mNew[i]), backgroundColor: css('--color-primary-soft'), borderColor: primary, borderWidth: 1, borderRadius: 2, maxBarThickness: 28 },
      ] }, options: base({ scales: { x: { ...base().scales.x, stacked: true }, y: { ...base().scales.y, stacked: true } } }) });

      const chRows = D.channels.map((c, i) => [c, R.chCust[i] ? R.chRev[i] / R.chCust[i] : 0]).sort((a, b) => b[1] - a[1]);
      draw('c-channel', { type: 'bar', data: { labels: chRows.map(r => r[0]), datasets: [{ label: 'Revenue per customer', data: chRows.map(r => r[1]),
        backgroundColor: chRows.map((r, i) => i === 0 ? success : i === chRows.length - 1 ? error : primary), borderRadius: 4, maxBarThickness: 26 }] },
        options: base({ indexAxis: 'y', plugins: { legend: { display: false }, tooltip: { ...base().plugins.tooltip, callbacks: { label: c => ' ' + inr(c.raw) } } },
          scales: { x: { ...base().scales.y, ticks: { ...base().scales.y.ticks, callback: v => inr(v) } }, y: base().scales.x } }) });

      const action = { 'Champions': 'VIP tier, early access', 'Loyal': 'Cross-sell Beauty & Fashion', 'At Risk (high value)': 'Win-back campaign now',
        'Needs Attention': 'Personalised recos', 'Hibernating / Lost': 'Low-cost email only', 'New / Promising': '2nd-order nudge' };
      table('t-rfm', [
        { k: 0, label: 'Segment', fmt: v => `<b>${v}</b>` }, { k: 1, label: 'Customers', r: 1, fmt: n0 },
        { k: 6, label: '% customers', r: 1, fmt: v => pct(v) }, { k: 7, label: '% revenue', r: 1, fmt: (v) => `<span class="pill ${v > 14 ? 'good' : v < 6 ? 'bad' : 'mid'}">${pct(v)}</span>` },
        { k: 2, label: 'Revenue', r: 1, fmt: inr }, { k: 3, label: 'Avg recency (days)', r: 1, fmt: n0 },
        { k: 4, label: 'Avg orders', r: 1, fmt: v => (+v).toFixed(1) }, { k: 5, label: 'Avg spend', r: 1, fmt: inr },
        { k: 0, label: 'Action', fmt: v => `<span class="muted">${action[v]}</span>` },
      ], D.rfm, { sortKey: 7 });

      const C = D.cohort, ct = sel('t-cohort');
      const cellBg = v => `color-mix(in oklab, ${primary} ${Math.min(100, v / 40 * 100).toFixed(0)}%, transparent)`;
      ct.innerHTML = `<thead><tr><th style="text-align:left">Cohort</th><th>Size</th>${C.vals[0].map((_, j) => `<th>M${j}</th>`).join('')}</tr></thead><tbody>` +
        C.rows.map((r, i) => `<tr><td class="lbl">${MONTH_LBL[D.months.indexOf(r)]}</td><td class="muted">${n0(C.size[i])}</td>${C.vals[i].map((v, j) =>
          v === null ? '<td></td>' : j === 0 ? `<td style="background:${cellBg(40)};color:#fff">100</td>`
          : `<td style="background:${cellBg(v)};color:${v > 24 ? '#fff' : 'inherit'}" title="${pct(v)} of cohort ordered in month ${j}">${Math.round(v)}</td>`).join('')}</tr>`).join('') + '</tbody>';
    }

    if (tab === 'operations') {
      kpiCards('kpi-operations', [
        { id: 'cancel', label: 'Cancellation rate', get: r => r.orders ? 100 * r.cancel / r.orders : 0, fmt: v => pct(v), pp: true, invert: true },
        { id: 'rto', label: 'RTO rate', get: r => r.orders ? 100 * r.rto / r.orders : 0, fmt: v => pct(v), pp: true, invert: true },
        { id: 'cod', label: 'COD share of orders', get: r => r.orders ? 100 * r.codN / r.orders : 0, fmt: v => pct(v), pp: true, invert: true },
        { id: 'delivery', label: 'Avg delivery time', get: r => r.ddN ? r.ddSum / r.ddN : 0, fmt: v => v.toFixed(1) + ' days', invert: true },
      ], R, prev);

      const pRows = D.payments.map((p, i) => ({ p, n: R.payN[i], c: R.payN[i] ? 100 * R.payCancel[i] / R.payN[i] : 0, r: R.payN[i] ? 100 * R.payRto[i] / R.payN[i] : 0 }))
        .filter(x => x.n > 0).sort((a, b) => b.r - a.r);
      draw('c-pay', { type: 'bar', data: { labels: pRows.map(x => x.p), datasets: [
        { label: 'RTO %', data: pRows.map(x => x.r), backgroundColor: error, borderRadius: 3, maxBarThickness: 18 },
        { label: 'Cancelled %', data: pRows.map(x => x.c), backgroundColor: grey, borderRadius: 3, maxBarThickness: 18 },
      ] }, options: base({ indexAxis: 'y', plugins: { ...base().plugins, tooltip: { ...base().plugins.tooltip, callbacks: { label: c => ` ${c.dataset.label.replace(' %', '')}: ${pct(c.raw)}` } } },
        scales: { x: { ...base().scales.y, ticks: { ...base().scales.y.ticks, callback: v => v + '%' } }, y: base().scales.x } }) });

      const bl = ['1–2 days', '3–4 days', '5–6 days', '7+ days'];
      const bv = R.bucket.map(b => b[0] ? 100 * b[1] / b[0] : 0);
      draw('c-deliv', { type: 'bar', data: { labels: bl, datasets: [{ label: 'Repeat rate', data: bv,
        backgroundColor: [success, success, accent, error], borderRadius: 4, maxBarThickness: 64 }] },
        options: base({ plugins: { legend: { display: false }, tooltip: { ...base().plugins.tooltip, callbacks: {
          label: c => ` ${pct(c.raw)} ordered again`, afterLabel: c => ` ${n0(R.bucket[c.dataIndex][0])} customers` } } },
          scales: { x: base().scales.x, y: { ...base().scales.y, min: 0, max: 80, ticks: { ...base().scales.y.ticks, callback: v => v + '%' } } } }) });

      const fm = (k, i) => R.fRev[k][i] ? 100 * R.fProfit[k][i] / R.fRev[k][i] : null;
      const fc = D.categories.map((c, i) => i).filter(i => R.cRev[i] > 0);
      draw('c-fest', { type: 'bar', data: { labels: fc.map(i => D.categories[i]), datasets: [
        { label: 'Rest of year', data: fc.map(i => fm(0, i)), backgroundColor: primary, borderRadius: 3, maxBarThickness: 22 },
        { label: 'Festive sale', data: fc.map(i => fm(1, i)), backgroundColor: fc.map(i => (fm(1, i) ?? 0) < 0 ? error : accent), borderRadius: 3, maxBarThickness: 22 },
      ] }, options: base({ plugins: { ...base().plugins, tooltip: { ...base().plugins.tooltip, callbacks: { label: c => ` ${c.dataset.label}: ${pct(c.raw)}` } } },
        scales: { x: base().scales.x, y: { ...base().scales.y, ticks: { ...base().scales.y.ticks, callback: v => v + '%' } } } }) });

      const tiers = [1, 2, 3].filter(t => R.tierN[t]);
      draw('c-tier', { type: 'bar', data: { labels: tiers.map(t => `Tier ${t}`), datasets: [{ label: 'Avg delivery days', data: tiers.map(t => R.tierDd[t] / R.tierN[t]),
        backgroundColor: tiers.map(t => t === 1 ? success : t === 2 ? accent : error), borderRadius: 4, maxBarThickness: 64 }] },
        options: base({ plugins: { legend: { display: false }, tooltip: { ...base().plugins.tooltip, callbacks: { label: c => ` ${c.raw.toFixed(1)} days`, afterLabel: c => ` ${n0(R.tierN[tiers[c.dataIndex]])} delivered orders` } } },
          scales: { x: base().scales.x, y: { ...base().scales.y, min: 0, ticks: { ...base().scales.y.ticks, callback: v => v + 'd' } } } }) });
    }
  }

  // ---------- theme ----------
  const root = document.documentElement, tbtn = document.querySelector('[data-theme-toggle]');
  const sun = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
  const moon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  let theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const applyTheme = () => {
    root.setAttribute('data-theme', theme); tbtn.innerHTML = theme === 'dark' ? sun : moon;
    tbtn.setAttribute('aria-label', 'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode');
    Object.keys(charts).forEach(k => { charts[k].destroy(); delete charts[k]; });
  };
  tbtn.addEventListener('click', () => { theme = theme === 'dark' ? 'light' : 'dark'; applyTheme(); render(); });
  applyTheme();
  render();
})();
