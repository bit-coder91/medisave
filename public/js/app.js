const API = "/api/v1/compare";
const $ = (id) => document.getElementById(id);
const inr = (n) => n == null ? "—" : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(n));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let position = null;
let sort = "price";
let data = [];
let currentGuide = null;
let providers = [];
const providersReady = loadProviders();

const examples = [
  { brand: "Atorva", generic: "Atorvastatin", brandPrice: 74, genericPrice: 24 },
  { brand: "Glycomet", generic: "Metformin", brandPrice: 22, genericPrice: 10 },
  { brand: "Dolo 650", generic: "Paracetamol", brandPrice: 32, genericPrice: 16 },
  { brand: "Telma", generic: "Telmisartan", brandPrice: 48, genericPrice: 22 },
];
let exampleIndex = 0;

function themeUI() {
  const dark = document.documentElement.classList.contains("dark");
  $("ti").textContent = dark ? "☀" : "☾";
  $("tl").textContent = dark ? "Light" : "Dark";
  $("theme").setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  document.querySelector('meta[name="theme-color"]').setAttribute("content", dark ? "#091321" : "#f6f8fc");
}

function rotateExample() {
  const card = $("case-card");
  card.classList.add("is-changing");
  setTimeout(() => {
    const e = examples[exampleIndex];
    $("case-brand-label").textContent = e.brand + " brand";
    $("case-generic-label").textContent = e.generic + " generic";
    $("case-brand").textContent = inr(e.brandPrice);
    $("case-generic").textContent = inr(e.genericPrice);
    $("case-save").textContent = "Illustrative difference " + inr(e.brandPrice - e.genericPrice);
    $("case-count").textContent = (exampleIndex + 1) + " of " + examples.length;
    card.classList.remove("is-changing");
    exampleIndex = (exampleIndex + 1) % examples.length;
  }, 180);
}

$("theme").onclick = () => {
  const dark = document.documentElement.classList.toggle("dark");
  try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch {}
  themeUI();
  paint();
};
themeUI();

["Paracetamol", "Dolo 650", "Cold and cough", "Headache", "Neck pain", "Sprain", "Fever"].forEach((name) => {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = name;
  button.className = "chip px-3 py-1 font-semibold";
  button.onclick = () => { $("q").value = name; run(name); };
  $("chips").append(button);
});
if (!matchMedia("(prefers-reduced-motion: reduce)").matches) setInterval(rotateExample, 5200);

$("geo").onclick = () => navigator.geolocation
  ? navigator.geolocation.getCurrentPosition((p) => {
    position = p.coords;
    updateSortControls();
    $("loc").textContent = "Location on. Nearby sample listings can now be sorted by distance.";
    if ($("q").value.trim().length > 1) run($("q").value.trim());
    }, () => { $("loc").textContent = "Location blocked. Showing sample price comparisons only."; })
  : $("loc").textContent = "Location is not supported in this browser.";

$("f").onsubmit = (event) => { event.preventDefault(); run($("q").value.trim()); };
$("source").onchange = () => { updateSortControls(); if ($("q").value.trim().length > 1) run($("q").value.trim()); };
$("pharmacy").onchange = () => paint();
document.querySelectorAll("[data-s]").forEach((button) => button.onclick = () => { sort = button.dataset.s; paint(); });

async function loadProviders() {
  const select = $("pharmacy");
  try {
    const response = await fetch("/api/v1/providers", { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Provider list unavailable.");
    providers = payload.providers || [];
    select.replaceChildren();
    if (!providers.length) {
      select.add(new Option("No pharmacy websites configured", ""));
      select.disabled = true;
      return;
    }
    for (const provider of providers) select.add(new Option(provider.name, String(provider.id)));
    select.disabled = false;
  } catch {
    providers = [];
    select.replaceChildren(new Option("Pharmacy websites unavailable", ""));
    select.disabled = true;
  }
}

function selectedProvider() {
  return providers.find((provider) => String(provider.id) === $("pharmacy").value) || null;
}

function providerSearchLink(query) {
  const provider = selectedProvider();
  if (!provider) return "";
  const googleQuery = `${query} site:${provider.domain}`;
  const url = `https://www.google.com/search?q=${encodeURIComponent(googleQuery)}`;
  return `<a class="retailer-search" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open Google results for ${esc(provider.name)} (prices not verified)</a>`;
}

function updateSortControls() {
  const nearest = document.querySelector('[data-s="km"]');
  const available = Boolean(position) && $("source").value !== "online";
  nearest.disabled = !available;
  nearest.title = available ? "Sort using nearby pharmacy distance" : "Allow location access and include nearby pharmacies first";
  if (!available && sort === "km") sort = "price";
}

async function getToken() {
  for (let i = 0; i < 100 && !window.MediSaveAuth; i++) await new Promise((resolve) => setTimeout(resolve, 20));
  if (!window.MediSaveAuth) return "";
  return window.MediSaveAuth.token();
}

async function run(query) {
  currentGuide = null;
  data = [];
  $("results-wrap").hidden = false;
  $("rt").textContent = "Searching the catalog…";
  $("out").innerHTML = '<div class="card h-64 sk"></div><div class="card h-64 sk"></div>';
  try {
    await providersReady;
    updateSortControls();
    const token = await getToken();
    const params = new URLSearchParams({ q: query, source: $("source").value });
    if (position) { params.set("lat", position.latitude); params.set("lng", position.longitude); }
    const response = await fetch(`${API}?${params}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (response.status === 401) {
      location.assign(`/login.html?next=${encodeURIComponent(location.pathname + location.search + location.hash)}`);
      return;
    }
    if (!response.ok) throw new Error("The catalog is temporarily unavailable.");
    const payload = await response.json();
    data = payload.results || [];
    currentGuide = payload.guide || null;
    $("sort-tools").hidden = Boolean(currentGuide);
    if (currentGuide) {
      $("rt").textContent = `Health information for ${query}`;
      $("out").innerHTML = guideCard(currentGuide);
      $("results-wrap").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
      return;
    }
    const closest = data.some((medicine) => medicine.closest_match);
    $("rt").textContent = data.length
      ? `${closest ? "Probable matches" : "Results"} for “${query}” · ${data.length} medicine${data.length === 1 ? "" : "s"}`
      : "No close match found";
    if (!data.length) {
      const providerLink = providerSearchLink(query);
      $("out").innerHTML = `<div class="card p-6 lg:col-span-2"><h3 class="text-lg font-extrabold">${esc(query)} is not in the MediSave catalogue yet</h3><p class="mt-2">Try the brand, active ingredient, strength, or a likely spelling. You can also search the selected pharmacy website or ask the community to find it.</p><div class="mt-4 flex flex-wrap items-center gap-4">${providerLink}<button class="store-link" id="request-unlisted" type="button">Request this medicine</button></div><p class="mt-3 text-xs" style="color:var(--muted)">Google results are opened for you to review. MediSave does not scrape or verify live prices, stock, or reviews.</p></div>`;
      $("request-medicine").value = query;
      $("request-unlisted")?.addEventListener("click", () => {
        $("request-medicine").value = query;
        $("community").scrollIntoView({ behavior: "smooth", block: "start" });
        $("request-medicine").focus({ preventScroll: true });
      });
    } else paint();
    $("results-wrap").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  } catch (error) {
    if (error.message === "Sign in to search.") return;
    $("rt").textContent = "We could not load prices";
    $("out").innerHTML = '<p class="card p-6 lg:col-span-2 error">' + esc(error.message || "Prices could not be loaded. Check your connection and try again.") + "</p>";
  }
}

function paint() {
  document.querySelectorAll("[data-s]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.s === sort)));
  const content = [];
  if (currentGuide) content.push(guideCard(currentGuide));
  if (data.length) {
    const ranked = [...data].sort((a, b) => {
      const rank = (medicine) => {
        const offers = medicine.offers || [];
        if (sort === "km") {
          const distances = offers.filter((offer) => offer.source === "nearby" && offer.km != null).map((offer) => Number(offer.km));
          return distances.length ? Math.min(...distances) : Number.POSITIVE_INFINITY;
        }
        const prices = offers.map((offer) => Number(offer.generic_price)).filter(Number.isFinite);
        return prices.length ? Math.min(...prices) : Number.POSITIVE_INFINITY;
      };
      return rank(a) - rank(b);
    });
    content.push(ranked.map(card).join(""));
  }
  if (content.length) $("out").innerHTML = content.join("");
}

function guideCard(guide) {
  const urgent = guide.urgent_match
    ? `<div class="urgent-banner" role="alert"><b>Possible warning sign in your search: ${esc(guide.urgent_match)}.</b> If this is happening now, get urgent medical help. For an emergency in India, <a href="tel:112">call 112</a>.</div>`
    : "";
  const care = (guide.self_care || []).map((item) => `<li>${esc(item)}</li>`).join("");
  const redFlags = (guide.red_flags || []).map((item) => `<li>${esc(item)}</li>`).join("");
  const references = [...(guide.sources || []), { label: "India emergency response: 112", url: "https://112.gov.in/" }];
  const sources = references.map((source) => `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.label)}</a>`).join("");
  return `<article class="card symptom-card p-5"><p class="section-kicker">General information · not a diagnosis</p><h3 class="mt-2 text-xl font-extrabold">${esc(guide.title)}</h3><p class="mt-2 text-sm" style="color:var(--muted)">${esc(guide.summary)}</p>${urgent}<div class="mt-5 grid md:grid-cols-2 gap-5"><section><h4 class="font-extrabold">Self-care information</h4><ul class="guidance-list mt-2 text-sm">${care}</ul></section><section><h4 class="font-extrabold">Get medical help promptly if</h4><ul class="guidance-list mt-2 text-sm">${redFlags}</ul></section></div><div class="source-links">${sources}</div><p class="mt-4 text-xs" style="color:var(--muted)">This phrase matcher cannot assess your health or select a medicine. If symptoms are severe, worsening, or worrying, contact a healthcare professional.</p></article>`;
}

function card(medicine) {
  const offers = [...medicine.offers].sort((a, b) => {
    if (sort === "km") {
      const aDistance = a.source === "nearby" && a.km != null ? Number(a.km) : Number.POSITIVE_INFINITY;
      const bDistance = b.source === "nearby" && b.km != null ? Number(b.km) : Number.POSITIVE_INFINITY;
      if (aDistance !== bDistance) return aDistance - bDistance;
    }
    return Number(a.generic_price) - Number(b.generic_price);
  });
  const maxBrand = Math.max(1, ...offers.map((offer) => offer.brand_price || 0));
  const savings = medicine.generic_savings_pct == null ? "" : `Illustrative difference ${medicine.generic_savings_pct}%`;
  const confidence = medicine.match_method === "tfidf_cosine"
    ? `<span class="match-note">TF-IDF NLP match · check the active ingredient</span>`
    : medicine.match_method === "character_fuzzy"
      ? `<span class="match-note">Probable spelling match · check the active ingredient</span>`
      : `<span class="match-note">Catalog name match</span>`;
  const retailerSearch = providerSearchLink(`${medicine.brand} ${medicine.generic_label} ${medicine.strength} reviews`);
  return `<article class="card results-card p-5"><div class="flex justify-between gap-3 flex-wrap"><div><h3 class="text-xl font-extrabold">${esc(medicine.brand)} <span class="font-semibold text-base" style="color:var(--muted)">${esc(medicine.strength)}</span></h3><p class="text-sm" style="color:var(--muted)">Active ingredient: ${esc(medicine.generic_label)} · ${esc(medicine.pack_size)} per pack</p>${confidence}${retailerSearch}</div>${savings ? `<span class="self-start rounded-full px-3 py-1 text-sm font-extrabold" style="background:var(--teal-soft);color:var(--teal)">${savings}</span>` : ""}</div><p class="mt-3 text-sm">${medicine.cheapest_brand == null ? "Illustrative generic listing" : `Illustrative pack prices differ by <b>${medicine.brand_price_spread_pct}%</b> between sample listings. Lowest listed generic: <b style="color:var(--teal)">${inr(medicine.cheapest_generic)}</b> vs. brand <b>${inr(medicine.cheapest_brand)}</b>.`}</p><ul class="mt-4 space-y-3">${offers.map((offer, index) => {
    const online = offer.source === "online";
    const title = online ? "Online · illustrative price" : "Pharmacy · illustrative price";
    const area = online ? (offer.area || "India") : offer.area;
    const distance = offer.km != null ? ` · ${offer.km} km` : "";
    const best = index === 0 ? ' <span class="text-xs" style="color:var(--teal)">(best)</span>' : "";
    const storeLink = online && offer.url ? ` <a class="store-link" href="${esc(offer.url)}" target="_blank" rel="noopener noreferrer">Visit website ↗</a>` : "";
    return `<li><div class="flex justify-between gap-2 flex-wrap text-sm"><span class="font-semibold">${esc(offer.pharmacy)}${best}<span class="font-normal" style="color:var(--muted)"> · ${esc(title)} · ${esc(area)}${distance}</span>${storeLink}</span><span><s style="color:var(--muted)">${inr(offer.brand_price)}</s> <b style="color:var(--teal)">${inr(offer.generic_price)}</b></span></div><div class="h-2 rounded mt-1" style="background:var(--line)"><div class="bar h-2 rounded" style="width:${Math.max(3, Math.round(offer.generic_price / maxBrand * 100))}%;background:var(--teal)"></div></div></li>`;
  }).join("")}</ul><details class="mt-4 rounded-lg p-3 text-sm" style="background:var(--surface-alt)"><summary>What should I check before choosing?</summary><p class="mt-2" style="color:var(--muted)">${esc(medicine.bioequiv_note)} Confirm the active ingredient, strength, dosage form, pack size, and current price with a pharmacist. Do not change a prescribed medicine without professional advice.</p></details><p class="mt-3 text-xs" style="color:var(--muted)">Demo prices only. Store listings and prices are not live; confirm current price, stock, pack size, and delivery directly with the provider.</p></article>`;
}

const requestForm = $("request-form");
const requestList = $("request-list");
const requestNote = $("request-note");

async function loadRequests() {
  if (!requestList) return;
  const auth = window.MediSaveAuth;
  if (!auth) { setTimeout(loadRequests, 50); return; }
  await auth.ready;
  if (!window.MediSaveAuth.config.communityEnabled) {
    requestNote.textContent = "Community requests need Firebase Authentication and Firestore configured.";
    requestForm?.querySelectorAll("input,textarea,button").forEach((el) => { el.disabled = true; });
    requestList.innerHTML = '<li class="request-empty">Community requests will appear here when the account service is configured.</li>';
    return;
  }
  if (!auth.state.user) {
    requestNote.innerHTML = 'Sign in to post a medicine request or browse requests from your community. <a class="store-link" href="/login.html">Sign in</a>';
    requestList.innerHTML = '<li class="request-empty">Sign in to load recent requests.</li>';
    return;
  }
  try {
    const token = await auth.token();
    const response = await fetch("/api/v1/requests", { headers: { Authorization: `Bearer ${token}` } });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "Could not load requests.");
    const items = body.requests || [];
    requestNote.textContent = auth.config.localCommunity
      ? "Local demo: requests are saved on this computer and are not shared with deployed users. Avoid personal health details."
      : "Signed in. Post a medicine you need; avoid adding personal health details.";
    requestList.innerHTML = items.length ? items.map((item) => {
      const when = item.created_at ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(Number(item.created_at))) : "Recently";
      return `<li class="request-item"><div><b>${esc(item.medicine)} ${esc(item.strength || "")}</b><span class="request-city">${esc(item.city)}</span>${item.notes ? `<p>${esc(item.notes)}</p>` : ""}</div><small>Posted ${when} by ${esc(item.display_name || "MediSave member")}</small></li>`;
    }).join("") : '<li class="request-empty">No open medicine requests yet. You can post the first one.</li>';
  } catch (error) {
    requestNote.textContent = error.message || "Community requests are unavailable right now.";
  }
}

requestForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("request-submit");
  button.disabled = true;
  requestNote.textContent = "Posting your request…";
  try {
    const token = await window.MediSaveAuth.token();
    const payload = Object.fromEntries(new FormData(requestForm));
    const response = await fetch("/api/v1/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "We could not post that request.");
    requestForm.reset();
    await loadRequests();
    requestNote.textContent = "Your medicine request is posted.";
  } catch (error) {
    requestNote.textContent = error.message || "We could not post that request.";
  } finally {
    button.disabled = false;
  }
});

loadRequests();
