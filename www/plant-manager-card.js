class PlantManagerCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return 4;
  }

  render() {
    if (!this._hass) return;

    const allPlants = Object.values(this._hass.states)
      .filter((s) => s.attributes?.plant_manager === true);
    const filterBy = ["all", "needs_water", "attention"].includes(this.config.filter_by)
      ? this.config.filter_by
      : "all";
    const plants = allPlants.filter((plant) => {
      const state = String(plant.state || "").toLocaleLowerCase("fr");
      if (filterBy === "needs_water") return state === "à arroser";
      if (filterBy === "attention") {
        return state === "à arroser" || state === "très humide" || state === "indisponible";
      }
      return true;
    });

    const sortBy = ["name", "moisture", "status"].includes(this.config.sort_by)
      ? this.config.sort_by
      : "name";
    const statusOrder = { "à arroser": 0, "très humide": 1, ok: 2, indisponible: 3 };
    const moistureOf = (plant) => {
      const value = plant.attributes?.moisture;
      if (value === null || value === undefined || value === "") return NaN;
      const number = Number(value);
      return Number.isFinite(number) ? number : NaN;
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
        const stateA = String(a.state || "").toLocaleLowerCase("fr");
        const stateB = String(b.state || "").toLocaleLowerCase("fr");
        const orderA = statusOrder[stateA] ?? 3;
        const orderB = statusOrder[stateB] ?? 3;
        if (orderA !== orderB) return orderA - orderB;
      }

      return (a.attributes.plant_name || "").localeCompare(
        b.attributes.plant_name || "",
        "fr",
      );
    });
    const showImages = this.config.show_images !== false;
    const showBattery = this.config.show_battery !== false;
    const compact = this.config.compact === true;

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));

    const safeImageUrl = (value) => {
      const url = String(value || "").trim();
      if (/^https?:\/\//i.test(url) || url.startsWith("/local/") || url.startsWith("/api/")) return url;
      return "";
    };

    const rows = plants.map((plant) => {
      const a = plant.attributes;
      const hasMoisture = a.moisture !== null && a.moisture !== undefined && a.moisture !== "";
      const moisture = hasMoisture ? Number(a.moisture) : NaN;
      const valid = Number.isFinite(moisture);
      const normalizedState = String(plant.state || "").toLocaleLowerCase("fr");
      let label = "Indisponible";
      let tone = "neutral";
      let icon = "mdi:help-circle-outline";

      if (normalizedState === "à arroser") {
        label = "À arroser";
        tone = "dry";
        icon = "mdi:water-alert-outline";
      } else if (normalizedState === "ok") {
        label = "En bonne santé";
        tone = "good";
        icon = "mdi:check-circle-outline";
      } else if (normalizedState === "très humide") {
        label = "Très humide";
        tone = "wet";
        icon = "mdi:water";
      }

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
      const imageUrl = showImages ? safeImageUrl(a.image_url) : "";
      const image = imageUrl
        ? `<img class="plant-image" src="${esc(imageUrl)}" alt="${esc(a.plant_name || "Plante")}" loading="lazy">`
        : '<div class="plant-icon"><ha-icon icon="mdi:flower"></ha-icon></div>';

      return `<article class="plant">
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
        </div>
      </article>`;
    }).join("");

    const needsWater = plants.filter((p) => String(p.state).toLocaleLowerCase("fr") === "à arroser").length;
    const summary = plants.length
      ? `<div class="summary"><span class="summary-dot"></span>${plants.length} plante${plants.length > 1 ? "s" : ""} affichée${plants.length > 1 ? "s" : ""}${needsWater ? ` <span class="summary-alert">· ${needsWater} à arroser</span>` : ""}</div>`
      : "";

    this.innerHTML = `
      <ha-card class="${compact ? "compact" : ""}">
        <div class="card-header">
          <div class="header-icon"><ha-icon icon="mdi:leaf"></ha-icon></div>
          <div class="header-text">
            <div class="title">${esc(this.config.title || "Mon jardin d’intérieur")}</div>
            ${summary}
          </div>
        </div>
        <div class="content">
          ${plants.length ? rows : allPlants.length ? '<div class="empty"><div class="empty-icon"><ha-icon icon="mdi:filter-off-outline"></ha-icon></div><strong>Aucune plante correspondante</strong><span>Modifiez le filtre pour afficher d’autres plantes.</span></div>' : '<div class="empty"><div class="empty-icon"><ha-icon icon="mdi:sprout-outline"></ha-icon></div><strong>Aucune plante pour le moment</strong><span>Ajoutez une plante dans Plant Manager pour commencer le suivi.</span></div>'}
        </div>
      </ha-card>
      <style>
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
          .plant { gap: 10px; }
          .photo { width: 54px; height: 54px; flex-basis: 54px; border-radius: 14px; }
          .plant-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
          .status { padding: 4px 7px; }
        }
      </style>`;
  }
}

customElements.define("plant-manager-card", PlantManagerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "plant-manager-card",
  name: "Plant Manager",
  description: "Affiche les plantes avec leur humidité, leur statut et leur batterie."
});
