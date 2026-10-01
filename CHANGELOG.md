# Journal des modifications

## [0.2.4] — 2026-10-01

### Ajouté
- Résumé visuel des plantes affichées, réparties par état : à arroser, très humides, en forme et indisponibles.
- Tri de la carte Lovelace par nom, humidité croissante ou statut de la plante.
- Filtres Lovelace pour afficher toutes les plantes, uniquement celles à arroser ou celles nécessitant une attention particulière.
- Option d'affichage compact pour réduire la hauteur de la carte.
- Les lignes de plantes ouvrent leurs détails Home Assistant au toucher ou au clavier ; cette action peut être désactivée.
- Options pour masquer les photos personnalisées et les indicateurs de batterie.
- Tests automatisés couvrant les nouveaux modes de tri et d'affichage.

### Fiabilité
- Alertes d'arrosage et de batterie dédupliquées et vérifiées après le délai configuré.
- Gestion renforcée des valeurs de capteurs invalides ou indisponibles ; les mesures d'humidité et de batterie hors plage 0–100 % sont ignorées.
- Le capteur de statut considère également une humidité hors plage comme indisponible, en cohérence avec les alertes.
- Tests supplémentaires sur le réarmement des alertes de batterie après récupération.
- Carte Lovelace plus robuste face aux valeurs d'humidité et de batterie invalides, aux noms HTML et aux URL d'image non sûres.
- Les valeurs d'humidité hors plage 0–100 % ne sont pas utilisées pour remplir la jauge de la carte.
- Amélioration de l'accessibilité : une humidité indisponible n'est plus annoncée comme une valeur de 0 %.
- Validation automatisée Python et JavaScript dans GitHub Actions.

### Documentation
- Documentation des options de la carte et des paramètres de notification.

> Avant de publier cette version, valider le comportement dans une instance de développement Home Assistant.
