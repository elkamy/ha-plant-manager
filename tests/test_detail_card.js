const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

class FakeHTMLElement {
  querySelectorAll() { return []; }
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

function plant(state = "OK", attributes = {}) {
  return {
    entity_id: "sensor.monstera_status",
    state,
    attributes: { plant_manager: true, plant_name: "Monstera", moisture: 54,
      low_threshold: 30, high_threshold: 75, battery: 82,
      battery_low_threshold: 25, ...attributes },
  };
}

function render(states, config = { entity: "sensor.monstera_status" }) {
  const card = new DetailCard();
  card.setConfig(config);
  card.hass = { states };
  return card.innerHTML;
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
