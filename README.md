# Plant Manager

Intégration personnalisée Home Assistant pour gérer des plantes d'intérieur : capteurs d'humidité, état d'arrosage, niveau de batterie et notifications.

## Fonctionnalités

- Ajouter chaque plante manuellement via l'interface de configuration.
- Sélectionner son capteur d'humidité et, facultativement, son capteur de batterie.
- Configurer un seuil d'arrosage, un seuil d'humidité élevée, un seuil de batterie faible, les services de notification et un délai.
- Créer un capteur de statut par plante.
- Afficher toutes les plantes configurées dans une carte Lovelace.
- Envoyer une notification lorsque l'humidité passe sous le seuil d'arrosage, avec une seule notification par épisode de sol sec.
- Envoyer une notification lorsque la batterie passe sous le seuil configuré (25 % par défaut).
- Éviter les notifications de batterie répétées tant que le niveau reste bas. L'alerte se réarme lorsque la batterie remonte à 5 points au-dessus du seuil (30 % par défaut).

## Configuration des notifications

Dans les options de chaque plante, sélectionnez un ou plusieurs services notify et définissez le délai avant l'envoi. Le délai est partagé entre les notifications d'arrosage et de batterie.

Le seuil de batterie faible est configurable dans les options de chaque plante. Par défaut, l'alerte se déclenche sous 25 % et se réarme à partir de 30 %. Les valeurs unknown, unavailable et non numériques sont ignorées.

La notification d'arrosage se déclenche au passage du seuil vers le bas, puis vérifie à nouveau l'humidité après le délai configuré. Une seule notification est envoyée pendant un épisode de sol sec. L'alerte peut se déclencher à nouveau lorsque l'humidité revient au seuil configuré ou au-dessus, puis repasse en dessous.

Les seuils d'humidité sont génériques : adaptez-les aux besoins de chaque plante. Les valeurs du capteur de batterie doivent être exprimées en pourcentage.

## Installation

1. Installez Plant Manager via HACS ou copiez custom_components/plant_manager dans config/custom_components/plant_manager.
2. Redémarrez Home Assistant.
3. Ouvrez Paramètres → Appareils et services → Ajouter une intégration et recherchez Plant Manager.
4. Ajoutez chaque plante séparément.
5. Ouvrez les options de chaque plante pour définir les seuils et les services de notification.

## Ajouter la carte Lovelace

1. Copiez www/plant-manager-card.js dans le dossier config/www/.
2. Dans Paramètres → Tableaux de bord → Ressources, ajoutez /local/plant-manager-card.js avec le type JavaScript Module.
3. Ajoutez une carte manuelle avec :

```yaml
type: custom:plant-manager-card
title: Mes plantes
sort_by: status # name (par défaut), moisture ou status
show_images: true
show_battery: true
```

Options de la carte :
- `sort_by: name` : tri alphabétique (par défaut).
- `sort_by: moisture` : humidité croissante, les valeurs indisponibles en dernier.
- `sort_by: status` : plantes à arroser en premier, puis très humides, en bonne santé et indisponibles.
- `show_images: false` : masque les photos personnalisées.
- `show_battery: false` : masque les indicateurs de batterie.

La carte détecte les capteurs de statut créés par l'intégration.

## Publication HACS

Le dépôt est prévu pour être ajouté comme dépôt personnalisé HACS de catégorie Integration. Avant une publication stable :

1. Vérifiez le code dans une instance de développement Home Assistant.
2. Créez un tag de version et une release GitHub après validation.
3. Dans HACS, ajoutez l'URL du dépôt comme dépôt personnalisé de catégorie Integration.
4. Pour une distribution plus aboutie, publiez la carte séparément comme plugin de tableau de bord HACS de type Dashboard ou conservez les instructions de ressource manuelle ci-dessus.

## Notes

- Le service de notification doit être choisi dans les options de chaque plante, par exemple notify.mobile_app_votre_telephone.
- Testez les changements dans une instance de développement Home Assistant avant de les utiliser au quotidien.
