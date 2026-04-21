let schools = [];
let currentSort = { key: "rank", dir: "asc" };

async function init() {
  const resp = await fetch("data.json");
  const data = await resp.json();
  schools = data.schools;

  renderStats(data.metadata);
  renderTable(schools);
  updateCount(schools.length, schools.length);
  bindSort();
  bindSearch();
  bindMethodology();
}

function renderStats(metadata) {
  const reg = metadata.regression;
  const c = reg.coefficients;
  const el = document.getElementById("regression-stats");
  const sign = (n) => (n >= 0 ? "+ " : "- ") + Math.abs(n);
  el.textContent =
    `n = ${reg.n_schools} schools · ` +
    `R² = ${reg.r_squared} (adj. ${reg.adj_r_squared}) · ` +
    `Model: grad_rate = ${c.sat}·SAT ${sign(c.pell_pct)}·Pell% ${sign(c.first_gen_pct)}·1stGen% ${sign(c.intercept)}`;

  const inline = document.getElementById("r-squared-inline");
  if (inline) inline.textContent = reg.r_squared.toFixed(2);
}

function renderTable(data) {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = data
    .map((s) => {
      const scoreClass =
        s.performance_score > 0
          ? "positive"
          : s.performance_score < 0
            ? "negative"
            : "neutral";
      const sign = s.performance_score > 0 ? "+" : "";
      const badges = [];
      if (s.hbcu) badges.push('<span class="badge badge-hbcu">HBCU</span>');
      if (s.hsi) badges.push('<span class="badge badge-hsi">HSI</span>');
      const nameCell = `${esc(s.name)} ${badges.join(" ")}`;
      return `<tr>
      <td>${s.rank}</td>
      <td class="school-name">${nameCell}</td>
      <td>${esc(s.state)}</td>
      <td>${esc(s.type)}</td>
      <td>${s.enrollment.toLocaleString()}</td>
      <td>${s.median_sat}</td>
      <td>${s.pell_pct}%</td>
      <td>${s.first_gen_pct}%</td>
      <td>${s.graduation_rate}%</td>
      <td>${s.expected_graduation_rate}%</td>
      <td class="score ${scoreClass}">${sign}${s.performance_score}</td>
    </tr>`;
    })
    .join("");
}

function bindSort() {
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      let dir = "desc";
      if (currentSort.key === key && currentSort.dir === "desc") dir = "asc";
      if (key === "name" || key === "state" || key === "type") {
        dir = currentSort.key === key && currentSort.dir === "asc" ? "desc" : "asc";
      }

      currentSort = { key, dir };

      document.querySelectorAll("th").forEach((t) => {
        t.classList.remove("sort-asc", "sort-desc", "active");
      });
      th.classList.add(dir === "asc" ? "sort-asc" : "sort-desc", "active");

      const filtered = getFiltered();
      filtered.sort(comparator(key, dir));
      renderTable(filtered);
    });
  });
}

function bindSearch() {
  const input = document.getElementById("search");
  input.addEventListener("input", () => {
    const filtered = getFiltered();
    filtered.sort(comparator(currentSort.key, currentSort.dir));
    renderTable(filtered);
    updateCount(filtered.length, schools.length);
  });
}

function getFiltered() {
  const query = document.getElementById("search").value.toLowerCase();
  if (!query) return [...schools];
  return schools.filter(
    (s) =>
      s.name.toLowerCase().includes(query) ||
      s.state.toLowerCase().includes(query) ||
      s.city.toLowerCase().includes(query),
  );
}

function comparator(key, dir) {
  return (a, b) => {
    let av = a[key],
      bv = b[key];
    if (typeof av === "string") {
      av = av.toLowerCase();
      bv = bv.toLowerCase();
    }
    if (av < bv) return dir === "asc" ? -1 : 1;
    if (av > bv) return dir === "asc" ? 1 : -1;
    return 0;
  };
}

function updateCount(shown, total) {
  const el = document.getElementById("count");
  el.textContent = shown === total ? `${total} schools` : `${shown} of ${total} schools`;
}

function bindMethodology() {
  const btn = document.querySelector(".methodology-toggle");
  const content = document.querySelector(".methodology-content");
  btn.addEventListener("click", () => {
    const expanded = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", !expanded);
    content.hidden = expanded;
    btn.textContent = expanded ? "How this works ▸" : "How this works ▾";
  });
}

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

init();
