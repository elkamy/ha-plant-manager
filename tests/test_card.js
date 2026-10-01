const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

class FakeHTMLElement {
  querySelectorAll() { return []; }
}

const registry = new Map();
const windowStub = { customCards: [] };
const context = {
  HTMLElement: FakeHTMLElement,
  customElements: {
    define: (name, component) => registry.set(name, component),
  },
  window: windowStub,
};

vm.runInNewContext(
  fs.readFileSync("www/plant-manager-card.js", "utf8"),
  context,
  { filename: "plant-manager-card.js" },
);

const PlantManagerCard = registry.get("plant-manager-card");

function renderCard(states, config = {}, hassExtras = {}) {
  const card = new PlantManagerCard();
  card.setConfig(config);
  card.hass = { states, ...hassExtras };
  return card.innerHTML;
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
    "sensor.pachira_status": plant("sensor.pachira_status", "indisponible", {
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
    "sensor.pachira_status": plant("sensor.pachira_status", "à arroser", {
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
    "sensor.pachira_status": plant("sensor.pachira_status", "à arroser", {
      plant_name: "Pachira",
      moisture: 22,
    }),
    "sensor.ficus_status": plant("sensor.ficus_status", "indisponible", {
      plant_name: "Ficus",
      moisture: null,
    }),
  }, { sort_by: "moisture" });

  assert.ok(html.indexOf("Pachira") < html.indexOf("Monstera"));
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
    "sensor.pachira_status": plant("sensor.pachira_status", "à arroser", {
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
    "sensor.pachira_status": plant("sensor.pachira_status", "à arroser", {
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
    "sensor.dry": plant("sensor.dry", "à arroser", { plant_name: "Pachira", moisture: 20 }),
    "sensor.wet": plant("sensor.wet", "très humide", { plant_name: "Fougère", moisture: 90 }),
    "sensor.unavailable": plant("sensor.unavailable", "indisponible", { plant_name: "Ficus", moisture: null }),
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
    "sensor.dry": plant("sensor.dry", "à arroser", { plant_name: "Pachira", moisture: 20 }),
    "sensor.wet": plant("sensor.wet", "très humide", { plant_name: "Fougère", moisture: 90 }),
    "sensor.ok": plant("sensor.ok", "OK", { plant_name: "Monstera", moisture: 50 }),
    "sensor.unavailable": plant("sensor.unavailable", "indisponible", { plant_name: "Ficus", moisture: null }),
  });

  assert.match(html, /aria-label="Résumé des plantes"/);
  assert.match(html, /overview-count">1<\/span><span>À arroser/);
  assert.match(html, /overview-count">1<\/span><span>Très humides/);
  assert.match(html, /overview-count">1<\/span><span>En forme/);
  assert.match(html, /overview-count">1<\/span><span>Indisponibles/);
});

test("does not display out-of-range moisture as a valid progress value", () => {
  const html = renderCard({
    "sensor.invalid": plant("sensor.invalid", "indisponible", {
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
    callWS: () => Promise.resolve([[{ state: "25" }, { state: "35" }, { state: "50" }]]),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.innerHTML, /Tendance sur 24 h/);
  assert.match(card.innerHTML, /En hausse/);
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
    callWS: () => Promise.resolve([[
      { state: "20" },
      { state: "22" },
      { state: "46" },
    ]]),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.innerHTML, /Hausse notable détectée : arrosage possible \(estimation\)/);
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
    callWS: () => Promise.resolve([[{ state: "20" }, { state: "24" }, { state: "30" }]]),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.doesNotMatch(card.innerHTML, /Hausse notable détectée/);
});

test("shows contextual care advice for the current plant status", () => {
  const html = renderCard({
    "sensor.dry": plant("sensor.dry", "à arroser", { plant_name: "Pachira", moisture: 20 }),
  });
  assert.match(html, /Vérifiez le substrat et arrosez si nécessaire/);
  assert.match(html, /mdi:lightbulb-outline/);
});
