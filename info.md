![Plant Manager for Home Assistant](https://raw.githubusercontent.com/elkamy/ha-plant-manager/main/docs/plant-manager-banner.svg)

# Plant Manager

**Suivez l'humidité, les besoins en arrosage et la batterie de vos plantes d'intérieur directement dans Home Assistant.**

[![HACS custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Validate](https://github.com/elkamy/ha-plant-manager/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/elkamy/ha-plant-manager/actions/workflows/validate.yml)
[![Hassfest](https://github.com/elkamy/ha-plant-manager/actions/workflows/hassfest.yml/badge.svg?branch=main)](https://github.com/elkamy/ha-plant-manager/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/elkamy/ha-plant-manager/actions/workflows/hacs.yml/badge.svg?branch=main)](https://github.com/elkamy/ha-plant-manager/actions/workflows/hacs.yml)

[**Installer avec HACS**](https://my.home-assistant.io/redirect/hacs_repository/?owner=elkamy&repository=ha-plant-manager&category=integration) · [Documentation](https://github.com/elkamy/ha-plant-manager#readme) · [Signaler un problème](https://github.com/elkamy/ha-plant-manager/issues)

## Ce que fait Plant Manager

Plant Manager est une intégration Home Assistant pour suivre les plantes d'intérieur à partir de capteurs d'humidité du sol et, en option, de capteurs de batterie. Elle ajoute un capteur de statut par plante et une carte Lovelace dédiée.

- Alertes d'arrosage configurables, avec délai et anti-répétition.
- Alertes de batterie faible avec seuil et réarmement.
- Notifications configurables individuellement pour chaque plante.
- Carte Lovelace avec tri, filtres, résumé visuel, conseils d'entretien et mode compact.
- Historique d'humidité sur 24 heures et tendance optionnels.

## Installation rapide

1. Installez [HACS](https://hacs.xyz/) si nécessaire.
2. Ouvrez le lien **Installer avec HACS** ci-dessus, ou ajoutez `elkamy/ha-plant-manager` comme dépôt personnalisé de catégorie **Integration**.
3. Installez Plant Manager, puis redémarrez Home Assistant.
4. Dans **Paramètres → Appareils et services**, ajoutez l'intégration **Plant Manager**.
5. Configurez une plante en sélectionnant son capteur d'humidité et, si disponible, son capteur de batterie.

La carte Lovelace est servie automatiquement par l'intégration. Ajoutez une carte manuelle avec le type `custom:plant-manager-card` ; aucune ressource JavaScript supplémentaire n'est normalement nécessaire.

Consultez le [README](https://github.com/elkamy/ha-plant-manager#readme) pour les options de configuration et les détails de la carte.
