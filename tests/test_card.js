const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

class FakeHTMLElement {
  querySelectorAll() { return []; }
  attachShadow() {
    this.shadowRoot = { innerHTML: "", querySelectorAll: () => [] };
    return this.shadowRoot;
  }
}

const registry = new Map();
const windowStub = { customCards: [] };
const context = {
  HTMLElement: FakeHTMLElement,
  customElements: {
    define: (name, component) => registry.set(name, component),
    get: (name) => registry.get(name),
  },
  window: windowStub,
};

vm.runInNewContext(
  fs.readFileSync("custom_components/plant_manager/www/plant-manager-card.js", "utf8"),
  context,
  { filename: "plant-manager-card.js" },
);

const PlantManagerCard = registry.get("plant-manager-card");

// Shape of a history/history_during_period websocket answer: states under the
// entity ID, with the state in "s" and timestamps in seconds.
function wsHistory(samples, entityId = "sensor.monstera_moisture") {
  return {
    [entityId]: samples.map(({ state, lu }) => (lu === undefined ? { s: state } : { s: state, lu })),
  };
}

function renderCard(states, config = {}, hassExtras = {}) {
  const card = new PlantManagerCard();
  card.setConfig(config);
  card.hass = { states, ...hassExtras };
  return card.shadowRoot.innerHTML;
}

function plant(entityId, state, attributes = {}) {
  return {
    entity_id: entityId,
    state,
    attributes: { plant_manager: true, plant_name: entityId, ...attributes },
  };
}

test("registers the custom card with Home Assistant", () => {
  assert.equal(typeof PlantManagerCard, "function");
  assert.equal(windowStub.customCards[0].type, "plant-manager-card");
});

test("renders an empty state when no plants are configured", () => {
  const html = renderCard({});
  assert.match(html, /Aucune plante pour le moment/);
  assert.match(html, /Mon jardin d’intérieur/);
});

test("shows unavailable moisture as unavailable, not zero percent", () => {
  const html = renderCard({
    "sensor.pachira_status": plant("sensor.pachira_status", "unknown", {
      moisture: null,
    }),
  });
  assert.match(html, /Indisponible/);
  assert.doesNotMatch(html, /0 %/);
  assert.doesNotMatch(html, /aria-valuenow="0"/);
  assert.match(html, /aria-valuetext="Indisponible"/);
});

test("renders valid moisture and watering summary", () => {
  const html = renderCard({
    "sensor.pachira_status": plant("sensor.pachira_status", "needs_water", {
      moisture: 22.6,
      battery: "18",
    }),
    "sensor.monstera_status": plant("sensor.monstera_status", "OK", {
      plant_name: "Monstera",
      moisture: 55,
    }),
  }, { title: "Mon jardin" });

  assert.match(html, /Mon jardin/);
  assert.match(html, /23 %/);
  assert.match(html, /18%/);
  assert.match(html, /battery low/);
  assert.match(html, /mdi:battery-alert/);
  assert.match(html, /2 plantes affichées/);
  assert.match(html, /1 à arroser/);
  assert.ok(html.indexOf("Monstera") < html.indexOf("sensor.pachira_status"));
});

test("escapes plant names and titles before inserting HTML", () => {
  const html = renderCard({
    "sensor.test_status": plant("sensor.test_status", "OK", {
      plant_name: '<img src=x onerror="alert(1)">',
      moisture: 50,
    }),
  }, { title: '<script>alert("x")</script>' });

  assert.doesNotMatch(html, /<script>alert/);
  assert.doesNotMatch(html, /<img src=x onerror/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&lt;img src=x/);
});

test("rejects unsafe image URL schemes", () => {
  const html = renderCard({
    "sensor.test_status": plant("sensor.test_status", "OK", {
      plant_name: "Pachira",
      moisture: 50,
      image_url: "javascript:alert(1)",
    }),
  });
  assert.doesNotMatch(html, /src="javascript:/);
  assert.match(html, /plant-icon/);
});

test("hides unavailable battery values and respects the configured low threshold", () => {
  const html = renderCard({
    "sensor.low_battery": plant("sensor.low_battery", "OK", {
      plant_name: "Pothos",
      moisture: 50,
      battery: "unavailable",
    }),
    "sensor.normal_battery": plant("sensor.normal_battery", "OK", {
      plant_name: "Ficus",
      moisture: 50,
      battery: "28",
      battery_low_threshold: 20,
    }),
  });

  assert.doesNotMatch(html, /unavailable/);
  assert.match(html, /28%/);
  assert.doesNotMatch(html, /battery low/);
  assert.doesNotMatch(html, /mdi:battery-alert/);
});

test("supports sorting plants by moisture with unavailable values last", () => {
  const html = renderCard({
    "sensor.monstera_status": plant("sensor.monstera_status", "OK", {
      plant_name: "Monstera",
      moisture: 55,
    }),
    "sensor.pachira_status": plant("sensor.pachira_status", "needs_water", {
      plant_name: "Pachira",
      moisture: 22,
    }),
    "sensor.ficus_status": plant("sensor.ficus_status", "unknown", {
      plant_name: "Ficus",
      moisture: null,
    }),
  }, { sort_by: "moisture" });

  assert.ok(html.indexOf("Pachira") < html.indexOf("Monstera"));
  assert.ok(html.indexOf("Monstera") < html.indexOf("Ficus"));
});

test("sorts out-of-range moisture values with unavailable readings", () => {
  const html = renderCard({
    "sensor.invalid": plant("sensor.invalid", "unknown", {
      plant_name: "Ficus",
      moisture: 150,
    }),
    "sensor.valid": plant("sensor.valid", "OK", {
      plant_name: "Monstera",
      moisture: 50,
    }),
  }, { sort_by: "moisture" });

  assert.ok(html.indexOf("Monstera") < html.indexOf("Ficus"));
});

test("supports sorting by plant status and hiding images and battery", () => {
  const html = renderCard({
    "sensor.monstera_status": plant("sensor.monstera_status", "OK", {
      plant_name: "Monstera",
      moisture: 55,
      battery: 18,
      image_url: "https://example.com/monstera.jpg",
    }),
    "sensor.pachira_status": plant("sensor.pachira_status", "needs_water", {
      plant_name: "Pachira",
      moisture: 22,
      battery: 80,
      image_url: "https://example.com/pachira.jpg",
    }),
  }, { sort_by: "status", show_images: false, show_battery: false });

  assert.ok(html.indexOf("Pachira") < html.indexOf("Monstera"));
  assert.doesNotMatch(html, /src="https:\/\/example\.com/);
  assert.doesNotMatch(html, /18%|80%/);
  assert.match(html, /plant-icon/);
});

test("filters plants that need watering", () => {
  const html = renderCard({
    "sensor.monstera_status": plant("sensor.monstera_status", "OK", {
      plant_name: "Monstera",
      moisture: 55,
    }),
    "sensor.pachira_status": plant("sensor.pachira_status", "needs_water", {
      plant_name: "Pachira",
      moisture: 22,
    }),
  }, { filter_by: "needs_water" });

  assert.match(html, /Pachira/);
  assert.doesNotMatch(html, /Monstera/);
  assert.match(html, /1 plante affichée/);
});

test("attention filter includes dry, very wet and unavailable plants", () => {
  const html = renderCard({
    "sensor.dry": plant("sensor.dry", "needs_water", { plant_name: "Pachira", moisture: 20 }),
    "sensor.wet": plant("sensor.wet", "too_wet", { plant_name: "Fougère", moisture: 90 }),
    "sensor.unavailable": plant("sensor.unavailable", "unknown", { plant_name: "Ficus", moisture: null }),
    "sensor.ok": plant("sensor.ok", "OK", { plant_name: "Monstera", moisture: 50 }),
  }, { filter_by: "attention" });

  assert.match(html, /Pachira/);
  assert.match(html, /Fougère/);
  assert.match(html, /Ficus/);
  assert.doesNotMatch(html, /Monstera/);
});

test("shows a dedicated empty state when no plant matches the filter", () => {
  const html = renderCard({
    "sensor.monstera_status": plant("sensor.monstera_status", "OK", {
      plant_name: "Monstera",
      moisture: 55,
    }),
  }, { filter_by: "needs_water" });

  assert.match(html, /Aucune plante correspondante/);
  assert.doesNotMatch(html, /Aucune plante pour le moment/);
});


test("supports compact display mode", () => {
  const normal = renderCard({
    "sensor.pachira_status": plant("sensor.pachira_status", "OK", {
      plant_name: "Pachira",
      moisture: 50,
    }),
  });
  const compact = renderCard({
    "sensor.pachira_status": plant("sensor.pachira_status", "OK", {
      plant_name: "Pachira",
      moisture: 50,
    }),
  }, { compact: true });

  assert.match(normal, /<ha-card class="">/);
  assert.match(compact, /<ha-card class="compact">/);
  assert.match(compact, /\.compact \.plant \{ gap: 10px; padding: 8px 3px; \}/);
});

test("makes plant rows keyboard-accessible and supports disabling tap actions", () => {
  const states = {
    "sensor.pachira_status": plant("sensor.pachira_status", "OK", {
      plant_name: "Pachira",
      moisture: 50,
    }),
  };
  const clickable = renderCard(states);
  const inert = renderCard(states, { tap_action: "none" });

  assert.match(clickable, /role="button" aria-label="Afficher les détails de Pachira"/);
  assert.match(clickable, /tabindex="0"/);
  assert.match(inert, /tabindex="-1"/);
  assert.doesNotMatch(inert, /<article class="plant"[^>]*role="button"/);
});

test("shows a status overview for the plants currently displayed", () => {
  const html = renderCard({
    "sensor.dry": plant("sensor.dry", "needs_water", { plant_name: "Pachira", moisture: 20 }),
    "sensor.wet": plant("sensor.wet", "too_wet", { plant_name: "Fougère", moisture: 90 }),
    "sensor.ok": plant("sensor.ok", "OK", { plant_name: "Monstera", moisture: 50 }),
    "sensor.unavailable": plant("sensor.unavailable", "unknown", { plant_name: "Ficus", moisture: null }),
  });

  assert.match(html, /aria-label="Résumé des plantes"/);
  assert.match(html, /overview-count">1<\/span><span>À arroser/);
  assert.match(html, /overview-count">1<\/span><span>Très humides/);
  assert.match(html, /overview-count">1<\/span><span>En forme/);
  assert.match(html, /overview-count">1<\/span><span>Indisponibles/);
});

test("does not display out-of-range moisture as a valid progress value", () => {
  const html = renderCard({
    "sensor.invalid": plant("sensor.invalid", "unknown", {
      plant_name: "Ficus",
      moisture: 150,
    }),
  });

  assert.match(html, /Indisponible/);
  assert.doesNotMatch(html, /aria-valuenow="100"/);
  assert.match(html, /aria-valuetext="Indisponible"/);
  assert.match(html, /width:0%/);
});

test("renders a 24-hour moisture trend when history is enabled and available", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "OK", {
        plant_name: "Monstera",
        moisture: 50,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([{ state: "25" }, { state: "35" }, { state: "50" }])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /Tendance sur 24 h/);
  assert.match(card.shadowRoot.innerHTML, /En hausse/);
});

test("ignores unknown and unavailable states in moisture history", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "OK", {
        plant_name: "Monstera",
        moisture: 50,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([
      { state: "unknown" },
      { state: "unavailable" },
      { state: "" },
      { state: "50" },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  // Only the "50" reading is valid: it is extended to now as a flat line.
  assert.match(card.shadowRoot.innerHTML, /Tendance sur 24 h<\/span><span>Stable/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Hausse notable détectée/);
});

test("shows a qualified possible-watering hint after a notable moisture rise", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "OK", {
        plant_name: "Monstera",
        moisture: 45,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([
      { state: "20" },
      { state: "22" },
      { state: "46" },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /Hausse notable détectée : arrosage possible \(estimation\)/);
});

test("does not infer a watering event from a small moisture increase", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "OK", {
        plant_name: "Monstera",
        moisture: 30,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([{ state: "20" }, { state: "24" }, { state: "30" }])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Hausse notable détectée/);
});

test("shows contextual care advice for the current plant status", () => {
  const html = renderCard({
    "sensor.dry": plant("sensor.dry", "needs_water", { plant_name: "Pachira", moisture: 20 }),
  });
  assert.match(html, /Vérifiez le substrat et arrosez si nécessaire/);
  assert.match(html, /mdi:lightbulb-outline/);
});


test("does not infer watering across an unavailable history sample", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "OK", {
        plant_name: "Monstera",
        moisture: 50,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([
      { state: "20" },
      { state: "unavailable" },
      { state: "45" },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /Tendance sur 24 h/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Hausse notable détectée/);
});


test("does not render a broken age label for an invalid sensor timestamp", () => {
  const html = renderCard({
    "sensor.plant_status": plant("sensor.plant_status", "OK", {
      plant_name: "Monstera",
      moisture: 50,
      moisture_entity: "sensor.monstera_moisture",
    }),
    "sensor.monstera_moisture": {
      entity_id: "sensor.monstera_moisture",
      state: "50",
      attributes: {},
      last_updated: "not-a-date",
    },
  });

  assert.doesNotMatch(html, /NaN/);
  assert.doesNotMatch(html, /Dernière mesure/);
});


test("plots moisture history using elapsed time up to now", async () => {
  const start = Date.now() / 1000 - 24 * 3600;
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "ok", {
        plant_name: "Monstera",
        moisture: 40,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([
      { state: "20", lu: start },
      { state: "30", lu: start + 6 * 3600 },
      { state: "40", lu: start + 12 * 3600 },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /points="0\.0,28\.0 25\.0,17\.0 50\.0,6\.0 100\.0,6\.0"/);
});

test("draws a flat line for a value unchanged over 24 hours", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "too_wet", {
        plant_name: "Ficus",
        moisture: 100,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([{ state: "100", lu: Date.now() / 1000 - 24 * 3600 }])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /points="0\.0,17\.0 100\.0,17\.0"/);
  assert.match(card.shadowRoot.innerHTML, /Stable/);
});

test("ignores a history answer for another entity", async () => {
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "ok", {
        plant_name: "Monstera",
        moisture: 50,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([{ state: "50" }, { state: "60" }], "sensor.other")),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /Historique insuffisant pour afficher la tendance/);
});

test("supports Home Assistant's object syntax for tap_action", () => {
  const html = renderCard({
    "sensor.pachira_status": plant("sensor.pachira_status", "ok", { plant_name: "Pachira", moisture: 50 }),
  }, { tap_action: { action: "none" } });
  assert.match(html, /tabindex="-1"/);
  assert.doesNotMatch(html, /<article[^>]*role="button"/);
});

test("renders into a shadow root so its styles stay scoped", () => {
  const card = new PlantManagerCard();
  card.setConfig({});
  card.hass = { states: {} };
  assert.ok(card.shadowRoot);
  assert.match(card.shadowRoot.innerHTML, /:host \{ display: block; \}/);
});

test("re-renders only when a plant or its moisture sensor changes", () => {
  const card = new PlantManagerCard();
  card.setConfig({});
  let renders = 0;
  const render = card.render.bind(card);
  card.render = () => { renders += 1; render(); };
  const pachira = plant("sensor.pachira_status", "ok", {
    plant_name: "Pachira", moisture: 50, moisture_entity: "sensor.pachira_moisture",
  });
  const moisture = { entity_id: "sensor.pachira_moisture", state: "50", attributes: {} };
  const states = { "sensor.pachira_status": pachira, "sensor.pachira_moisture": moisture };

  card.hass = { states };
  card.hass = { states: { ...states, "light.kitchen": { state: "on", attributes: {} } } };
  assert.equal(renders, 1);

  card.hass = { states: { ...states, "sensor.pachira_moisture": { ...moisture, state: "49" } } };
  assert.equal(renders, 2);
  card.hass = { states: { ...states, "sensor.ficus_status": plant("sensor.ficus_status", "ok") } };
  assert.equal(renders, 3);
});

test("treats unavailable and unknown statuses as needing attention", () => {
  const html = renderCard({
    "sensor.a": plant("sensor.a", "unavailable", { plant_name: "Ficus" }),
    "sensor.b": plant("sensor.b", "unknown", { plant_name: "Pothos" }),
    "sensor.c": plant("sensor.c", "ok", { plant_name: "Monstera", moisture: 50 }),
  }, { filter_by: "attention" });
  assert.match(html, /Ficus/);
  assert.match(html, /Pothos/);
  assert.doesNotMatch(html, /Monstera/);
});

test("accepts Home Assistant local, API and media image paths", () => {
  for (const url of ["/local/a.jpg", "/api/image/b", "/media/local/c.jpg", "/plant_manager/images/d.png"]) {
    const html = renderCard({
      "sensor.a": plant("sensor.a", "ok", { moisture: 50, image_url: url }),
    });
    assert.match(html, new RegExp(`src="${url}"`));
  }
});

test("provides a stub config and a visual editor for the card picker", () => {
  assert.deepEqual(
    JSON.parse(JSON.stringify(PlantManagerCard.getStubConfig())),
    { title: "Mes plantes", sort_by: "status" },
  );
  assert.equal(typeof registry.get("plant-manager-card-editor"), "function");
  assert.equal(windowStub.customCards[0].preview, true);
});

test("ignores a lone sensor glitch in the history", async () => {
  // Real case: a soil sensor reported 100 → 20 → 100 % within a second.
  const start = Date.now() / 1000 - 24 * 3600;
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "too_wet", {
        plant_name: "Ficus",
        moisture: 100,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([
      { state: "100", lu: start },
      { state: "20", lu: start + 14 * 3600 },
      { state: "100", lu: start + 14 * 3600 + 1 },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Hausse notable détectée/);
  assert.match(card.shadowRoot.innerHTML, /points="0\.0,17\.0 58\.3,17\.0 100\.0,17\.0"/);
});

test("keeps a real watering, which is not a lone glitch", async () => {
  const start = Date.now() / 1000 - 24 * 3600;
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "ok", {
        plant_name: "Monstera",
        moisture: 60,
        moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: () => Promise.resolve(wsHistory([
      { state: "25", lu: start },
      { state: "60", lu: start + 3600 },
      { state: "58", lu: start + 7200 },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /Hausse notable détectée : arrosage possible/);
});

test("shows when the plant was watered and needs water next", () => {
  const day = 24 * 3600 * 1000;
  const html = renderCard({
    "sensor.pachira_status": plant("sensor.pachira_status", "ok", {
      plant_name: "Pachira",
      moisture: 55,
      last_watered: new Date(Date.now() - 3 * day - 60000).toISOString(),
      next_watering: new Date(Date.now() + 4 * day).toISOString(),
    }),
    "sensor.ficus_status": plant("sensor.ficus_status", "ok", { plant_name: "Ficus", moisture: 50 }),
  });
  assert.match(html, /Arrosée il y a 3 j · prochain arrosage dans ~4 j/);
  assert.equal((html.match(/class="watering"/g) || []).length, 1);
});

test("speaks English to an English interface", () => {
  const html = renderCard({
    "sensor.dry": plant("sensor.dry", "needs_water", { plant_name: "Pachira", moisture: 20 }),
  }, {}, { locale: { language: "en-GB" } });
  assert.match(html, /My indoor garden/);
  assert.match(html, /1 plant shown/);
  assert.match(html, /Needs water/);
  assert.match(html, /Check the soil and water if needed/);
  assert.doesNotMatch(html, /arroser/);
});

test("requests the configured history length and averages long histories", async () => {
  const requests = [];
  const start = Date.now() / 1000 - 3 * 86400;
  // A reading every 5 minutes for 3 days: 864 points, averaged before drawing.
  const samples = Array.from({ length: 864 }, (_, i) => ({ state: String(60 - i / 30), lu: start + i * 300 }));
  const card = new PlantManagerCard();
  card.setConfig({ show_history: true, history_days: 3 });
  card.hass = {
    states: {
      "sensor.plant_status": plant("sensor.plant_status", "ok", {
        plant_name: "Monstera", moisture: 31, moisture_entity: "sensor.monstera_moisture",
      }),
    },
    callWS: (request) => { requests.push(request); return Promise.resolve(wsHistory(samples)); },
  };
  await new Promise((resolve) => setImmediate(resolve));
  const days = (Date.parse(requests[0].end_time) - Date.parse(requests[0].start_time)) / 86400000;
  assert.equal(Math.round(days), 3);
  const html = card.shadowRoot.innerHTML;
  assert.match(html, /Tendance sur 3 j/);
  const points = html.match(/points="([^"]+)"/)[1].split(" ");
  assert.ok(points.length <= 120, `${points.length} points drawn`);
  assert.match(html, /En baisse/);
});

test("fills a sections dashboard row by default", () => {
  assert.deepEqual(JSON.parse(JSON.stringify(new PlantManagerCard().getGridOptions())), { columns: 12, min_columns: 6 });
});

test("shows the temperature with its status", () => {
  const html = renderCard({
    "sensor.cold": plant("sensor.cold", "ok", {
      plant_name: "Kentia", moisture: 50, temperature: 13.5, temperature_status: "too_cold",
      min_temperature: 15, max_temperature: 30,
    }),
    "sensor.fine": plant("sensor.fine", "ok", {
      plant_name: "Ficus", moisture: 50, temperature: 20, temperature_status: "ok",
      min_temperature: 15, max_temperature: 30,
    }),
  });
  assert.match(html, /class="temperature cold" title="Conseillé : 15–30 °C"><ha-icon icon="mdi:thermometer"><\/ha-icon><span>13,5 °C/);
  assert.match(html, /class="temperature" title="[^"]*"><ha-icon icon="mdi:thermometer"><\/ha-icon><span>20 °C/);
  // Watering is fine for both: the cold one gets the temperature advice.
  assert.match(html, /Il fait trop froid pour cette plante/);
  assert.match(html, /Rien à signaler pour le moment/);
});

test("the moisture advice comes before the temperature one", () => {
  const html = renderCard({
    "sensor.dry": plant("sensor.dry", "needs_water", {
      plant_name: "Pachira", moisture: 20, temperature: 35, temperature_status: "too_hot",
    }),
  });
  assert.match(html, /Vérifiez le substrat et arrosez/);
  assert.doesNotMatch(html, /trop chaud/);
});

test("can hide the temperature", () => {
  const html = renderCard({
    "sensor.cold": plant("sensor.cold", "ok", { moisture: 50, temperature: 13, temperature_status: "too_cold" }),
  }, { show_temperature: false });
  assert.doesNotMatch(html, /class="temperature/);
});

test("shows a bell reflecting the plant's notifications", () => {
  const html = renderCard({
    "sensor.on": plant("sensor.on", "ok", {
      plant_name: "Ficus", moisture: 50,
      notifications_entity: "switch.ficus_notifications", notifications_enabled: true,
    }),
    "sensor.off": plant("sensor.off", "ok", {
      plant_name: "Kentia", moisture: 50,
      notifications_entity: "switch.kentia_notifications", notifications_enabled: false,
    }),
    "sensor.none": plant("sensor.none", "ok", { plant_name: "Pachira", moisture: 50 }),
  });
  assert.match(html, /class="bell" data-switch="switch\.ficus_notifications" aria-pressed="true"[^>]*><ha-icon icon="mdi:bell">/);
  assert.match(html, /class="bell off" data-switch="switch\.kentia_notifications" aria-pressed="false"[^>]*><ha-icon icon="mdi:bell-off">/);
  assert.match(html, /cliquer pour les couper/);
  assert.equal((html.match(/<button type="button" class="bell/g) || []).length, 2);
});

test("clicking the bell toggles the switch without opening the plant", () => {
  const calls = [];
  const card = new PlantManagerCard();
  card.setConfig({});
  card.hass = { states: {}, callService: (...args) => calls.push(args) };
  const handlers = {};
  const attributes = { "aria-pressed": "true" };
  const icon = { attributes: { icon: "mdi:bell" }, setAttribute(name, value) { this.attributes[name] = value; } };
  const classes = new Set();
  const bell = {
    dataset: { switch: "switch.ficus_notifications" },
    getAttribute: (name) => attributes[name],
    setAttribute: (name, value) => { attributes[name] = value; },
    classList: { toggle: (name, on) => (on ? classes.add(name) : classes.delete(name)) },
    querySelector: () => icon,
    addEventListener: (type, handler) => { handlers[type] = handler; },
  };
  card.shadowRoot.querySelectorAll = () => [bell];
  card._bindBells();

  let stopped = false;
  handlers.click({ stopPropagation: () => { stopped = true; } });
  assert.ok(stopped);
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [["switch", "turn_off", { entity_id: "switch.ficus_notifications" }]]);
  assert.equal(attributes["aria-pressed"], "false");
  assert.equal(icon.attributes.icon, "mdi:bell-off");
  assert.ok(classes.has("off"));

  handlers.click({ stopPropagation() {} });
  assert.equal(calls[1][1], "turn_on");
  assert.equal(icon.attributes.icon, "mdi:bell");
});
