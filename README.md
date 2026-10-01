# Plant Manager

Intégration personnalisée Home Assistant pour gérer des plantes d'intérieur : capteurs d'humidité, état d'arrosage, niveau de batterie et notifications.

## État du projet

Prototype initial `0.1.0`. À tester dans une instance de développement Home Assistant avant usage quotidien. Les contributions et rapports de bugs sont les bienvenus.

## Fonctionnalités

- Ajouter chaque plante manuellement via l'interface de configuration.
- Sélectionner son capteur d'humidité et, facultativement, son capteur de batterie.
- Configurer un seuil d'arrosage, un seuil d'humidité élevée, un service de notification et un délai.
- Créer un capteur de statut par plante.
- Afficher toutes les plantes configurées dans une carte Lovelace.

## Installation pour développeur

1. Copiez `custom_components/plant_manager` dans le dossier `config/custom_components/plant_manager` de Home Assistant.
2. Redémarrez Home Assistant.
3. Ouvrez **Paramètres → Appareils et services → Ajouter une intégration** et recherchez **Plant Manager**.
4. Ajoutez chaque plante séparément.
5. Ouvrez les options de l'intégration pour définir les seuils et le service de notification.

## Ajouter la carte Lovelace

1. Copiez `www/plant-manager-card.js` dans le dossier `config/www/`.
2. Dans **Paramètres → Tableaux de bord → Ressources**, ajoutez `/local/plant-manager-card.js` avec le type **JavaScript Module**.
3. Ajoutez une carte manuelle avec :

```yaml
type: custom:plant-manager-card
title: Mes plantes
```

La carte détecte les capteurs de statut créés par l'intégration.

## Publication HACS

Le dépôt est prévu pour être ajouté comme dépôt personnalisé HACS de catégorie **Integration**. Avant une publication stable :

1. Vérifiez le code dans une instance de développement Home Assistant.
2. Créez un tag de version, par exemple `v0.1.0`, et une release GitHub après validation.
3. Dans HACS, ajoutez l'URL du dépôt comme dépôt personnalisé de catégorie **Integration**.
4. Pour une distribution plus aboutie, publiez la carte séparément comme plugin de tableau de bord HACS de type **Dashboard** ou conservez les instructions de ressource manuelle ci-dessus.

## Notes

- Le service de notification doit être choisi dans les options de chaque plante, par exemple `notify.mobile_app_votre_telephone`.
- Le déclenchement de notification se fait au passage du seuil vers le bas, puis vérifie à nouveau l'humidité après le délai configuré.
- La logique des seuils est un point de départ générique : adaptez-les aux besoins de chaque plante.
- Ce prototype n'a pas encore été validé contre toutes les versions de Home Assistant. Testez-le avant de l'utiliser en production.
