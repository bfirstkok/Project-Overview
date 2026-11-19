import {active, effectiveStatus, escapeHTML as e} from './core.js';

const teams = [
  {key: 'sales', label: 'Sales'},
  {key: 'engineer', label: 'Engineer'},
];
const segments = [
  {key: 'done', label: 'เสร็จแล้ว'},
  {key: 'open', label: 'ยังไม่เสร็จ'},
  {key: 'cancelled', label: 'ยกเลิก'},
];

export function extraOverviewData(tasks, months) {
  const open = tasks.filter(active);
  const buckets = [0, 25, 50, 75].map(min => {
    const max = min + 24;
    return {min, max, count: open.filter(t => t.progress >= min && t.progress <= max).length};
  });
  const mean = open.length ? open.reduce((sum, t) => sum + Number(t.progress), 0) / open.length : null;

  // Carry forward tasks dated before the first visible month.
  let cumulative = tasks.filter(t => t.start && t.start.slice(0, 7) < months[0].key).length;
  const trend = months.map(month => {
    cumulative += month.count;
    return {...month, count: cumulative};
  });

  const assignments = teams.map(team => {
    const counts = {done: 0, open: 0, cancelled: 0};
    const assigned = tasks.filter(t => t[team.key]?.length);
    for (const task of assigned) {
      const status = effectiveStatus(task);
      const category = status === 'Complete' ? 'done' : status === 'Cancelled' ? 'cancelled' : 'open';
      counts[category]++;
    }
    return {...team, ...counts, total: assigned.length};
  });
  return {trend, buckets, mean, openCount: open.length, assignments};
}

function chart(kind, heading, description, body, note) {
  return `<section class="overview-chart overview-extra" data-overview-chart="${kind}">
    <div class="overview-chart-heading"><div><h2>${heading}</h2><p>${description}</p></div></div>
    ${body}
    <p class="overview-chart-note">${note}</p>
  </section>`;
}

function trendChart(trend) {
  const peak = trend.at(-1).count;
  const step = Math.max(1, Math.ceil(peak / 4));
  const points = trend.map((month, index) => ({
    ...month, x: 48 + 69 * index, y: 158 - 125 * month.count / (4 * step),
  }));
  const path = points.map(({x, y}) => `${x},${y}`).join(' ');
  const summary = points.map(month => `${month.key} ${month.count} งาน`).join(', ');
  return `<svg viewBox="0 0 420 190" class="overview-trend" role="img" aria-label="${e(summary)}">
    ${[0, 2, 4].map(tick => {
      const y = 158 - tick * 125 / 4;
      return `<line x1="40" x2="405" y1="${y}" y2="${y}" class="chart-grid-line"/>
        <text x="34" y="${y + 4}" text-anchor="end" class="chart-axis">${tick * step}</text>`;
    }).join('')}
    <polygon points="48,158 ${path} 393,158" class="overview-trend-area"/>
    <polyline points="${path}" class="overview-trend-line"/>
    ${points.map(month => `<g>
      <circle cx="${month.x}" cy="${month.y}" r="4"><title>${month.key} · ${month.count} งาน</title></circle>
      <text x="${month.x}" y="${month.y - 11}" text-anchor="middle" class="chart-bar-value">${month.count}</text>
      <text x="${month.x}" y="181" text-anchor="middle" class="chart-axis">${e(month.label)}</text>
    </g>`).join('')}
  </svg>`;
}

function progressChart(buckets) {
  const max = Math.max(1, ...buckets.map(bucket => bucket.count));
  return `<div class="overview-progress-bins">${buckets.map(({min, max: upper, count}, index) => `
    <button type="button" data-progress-bin="${index}" ${count ? '' : 'disabled'}
      aria-label="ดูงานความคืบหน้า ${min} ถึง ${upper}% จำนวน ${count} งาน">
      <strong>${count}</strong>
      <span class="overview-bin-track" aria-hidden="true"><span style="height:${count / max * 100}%"></span></span>
      <span>${min}–${upper}%</span>
    </button>`).join('')}</div>`;
}

function meanChart(mean) {
  const value = mean === null ? '—' : `${Math.round(mean)}%`;
  const arc = 'M 30 110 A 90 90 0 0 1 210 110';
  return `<svg viewBox="0 0 240 139" class="overview-gauge" role="img"
    aria-label="${mean === null ? 'ไม่มีงานที่ยังไม่เสร็จ' : 'ความคืบหน้าเฉลี่ย ' + value}">
    <path d="${arc}" class="overview-gauge-track"/>
    ${mean > 0 ? `<path d="${arc}" class="overview-gauge-fill" pathLength="100" stroke-dasharray="${mean} 100"/>` : ''}
    <text x="120" y="99" text-anchor="middle" class="chart-total">${value}</text>
    <text x="23" y="132" class="chart-axis">0%</text>
    <text x="218" y="132" text-anchor="end" class="chart-axis">100%</text>
  </svg>`;
}

function teamChart(assignments) {
  const max = Math.max(1, ...assignments.map(team => team.total));
  return `<div class="overview-workload-legend overview-team-legend">${segments.map(({key, label}) =>
    `<span><i class="team-fill-${key}"></i>${label}</span>`).join('')}</div>
    <div class="overview-team-bars">${assignments.map(team => `
      <button type="button" class="overview-team-bar" data-chart-team="${team.key}" ${team.total ? '' : 'disabled'}>
        <span><strong>${team.label}</strong><span>${team.total} งาน</span></span>
        <span class="overview-bar-track" aria-hidden="true">${segments.map(({key}) =>
          `<i class="team-fill-${key}" style="width:${team[key] / max * 100}%"></i>`).join('')}</span>
        <small>${segments.map(({key, label}) => `${label} ${team[key]}`).join(' · ')}</small>
      </button>`).join('')}</div>`;
}

export function extraOverviewCharts(data) {
  return [
    chart('trend', 'งานสะสมตามวันเริ่ม', 'ยอดสะสมถึงสิ้นเดือนในช่วง 6 เดือนล่าสุด', trendChart(data.trend),
      'รวมงานก่อนช่วงที่แสดง และนับเฉพาะงานที่ระบุ Start Date'),
    chart('progress', 'งานตามช่วงความคืบหน้า', 'จำนวนงานที่ยังไม่เสร็จในแต่ละช่วง', progressChart(data.buckets),
      'กดแท่งกราฟเพื่อเปิดรายการงานในช่วงนั้น'),
    chart('mean', 'ความคืบหน้าเฉลี่ย', 'เฉลี่ย % Complete ของงานที่ยังไม่เสร็จ', meanChart(data.mean),
      data.openCount ? `เฉลี่ยจาก ${data.openCount} งาน โดยให้น้ำหนักเท่ากันทุกงาน` : 'ไม่มีงานที่ยังไม่เสร็จ'),
    chart('teams', 'งานที่มอบหมายให้แต่ละทีม', 'เปรียบเทียบจำนวนงานและสถานะของ Sales กับ Engineer', teamChart(data.assignments),
      'งานที่มอบหมายให้ทั้งสองทีมจะนับในแต่ละทีม กดชื่อทีมเพื่อเปิดรายการ'),
  ].join('');
}
