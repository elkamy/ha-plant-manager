const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

class FakeHTMLElement {}

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

function renderCard(states, config = {}) {
  const card = new PlantManagerCard();
  card.setConfig(config);
  card.hass = { states };
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
  assert.match(html, /aria-valuenow="0"/);
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
  assert.match(html, /2 plantes suivies/);
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
