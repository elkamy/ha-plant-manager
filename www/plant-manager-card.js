class PlantManagerCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    this.innerHTML = "";
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
    const plants = Object.values(this._hass.states)
      .filter((s) => s.attributes?.plant_manager === true)
      .sort((a, b) => (a.attributes.plant_name || "").localeCompare(b.attributes.plant_name || "", "fr"));

    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));

    const safeImageUrl = (value) => {
      const url = String(value || "").trim();
      if (/^https?:\/\//i.test(url) || url.startsWith("/local/") || url.startsWith("/api/")) {
        return url;
      }
      return "";
    };

    const rows = plants.map((plant) => {
      const a = plant.attributes;
      const moisture = Number(a.moisture);
      const valid = Number.isFinite(moisture);
      let label = plant.state || "indisponible";
      let color = "#64748b";
      if (label === "à arroser") color = "#dc2626";
      else if (label === "OK") color = "#16a34a";
      else if (label === "très humide") color = "#d97706";
      const battery = a.battery !== null && a.battery !== undefined
        ? `<span class="battery">Batterie : ${esc(a.battery)}${String(a.battery).match(/^\d+(\.\d+)?$/) ? "%" : ""}</span>`
        : "";
      const imageUrl = safeImageUrl(a.image_url);
      const image = imageUrl
        ? `<img class="plant-image" src="${esc(imageUrl)}" alt="${esc(a.plant_name || "Plante")}" loading="lazy">`
        : '<div class="plant-icon">🌿</div>';
      return `<div class="plant">
        ${image}
        <div class="details">
          <div class="name">${esc(a.plant_name || plant.entity_id)}</div>
          <div class="meta">${valid ? `Humidité du sol : ${Math.round(moisture)} %` : "Humidité indisponible"} ${battery}</div>
        </div>
        <div class="status" style="color:${color}">${esc(label)}</div>
      </div>`;
    }).join("");

    this.innerHTML = `
      <ha-card header="${esc(this.config.title || "Mes plantes")}">
        <div class="content">
          ${plants.length ? rows : '<div class="empty">Aucune plante configurée dans Plant Manager.</div>'}
        </div>
      </ha-card>
      <style>
        .content { padding: 0 16px 12px; }
        .plant { display:flex; align-items:center; gap:12px; padding:14px 0; border-bottom:1px solid var(--divider-color); }
        .plant:last-child { border-bottom:0; }
        .plant-icon, .plant-image { width:52px; height:52px; flex:0 0 52px; border-radius:8px; }
        .plant-icon { display:flex; align-items:center; justify-content:center; font-size:25px; background:var(--secondary-background-color); }
        .plant-image { object-fit:cover; }
        .details { flex:1; min-width:0; }
        .name { font-weight:600; color:var(--primary-text-color); }
        .meta { font-size:12px; color:var(--secondary-text-color); margin-top:4px; }
        .battery { margin-left:8px; }
        .status { font-size:13px; font-weight:600; text-align:right; }
        .empty { padding:18px 0; color:var(--secondary-text-color); }
      </style>`;
  }
}

customElements.define("plant-manager-card", PlantManagerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "plant-manager-card",
  name: "Plant Manager",
  description: "Affiche automatiquement les plantes configurées dans Plant Manager."
});
