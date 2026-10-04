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
const context = {
  HTMLElement: FakeHTMLElement,
  customElements: {
    define: (name, component) => registry.set(name, component),
    get: (name) => registry.get(name),
  },
  window: { customCards: [] },
};
vm.runInNewContext(
  fs.readFileSync("custom_components/plant_manager/www/plant-manager-detail-card.js", "utf8"),
  context,
  { filename: "plant-manager-detail-card.js" },
);
const DetailCard = registry.get("plant-manager-detail-card");

// Shape of a history/history_during_period websocket answer: states under the
// entity ID, with the state in "s" and timestamps in seconds.
function wsHistory(samples, entityId = "sensor.monstera_moisture") {
  return {
    [entityId]: samples.map(({ state, lu }) => (lu === undefined ? { s: state } : { s: state, lu })),
  };
}

function plant(state = "OK", attributes = {}) {
  return {
    entity_id: "sensor.monstera_status",
    state,
    attributes: { plant_manager: true, plant_name: "Monstera", moisture: 54,
      low_threshold: 30, high_threshold: 75, battery: 82,
      battery_entity: "sensor.monstera_battery",
      battery_low_threshold: 25, ...attributes },
  };
}

function render(states, config = { entity: "sensor.monstera_status" }) {
  const card = new DetailCard();
  card.setConfig(config);
  card.hass = { states };
  return card.shadowRoot.innerHTML;
}

test("registers the detail card", () => {
  assert.equal(typeof DetailCard, "function");
  assert.equal(context.window.customCards[0].type, "plant-manager-detail-card");
});

test("requires a status entity", () => {
  assert.throws(() => new DetailCard().setConfig({}), /définir l'entité/);
});

test("renders moisture, thresholds, battery and care advice", () => {
  const html = render({ "sensor.monstera_status": plant() });
  assert.match(html, /Monstera/);
  assert.match(html, /54 %/);
  assert.match(html, /Seuil bas : 30 %/);
  assert.match(html, /Seuil haut : 75 %/);
  assert.match(html, /Batterie du capteur/);
  assert.match(html, /82 %/);
  assert.match(html, /Rien à signaler pour le moment/);
});

test("does not present invalid moisture as zero", () => {
  const html = render({ "sensor.monstera_status": plant("unknown", { moisture: 150 }) });
  assert.match(html, /Indisponible/);
  assert.match(html, /aria-valuetext="Indisponible"/);
  assert.doesNotMatch(html, /aria-valuenow="100"/);
});

test("shows a clear message for a missing plant entity", () => {
  const html = render({});
  assert.match(html, /Entité Plant Manager introuvable/);
});

test("shows a low-battery warning when below the configured threshold", () => {
  const html = render({ "sensor.monstera_status": plant("OK", { battery: 15 }) });
  assert.match(html, /class="battery-value low"/);
  assert.match(html, /Seuil d'alerte : 25 %/);
});

test("does not treat an out-of-range battery as a valid percentage", () => {
  const html = render({ "sensor.monstera_status": plant("OK", { battery: 150 }) });
  assert.match(html, /Batterie du capteur/);
  assert.match(html, /Indisponible/);
  assert.doesNotMatch(html, /class="battery-value low"/);
});

test("escapes plant names before inserting them into the card", () => {
  const html = render({ "sensor.monstera_status": plant("OK", { plant_name: "<Monstera>" }) });
  assert.match(html, /&lt;Monstera&gt;/);
  assert.doesNotMatch(html, /<h2><Monstera><\/h2>/);
});

test("allows the history section to be hidden", () => {
  const html = render(
    { "sensor.monstera_status": plant() },
    { entity: "sensor.monstera_status", show_history: false },
  );
  assert.match(html, /Historique masqué dans la configuration/);
  assert.doesNotMatch(html, /Évolution sur 24 h/);
});

test("labels the plant status from the sensor state", () => {
  const html = render({ "sensor.monstera_status": plant("needs_water", { moisture: 20 }) });
  assert.match(html, /À arroser/);
  assert.match(html, /Vérifiez le substrat et arrosez si nécessaire/);
});

test("accepts Home Assistant API image paths like the list card", () => {
  const html = render({ "sensor.monstera_status": plant("ok", { image_url: "/api/image/monstera" }) });
  assert.match(html, /src="\/api\/image\/monstera"/);
});

test("re-renders only when the plant or its moisture sensor changes", () => {
  const card = new DetailCard();
  card.setConfig({ entity: "sensor.monstera_status", show_history: false });
  let renders = 0;
  const original = card.render.bind(card);
  card.render = () => { renders += 1; original(); };
  const states = { "sensor.monstera_status": plant("ok", { moisture_entity: "sensor.monstera_moisture" }) };

  card.hass = { states };
  card.hass = { states: { ...states, "light.kitchen": { state: "on", attributes: {} } } };
  assert.equal(renders, 1);
  card.hass = { states: { ...states, "sensor.monstera_moisture": { state: "40", attributes: {} } } };
  assert.equal(renders, 2);
});

test("stub config selects the first Plant Manager plant", () => {
  const stub = DetailCard.getStubConfig({
    states: {
      "light.kitchen": { entity_id: "light.kitchen", attributes: {} },
      "sensor.monstera_status": plant(),
    },
  });
  assert.equal(stub.entity, "sensor.monstera_status");
  assert.equal(typeof registry.get("plant-manager-detail-card-editor"), "function");
});

test("draws the 24-hour history from the websocket answer", async () => {
  const start = Date.now() / 1000 - 24 * 3600;
  const card = new DetailCard();
  card.setConfig({ entity: "sensor.monstera_status" });
  card.hass = {
    states: { "sensor.monstera_status": plant("ok", { moisture_entity: "sensor.monstera_moisture" }) },
    callWS: () => Promise.resolve(wsHistory([
      { state: "60", lu: start },
      { state: "unavailable", lu: start + 3600 },
      { state: "54", lu: start + 12 * 3600 },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  const html = card.shadowRoot.innerHTML;
  assert.match(html, /Évolution sur 24 h<\/span><strong>En baisse/);
  // The scale spans the thresholds (30 and 75 %) as well as the readings.
  assert.match(html, /points="0\.0,13\.3 50\.0,16\.3 100\.0,16\.3"/);
  assert.match(html, /class="threshold low"[^>]*y1="28\.0"/);
  assert.match(html, /class="threshold high"[^>]*y1="6\.0"/);
  assert.match(html, /54 % min\./);
  assert.match(html, /60 % max\./);
});

test("draws a flat line when moisture did not change", async () => {
  const card = new DetailCard();
  card.setConfig({ entity: "sensor.monstera_status" });
  card.hass = {
    states: { "sensor.monstera_status": plant("too_wet", { moisture: 100, moisture_entity: "sensor.monstera_moisture" }) },
    callWS: () => Promise.resolve(wsHistory([{ state: "100", lu: Date.now() / 1000 - 3600 }])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /<strong>Stable<\/strong>/);
  assert.match(card.shadowRoot.innerHTML, /points="0\.0,6\.0 100\.0,6\.0"/);
});

test("hides the battery section when the plant has no battery sensor", () => {
  const withBattery = render({
    "sensor.monstera_status": plant("ok", { battery_entity: "sensor.monstera_battery" }),
  });
  const withoutBattery = render({
    "sensor.monstera_status": plant("ok", { battery_entity: null, battery: null }),
  });
  assert.match(withBattery, /Batterie du capteur/);
  assert.doesNotMatch(withoutBattery, /Batterie du capteur/);
});

test("does not plot a lone sensor glitch", async () => {
  const start = Date.now() / 1000 - 24 * 3600;
  const card = new DetailCard();
  card.setConfig({ entity: "sensor.monstera_status" });
  card.hass = {
    states: { "sensor.monstera_status": plant("too_wet", { moisture: 100, moisture_entity: "sensor.monstera_moisture" }) },
    callWS: () => Promise.resolve(wsHistory([
      { state: "100", lu: start },
      { state: "20", lu: start + 14 * 3600 },
      { state: "100", lu: start + 14 * 3600 + 1 },
    ])),
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(card.shadowRoot.innerHTML, /100 % min\./);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /20 % min\./);
});

test("shows the species under the plant name", () => {
  const html = render({
    "sensor.monstera_status": plant("ok", {
      plant_name: "Mon caoutchouc",
      species: "Ficus elastica",
      species_description: "arbre de la famille des Moracées",
    }),
  });
  assert.match(html, /<div class="species"><em>Ficus elastica<\/em> · arbre de la famille des Moracées<\/div>/);
});

test("does not repeat a species equal to the plant name", () => {
  const html = render({ "sensor.monstera_status": plant("ok", { species: "monstera" }) });
  assert.doesNotMatch(html, /class="species"/);
});

test("displays photos stored by the integration", () => {
  const html = render({
    "sensor.monstera_status": plant("ok", { image_url: "/plant_manager/images/0123456789abcdef0123456789abcdef.jpg" }),
  });
  assert.match(html, /src="\/plant_manager\/images\/0123456789abcdef0123456789abcdef\.jpg"/);
});

test("shows the last and next watering", () => {
  const html = render({
    "sensor.monstera_status": plant("ok", {
      last_watered: new Date(Date.now() - 5 * 3600 * 1000 - 60000).toISOString(),
      next_watering: new Date(Date.now() - 1000).toISOString(),
    }),
  });
  assert.match(html, /Dernier arrosage<\/span><strong>Il y a 5 h/);
  assert.match(html, /Prochain arrosage<\/span><strong>Maintenant/);
});

test("hides the watering section without watering data", () => {
  assert.doesNotMatch(render({ "sensor.monstera_status": plant() }), /class="watering"/);
});

test("speaks English to an English interface", () => {
  const card = new DetailCard();
  card.setConfig({ entity: "sensor.monstera_status", show_history: false });
  card.hass = {
    language: "en",
    states: { "sensor.monstera_status": plant("needs_water", { moisture: 20 }) },
  };
  const html = card.shadowRoot.innerHTML;
  assert.match(html, /Needs water/);
  assert.match(html, /Soil moisture/);
  assert.match(html, /Low threshold: 30 %/);
  assert.match(html, /Check the soil and water if needed/);
  assert.doesNotMatch(html, /Humidité/);
});

test("requests the configured history length", async () => {
  const requests = [];
  const card = new DetailCard();
  card.setConfig({ entity: "sensor.monstera_status", history_days: 7 });
  card.hass = {
    states: { "sensor.monstera_status": plant("ok", { moisture_entity: "sensor.monstera_moisture" }) },
    callWS: (request) => { requests.push(request); return Promise.resolve(wsHistory([{ state: "50" }, { state: "48" }])); },
  };
  await new Promise((resolve) => setImmediate(resolve));
  const days = (Date.parse(requests[0].end_time) - Date.parse(requests[0].start_time)) / 86400000;
  assert.equal(Math.round(days), 7);
  assert.match(card.shadowRoot.innerHTML, /Évolution sur 7 j/);
});

test("takes half of a sections dashboard by default", () => {
  assert.deepEqual(JSON.parse(JSON.stringify(new DetailCard().getGridOptions())), { columns: 6, min_columns: 4 });
});

test("shows the temperature row with the recommended range", () => {
  const html = render({
    "sensor.monstera_status": plant("ok", {
      temperature_entity: "sensor.monstera_temperature", temperature: 31.2,
      temperature_status: "too_hot", min_temperature: 18, max_temperature: 30,
    }),
  });
  assert.match(html, /<strong>Température<\/strong><span>Conseillé : 18–30 °C<\/span>/);
  assert.match(html, /class="temperature-value hot">31,2 °C/);
  assert.match(html, /Il fait trop chaud pour cette plante/);
});

test("hides the temperature row without a temperature sensor", () => {
  assert.doesNotMatch(render({ "sensor.monstera_status": plant() }), /<section class="temperature-row"/);
});

test("skips a species description that repeats the name", () => {
  // Real case: OpenPlantbook alias "chlorophytum comosum" for "Chlorophytum comosum 'Variegatum'".
  const html = render({
    "sensor.monstera_status": plant("ok", {
      plant_name: "Chlorophytum",
      species: "Chlorophytum comosum 'Variegatum'",
      species_description: "chlorophytum comosum",
    }),
  });
  assert.match(html, /<div class="species"><em>Chlorophytum comosum &#39;Variegatum&#39;<\/em><\/div>/);
});

test("shows the notifications bell in the header", () => {
  const on = render({
    "sensor.monstera_status": plant("ok", {
      notifications_entity: "switch.monstera_notifications", notifications_enabled: true,
    }),
  });
  assert.match(on, /<button type="button" class="bell" data-switch="switch\.monstera_notifications" aria-pressed="true"/);
  const off = render({
    "sensor.monstera_status": plant("ok", {
      notifications_entity: "switch.monstera_notifications", notifications_enabled: false,
    }),
  });
  assert.match(off, /class="bell off"[^>]*title="Notifications coupées pour cette plante : cliquer pour les activer"/);
  assert.doesNotMatch(render({ "sensor.monstera_status": plant() }), /<button type="button" class="bell/);
});
