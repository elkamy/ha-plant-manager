const PLANT_MANAGER_STATUSES = {
  needs_water: {
    label: "À arroser", tone: "dry", icon: "mdi:water-alert-outline", order: 0,
    advice: "Vérifiez le substrat et arrosez si nécessaire.",
  },
  too_wet: {
    label: "Très humide", tone: "wet", icon: "mdi:water", order: 1,
    advice: "Laissez le substrat sécher avant le prochain arrosage.",
  },
  ok: {
    label: "En bonne santé", tone: "good", icon: "mdi:check-circle-outline", order: 2,
    advice: "Rien à signaler pour le moment.",
  },
};
// "unknown" (invalid reading) and "unavailable" share the neutral status.
const PLANT_MANAGER_UNKNOWN_STATUS = {
  label: "Indisponible", tone: "neutral", icon: "mdi:help-circle-outline", order: 3,
  advice: "Vérifiez le capteur et sa connexion.",
};
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

const plantManagerStatus = (plant) =>
  PLANT_MANAGER_STATUSES[String(plant?.state || "").toLowerCase()]
  || PLANT_MANAGER_UNKNOWN_STATUS;

class PlantManagerCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("plant-manager-card-editor");
  }

  static getStubConfig() {
    return { title: "Mes plantes", sort_by: "status" };
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

    const allPlants = Object.values(this._hass.states)
      .filter((s) => s.attributes?.plant_manager === true);
    const filterBy = ["all", "needs_water", "attention"].includes(this.config.filter_by)
      ? this.config.filter_by
      : "all";
    const plants = allPlants.filter((plant) => {
      const { tone } = plantManagerStatus(plant);
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
        const orderA = plantManagerStatus(a).order;
        const orderB = plantManagerStatus(b).order;
        if (orderA !== orderB) return orderA - orderB;
      }

      return (a.attributes.plant_name || "").localeCompare(
        b.attributes.plant_name || "",
        "fr",
      );
    });
    const showImages = this.config.show_images !== false;
    const showBattery = this.config.show_battery !== false;
    const showHistory = this.config.show_history === true;
    const compact = this.config.compact === true;

    // Cache history per entity so ordinary Home Assistant state updates do not
    // trigger repeated history requests while the card is being rendered.
    if (!this._historyCache) this._historyCache = new Map();
    if (!this._historyPending) this._historyPending = new Set();
    const requestHistory = (entityId) => {
      const cached = entityId ? this._historyCache.get(entityId) : null;
      if (!showHistory || !entityId
        || (cached && Date.now() - cached.fetchedAt < 15 * 60 * 1000)
        || this._historyPending.has(entityId)
        || typeof this._hass.callWS !== "function") return;
      this._historyPending.add(entityId);
      const end = new Date();
      const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
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
        const points = validSamples.map((sample) => sample.value);
        const timestamps = validSamples.map((sample) => sample.timestamp);
        // A sudden increase can indicate watering, but moisture sensors can
        // also jump for other reasons; this is only a hint, never a confirmed event.
        const possibleWatering = sampleValues.some((value, index) =>
          index > 0 && Number.isFinite(value)
          && Number.isFinite(sampleValues[index - 1])
          && value - sampleValues[index - 1] >= 15);
        this._historyCache.set(entityId, {
          points, timestamps, possibleWatering, fetchedAt: Date.now(),
        });
      }).catch(() => {
        this._historyCache.set(entityId, { points: [], fetchedAt: Date.now() });
      }).finally(() => {
        this._historyPending.delete(entityId);
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
      const { label, tone, icon, advice } = plantManagerStatus(plant);

      const percentage = valid ? Math.max(0, Math.min(100, moisture)) : 0;
      const moistureText = valid ? `${Math.round(moisture)} %` : "Indisponible";
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
      const historyEntity = a.moisture_entity;
      const moistureSource = historyEntity ? this._hass.states[historyEntity] : null;
      let updatedText = "";
      const updatedAt = moistureSource?.last_updated || moistureSource?.last_changed;
      const updatedTimestamp = updatedAt ? new Date(updatedAt).getTime() : NaN;
      if (Number.isFinite(updatedTimestamp)) {
        const ageMinutes = Math.max(0, Math.floor((Date.now() - updatedTimestamp) / 60000));
        const ageLabel = ageMinutes < 1 ? "à l’instant"
          : ageMinutes < 60 ? `il y a ${ageMinutes} min`
          : ageMinutes < 1440 ? `il y a ${Math.floor(ageMinutes / 60)} h`
          : `il y a ${Math.floor(ageMinutes / 1440)} j`;
        updatedText = `<div class="updated">Dernière mesure ${ageLabel}</div>`;
      }
      requestHistory(historyEntity);
      const historyEntry = showHistory && historyEntity ? this._historyCache.get(historyEntity) : null;
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
        const trendText = trend > 2 ? "En hausse" : trend < -2 ? "En baisse" : "Stable";
        const wateringHint = historyEntry.possibleWatering
          ? '<div class="watering-hint"><ha-icon icon="mdi:water-plus-outline"></ha-icon> Hausse notable détectée : arrosage possible (estimation).</div>'
          : "";
        historyMarkup = `<div class="history">
          <div class="history-heading"><span>Tendance sur 24 h</span><span>${trendText}</span></div>
          <svg viewBox="0 0 100 32" preserveAspectRatio="none" role="img" aria-label="Historique de l'humidité sur 24 heures : ${trendText.toLocaleLowerCase("fr")}">
            <polyline points="${points}" fill="none" stroke="var(--info-color, var(--primary-color))" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></polyline>
          </svg>
          ${wateringHint}
        </div>`;
      } else if (showHistory && Array.isArray(history)) {
        historyMarkup = '<div class="history history-empty">Historique insuffisant pour afficher la tendance.</div>';
      }
      const imageUrl = showImages ? safeImageUrl(a.image_url) : "";
      const image = imageUrl
        ? `<img class="plant-image" src="${esc(imageUrl)}" alt="${esc(a.plant_name || "Plante")}" loading="lazy">`
        : '<div class="plant-icon"><ha-icon icon="mdi:flower"></ha-icon></div>';

      return `<article class="plant" data-entity-id="${esc(plant.entity_id)}" tabindex="${tapAction === "none" ? "-1" : "0"}" ${tapAction === "none" ? "" : `role="button" aria-label="Afficher les détails de ${esc(a.plant_name || plant.entity_id)}"`}>
        <div class="photo">${image}</div>
        <div class="details">
          <div class="plant-heading">
            <div class="name" title="${esc(a.plant_name || plant.entity_id)}">${esc(a.plant_name || plant.entity_id)}</div>
            <span class="status ${tone}"><ha-icon icon="${icon}"></ha-icon>${label}</span>
          </div>
          <div class="moisture-line">
            <span class="moisture-label"><ha-icon icon="mdi:water-percent"></ha-icon> Humidité du sol</span>
            <strong class="moisture-value">${moistureText}</strong>
          </div>
          <div class="progress-track" role="progressbar" aria-label="Humidité du sol" aria-valuemin="0" aria-valuemax="100" ${valid ? `aria-valuenow="${Math.round(percentage)}"` : 'aria-valuetext="Indisponible"'}>
            <div class="progress-fill ${tone}" style="width:${percentage}%"></div>
          </div>
          ${showBattery && battery ? `<div class="extras">${battery}</div>` : ""}
          ${historyMarkup}
          <div class="advice"><ha-icon icon="mdi:lightbulb-outline"></ha-icon><span>${advice}</span></div>
          ${updatedText}
        </div>
      </article>`;
    }).join("");

    const countTone = (tone) => plants.filter(
      (plant) => plantManagerStatus(plant).tone === tone,
    ).length;
    const needsWater = countTone("dry");
    const veryWet = countTone("wet");
    const healthy = countTone("good");
    const unavailable = countTone("neutral");
    const summary = plants.length
      ? `<div class="summary"><span class="summary-dot"></span>${plants.length} plante${plants.length > 1 ? "s" : ""} affichée${plants.length > 1 ? "s" : ""}${needsWater ? ` <span class="summary-alert">· ${needsWater} à arroser</span>` : ""}</div>`
      : "";
    const overview = plants.length
      ? `<div class="overview" aria-label="Résumé des plantes">
          <div class="overview-item dry"><span class="overview-count">${needsWater}</span><span>À arroser</span></div>
          <div class="overview-item wet"><span class="overview-count">${veryWet}</span><span>Très humides</span></div>
          <div class="overview-item good"><span class="overview-count">${healthy}</span><span>En forme</span></div>
          <div class="overview-item neutral"><span class="overview-count">${unavailable}</span><span>Indisponibles</span></div>
        </div>`
      : "";

    this._root.innerHTML = `
      <ha-card class="${compact ? "compact" : ""}">
        <div class="card-header">
          <div class="header-icon"><ha-icon icon="mdi:leaf"></ha-icon></div>
          <div class="header-text">
            <div class="title">${esc(this.config.title || "Mon jardin d’intérieur")}</div>
            ${summary}
          </div>
        </div>
        ${overview}
        <div class="content">
          ${plants.length ? rows : allPlants.length ? '<div class="empty"><div class="empty-icon"><ha-icon icon="mdi:filter-off-outline"></ha-icon></div><strong>Aucune plante correspondante</strong><span>Modifiez le filtre pour afficher d’autres plantes.</span></div>' : '<div class="empty"><div class="empty-icon"><ha-icon icon="mdi:sprout-outline"></ha-icon></div><strong>Aucune plante pour le moment</strong><span>Ajoutez une plante dans Plant Manager pour commencer le suivi.</span></div>'}
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
          color: var(--success-color, #2e7d32);
          background: color-mix(in srgb, var(--success-color, #2e7d32) 12%, var(--card-background-color));
        }
        .header-icon ha-icon { --mdc-icon-size: 26px; }
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
        .compact .header-icon ha-icon { --mdc-icon-size: 21px; }
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
        .extras { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
        .battery { display: inline-flex; align-items: center; gap: 4px; color: var(--secondary-text-color); font-size: 11px; }
        .battery.low { color: var(--error-color, #c62828); font-weight: 700; }
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

const PLANT_MANAGER_CARD_LABELS = {
  title: "Titre",
  sort_by: "Tri",
  filter_by: "Plantes affichées",
  tap_action: "Action au toucher",
  show_images: "Afficher les photos",
  show_battery: "Afficher la batterie",
  show_history: "Afficher l'historique sur 24 h",
  compact: "Mode compact",
};
const PLANT_MANAGER_CARD_SCHEMA = [
  { name: "title", selector: { text: {} } },
  {
    name: "sort_by",
    selector: { select: { mode: "dropdown", options: [
      { value: "name", label: "Nom" },
      { value: "moisture", label: "Humidité croissante" },
      { value: "status", label: "Statut" },
    ] } },
  },
  {
    name: "filter_by",
    selector: { select: { mode: "dropdown", options: [
      { value: "all", label: "Toutes" },
      { value: "needs_water", label: "À arroser" },
      { value: "attention", label: "Nécessitant une attention" },
    ] } },
  },
  {
    name: "tap_action",
    selector: { select: { mode: "dropdown", options: [
      { value: "more-info", label: "Ouvrir les détails" },
      { value: "none", label: "Aucune" },
    ] } },
  },
  {
    type: "grid",
    name: "",
    schema: ["show_images", "show_battery", "show_history", "compact"]
      .map((name) => ({ name, selector: { boolean: {} } })),
  },
];
const PLANT_MANAGER_CARD_DEFAULTS = {
  sort_by: "name",
  filter_by: "all",
  tap_action: "more-info",
  show_images: true,
  show_battery: true,
  show_history: false,
  compact: false,
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
      this._form.computeLabel = (schema) => PLANT_MANAGER_CARD_LABELS[schema.name] || schema.name;
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
    this._form.schema = PLANT_MANAGER_CARD_SCHEMA;
    this._form.data = { ...PLANT_MANAGER_CARD_DEFAULTS, ...this._config };
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
    description: "Affiche les plantes avec leur humidité, leur statut et leur batterie.",
    preview: true,
  });
}
