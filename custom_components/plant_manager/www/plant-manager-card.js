const PLANT_MANAGER_TEXT = {
  fr: {
    status: {
      needs_water: ["À arroser", "Vérifiez le substrat et arrosez si nécessaire."],
      too_wet: ["Très humide", "Laissez le substrat sécher avant le prochain arrosage."],
      ok: ["En bonne santé", "Rien à signaler pour le moment."],
      unknown: ["Indisponible", "Vérifiez le capteur et sa connexion."],
    },
    unavailable: "Indisponible",
    justNow: "à l’instant",
    minutesAgo: (n) => `il y a ${n} min`,
    hoursAgo: (n) => `il y a ${n} h`,
    daysAgo: (n) => `il y a ${n} j`,
    now: "maintenant",
    inHours: (n) => `dans ~${n} h`,
    inDays: (n) => `dans ~${n} j`,
    lastReading: (age) => `Dernière mesure ${age}`,
    watered: (when) => `Arrosée ${when}`,
    nextWatering: (when) => `prochain arrosage ${when}`,
    rising: "En hausse",
    falling: "En baisse",
    stable: "Stable",
    trendTitle: (days) => (days > 1 ? `Tendance sur ${days} j` : "Tendance sur 24 h"),
    historyLabel: (days, trend) => `Historique de l'humidité sur ${days > 1 ? `${days} jours` : "24 heures"} : ${trend.toLocaleLowerCase("fr")}`,
    wateringHint: "Hausse notable détectée : arrosage possible (estimation).",
    notEnoughHistory: "Historique insuffisant pour afficher la tendance.",
    plant: "Plante",
    showDetails: (name) => `Afficher les détails de ${name}`,
    soilMoisture: "Humidité du sol",
    shown: (n) => `${n} plante${n > 1 ? "s" : ""} affichée${n > 1 ? "s" : ""}`,
    toWater: (n) => `${n} à arroser`,
    overview: "Résumé des plantes",
    overviewDry: "À arroser",
    overviewWet: "Très humides",
    overviewGood: "En forme",
    overviewNeutral: "Indisponibles",
    defaultTitle: "Mon jardin d’intérieur",
    noMatchTitle: "Aucune plante correspondante",
    noMatchText: "Modifiez le filtre pour afficher d’autres plantes.",
    emptyTitle: "Aucune plante pour le moment",
    emptyText: "Ajoutez une plante dans Plant Manager pour commencer le suivi.",
    stubTitle: "Mes plantes",
    locale: "fr",
    temperatureRange: (min, max) => `Conseillé : ${min}–${max} °C`,
    coldAdvice: "Il fait trop froid pour cette plante : éloignez-la d’une fenêtre ou d’un courant d’air.",
    hotAdvice: "Il fait trop chaud pour cette plante : éloignez-la du soleil direct ou d’une source de chaleur.",
    editor: {
      labels: {
        title: "Titre",
        sort_by: "Tri",
        filter_by: "Plantes affichées",
        tap_action: "Action au toucher",
        history_days: "Durée de l'historique",
        show_images: "Afficher les photos",
        show_battery: "Afficher la batterie",
        show_temperature: "Afficher la température",
        show_history: "Afficher l'historique",
        compact: "Mode compact",
      },
      sort: { name: "Nom", moisture: "Humidité croissante", status: "Statut" },
      filter: { all: "Toutes", needs_water: "À arroser", attention: "Nécessitant une attention" },
      tap: { "more-info": "Ouvrir les détails", none: "Aucune" },
      days: { 1: "24 heures", 3: "3 jours", 7: "7 jours" },
    },
    description: "Affiche les plantes avec leur humidité, leur statut et leur batterie.",
  },
  en: {
    status: {
      needs_water: ["Needs water", "Check the soil and water if needed."],
      too_wet: ["Too wet", "Let the soil dry before the next watering."],
      ok: ["Healthy", "Nothing to report for now."],
      unknown: ["Unavailable", "Check the sensor and its connection."],
    },
    unavailable: "Unavailable",
    justNow: "just now",
    minutesAgo: (n) => `${n} min ago`,
    hoursAgo: (n) => `${n} h ago`,
    daysAgo: (n) => `${n} d ago`,
    now: "now",
    inHours: (n) => `in ~${n} h`,
    inDays: (n) => `in ~${n} d`,
    lastReading: (age) => `Last reading ${age}`,
    watered: (when) => `Watered ${when}`,
    nextWatering: (when) => `next watering ${when}`,
    rising: "Rising",
    falling: "Falling",
    stable: "Stable",
    trendTitle: (days) => (days > 1 ? `${days}-day trend` : "24-hour trend"),
    historyLabel: (days, trend) => `Moisture history over ${days > 1 ? `${days} days` : "24 hours"}: ${trend.toLowerCase()}`,
    wateringHint: "Notable rise detected: possibly watered (estimate).",
    notEnoughHistory: "Not enough history to show the trend.",
    plant: "Plant",
    showDetails: (name) => `Show details of ${name}`,
    soilMoisture: "Soil moisture",
    shown: (n) => `${n} plant${n > 1 ? "s" : ""} shown`,
    toWater: (n) => `${n} to water`,
    overview: "Plants summary",
    overviewDry: "To water",
    overviewWet: "Too wet",
    overviewGood: "Healthy",
    overviewNeutral: "Unavailable",
    defaultTitle: "My indoor garden",
    noMatchTitle: "No matching plant",
    noMatchText: "Change the filter to show other plants.",
    emptyTitle: "No plants yet",
    emptyText: "Add a plant in Plant Manager to start tracking it.",
    stubTitle: "My plants",
    locale: "en",
    temperatureRange: (min, max) => `Recommended: ${min}–${max} °C`,
    coldAdvice: "Too cold for this plant: move it away from a window or a draught.",
    hotAdvice: "Too hot for this plant: move it away from direct sun or a heat source.",
    editor: {
      labels: {
        title: "Title",
        sort_by: "Sort by",
        filter_by: "Plants shown",
        tap_action: "Tap action",
        history_days: "History length",
        show_images: "Show photos",
        show_battery: "Show battery",
        show_temperature: "Show temperature",
        show_history: "Show history",
        compact: "Compact mode",
      },
      sort: { name: "Name", moisture: "Moisture (lowest first)", status: "Status" },
      filter: { all: "All", needs_water: "To water", attention: "Needing attention" },
      tap: { "more-info": "Open details", none: "None" },
      days: { 1: "24 hours", 3: "3 days", 7: "7 days" },
    },
    description: "Shows your plants with their moisture, status and battery.",
  },
};
// French for a French interface, English otherwise.
const plantManagerText = (language) =>
  (String(language || "fr").toLowerCase().startsWith("fr") ? PLANT_MANAGER_TEXT.fr : PLANT_MANAGER_TEXT.en);
const plantManagerLanguage = (hass) => hass?.locale?.language || hass?.language;

// "20,5" in French, "20.5" in English.
const plantManagerNumber = (value, T) => Number(value).toLocaleString(T.locale, { maximumFractionDigits: 1 });

// The Plant Manager emblem, generated from docs/brand/plant-manager-icon.svg.
const PLANT_MANAGER_EMBLEM = '<svg viewBox="0 0 256 256" aria-hidden="true"><defs><linearGradient id="pm-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#102d27"/><stop offset="1" stop-color="#1e5141"/></linearGradient><linearGradient id="pm-pot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e7f2e8"/><stop offset="1" stop-color="#cfe3d4"/></linearGradient><linearGradient id="pm-drop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fd3f7"/><stop offset="1" stop-color="#2e8fd8"/></linearGradient><linearGradient id="pm-leaf" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#b9f2a1"/><stop offset="1" stop-color="#55b879"/></linearGradient></defs><rect id="pm-tile" width="256" height="256" rx="56" fill="url(#pm-bg)"/><g id="pm-plant" transform="translate(20.3 -15.9) scale(.795)" fill="url(#pm-leaf)" stroke="#d8f7cb" stroke-width="2"><g transform="translate(111 214) scale(.8) translate(-111 -214)"><path d="M112 212C18 176 4 96 18 24c74 12 132 65 94 188Z"/><path d="M113 214C91 128 111 55 180 12c35 70 10 145-67 202Z"/><path d="M109 214C162 154 224 147 280 171c-35 65-94 83-171 43Z"/><path d="M111 214C58 196 35 158 40 117c53 13 78 47 71 97Z"/><path d="M110 215L42 64M111 214L177 53M112 215L250 183" fill="none" stroke="#e7ffe0" stroke-width="4" stroke-linecap="round"/></g><g stroke="none"><path d="M60 228H164L152 304Q150 312 142 312H82Q74 312 72 304Z" fill="url(#pm-pot)"/><path d="M61 233H163L162 241H62Z" fill="#a9cbb2" opacity=".55"/><rect x="50" y="212" width="124" height="22" rx="7" fill="#f4faf4"/></g></g><g id="pm-drop-mark" transform="translate(198 62)"><path d="M0-30C11-14 20-4 20 8A20 20 0 0 1-20 8C-20-4-11-14 0-30Z" fill="url(#pm-drop)" stroke="#d6f1fd" stroke-width="2"/><ellipse cx="-7" cy="6" rx="4.5" ry="7" fill="#ffffff" opacity=".6"/></g></svg>';

const PLANT_MANAGER_STATUSES = {
  needs_water: { tone: "dry", icon: "mdi:water-alert-outline", order: 0 },
  too_wet: { tone: "wet", icon: "mdi:water", order: 1 },
  ok: { tone: "good", icon: "mdi:check-circle-outline", order: 2 },
};
// "unknown" (invalid reading) and "unavailable" share the neutral status.
const PLANT_MANAGER_UNKNOWN_STATUS = { tone: "neutral", icon: "mdi:help-circle-outline", order: 3 };
const PLANT_MANAGER_HISTORY_DAYS = [1, 3, 7];
// Above this, points are averaged per period before being drawn.
const PLANT_MANAGER_MAX_POINTS = 120;

// history/history_during_period answers {entity_id: [{s, lc, lu}]}: the state
// is in "s" and the timestamps are in seconds, "lc" being omitted when it
// equals "lu".
const plantManagerHistorySamples = (result, entityId) =>
  (Array.isArray(result?.[entityId]) ? result[entityId] : []).map((sample) => {
    const raw = sample?.s;
    const value = raw === null || raw === undefined || String(raw).trim() === ""
      ? NaN : Number(raw);
    const seconds = Number(sample?.lc ?? sample?.lu);
    return {
      value: Number.isFinite(value) && value >= 0 && value <= 100 ? value : NaN,
      timestamp: Number.isFinite(seconds) ? seconds * 1000 : NaN,
    };
  });

// A lone reading far from both neighbours, which agree with each other, is a
// sensor glitch (e.g. 100 → 20 → 100 %): it is neither plotted nor taken for
// a watering.
const plantManagerWithoutSpikes = (samples) => {
  const valid = samples
    .map((sample, index) => ({ value: sample.value, index }))
    .filter((sample) => Number.isFinite(sample.value));
  const spikes = new Set();
  for (let k = 1; k < valid.length - 1; k += 1) {
    const [previous, current, next] = [valid[k - 1].value, valid[k].value, valid[k + 1].value];
    if (Math.abs(previous - next) < 5 && Math.abs(current - previous) >= 15
      && Math.abs(current - next) >= 15) spikes.add(valid[k].index);
  }
  return samples.map((sample, index) => (spikes.has(index) ? { ...sample, value: NaN } : sample));
};

// "il y a 3 j" / "dans ~4 j" from the ISO dates published by the status sensor.
const plantManagerSince = (iso, T, now = Date.now()) => {
  const time = Date.parse(iso || "");
  if (!Number.isFinite(time)) return null;
  const hours = Math.max(0, (now - time) / 3600000);
  return hours < 1 ? T.justNow : hours < 24 ? T.hoursAgo(Math.floor(hours))
    : T.daysAgo(Math.floor(hours / 24));
};
const plantManagerUntil = (iso, T, now = Date.now()) => {
  const time = Date.parse(iso || "");
  if (!Number.isFinite(time)) return null;
  const hours = (time - now) / 3600000;
  return hours <= 1 ? T.now : hours < 24 ? T.inHours(Math.round(hours))
    : T.inDays(Math.round(hours / 24));
};

const plantManagerStatus = (plant, T = PLANT_MANAGER_TEXT.fr) => {
  const key = String(plant?.state || "").toLowerCase();
  const base = PLANT_MANAGER_STATUSES[key] || PLANT_MANAGER_UNKNOWN_STATUS;
  const [label, advice] = T.status[PLANT_MANAGER_STATUSES[key] ? key : "unknown"];
  return { ...base, label, advice };
};

// Averages the points per period so a week of frequent readings stays light.
const plantManagerDownsample = (values, timestamps, max = PLANT_MANAGER_MAX_POINTS) => {
  if (values.length <= max || timestamps.length !== values.length) return { values, timestamps };
  const first = timestamps[0];
  const span = timestamps[timestamps.length - 1] - first || 1;
  const buckets = new Map();
  values.forEach((value, index) => {
    const bucket = Math.min(max - 1, Math.floor((timestamps[index] - first) / span * max));
    const entry = buckets.get(bucket) || { sum: 0, count: 0, time: 0 };
    entry.sum += value;
    entry.count += 1;
    entry.time += timestamps[index];
    buckets.set(bucket, entry);
  });
  const ordered = [...buckets.entries()].sort((a, b) => a[0] - b[0]).map(([, e]) => e);
  return {
    values: ordered.map((e) => e.sum / e.count),
    timestamps: ordered.map((e) => e.time / e.count),
  };
};

class PlantManagerCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("plant-manager-card-editor");
  }

  static getStubConfig(hass) {
    return { title: plantManagerText(plantManagerLanguage(hass)).stubTitle, sort_by: "status" };
  }

  // Sections dashboards: full width by default, never narrower than half.
  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  setConfig(config) {
    this.config = config || {};
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    // Home Assistant sets hass on every state change in the instance: only
    // re-render when a plant or one of its moisture sensors actually changed.
    const tracked = this._trackedStates(hass);
    const changed = !this._tracked
      || tracked.length !== this._tracked.length
      || tracked.some((state, index) => state !== this._tracked[index]);
    this._tracked = tracked;
    if (changed) this.render();
  }

  _trackedStates(hass) {
    const tracked = [];
    for (const state of Object.values(hass?.states || {})) {
      if (state?.attributes?.plant_manager !== true) continue;
      tracked.push(state, hass.states[state.attributes.moisture_entity]);
    }
    return tracked;
  }

  connectedCallback() {
    // Keeps the "last reading" age current between sensor updates.
    this._ageTimer = setInterval(() => this.render(), 60 * 1000);
  }

  disconnectedCallback() {
    clearInterval(this._ageTimer);
  }

  getCardSize() {
    return 4;
  }

  get _root() {
    // A shadow root keeps this card's styles from leaking into other cards.
    return this.shadowRoot || this.attachShadow({ mode: "open" });
  }

  render() {
    if (!this._hass) return;
    const T = plantManagerText(plantManagerLanguage(this._hass));

    const allPlants = Object.values(this._hass.states)
      .filter((s) => s.attributes?.plant_manager === true);
    const filterBy = ["all", "needs_water", "attention"].includes(this.config.filter_by)
      ? this.config.filter_by
      : "all";
    const plants = allPlants.filter((plant) => {
      const { tone } = plantManagerStatus(plant, T);
      if (filterBy === "needs_water") return tone === "dry";
      if (filterBy === "attention") return tone !== "good";
      return true;
    });

    const sortBy = ["name", "moisture", "status"].includes(this.config.sort_by)
      ? this.config.sort_by
      : "name";
    const moistureOf = (plant) => {
      const value = plant.attributes?.moisture;
      if (value === null || value === undefined || value === "") return NaN;
      const number = Number(value);
      return Number.isFinite(number) && number >= 0 && number <= 100 ? number : NaN;
    };
    plants.sort((a, b) => {
      if (sortBy === "moisture") {
        const moistureA = moistureOf(a);
        const moistureB = moistureOf(b);
        if (Number.isFinite(moistureA) !== Number.isFinite(moistureB)) {
          return Number.isFinite(moistureA) ? -1 : 1;
        }
        if (Number.isFinite(moistureA) && moistureA !== moistureB) {
          return moistureA - moistureB;
        }
      } else if (sortBy === "status") {
        const orderA = plantManagerStatus(a, T).order;
        const orderB = plantManagerStatus(b, T).order;
        if (orderA !== orderB) return orderA - orderB;
      }

      return (a.attributes.plant_name || "").localeCompare(
        b.attributes.plant_name || "",
        "fr",
      );
    });
    const showImages = this.config.show_images !== false;
    const showBattery = this.config.show_battery !== false;
    const showTemperature = this.config.show_temperature !== false;
    const showHistory = this.config.show_history === true;
    const historyDays = PLANT_MANAGER_HISTORY_DAYS.includes(Number(this.config.history_days))
      ? Number(this.config.history_days) : 1;
    const compact = this.config.compact === true;

    // Cache history per entity so ordinary Home Assistant state updates do not
    // trigger repeated history requests while the card is being rendered.
    if (!this._historyCache) this._historyCache = new Map();
    if (!this._historyPending) this._historyPending = new Set();
    const historyKey = (entityId) => `${entityId}|${historyDays}`;
    const requestHistory = (entityId) => {
      const key = historyKey(entityId);
      const cached = entityId ? this._historyCache.get(key) : null;
      if (!showHistory || !entityId
        || (cached && Date.now() - cached.fetchedAt < 15 * 60 * 1000)
        || this._historyPending.has(key)
        || typeof this._hass.callWS !== "function") return;
      this._historyPending.add(key);
      const end = new Date();
      const start = new Date(end.getTime() - historyDays * 24 * 60 * 60 * 1000);
      this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: [entityId],
        minimal_response: false,
        no_attributes: true,
      }).then((result) => {
        const samples = plantManagerWithoutSpikes(plantManagerHistorySamples(result, entityId));
        // Keep invalid samples in the sequence while detecting a rise: an
        // unknown/unavailable reading must break continuity, not create a
        // false jump between two measurements several hours apart.
        const sampleValues = samples.map((sample) => sample.value);
        const validSamples = samples.filter((sample) => Number.isFinite(sample.value));
        // The last reading still holds now: extend it so the line spans the
        // period, and a value unchanged for 24 h draws a flat line.
        if (validSamples.length) {
          validSamples.push({ value: validSamples[validSamples.length - 1].value, timestamp: Date.now() });
        }
        const { values: points, timestamps } = plantManagerDownsample(
          validSamples.map((sample) => sample.value),
          validSamples.map((sample) => sample.timestamp),
        );
        // A sudden increase can indicate watering, but moisture sensors can
        // also jump for other reasons; this is only a hint, never a confirmed event.
        const possibleWatering = sampleValues.some((value, index) =>
          index > 0 && Number.isFinite(value)
          && Number.isFinite(sampleValues[index - 1])
          && value - sampleValues[index - 1] >= 15);
        this._historyCache.set(key, {
          points, timestamps, possibleWatering, fetchedAt: Date.now(),
        });
      }).catch(() => {
        this._historyCache.set(key, { points: [], fetchedAt: Date.now() });
      }).finally(() => {
        this._historyPending.delete(key);
        if (this.isConnected !== false) this.render();
      });
    };
    // Accepts both "none" and Home Assistant's { action: "none" } syntax.
    const tapAction = (this.config.tap_action?.action ?? this.config.tap_action) === "none"
      ? "none" : "more-info";

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));

    const safeImageUrl = (value) => {
      const url = String(value || "").trim();
      if (/^https?:\/\//i.test(url) || /^\/(local|api|media|plant_manager\/images)\//.test(url)) return url;
      return "";
    };

    const rows = plants.map((plant) => {
      const a = plant.attributes;
      const hasMoisture = a.moisture !== null && a.moisture !== undefined && a.moisture !== "";
      const moisture = hasMoisture ? Number(a.moisture) : NaN;
      const valid = Number.isFinite(moisture) && moisture >= 0 && moisture <= 100;
      const { label, tone, icon, advice } = plantManagerStatus(plant, T);

      const percentage = valid ? Math.max(0, Math.min(100, moisture)) : 0;
      const moistureText = valid ? `${Math.round(moisture)} %` : T.unavailable;
      const hasBattery = a.battery !== null && a.battery !== undefined && a.battery !== "";
      const batteryValue = hasBattery ? Number(a.battery) : NaN;
      const batteryValid = Number.isFinite(batteryValue) && batteryValue >= 0 && batteryValue <= 100;
      const batteryThresholdValue = Number(a.battery_low_threshold);
      const batteryThreshold = Number.isFinite(batteryThresholdValue)
        && batteryThresholdValue >= 0 && batteryThresholdValue <= 100
        ? batteryThresholdValue
        : 25;
      const batteryLow = batteryValid && batteryValue < batteryThreshold;
      const battery = batteryValid
        ? `<span class="battery${batteryLow ? " low" : ""}"><ha-icon icon="mdi:${batteryLow ? "battery-alert" : "battery-medium"}"></ha-icon><span>${Math.round(batteryValue)}%</span></span>`
        : "";
      const temperatureValue = Number(a.temperature);
      const temperatureValid = a.temperature !== null && a.temperature !== undefined
        && a.temperature !== "" && Number.isFinite(temperatureValue);
      const temperatureTone = a.temperature_status === "too_cold" ? " cold"
        : a.temperature_status === "too_hot" ? " hot" : "";
      const temperatureChip = temperatureValid
        ? `<span class="temperature${temperatureTone}" title="${esc(T.temperatureRange(plantManagerNumber(a.min_temperature, T), plantManagerNumber(a.max_temperature, T)))}"><ha-icon icon="mdi:thermometer"></ha-icon><span>${plantManagerNumber(temperatureValue, T)} °C</span></span>`
        : "";
      // The moisture advice comes first; the temperature one only when watering is fine.
      const shownAdvice = tone === "good" && a.temperature_status === "too_cold" ? T.coldAdvice
        : tone === "good" && a.temperature_status === "too_hot" ? T.hotAdvice : advice;
      const extras = `${showBattery ? battery : ""}${showTemperature ? temperatureChip : ""}`;
      const historyEntity = a.moisture_entity;
      const moistureSource = historyEntity ? this._hass.states[historyEntity] : null;
      let updatedText = "";
      const updatedAt = moistureSource?.last_updated || moistureSource?.last_changed;
      const updatedTimestamp = updatedAt ? new Date(updatedAt).getTime() : NaN;
      if (Number.isFinite(updatedTimestamp)) {
        const ageMinutes = Math.max(0, Math.floor((Date.now() - updatedTimestamp) / 60000));
        const ageLabel = ageMinutes < 1 ? T.justNow
          : ageMinutes < 60 ? T.minutesAgo(ageMinutes)
          : ageMinutes < 1440 ? T.hoursAgo(Math.floor(ageMinutes / 60))
          : T.daysAgo(Math.floor(ageMinutes / 1440));
        updatedText = `<div class="updated">${T.lastReading(ageLabel)}</div>`;
      }
      const watered = plantManagerSince(a.last_watered, T);
      const nextWatering = plantManagerUntil(a.next_watering, T);
      const wateringMarkup = watered || nextWatering
        ? `<div class="watering"><ha-icon icon="mdi:watering-can-outline"></ha-icon><span>${[
          watered ? T.watered(watered) : "",
          nextWatering ? T.nextWatering(nextWatering) : "",
        ].filter(Boolean).join(" · ")}</span></div>`
        : "";
      requestHistory(historyEntity);
      const historyEntry = showHistory && historyEntity ? this._historyCache.get(historyKey(historyEntity)) : null;
      const history = historyEntry ? historyEntry.points : null;
      let historyMarkup = "";
      if (showHistory && Array.isArray(history) && history.length >= 2) {
        const min = Math.min(...history);
        const max = Math.max(...history);
        const range = Math.max(max - min, 1);
        const flat = max === min;
        const timestamps = historyEntry.timestamps || [];
        const hasUsableTimeline = timestamps.length === history.length
          && timestamps.every(Number.isFinite)
          && Math.max(...timestamps) > Math.min(...timestamps);
        const firstTimestamp = hasUsableTimeline ? Math.min(...timestamps) : 0;
        const timeRange = hasUsableTimeline
          ? Math.max(...timestamps) - firstTimestamp
          : 0;
        const points = history.map((value, index) => {
          const x = history.length === 1 ? 0 : hasUsableTimeline
            ? (timestamps[index] - firstTimestamp) * 100 / timeRange
            : index * 100 / (history.length - 1);
          const y = flat ? 17 : 28 - ((value - min) / range) * 22;
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(" ");
        const trend = history[history.length - 1] - history[0];
        const trendText = trend > 2 ? T.rising : trend < -2 ? T.falling : T.stable;
        const wateringHint = historyEntry.possibleWatering
          ? `<div class="watering-hint"><ha-icon icon="mdi:water-plus-outline"></ha-icon> ${T.wateringHint}</div>`
          : "";
        historyMarkup = `<div class="history">
          <div class="history-heading"><span>${T.trendTitle(historyDays)}</span><span>${trendText}</span></div>
          <svg viewBox="0 0 100 32" preserveAspectRatio="none" role="img" aria-label="${esc(T.historyLabel(historyDays, trendText))}">
            <polyline points="${points}" fill="none" stroke="var(--info-color, var(--primary-color))" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></polyline>
          </svg>
          ${wateringHint}
        </div>`;
      } else if (showHistory && Array.isArray(history)) {
        historyMarkup = `<div class="history history-empty">${T.notEnoughHistory}</div>`;
      }
      const imageUrl = showImages ? safeImageUrl(a.image_url) : "";
      const image = imageUrl
        ? `<img class="plant-image" src="${esc(imageUrl)}" alt="${esc(a.plant_name || T.plant)}" loading="lazy">`
        : '<div class="plant-icon"><ha-icon icon="mdi:flower"></ha-icon></div>';

      return `<article class="plant" data-entity-id="${esc(plant.entity_id)}" tabindex="${tapAction === "none" ? "-1" : "0"}" ${tapAction === "none" ? "" : `role="button" aria-label="${esc(T.showDetails(a.plant_name || plant.entity_id))}"`}>
        <div class="photo">${image}</div>
        <div class="details">
          <div class="plant-heading">
            <div class="name" title="${esc(a.plant_name || plant.entity_id)}">${esc(a.plant_name || plant.entity_id)}</div>
            <span class="status ${tone}"><ha-icon icon="${icon}"></ha-icon>${label}</span>
          </div>
          <div class="moisture-line">
            <span class="moisture-label"><ha-icon icon="mdi:water-percent"></ha-icon> ${T.soilMoisture}</span>
            <strong class="moisture-value">${moistureText}</strong>
          </div>
          <div class="progress-track" role="progressbar" aria-label="${T.soilMoisture}" aria-valuemin="0" aria-valuemax="100" ${valid ? `aria-valuenow="${Math.round(percentage)}"` : `aria-valuetext="${T.unavailable}"`}>
            <div class="progress-fill ${tone}" style="width:${percentage}%"></div>
          </div>
          ${extras ? `<div class="extras">${extras}</div>` : ""}
          ${historyMarkup}
          ${wateringMarkup}
          <div class="advice"><ha-icon icon="mdi:lightbulb-outline"></ha-icon><span>${shownAdvice}</span></div>
          ${updatedText}
        </div>
      </article>`;
    }).join("");

    const countTone = (tone) => plants.filter(
      (plant) => plantManagerStatus(plant, T).tone === tone,
    ).length;
    const needsWater = countTone("dry");
    const veryWet = countTone("wet");
    const healthy = countTone("good");
    const unavailable = countTone("neutral");
    const summary = plants.length
      ? `<div class="summary"><span class="summary-dot"></span>${T.shown(plants.length)}${needsWater ? ` <span class="summary-alert">· ${T.toWater(needsWater)}</span>` : ""}</div>`
      : "";
    const overview = plants.length
      ? `<div class="overview" aria-label="${T.overview}">
          <div class="overview-item dry"><span class="overview-count">${needsWater}</span><span>${T.overviewDry}</span></div>
          <div class="overview-item wet"><span class="overview-count">${veryWet}</span><span>${T.overviewWet}</span></div>
          <div class="overview-item good"><span class="overview-count">${healthy}</span><span>${T.overviewGood}</span></div>
          <div class="overview-item neutral"><span class="overview-count">${unavailable}</span><span>${T.overviewNeutral}</span></div>
        </div>`
      : "";

    this._root.innerHTML = `
      <ha-card class="${compact ? "compact" : ""}">
        <div class="card-header">
          <div class="header-icon">${PLANT_MANAGER_EMBLEM}</div>
          <div class="header-text">
            <div class="title">${esc(this.config.title || T.defaultTitle)}</div>
            ${summary}
          </div>
        </div>
        ${overview}
        <div class="content">
          ${plants.length ? rows : allPlants.length ? `<div class="empty"><div class="empty-icon"><ha-icon icon="mdi:filter-off-outline"></ha-icon></div><strong>${T.noMatchTitle}</strong><span>${T.noMatchText}</span></div>` : `<div class="empty"><div class="empty-icon"><ha-icon icon="mdi:sprout-outline"></ha-icon></div><strong>${T.emptyTitle}</strong><span>${T.emptyText}</span></div>`}
        </div>
      </ha-card>
      <style>
        :host { display: block; }
        ha-card {
          overflow: hidden;
          border-radius: var(--ha-card-border-radius, 16px);
        }
        .card-header {
          display: flex;
          align-items: center;
          gap: 13px;
          padding: 20px 18px 16px;
        }
        .header-icon {
          display: grid;
          place-items: center;
          width: 46px;
          height: 46px;
          flex: 0 0 46px;
          border-radius: 15px;
        }
        .header-icon svg { display: block; width: 46px; height: 46px; }
        .header-text { min-width: 0; }
        .title {
          color: var(--primary-text-color);
          font-size: 20px;
          font-weight: 700;
          letter-spacing: -0.3px;
          line-height: 1.25;
        }
        .summary {
          margin-top: 5px;
          color: var(--secondary-text-color);
          font-size: 12px;
        }
        .summary-dot {
          display: inline-block;
          width: 7px;
          height: 7px;
          margin: 0 6px 1px 0;
          border-radius: 50%;
          background: var(--success-color, #2e7d32);
        }
        .summary-alert { color: var(--error-color, #c62828); font-weight: 600; }
        .overview {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 8px;
          padding: 0 18px 16px;
        }
        .overview-item {
          display: flex;
          min-width: 0;
          flex-direction: column;
          gap: 3px;
          padding: 10px 8px;
          border-radius: 12px;
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
          font-size: 10px;
          line-height: 1.25;
          text-align: center;
        }
        .overview-count {
          color: var(--primary-text-color);
          font-size: 20px;
          font-weight: 750;
          font-variant-numeric: tabular-nums;
          line-height: 1.1;
        }
        .overview-item.dry .overview-count { color: var(--error-color, #c62828); }
        .overview-item.wet .overview-count { color: var(--warning-color, #b7791f); }
        .overview-item.good .overview-count { color: var(--success-color, #2e7d32); }
        .compact .overview { gap: 5px; padding: 0 14px 10px; }
        .compact .overview-item { padding: 7px 4px; font-size: 9px; }
        .compact .overview-count { font-size: 17px; }
        .compact .card-header { gap: 9px; padding: 12px 14px 10px; }
        .compact .header-icon { width: 36px; height: 36px; flex-basis: 36px; border-radius: 12px; }
        .compact .header-icon svg { width: 36px; height: 36px; }
        .compact .title { font-size: 17px; }
        .compact .content { padding: 0 10px 4px; }
        .compact .plant { gap: 10px; padding: 8px 3px; }
        .compact .photo { width: 48px; height: 48px; flex-basis: 48px; border-radius: 12px; }
        .compact .plant-icon ha-icon { --mdc-icon-size: 26px; }
        .compact .name { font-size: 14px; }
        .compact .moisture-line { margin-top: 6px; }
        .compact .progress-track { height: 4px; margin-top: 5px; }
        .compact .extras { margin-top: 5px; }
        .content { padding: 0 14px 8px; }
        .plant {
          display: flex;
          align-items: center;
          gap: 13px;
          padding: 14px 4px;
          border-top: 1px solid var(--divider-color);
        }
        .plant[role="button"] { cursor: pointer; }
        .plant[role="button"]:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; border-radius: 10px; }
        .photo {
          width: 68px;
          height: 68px;
          flex: 0 0 68px;
          overflow: hidden;
          border-radius: 17px;
          background: var(--secondary-background-color);
        }
        .plant-image { display: block; width: 100%; height: 100%; object-fit: cover; }
        .plant-icon { display: grid; place-items: center; width: 100%; height: 100%; color: var(--success-color, #2e7d32); }
        .plant-icon ha-icon { --mdc-icon-size: 34px; }
        .details { flex: 1; min-width: 0; }
        .plant-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .name {
          overflow: hidden;
          color: var(--primary-text-color);
          font-size: 15px;
          font-weight: 700;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .status {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          flex: 0 0 auto;
          padding: 5px 8px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 700;
          white-space: nowrap;
        }
        .status ha-icon { --mdc-icon-size: 14px; }
        .status.good { color: var(--success-color, #2e7d32); background: color-mix(in srgb, var(--success-color, #2e7d32) 12%, var(--card-background-color)); }
        .status.dry { color: var(--error-color, #c62828); background: color-mix(in srgb, var(--error-color, #c62828) 12%, var(--card-background-color)); }
        .status.wet { color: var(--warning-color, #b7791f); background: color-mix(in srgb, var(--warning-color, #b7791f) 14%, var(--card-background-color)); }
        .status.neutral { color: var(--secondary-text-color); background: var(--secondary-background-color); }
        .moisture-line { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 11px; }
        .moisture-label { display: inline-flex; align-items: center; gap: 5px; color: var(--secondary-text-color); font-size: 12px; }
        .moisture-label ha-icon { --mdc-icon-size: 15px; }
        .moisture-value { color: var(--primary-text-color); font-size: 12px; font-variant-numeric: tabular-nums; }
        .progress-track { height: 6px; overflow: hidden; margin-top: 7px; border-radius: 999px; background: var(--divider-color); }
        .progress-fill { height: 100%; border-radius: inherit; transition: width 300ms ease; }
        .progress-fill.good { background: var(--success-color, #2e7d32); }
        .progress-fill.dry { background: var(--error-color, #c62828); }
        .progress-fill.wet { background: var(--warning-color, #b7791f); }
        .progress-fill.neutral { background: var(--disabled-text-color, #9e9e9e); }
        .history { margin-top: 9px; padding: 7px 9px 4px; border-radius: 9px; background: var(--secondary-background-color); }
        .history-heading { display: flex; justify-content: space-between; gap: 8px; color: var(--secondary-text-color); font-size: 10px; }
        .history-heading span:last-child { color: var(--primary-text-color); font-weight: 600; }
        .history svg { display: block; width: 100%; height: 24px; margin-top: 4px; overflow: visible; }
        .history-empty { color: var(--secondary-text-color); font-size: 10px; }
        .watering-hint {
          display: flex;
          align-items: center;
          gap: 5px;
          margin-top: 6px;
          color: var(--secondary-text-color);
          font-size: 11px;
          line-height: 1.35;
        }
        .watering-hint ha-icon { --mdc-icon-size: 14px; color: var(--info-color, var(--primary-color)); }
        .advice { display: flex; align-items: flex-start; gap: 5px; margin-top: 8px; color: var(--secondary-text-color); font-size: 11px; line-height: 1.4; }
        .advice ha-icon { --mdc-icon-size: 14px; flex: 0 0 auto; color: var(--primary-color); }
        .updated { margin-top: 4px; color: var(--disabled-text-color, var(--secondary-text-color)); font-size: 10px; }
        .compact .history { margin-top: 6px; padding: 5px 7px 3px; }
        .compact .history svg { height: 18px; }
        .watering { display: flex; align-items: center; gap: 5px; margin-top: 8px; color: var(--secondary-text-color); font-size: 11px; }
        .watering ha-icon { --mdc-icon-size: 14px; flex: 0 0 auto; color: var(--info-color, var(--primary-color)); }
        .watering span::first-letter { text-transform: uppercase; }
        .extras { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
        .battery { display: inline-flex; align-items: center; gap: 4px; color: var(--secondary-text-color); font-size: 11px; }
        .battery.low { color: var(--error-color, #c62828); font-weight: 700; }
        .temperature { display: inline-flex; align-items: center; gap: 4px; color: var(--secondary-text-color); font-size: 11px; }
        .temperature ha-icon { --mdc-icon-size: 14px; }
        .temperature.cold { color: var(--info-color, #039be5); font-weight: 700; }
        .temperature.hot { color: var(--error-color, #c62828); font-weight: 700; }
        .battery ha-icon { --mdc-icon-size: 14px; }
        .empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 26px 12px 30px; text-align: center; }
        .empty-icon { display: grid; place-items: center; width: 52px; height: 52px; margin-bottom: 3px; border-radius: 18px; color: var(--success-color, #2e7d32); background: var(--secondary-background-color); }
        .empty-icon ha-icon { --mdc-icon-size: 28px; }
        .empty strong { color: var(--primary-text-color); font-size: 14px; }
        .empty span { max-width: 260px; color: var(--secondary-text-color); font-size: 12px; line-height: 1.5; }
        @media (max-width: 420px) {
          .overview { gap: 5px; padding-right: 12px; padding-left: 12px; }
          .overview-item { padding: 8px 3px; font-size: 9px; }
          .overview-count { font-size: 18px; }
          .plant { gap: 10px; }
          .photo { width: 54px; height: 54px; flex-basis: 54px; border-radius: 14px; }
          .plant-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
          .status { padding: 4px 7px; }
        }
      </style>`;
    if (tapAction !== "none") {
      this._root.querySelectorAll(".plant[role=button]").forEach((row) => {
        const showDetails = () => {
          this.dispatchEvent(new CustomEvent("hass-more-info", {
            detail: { entityId: row.dataset.entityId },
            bubbles: true,
            composed: true,
          }));
        };
        row.addEventListener("click", showDetails);
        row.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            showDetails();
          }
        });
      });
    }
  }
}

if (!customElements.get("plant-manager-card")) {
  customElements.define("plant-manager-card", PlantManagerCard);
}

const plantManagerCardSchema = (T) => {
  const options = (values) => Object.entries(values).map(([value, label]) => ({ value, label }));
  return [
    { name: "title", selector: { text: {} } },
    { name: "sort_by", selector: { select: { mode: "dropdown", options: options(T.editor.sort) } } },
    { name: "filter_by", selector: { select: { mode: "dropdown", options: options(T.editor.filter) } } },
    { name: "tap_action", selector: { select: { mode: "dropdown", options: options(T.editor.tap) } } },
    {
      type: "grid",
      name: "",
      schema: ["show_images", "show_battery", "show_temperature", "show_history", "compact"]
        .map((name) => ({ name, selector: { boolean: {} } })),
    },
    { name: "history_days", selector: { select: { mode: "dropdown", options: options(T.editor.days) } } },
  ];
};
const PLANT_MANAGER_CARD_DEFAULTS = {
  sort_by: "name",
  filter_by: "all",
  tap_action: "more-info",
  show_images: true,
  show_battery: true,
  show_temperature: true,
  show_history: false,
  compact: false,
  history_days: "1",
};

class PlantManagerCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) =>
        plantManagerText(plantManagerLanguage(this._hass)).editor.labels[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (event) => {
        this._config = event.detail.value;
        this.dispatchEvent(new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = plantManagerCardSchema(plantManagerText(plantManagerLanguage(this._hass)));
    // The select works with strings; the card accepts the number too.
    const data = { ...PLANT_MANAGER_CARD_DEFAULTS, ...this._config };
    this._form.data = { ...data, history_days: String(data.history_days) };
  }
}

if (!customElements.get("plant-manager-card-editor")) {
  customElements.define("plant-manager-card-editor", PlantManagerCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "plant-manager-card")) {
  window.customCards.push({
    type: "plant-manager-card",
    name: "Plant Manager",
    // The card picker is shown in the interface language, set on <html lang>.
    description: plantManagerText(
      typeof document !== "undefined" ? document.documentElement?.lang : undefined,
    ).description,
    preview: true,
  });
}
