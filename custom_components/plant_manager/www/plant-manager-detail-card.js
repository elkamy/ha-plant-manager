const PLANT_MANAGER_DETAIL_STATUSES = {
  needs_water: ["À arroser", "dry", "mdi:water-alert-outline", "Vérifiez le substrat et arrosez si nécessaire."],
  too_wet: ["Très humide", "wet", "mdi:water", "Laissez le substrat sécher avant le prochain arrosage."],
  ok: ["En bonne santé", "good", "mdi:check-circle-outline", "Rien à signaler pour le moment."],
};
// "unknown" (invalid reading) and "unavailable" share the neutral status.
const PLANT_MANAGER_DETAIL_UNKNOWN = [
  "Indisponible", "neutral", "mdi:help-circle-outline", "Vérifiez le capteur et sa connexion.",
];

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

class PlantManagerDetailCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("plant-manager-detail-card-editor");
  }

  static getStubConfig(hass) {
    const plant = Object.values(hass?.states || {})
      .find((state) => state?.attributes?.plant_manager === true);
    return { entity: plant ? plant.entity_id : "", show_history: true };
  }

  setConfig(config) {
    if (!config?.entity || typeof config.entity !== "string") {
      throw new Error("Veuillez définir l'entité de statut Plant Manager dans « entity ».");
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
    const plant = this._hass.states[this.config.entity];
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
    if (!plant || plant.attributes?.plant_manager !== true) {
      this._root.innerHTML = `<ha-card><div class="empty">Entité Plant Manager introuvable : ${esc(this.config.entity)}</div></ha-card>`;
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
    const [statusLabel, tone, statusIcon, advice] = PLANT_MANAGER_DETAIL_STATUSES[
      String(plant.state || "").toLowerCase()
    ] || PLANT_MANAGER_DETAIL_UNKNOWN;
    const imageUrl = String(a.image_url || "").trim();
    const safeImage = /^https?:\/\//i.test(imageUrl) || /^\/(local|api|media)\//.test(imageUrl)
      ? imageUrl : "";
    const moistureEntity = a.moisture_entity;
    const moistureSource = moistureEntity ? this._hass.states[moistureEntity] : null;
    const timestamp = Date.parse(moistureSource?.last_updated || moistureSource?.last_changed || "");
    const ageMinutes = Number.isFinite(timestamp)
      ? Math.max(0, Math.floor((Date.now() - timestamp) / 60000)) : null;
    const ageLabel = ageMinutes === null ? "Date inconnue"
      : ageMinutes < 1 ? "À l’instant"
      : ageMinutes < 60 ? `Il y a ${ageMinutes} min`
      : ageMinutes < 1440 ? `Il y a ${Math.floor(ageMinutes / 60)} h`
      : `Il y a ${Math.floor(ageMinutes / 1440)} j`;

    if (!this._historyCache) this._historyCache = { entity: null, fetchedAt: 0, points: [], timestamps: [] };
    const showHistory = this.config.show_history !== false;
    if (showHistory && moistureEntity && typeof this._hass.callWS === "function"
      && (this._historyCache.entity !== moistureEntity
        || Date.now() - this._historyCache.fetchedAt > 15 * 60 * 1000)
      && !this._historyPending) {
      this._historyPending = true;
      const end = new Date();
      const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
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
          entity: moistureEntity,
          fetchedAt: Date.now(),
          points: valid.map((sample) => sample.value),
          timestamps: valid.map((sample) => sample.timestamp),
        };
      }).catch(() => {
        this._historyCache = { entity: moistureEntity, fetchedAt: Date.now(), points: [], timestamps: [] };
      }).finally(() => {
        this._historyPending = false;
        if (this.isConnected !== false) this.render();
      });
    }

    const history = this._historyCache.entity === moistureEntity ? this._historyCache.points : [];
    let chart = '<div class="history-empty">Historique indisponible ou insuffisant.</div>';
    if (showHistory && history.length >= 2) {
      const min = Math.min(...history);
      const max = Math.max(...history);
      const range = Math.max(max - min, 1);
      const flat = max === min;
      const times = this._historyCache.timestamps || [];
      const timed = times.length === history.length && times.every(Number.isFinite)
        && Math.max(...times) > Math.min(...times);
      const first = timed ? Math.min(...times) : 0;
      const span = timed ? Math.max(...times) - first : 0;
      const points = history.map((value, index) => {
        const x = timed ? (times[index] - first) * 100 / span : index * 100 / (history.length - 1);
        const y = flat ? 17 : 28 - ((value - min) / range) * 22;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
      const delta = history[history.length - 1] - history[0];
      const trend = delta > 2 ? "En hausse" : delta < -2 ? "En baisse" : "Stable";
      chart = `<div class="history-heading"><span>Évolution sur 24 h</span><strong>${trend}</strong></div>
        <svg viewBox="0 0 100 32" preserveAspectRatio="none" role="img" aria-label="Évolution de l'humidité : ${trend.toLocaleLowerCase("fr")}">
          <polyline points="${points}" fill="none" stroke="var(--info-color, var(--primary-color))" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></polyline>
        </svg>
        <div class="history-range"><span>${Math.round(min)} % min.</span><span>${Math.round(max)} % max.</span></div>`;
    } else if (!showHistory) {
      chart = '<div class="history-empty">Historique masqué dans la configuration.</div>';
    }

    const moistureText = moistureValid ? `${Math.round(moisture)} %` : "Indisponible";
    const batteryText = batteryValid ? `${Math.round(battery)} %` : "Indisponible";
    const batteryLow = batteryValid && Number.isFinite(batteryThreshold) && battery < batteryThreshold;
    this._root.innerHTML = `
      <ha-card>
        <header>
          ${safeImage ? `<img src="${esc(safeImage)}" alt="${esc(name)}" />` : '<div class="plant-icon"><ha-icon icon="mdi:flower"></ha-icon></div>'}
          <div class="heading"><h2>${esc(this.config.title || name)}</h2><span class="status ${tone}"><ha-icon icon="${statusIcon}"></ha-icon>${statusLabel}</span></div>
        </header>
        <section class="metric">
          <div class="metric-heading"><span><ha-icon icon="mdi:water-percent"></ha-icon> Humidité du sol</span><strong>${moistureText}</strong></div>
          <div class="track" role="progressbar" aria-label="Humidité du sol" aria-valuemin="0" aria-valuemax="100" ${moistureValid ? `aria-valuenow="${Math.round(moisture)}"` : 'aria-valuetext="Indisponible"'}>
            <div class="fill ${tone}" style="width:${moistureValid ? moisture : 0}%"></div>
          </div>
          <div class="thresholds"><span>Seuil bas : ${Number.isFinite(low) ? `${low} %` : "—"}</span><span>Seuil haut : ${Number.isFinite(high) ? `${high} %` : "—"}</span></div>
          <div class="updated">Dernière mesure : ${ageLabel}</div>
        </section>
        <section class="history">${chart}</section>
        ${a.battery_entity ? `<section class="battery-row">
          <div class="battery-icon"><ha-icon icon="${batteryLow ? "mdi:battery-alert" : "mdi:battery-medium"}"></ha-icon></div>
          <div class="battery-copy"><strong>Batterie du capteur</strong><span>Seuil d'alerte : ${Number.isFinite(batteryThreshold) ? `${batteryThreshold} %` : "25 %"}</span></div>
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
        .history{padding:14px 18px;border-top:1px solid var(--divider-color)}
        .history-heading,.history-range{display:flex;justify-content:space-between;gap:8px;font-size:12px}
        .history-heading{color:var(--secondary-text-color)}.history-heading strong{color:var(--primary-text-color)}
        .history svg{display:block;width:100%;height:70px;margin-top:8px;overflow:visible}
        .history-range{color:var(--secondary-text-color);font-size:10px}
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
const PLANT_MANAGER_DETAIL_LABELS = {
  entity: "Plante",
  title: "Titre (facultatif)",
  show_history: "Afficher l'historique sur 24 h",
};
const PLANT_MANAGER_DETAIL_SCHEMA = [
  {
    name: "entity",
    required: true,
    selector: { entity: { filter: { integration: "plant_manager", domain: "sensor" } } },
  },
  { name: "title", selector: { text: {} } },
  { name: "show_history", selector: { boolean: {} } },
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
      this._form.computeLabel = (schema) => PLANT_MANAGER_DETAIL_LABELS[schema.name] || schema.name;
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
    this._form.schema = PLANT_MANAGER_DETAIL_SCHEMA;
    this._form.data = { show_history: true, ...this._config };
  }
}

if (!customElements.get("plant-manager-detail-card-editor")) {
  customElements.define("plant-manager-detail-card-editor", PlantManagerDetailCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "plant-manager-detail-card")) {
  window.customCards.push({
    type: "plant-manager-detail-card",
    name: "Plant Manager — Fiche plante",
    description: "Affiche les détails, seuils, batterie et l'historique d'une plante.",
    preview: true,
  });
}
