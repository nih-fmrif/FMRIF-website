(function () {
  const root = document.querySelector("[data-site-search]");
  if (!root) return;

  const toggle = root.querySelector("[data-search-toggle]");
  const panel = root.querySelector("[data-search-panel]");
  const input = root.querySelector("[data-search-input]");
  const results = root.querySelector("[data-search-results]");
  const indexUrl = window.FMRIF_SEARCH_INDEX || "/search-index.json";
  let indexPromise;
  let index = [];

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[character]));
  }

  function normalize(value) {
    return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(indexUrl)
        .then((response) => (response.ok ? response.json() : []))
        .then((records) => {
          index = Array.isArray(records) ? records : [];
          return index;
        })
        .catch(() => {
          index = [];
          return index;
        });
    }
    return indexPromise;
  }

  function scoreRecord(record, terms, query) {
    const title = normalize(record.title);
    const section = normalize(record.section || record.type);
    const text = normalize(record.text);
    let score = 0;

    if (title === query) score += 80;
    if (title.includes(query)) score += 50;
    if (section.includes(query)) score += 15;

    for (const term of terms) {
      if (title.includes(term)) score += 20;
      if (section.includes(term)) score += 6;
      if (text.includes(term)) score += 3;
    }

    return score;
  }

  function renderResults(records, query) {
    if (!query) {
      results.innerHTML = '<p class="search-empty">Start typing to search pages, staff, scanners, courses, and publications.</p>';
      return;
    }

    if (!records.length) {
      results.innerHTML = '<p class="search-empty">No results found.</p>';
      return;
    }

    results.innerHTML = records.map((record) => {
      const section = record.section || record.type || "Result";
      return `
        <a class="search-popdown-result" href="${escapeHtml(record.url)}">
          <span class="search-result-section">${escapeHtml(section)}</span>
          <strong>${escapeHtml(record.title)}</strong>
          ${record.summary ? `<span>${escapeHtml(record.summary)}</span>` : ""}
        </a>
      `;
    }).join("");
  }

  function runSearch() {
    const query = normalize(input.value);
    const terms = query.split(" ").filter(Boolean);

    if (!terms.length) {
      renderResults([], "");
      return;
    }

    const matches = index
      .map((record) => ({ record, score: scoreRecord(record, terms, query) }))
      .filter((match) => match.score > 0)
      .sort((a, b) => b.score - a.score || a.record.title.localeCompare(b.record.title))
      .slice(0, 8)
      .map((match) => match.record);

    renderResults(matches, query);
  }

  function openSearch() {
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    loadIndex().then(runSearch);
    window.requestAnimationFrame(() => input.focus());
  }

  function closeSearch() {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", () => {
    if (panel.hidden) openSearch();
    else closeSearch();
  });

  input.addEventListener("input", () => {
    loadIndex().then(runSearch);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      closeSearch();
      toggle.focus();
    }
  });

  document.addEventListener("click", (event) => {
    if (!panel.hidden && !root.contains(event.target)) {
      closeSearch();
    }
  });

  renderResults([], "");
}());
