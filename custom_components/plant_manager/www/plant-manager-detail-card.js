const PLANT_MANAGER_DETAIL_TEXT = {
  fr: {
    status: {
      needs_water: ["À arroser", "Vérifiez le substrat et arrosez si nécessaire."],
      too_wet: ["Très humide", "Laissez le substrat sécher avant le prochain arrosage."],
      ok: ["En bonne santé", "Rien à signaler pour le moment."],
      unknown: ["Indisponible", "Vérifiez le capteur et sa connexion."],
    },
    missingEntity: "Veuillez définir l'entité de statut Plant Manager dans « entity ».",
    notFound: (entity) => `Entité Plant Manager introuvable : ${entity}`,
    unavailable: "Indisponible",
    unknownDate: "Date inconnue",
    justNow: "à l’instant",
    minutesAgo: (n) => `il y a ${n} min`,
    hoursAgo: (n) => `il y a ${n} h`,
    daysAgo: (n) => `il y a ${n} j`,
    now: "maintenant",
    inHours: (n) => `dans ~${n} h`,
    inDays: (n) => `dans ~${n} j`,
    rising: "En hausse",
    falling: "En baisse",
    stable: "Stable",
    trendTitle: (days) => (days > 1 ? `Évolution sur ${days} j` : "Évolution sur 24 h"),
    trendLabel: (trend) => `Évolution de l'humidité : ${trend.toLocaleLowerCase("fr")}`,
    min: (value) => `${value} % min.`,
    max: (value) => `${value} % max.`,
    noHistory: "Historique indisponible ou insuffisant.",
    historyHidden: "Historique masqué dans la configuration.",
    soilMoisture: "Humidité du sol",
    lowThreshold: (value) => `Seuil bas : ${value}`,
    highThreshold: (value) => `Seuil haut : ${value}`,
    lastReading: (age) => `Dernière mesure : ${age}`,
    lastWatered: "Dernier arrosage",
    nextWatering: "Prochain arrosage",
    battery: "Batterie du capteur",
    batteryThreshold: (value) => `Seuil d'alerte : ${value}`,
    editor: {
      entity: "Plante",
      title: "Titre (facultatif)",
      show_history: "Afficher l'historique",
      history_days: "Durée de l'historique",
      days: { 1: "24 heures", 3: "3 jours", 7: "7 jours" },
    },
    name: "Plant Manager — Fiche plante",
    description: "Affiche les détails, seuils, batterie et l'historique d'une plante.",
  },
  en: {
    status: {
      needs_water: ["Needs water", "Check the soil and water if needed."],
      too_wet: ["Too wet", "Let the soil dry before the next watering."],
      ok: ["Healthy", "Nothing to report for now."],
      unknown: ["Unavailable", "Check the sensor and its connection."],
    },
    missingEntity: "Please set the Plant Manager status entity in \"entity\".",
    notFound: (entity) => `Plant Manager entity not found: ${entity}`,
    unavailable: "Unavailable",
    unknownDate: "Unknown date",
    justNow: "just now",
    minutesAgo: (n) => `${n} min ago`,
    hoursAgo: (n) => `${n} h ago`,
    daysAgo: (n) => `${n} d ago`,
    now: "now",
    inHours: (n) => `in ~${n} h`,
    inDays: (n) => `in ~${n} d`,
    rising: "Rising",
    falling: "Falling",
    stable: "Stable",
    trendTitle: (days) => (days > 1 ? `${days}-day trend` : "24-hour trend"),
    trendLabel: (trend) => `Moisture trend: ${trend.toLowerCase()}`,
    min: (value) => `${value}% min`,
    max: (value) => `${value}% max`,
    noHistory: "History unavailable or insufficient.",
    historyHidden: "History hidden in the card settings.",
    soilMoisture: "Soil moisture",
    lowThreshold: (value) => `Low threshold: ${value}`,
    highThreshold: (value) => `High threshold: ${value}`,
    lastReading: (age) => `Last reading: ${age}`,
    lastWatered: "Last watered",
    nextWatering: "Next watering",
    battery: "Sensor battery",
    batteryThreshold: (value) => `Alert threshold: ${value}`,
    editor: {
      entity: "Plant",
      title: "Title (optional)",
      show_history: "Show history",
      history_days: "History length",
      days: { 1: "24 hours", 3: "3 days", 7: "7 days" },
    },
    name: "Plant Manager — Plant details",
    description: "Shows a plant's details, thresholds, battery and history.",
  },
};
// French for a French interface, English otherwise.
const plantManagerDetailText = (language) => (
  String(language || "fr").toLowerCase().startsWith("fr")
    ? PLANT_MANAGER_DETAIL_TEXT.fr : PLANT_MANAGER_DETAIL_TEXT.en
);
const plantManagerDetailLanguage = (hass) => hass?.locale?.language || hass?.language;
const plantManagerDetailPageLanguage = () => (
  typeof document !== "undefined" ? document.documentElement?.lang : undefined
);
const plantManagerDetailCapitalize = (text) => text.replace(/^./, (c) => c.toUpperCase());

const PLANT_MANAGER_DETAIL_STATUSES = {
  needs_water: ["dry", "mdi:water-alert-outline"],
  too_wet: ["wet", "mdi:water"],
  ok: ["good", "mdi:check-circle-outline"],
};
// "unknown" (invalid reading) and "unavailable" share the neutral status.
const PLANT_MANAGER_DETAIL_UNKNOWN = ["neutral", "mdi:help-circle-outline"];
const PLANT_MANAGER_DETAIL_HISTORY_DAYS = [1, 3, 7];

// history/history_during_period answers {entity_id: [{s, lc, lu}]}: the state
// is in "s" and the timestamps are in seconds, "lc" being omitted when it
// equals "lu".
const plantManagerDetailHistorySamples = (result, entityId) =>
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
const plantManagerDetailWithoutSpikes = (samples) => {
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
const plantManagerDetailSince = (iso, T, now = Date.now()) => {
  const time = Date.parse(iso || "");
  if (!Number.isFinite(time)) return null;
  const hours = Math.max(0, (now - time) / 3600000);
  return hours < 1 ? T.justNow : hours < 24 ? T.hoursAgo(Math.floor(hours))
    : T.daysAgo(Math.floor(hours / 24));
};
const plantManagerDetailUntil = (iso, T, now = Date.now()) => {
  const time = Date.parse(iso || "");
  if (!Number.isFinite(time)) return null;
  const hours = (time - now) / 3600000;
  return hours <= 1 ? T.now : hours < 24 ? T.inHours(Math.round(hours))
    : T.inDays(Math.round(hours / 24));
};

class PlantManagerDetailCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("plant-manager-detail-card-editor");
  }

  static getStubConfig(hass) {
    const plant = Object.values(hass?.states || {})
      .find((state) => state?.attributes?.plant_manager === true);
    return { entity: plant ? plant.entity_id : "", show_history: true };
  }

  // Sections dashboards: half width by default.
  getGridOptions() {
    return { columns: 6, min_columns: 4 };
  }

  setConfig(config) {
    if (!config?.entity || typeof config.entity !== "string") {
      throw new Error(plantManagerDetailText(plantManagerDetailPageLanguage()).missingEntity);
    }
    this.config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    // Home Assistant sets hass on every state change in the instance: only
    // re-render when this plant or its moisture sensor actually changed.
    const plant = hass?.states?.[this.config?.entity];
    const tracked = [plant, hass?.states?.[plant?.attributes?.moisture_entity]];
    const changed = !this._tracked
      || tracked.some((state, index) => state !== this._tracked[index]);
    this._tracked = tracked;
    if (changed) this.render();
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
    if (!this._hass || !this.config) return;
    const T = plantManagerDetailText(plantManagerDetailLanguage(this._hass));
    const plant = this._hass.states[this.config.entity];
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
    if (!plant || plant.attributes?.plant_manager !== true) {
      this._root.innerHTML = `<ha-card><div class="empty">${esc(T.notFound(this.config.entity))}</div></ha-card>`;
      return;
    }

    const a = plant.attributes;
    const name = a.plant_name || this.config.entity;
    const moisture = Number(a.moisture);
    const moistureValid = a.moisture !== null && a.moisture !== undefined
      && a.moisture !== "" && Number.isFinite(moisture) && moisture >= 0 && moisture <= 100;
    const battery = Number(a.battery);
    const batteryValid = a.battery !== null && a.battery !== undefined
      && a.battery !== "" && Number.isFinite(battery) && battery >= 0 && battery <= 100;
    const low = Number(a.low_threshold);
    const high = Number(a.high_threshold);
    const batteryThreshold = Number(a.battery_low_threshold);
    const statusKey = String(plant.state || "").toLowerCase();
    const [tone, statusIcon] = PLANT_MANAGER_DETAIL_STATUSES[statusKey] || PLANT_MANAGER_DETAIL_UNKNOWN;
    const [statusLabel, advice] = T.status[PLANT_MANAGER_DETAIL_STATUSES[statusKey] ? statusKey : "unknown"];
    // The species name is shown only when it adds something to the plant's name.
    const species = String(a.species || "").trim();
    const speciesDescription = String(a.species_description || "").trim();
    const speciesLine = species && species.toLowerCase() !== String(this.config.title || name).toLowerCase()
      ? `<div class="species"><em>${esc(species)}</em>${speciesDescription ? ` · ${esc(speciesDescription)}` : ""}</div>`
      : "";
    const watered = plantManagerDetailSince(a.last_watered, T);
    const nextWatering = plantManagerDetailUntil(a.next_watering, T);
    const imageUrl = String(a.image_url || "").trim();
    const safeImage = /^https?:\/\//i.test(imageUrl) || /^\/(local|api|media|plant_manager\/images)\//.test(imageUrl)
      ? imageUrl : "";
    const moistureEntity = a.moisture_entity;
    const moistureSource = moistureEntity ? this._hass.states[moistureEntity] : null;
    const timestamp = Date.parse(moistureSource?.last_updated || moistureSource?.last_changed || "");
    const ageMinutes = Number.isFinite(timestamp)
      ? Math.max(0, Math.floor((Date.now() - timestamp) / 60000)) : null;
    const ageLabel = ageMinutes === null ? T.unknownDate : plantManagerDetailCapitalize(
      ageMinutes < 1 ? T.justNow
        : ageMinutes < 60 ? T.minutesAgo(ageMinutes)
        : ageMinutes < 1440 ? T.hoursAgo(Math.floor(ageMinutes / 60))
        : T.daysAgo(Math.floor(ageMinutes / 1440)),
    );

    if (!this._historyCache) this._historyCache = { key: null, fetchedAt: 0, points: [], timestamps: [] };
    const showHistory = this.config.show_history !== false;
    const historyDays = PLANT_MANAGER_DETAIL_HISTORY_DAYS.includes(Number(this.config.history_days))
      ? Number(this.config.history_days) : 1;
    const historyKey = `${moistureEntity}|${historyDays}`;
    if (showHistory && moistureEntity && typeof this._hass.callWS === "function"
      && (this._historyCache.key !== historyKey
        || Date.now() - this._historyCache.fetchedAt > 15 * 60 * 1000)
      && !this._historyPending) {
      this._historyPending = true;
      const end = new Date();
      const start = new Date(end.getTime() - historyDays * 24 * 60 * 60 * 1000);
      this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: [moistureEntity],
        minimal_response: false,
        no_attributes: true,
      }).then((result) => {
        const valid = plantManagerDetailWithoutSpikes(plantManagerDetailHistorySamples(result, moistureEntity))
          .filter((sample) => Number.isFinite(sample.value));
        // The last reading still holds now: extend it so the line spans the
        // period, and a value unchanged for 24 h draws a flat line.
        if (valid.length) {
          valid.push({ value: valid[valid.length - 1].value, timestamp: Date.now() });
        }
        this._historyCache = {
          key: historyKey,
          fetchedAt: Date.now(),
          points: valid.map((sample) => sample.value),
          timestamps: valid.map((sample) => sample.timestamp),
        };
      }).catch(() => {
        this._historyCache = { key: historyKey, fetchedAt: Date.now(), points: [], timestamps: [] };
      }).finally(() => {
        this._historyPending = false;
        if (this.isConnected !== false) this.render();
      });
    }

    const history = this._historyCache.key === historyKey ? this._historyCache.points : [];
    let chart = `<div class="history-empty">${T.noHistory}</div>`;
    if (showHistory && history.length >= 2) {
      const min = Math.min(...history);
      const max = Math.max(...history);
      // The scale includes the thresholds, drawn as dashed lines, so the
      // curve shows how close the plant is to needing water or being too wet.
      const lowShown = Number.isFinite(low) && low >= 0 && low <= 100;
      const highShown = Number.isFinite(high) && high >= 0 && high <= 100;
      const bottom = Math.min(min, lowShown ? low : min);
      const top = Math.max(max, highShown ? high : max);
      const range = Math.max(top - bottom, 1);
      const flat = top === bottom;
      const yOf = (value) => (flat ? 17 : 28 - ((value - bottom) / range) * 22);
      const times = this._historyCache.timestamps || [];
      const timed = times.length === history.length && times.every(Number.isFinite)
        && Math.max(...times) > Math.min(...times);
      const first = timed ? Math.min(...times) : 0;
      const span = timed ? Math.max(...times) - first : 0;
      const points = history.map((value, index) => {
        const x = timed ? (times[index] - first) * 100 / span : index * 100 / (history.length - 1);
        return `${x.toFixed(1)},${yOf(value).toFixed(1)}`;
      }).join(" ");
      const delta = history[history.length - 1] - history[0];
      const trend = delta > 2 ? T.rising : delta < -2 ? T.falling : T.stable;
      const thresholdLine = (value, kind) => `<line class="threshold ${kind}" x1="0" x2="100" y1="${yOf(value).toFixed(1)}" y2="${yOf(value).toFixed(1)}" vector-effect="non-scaling-stroke"></line>`;
      chart = `<div class="history-heading"><span>${T.trendTitle(historyDays)}</span><strong>${trend}</strong></div>
        <svg viewBox="0 0 100 32" preserveAspectRatio="none" role="img" aria-label="${esc(T.trendLabel(trend))}">
          ${lowShown && !flat ? thresholdLine(low, "low") : ""}
          ${highShown && !flat ? thresholdLine(high, "high") : ""}
          <polyline points="${points}" fill="none" stroke="var(--info-color, var(--primary-color))" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></polyline>
        </svg>
        <div class="history-range"><span>${T.min(Math.round(min))}</span><span>${T.max(Math.round(max))}</span></div>`;
    } else if (!showHistory) {
      chart = `<div class="history-empty">${T.historyHidden}</div>`;
    }

    const moistureText = moistureValid ? `${Math.round(moisture)} %` : T.unavailable;
    const batteryText = batteryValid ? `${Math.round(battery)} %` : T.unavailable;
    const batteryLow = batteryValid && Number.isFinite(batteryThreshold) && battery < batteryThreshold;
    this._root.innerHTML = `
      <ha-card>
        <header>
          ${safeImage ? `<img src="${esc(safeImage)}" alt="${esc(name)}" />` : '<div class="plant-icon"><ha-icon icon="mdi:flower"></ha-icon></div>'}
          <div class="heading"><h2>${esc(this.config.title || name)}</h2>${speciesLine}<span class="status ${tone}"><ha-icon icon="${statusIcon}"></ha-icon>${statusLabel}</span></div>
        </header>
        <section class="metric">
          <div class="metric-heading"><span><ha-icon icon="mdi:water-percent"></ha-icon> ${T.soilMoisture}</span><strong>${moistureText}</strong></div>
          <div class="track" role="progressbar" aria-label="${T.soilMoisture}" aria-valuemin="0" aria-valuemax="100" ${moistureValid ? `aria-valuenow="${Math.round(moisture)}"` : `aria-valuetext="${T.unavailable}"`}>
            <div class="fill ${tone}" style="width:${moistureValid ? moisture : 0}%"></div>
          </div>
          <div class="thresholds"><span>${T.lowThreshold(Number.isFinite(low) ? `${low} %` : "—")}</span><span>${T.highThreshold(Number.isFinite(high) ? `${high} %` : "—")}</span></div>
          <div class="updated">${T.lastReading(ageLabel)}</div>
        </section>
        ${watered || nextWatering ? `<section class="watering">
          <div><span>${T.lastWatered}</span><strong>${watered ? plantManagerDetailCapitalize(watered) : "—"}</strong></div>
          <div><span>${T.nextWatering}</span><strong>${nextWatering ? plantManagerDetailCapitalize(nextWatering) : "—"}</strong></div>
        </section>` : ""}
        <section class="history">${chart}</section>
        ${a.battery_entity ? `<section class="battery-row">
          <div class="battery-icon"><ha-icon icon="${batteryLow ? "mdi:battery-alert" : "mdi:battery-medium"}"></ha-icon></div>
          <div class="battery-copy"><strong>${T.battery}</strong><span>${T.batteryThreshold(Number.isFinite(batteryThreshold) ? `${batteryThreshold} %` : "25 %")}</span></div>
          <strong class="battery-value ${batteryLow ? "low" : ""}">${batteryText}</strong>
        </section>` : ""}
        <section class="advice"><ha-icon icon="mdi:lightbulb-outline"></ha-icon><span>${advice}</span></section>
      </ha-card>
      <style>
        :host{display:block}
        ha-card{overflow:hidden;border-radius:var(--ha-card-border-radius,16px);color:var(--primary-text-color)}
        header{display:flex;align-items:center;gap:14px;padding:18px}
        header img,.plant-icon{width:76px;height:76px;flex:0 0 76px;object-fit:cover;border-radius:18px;background:var(--secondary-background-color)}
        .plant-icon{display:grid;place-items:center;color:var(--success-color,var(--primary-color))}
        .plant-icon ha-icon{--mdc-icon-size:38px}
        .heading{min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:8px}
        .species{margin-top:-4px;color:var(--secondary-text-color);font-size:12px;line-height:1.35}.species em{font-style:italic}
        h2{margin:0;font-size:20px;line-height:1.25;font-weight:700;overflow-wrap:anywhere}
        .status{display:inline-flex;align-items:center;gap:5px;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700}
        .status ha-icon{--mdc-icon-size:15px}
        .good{color:var(--success-color,#2e7d32);background:color-mix(in srgb,var(--success-color,#2e7d32) 12%,var(--card-background-color))}
        .dry{color:var(--error-color,#c62828);background:color-mix(in srgb,var(--error-color,#c62828) 12%,var(--card-background-color))}
        .wet{color:var(--warning-color,#b7791f);background:color-mix(in srgb,var(--warning-color,#b7791f) 14%,var(--card-background-color))}
        .neutral{color:var(--secondary-text-color);background:var(--secondary-background-color)}
        .metric{padding:16px 18px;border-top:1px solid var(--divider-color)}
        .metric-heading{display:flex;justify-content:space-between;align-items:center;gap:8px}
        .metric-heading span{display:flex;align-items:center;gap:6px;color:var(--secondary-text-color);font-size:13px}
        .metric-heading strong{font-size:24px;font-variant-numeric:tabular-nums}
        .track{height:9px;overflow:hidden;margin-top:12px;border-radius:999px;background:var(--divider-color)}
        .fill{height:100%;border-radius:inherit;transition:width .3s ease}
        .fill.good{background:var(--success-color,#2e7d32)}.fill.dry{background:var(--error-color,#c62828)}
        .fill.wet{background:var(--warning-color,#b7791f)}.fill.neutral{background:var(--disabled-text-color,#9e9e9e)}
        .thresholds{display:flex;justify-content:space-between;gap:8px;margin-top:9px;color:var(--secondary-text-color);font-size:11px}
        .updated{margin-top:7px;color:var(--disabled-text-color,var(--secondary-text-color));font-size:11px}
        .watering{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px 18px;border-top:1px solid var(--divider-color)}
        .watering div{display:flex;flex-direction:column;gap:3px}.watering span{color:var(--secondary-text-color);font-size:11px}
        .watering strong{font-size:15px}
        .history{padding:14px 18px;border-top:1px solid var(--divider-color)}
        .history-heading,.history-range{display:flex;justify-content:space-between;gap:8px;font-size:12px}
        .history-heading{color:var(--secondary-text-color)}.history-heading strong{color:var(--primary-text-color)}
        .history svg{display:block;width:100%;height:70px;margin-top:8px;overflow:visible}
        .history-range{color:var(--secondary-text-color);font-size:10px}
        .threshold{stroke-width:1;stroke-dasharray:3 3;opacity:.7}
        .threshold.low{stroke:var(--error-color,#c62828)}.threshold.high{stroke:var(--warning-color,#b7791f)}
        .history-empty{color:var(--secondary-text-color);font-size:12px}
        .battery-row{display:flex;align-items:center;gap:12px;padding:14px 18px;border-top:1px solid var(--divider-color)}
        .battery-icon{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:var(--secondary-background-color)}
        .battery-icon ha-icon{--mdc-icon-size:22px}
        .battery-copy{display:flex;flex:1;min-width:0;flex-direction:column;gap:3px}
        .battery-copy strong{font-size:13px}.battery-copy span{color:var(--secondary-text-color);font-size:11px}
        .battery-value{font-size:16px;font-variant-numeric:tabular-nums}.battery-value.low{color:var(--error-color,#c62828)}
        .advice{display:flex;align-items:flex-start;gap:8px;margin:0 18px 18px;padding:12px;border-radius:12px;background:var(--secondary-background-color);color:var(--secondary-text-color);font-size:12px;line-height:1.45}
        .advice ha-icon{--mdc-icon-size:17px;flex:0 0 auto;color:var(--primary-color)}
        .empty{padding:20px;color:var(--secondary-text-color)}
        @media(max-width:420px){header{padding:14px}.metric,.history,.battery-row{padding:12px 14px}header img,.plant-icon{width:60px;height:60px;flex-basis:60px}h2{font-size:18px}}
      </style>`;
  }
}

if (!customElements.get("plant-manager-detail-card")) {
  customElements.define("plant-manager-detail-card", PlantManagerDetailCard);
}
const plantManagerDetailSchema = (T) => [
  {
    name: "entity",
    required: true,
    selector: { entity: { filter: { integration: "plant_manager", domain: "sensor" } } },
  },
  { name: "title", selector: { text: {} } },
  { name: "show_history", selector: { boolean: {} } },
  {
    name: "history_days",
    selector: { select: { mode: "dropdown", options: Object.entries(T.editor.days).map(([value, label]) => ({ value, label })) } },
  },
];

class PlantManagerDetailCardEditor extends HTMLElement {
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
        plantManagerDetailText(plantManagerDetailLanguage(this._hass)).editor[schema.name] || schema.name;
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
    this._form.schema = plantManagerDetailSchema(plantManagerDetailText(plantManagerDetailLanguage(this._hass)));
    // The select works with strings; the card accepts the number too.
    const data = { show_history: true, history_days: "1", ...this._config };
    this._form.data = { ...data, history_days: String(data.history_days) };
  }
}

if (!customElements.get("plant-manager-detail-card-editor")) {
  customElements.define("plant-manager-detail-card-editor", PlantManagerDetailCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "plant-manager-detail-card")) {
  window.customCards.push({
    type: "plant-manager-detail-card",
    // The card picker is shown in the interface language, set on <html lang>.
    name: plantManagerDetailText(plantManagerDetailPageLanguage()).name,
    description: plantManagerDetailText(plantManagerDetailPageLanguage()).description,
    preview: true,
  });
}
