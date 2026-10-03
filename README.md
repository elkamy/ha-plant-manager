![Plant Manager for Home Assistant](docs/plant-manager-banner.svg)

<div align="center">

**Suivez l'humidité, les besoins en arrosage et la batterie de vos plantes d'intérieur directement dans Home Assistant.**

[![Available in HACS](https://img.shields.io/badge/Available%20in-HACS-41BDF5?logo=home-assistant&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=elkamy&repository=ha-plant-manager&category=integration)
[![Latest Release](https://img.shields.io/github/v/release/elkamy/ha-plant-manager?label=Release&logo=github)](https://github.com/elkamy/ha-plant-manager/releases)
[![Last Commit](https://img.shields.io/github/last-commit/elkamy/ha-plant-manager?label=Last%20commit)](https://github.com/elkamy/ha-plant-manager/commits/main)
[![GitHub Stars](https://img.shields.io/github/stars/elkamy/ha-plant-manager?style=social)](https://github.com/elkamy/ha-plant-manager/stargazers)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-☕-orange?logo=buymeacoffee&logoColor=white)](https://buymeacoffee.com/elkamy)
[![Validate](https://github.com/elkamy/ha-plant-manager/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/elkamy/ha-plant-manager/actions/workflows/validate.yml)
[![Hassfest](https://github.com/elkamy/ha-plant-manager/actions/workflows/hassfest.yml/badge.svg?branch=main)](https://github.com/elkamy/ha-plant-manager/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/elkamy/ha-plant-manager/actions/workflows/hacs.yml/badge.svg?branch=main)](https://github.com/elkamy/ha-plant-manager/actions/workflows/hacs.yml)

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=elkamy&repository=ha-plant-manager&category=integration)
[![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=plant_manager)

[Ouvrir les issues](https://github.com/elkamy/ha-plant-manager/issues) · [Consulter les versions](https://github.com/elkamy/ha-plant-manager/releases)

</div>

> **English summary** — Plant Manager is a Home Assistant custom integration for houseplants. Each plant combines a soil moisture sensor and an optional battery sensor into a status sensor (`needs_water`, `ok`, `too_wet`), sends watering and low-battery notifications once per episode, and ships two Lovelace cards (plant list and plant detail) with a visual editor. The configuration UI is available in English and French; the cards and notification messages are in French.

Plant Manager est une intégration personnalisée Home Assistant pour gérer des plantes d'intérieur à partir de capteurs d'humidité du sol et, facultativement, de capteurs de batterie. Elle crée un capteur de statut par plante et fournit deux cartes Lovelace dédiées.

## Fonctionnalités

- Configuration de chaque plante depuis l'interface Home Assistant, avec changement des capteurs possible après coup.
- Sélection d'un capteur d'humidité et, facultativement, d'un capteur de batterie.
- Capteur de statut par plante, utilisable dans vos automatisations.
- Alertes d'arrosage avec seuil configurable, délai et anti-répétition pendant un épisode de sol sec.
- Alertes de batterie faible avec seuil configurable et réarmement après récupération.
- Notifications vers les services `notify.*` et vers les entités de notification.
- Activation/désactivation des notifications indépendamment pour chaque plante.
- Carte Lovelace avec tri par nom, humidité ou statut ; filtres par état ; résumé visuel et mode compact.
- Fiche détaillée par plante.
- Éditeur visuel pour les deux cartes.
- Conseils d'entretien contextuels et indication de l'ancienneté de la dernière mesure.
- Historique d'humidité sur 24 heures et tendance optionnels.
- Vérifications des valeurs invalides ou indisponibles pour éviter les alertes et affichages trompeurs.

## Installation

### Avec HACS

1. Assurez-vous que [HACS](https://hacs.xyz/) est installé.
2. Cliquez sur le bouton ci-dessous, ou ouvrez HACS → Intégrations → menu ⋮ → Dépôts personnalisés et ajoutez `elkamy/ha-plant-manager` avec la catégorie **Integration**.

   [![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=elkamy&repository=ha-plant-manager&category=integration)

3. Installez **Plant Manager** puis redémarrez Home Assistant.
4. Ajoutez l'intégration avec le bouton ci-dessous, ou depuis **Paramètres → Appareils et services → Ajouter une intégration** en recherchant **Plant Manager**.

   [![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=plant_manager)

### Installation manuelle

1. Copiez le dossier `custom_components/plant_manager` dans `config/custom_components/plant_manager`.
2. Redémarrez Home Assistant.
3. Ajoutez l'intégration depuis **Paramètres → Appareils et services**.

## Configuration des plantes et des alertes

Ajoutez chaque plante depuis le flux de configuration, puis ouvrez ses options pour régler les seuils, les notifications et le délai. Pour changer le capteur d'humidité ou de batterie d'une plante existante, utilisez **Reconfigurer** dans le menu ⋮ de la plante.

- **Humidité basse** : l'alerte se déclenche au passage sous le seuil, ou au démarrage si la plante est déjà sèche. Une seule notification est envoyée pendant un épisode de sol sec, même après un redémarrage de Home Assistant ; l'humidité doit revenir au seuil ou au-dessus avant qu'un nouvel épisode puisse déclencher une alerte.
- **Batterie faible** : seuil par défaut de 25 %. L'alerte se réarme lorsque la batterie remonte à 5 points au-dessus du seuil (30 % par défaut).
- **Délai** : partagé entre les alertes d'arrosage et de batterie, configurable de 0 à 1 440 minutes.
- **Destinataires** : services `notify.*` (par exemple `notify.mobile_app_telephone`) et/ou entités de notification (envoi via `notify.send_message`). Sans destinataire, aucune alerte n'est envoyée.
- **Notifications activées** : désactive les alertes de cette plante sans modifier les autres plantes.
- Les capteurs de batterie doivent fournir un pourcentage de 0 à 100. Les états non numériques, indisponibles et hors plage sont ignorés.

Les seuils d'humidité sont génériques : adaptez-les aux besoins de chaque plante et aux caractéristiques de son capteur.

## Capteur de statut

Chaque plante crée une entité `sensor.<plante>_statut` (ou `sensor.<plante>_status` si Home Assistant est en anglais) de type énumération.

| État | Affichage | Signification |
| --- | --- | --- |
| `needs_water` | À arroser | Humidité sous le seuil d'arrosage. |
| `ok` | OK | Humidité entre les deux seuils. |
| `too_wet` | Très humide | Humidité au-dessus du seuil de sol très humide. |
| `unknown` | Inconnu | Mesure d'humidité absente, invalide ou hors plage. |

Attributs disponibles pour vos automatisations et modèles :

| Attribut | Description |
| --- | --- |
| `plant_name` | Nom de la plante. |
| `moisture` | Humidité du sol validée (0–100), ou `null`. |
| `moisture_entity` | Capteur d'humidité utilisé. |
| `battery` | Batterie validée (0–100), ou `null`. |
| `battery_entity` | Capteur de batterie utilisé, ou `null`. |
| `low_threshold`, `high_threshold` | Seuils d'humidité configurés. |
| `battery_low_threshold`, `battery_reset_threshold` | Seuil d'alerte batterie et seuil de réarmement. |
| `image_url` | Image configurée pour la plante. |
| `plant_manager` | Toujours `true` ; permet aux cartes de retrouver les plantes. |

Exemple de déclencheur d'automatisation :

```yaml
trigger:
  - platform: state
    entity_id: sensor.monstera_statut
    to: needs_water
```

## Cartes Lovelace

L'intégration enregistre automatiquement le JavaScript des cartes au démarrage. Après une mise à jour, redémarrez Home Assistant puis rechargez le tableau de bord. Une ancienne ressource manuelle `/local/plant-manager-card.js` peut être supprimée si elle est encore configurée.

Les deux cartes apparaissent dans le sélecteur de cartes (**Ajouter une carte → Plant Manager**) et se configurent avec l'éditeur visuel ou en YAML.

### Liste des plantes

```yaml
type: custom:plant-manager-card
title: Mes plantes
sort_by: status
show_images: true
show_battery: true
```

| Option | Valeurs | Par défaut | Description |
| --- | --- | --- | --- |
| `title` | texte | `Mon jardin d’intérieur` | Titre affiché en haut de la carte. |
| `sort_by` | `name`, `moisture`, `status` | `name` | Trie les plantes par nom, humidité croissante ou statut. Les humidités indisponibles sont placées en dernier. |
| `filter_by` | `all`, `needs_water`, `attention` | `all` | Affiche toutes les plantes, celles à arroser ou celles qui nécessitent une attention. |
| `show_images` | `true`, `false` | `true` | Affiche ou masque les photos personnalisées. |
| `show_battery` | `true`, `false` | `true` | Affiche ou masque les indicateurs de batterie. |
| `show_history` | `true`, `false` | `false` | Affiche la courbe et la tendance d'humidité sur 24 h. |
| `compact` | `true`, `false` | `false` | Réduit les marges et l'espacement vertical. |
| `tap_action` | `more-info`, `none` | `more-info` | Ouvre « Plus d'informations » au toucher, ou ne fait rien. La syntaxe `tap_action: { action: none }` est aussi acceptée. |

Exemple compact avec historique et filtre d'attention :

```yaml
type: custom:plant-manager-card
title: Mes plantes à surveiller
sort_by: status
filter_by: attention
show_history: true
compact: true
```

La carte peut signaler une hausse d'humidité d'au moins 15 points comme **arrosage possible (estimation)**. Ce signal n'est pas une détection certaine : un changement de capteur ou une autre cause peut produire une hausse similaire.

### Fiche détaillée d'une plante

Affiche une plante individuellement, avec son humidité, les seuils configurés, l'état de la batterie, l'ancienneté de la dernière mesure et la tendance sur 24 h.

```yaml
type: custom:plant-manager-detail-card
entity: sensor.monstera_statut
show_history: true
```

| Option | Valeurs | Par défaut | Description |
| --- | --- | --- | --- |
| `entity` | entité de statut | obligatoire | Capteur de statut de la plante à afficher. |
| `title` | texte | nom de la plante | Titre affiché sur la fiche. |
| `show_history` | `true`, `false` | `true` | Affiche ou masque l'historique sur 24 h. |

### Images

`image_url` (dans les options de la plante) accepte une URL `http(s)://` ou un chemin Home Assistant commençant par `/local/`, `/api/` ou `/media/`. Pour une image stockée dans `config/www/plantes/monstera.jpg`, utilisez `/local/plantes/monstera.jpg`.

## Mise à jour depuis une version 0.2.x

La version 1.0.0 remplace les états français du capteur de statut par des clés stables, traduites dans l'interface :

| Avant 1.0.0 | Depuis 1.0.0 |
| --- | --- |
| `à arroser` | `needs_water` |
| `OK` | `ok` |
| `très humide` | `too_wet` |
| `indisponible` (entité indisponible) | `unknown` |

Mettez à jour les automatisations, scripts et modèles qui comparent l'état du capteur à ces valeurs. Les cartes Plant Manager sont mises à jour automatiquement.

## Désinstallation

1. Supprimez les cartes Plant Manager de vos tableaux de bord.
2. Supprimez chaque plante depuis **Paramètres → Appareils et services → Plant Manager**.
3. Désinstallez Plant Manager depuis HACS (ou supprimez `config/custom_components/plant_manager`), puis redémarrez Home Assistant.

## Développement et tests

Les tests automatisés couvrent la logique d'alerte, les capteurs et le rendu des cartes.

Exécuter les tests localement :

```bash
python -m compileall -q custom_components/plant_manager tests
python -m unittest discover -s tests -v
node --check custom_components/plant_manager/www/plant-manager-card.js
node --check custom_components/plant_manager/www/plant-manager-detail-card.js
node --test tests/test_card.js tests/test_detail_card.js
```

La CI vérifie également les métadonnées JSON, HACS et Hassfest.

Pour contribuer, consultez [CONTRIBUTING.md](CONTRIBUTING.md). Pour signaler un bug ou demander une fonctionnalité, [ouvrez une issue](https://github.com/elkamy/ha-plant-manager/issues/new/choose).

## Compatibilité

- Intégration personnalisée Home Assistant.
- Version minimale déclarée : Home Assistant 2024.11.0.
- Installation et mises à jour via HACS ou manuellement.

## Licence

Distribué sous licence MIT. Consultez le fichier [LICENSE](LICENSE).
