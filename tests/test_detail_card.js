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
  const html = render({ "sensor.monstera_status": plant("indisponible", { moisture: 150 }) });
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
