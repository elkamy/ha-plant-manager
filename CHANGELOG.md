# Journal des modifications

## [1.5.0] — 2026-10-04

### Ajouté
- Suivi de l'arrosage : entité « Dernier arrosage », détecté automatiquement par une hausse d'humidité confirmée (les pics isolés du capteur sont ignorés), et entité « Prochain arrosage », estimée d'après la vitesse de dessèchement.
- Bouton « Marquer comme arrosée » pour un arrosage que la sonde n'a pas vu.
- Notifications actionnables sur l'application mobile : « C'est arrosé » et « Rappeler dans 2 h ».
- Rappel facultatif tant que la plante reste sèche et qu'aucun arrosage n'a été détecté.
- Heures calmes : les notifications qui tomberaient dans la plage attendent sa fin.
- Les cartes affichent le dernier arrosage et le prochain arrosage estimé.
- Option `history_days` (1, 3 ou 7 jours) pour l'historique des deux cartes ; les historiques longs sont moyennés avant d'être tracés.
- La fiche détaillée trace les seuils d'arrosage et de sol très humide en pointillés sur la courbe.
- Les cartes et leur éditeur s'affichent en anglais lorsque l'interface de Home Assistant n'est pas en français.
- Largeur par défaut dans les tableaux de bord en sections : pleine largeur pour la liste, demi-largeur pour la fiche.
- Diagnostics téléchargeables pour chaque plante (état des alertes, mesures suivies, vitesse de dessèchement), sans les destinataires de notification.

### Maintenance
- L'état de chaque plante est conservé dans `entry.runtime_data`, comme le recommande Home Assistant.
- Nouveaux tests exécutés dans un vrai Home Assistant (`tests_ha/`, avec `pytest-homeassistant-custom-component`) pour les flux de création, d'options et de reconfiguration, les entités et les notifications, et job CI correspondant.

## [1.2.2] — 2026-10-03

### Corrigé
- Valider de nouveau la même espèce dans **Options → Espèce et photo** relance la recherche, ce qui permet d'actualiser sa photo (nécessaire pour réparer une photo enregistrée tronquée par la 1.2.0). Auparavant, le formulaire se fermait sans rien faire.

## [1.2.1] — 2026-10-03

### Corrigé
- Les photos d'espèce étaient enregistrées tronquées (seul le haut de l'image s'affichait) : le téléchargement lit désormais l'image en entier. Pour réparer une photo déjà enregistrée, mettez à jour vers la 1.2.2 puis validez de nouveau l'espèce dans **Options → Espèce et photo**.
- La recherche d'espèce n'affiche plus les résultats Wikipedia qui ne sont manifestement pas des plantes (pays, entreprises…).

## [1.2.0] — 2026-10-03

### Ajouté
- Espèce de la plante, à l'ajout ou dans les options : recherche sur Wikipedia (sans compte), avec photo et description dans la langue de Home Assistant.
- Compte OpenPlantbook facultatif, commun à toutes les plantes, pour récupérer les seuils d'humidité de l'espèce choisie.
- Envoi de sa propre photo depuis les options de la plante.
- Les photos sont stockées dans `config/plant_manager/images/` et servies par l'intégration, sans accès à Internet à l'affichage ; elles sont supprimées avec la plante.
- La fiche détaillée affiche l'espèce sous le nom de la plante.

### Modifié
- Les options d'une plante s'ouvrent sur un menu : « Seuils et notifications », « Espèce et photo » et « Compte OpenPlantbook ».

## [1.1.1] — 2026-10-03

### Corrigé
- La mise en place de la pièce des plantes existantes n'utilise plus une fonction de Home Assistant dépréciée, qui aurait empêché le chargement des plantes à partir de Home Assistant 2027.8.

## [1.1.0] — 2026-10-03

### Ajouté
- Ajout d'une plante simplifié : on choisit d'abord la sonde d'humidité, puis le nom de la plante et le capteur de batterie sont proposés à partir de son appareil.
- Profils de plante (standard, cactus et succulentes, tropicale, fougère, orchidée) qui fixent les seuils d'humidité de départ.
- Les nouvelles plantes sont placées dans la pièce de leur sonde ; les plantes existantes sans pièce y sont placées une fois lors de la mise à jour, sans modifier une pièce déjà choisie.

### Amélioré
- Les cartes ignorent une mesure isolée très éloignée de ses voisines (erreur de capteur) : elle n'est plus tracée ni signalée comme un arrosage possible.

## [1.0.1] — 2026-10-03

### Corrigé
- L'historique sur 24 h s'affiche enfin : les cartes lisaient la réponse de l'API d'historique de Home Assistant dans un mauvais format et ne trouvaient jamais aucune mesure.
- Une humidité inchangée sur 24 h est tracée en ligne plate « Stable » au lieu d'« Historique insuffisant », et la courbe s'étend jusqu'à maintenant.
- Les styles des cartes ne débordent plus sur les autres cartes du tableau de bord (rendu dans un Shadow DOM).
- Une plante déjà sèche au démarrage, après une modification des options ou à l'activation des notifications déclenche désormais une alerte.
- Une alerte déjà envoyée n'est pas renvoyée après un redémarrage, et une alerte en attente n'est plus perdue lors d'une modification des options.
- L'échec d'un destinataire de notification n'empêche plus l'envoi aux autres et est signalé dans le journal.
- Un nom de plante vide est refusé à la création.
- La fiche détaillée masque la batterie lorsque la plante n'a pas de capteur de batterie.
- La carte liste accepte la syntaxe `tap_action: { action: none }`.

### Amélioré
- Seuils réglables par curseur et délai en minutes dans les options de la plante.

## [1.0.0] — 2026-10-03

Première version stable de Plant Manager.

### ⚠️ Changements incompatibles
- Le capteur de statut publie désormais des états stables, traduits dans l'interface : `needs_water`, `ok`, `too_wet` (au lieu de `à arroser`, `OK`, `très humide`). Mettez à jour les automatisations et modèles qui comparent ces valeurs.
- Une mesure d'humidité invalide donne l'état `unknown` au lieu de rendre l'entité indisponible.
- L'attribut `battery` est désormais un nombre validé (0–100) ou `null`, et non plus l'état brut du capteur.
- Version minimale de Home Assistant relevée à 2024.11.0, nécessaire au formulaire d'options.

### Ajouté
- Nouvelle carte Lovelace `plant-manager-detail-card` pour afficher une fiche individuelle avec humidité, seuils, batterie, dernière mesure et historique sur 24 h.
- Éditeur visuel et aperçu dans le sélecteur de cartes pour les deux cartes.
- Reconfiguration d'une plante pour changer son capteur d'humidité ou de batterie sans la recréer.
- Notifications vers les entités de notification (`notify.send_message`), en plus des services `notify.*`.
- Traduction anglaise du flux de configuration, des options et des états du capteur.
- README : boutons My Home Assistant, documentation des états et attributs, tableaux d'options des cartes, guide de mise à jour et de désinstallation.

### Corrigé
- Une plante dont le capteur d'humidité est indisponible ne disparaît plus des cartes.
- Les cartes ne se redessinent plus à chaque changement d'état de Home Assistant, seulement quand une plante ou son capteur change ; l'ancienneté de la dernière mesure est rafraîchie chaque minute.
- La fiche détaillée accepte les mêmes chemins d'image que la liste (`/local/`, `/api/`, `/media/`).
- Libellé manquant pour l'option « Notifications activées ».
- Les alertes programmées n'accumulent plus de callbacks d'annulation jusqu'au rechargement de la plante.

### Maintenance
- Logique d'alerte humidité et batterie regroupée dans une fonction commune.
- Choix du capteur d'humidité via un sélecteur d'entité.
- `iot_class` passe à `calculated`, l'état étant calculé à partir d'autres entités.
- Suppression de `info.md`, qui n'est plus utilisé par HACS 2.

## [0.2.7] — 2026-10-02

### Fiabilité
- Une récupération de l'humidité pendant le délai annule l'alerte d'arrosage en attente ; si le sol redevient sec, un nouveau délai complet démarre.
- Une remontée de batterie au-dessus du seuil pendant le délai annule l'alerte batterie en attente ; une nouvelle baisse démarre un nouveau délai.
- Les anciennes mesures hors plage ou non finies ne bloquent plus le déclenchement d'une nouvelle alerte.

### Tests
- Tests de non-régression sur la récupération puis le retour à un état sec ou à une batterie faible avant l'expiration du délai.

## [0.2.6] — 2026-10-02

### Ajouté
- Option « Notifications activées » dans les options de chaque plante pour désactiver indépendamment les alertes d'arrosage et de batterie.
- Les notifications restent activées par défaut, y compris pour les plantes déjà configurées.
- Vérification du réglage juste avant l'envoi pour empêcher une notification en attente de partir après désactivation.

### Tests
- Tests de non-déclenchement lorsque les notifications sont désactivées et de suppression d'un envoi en attente.

## [0.2.5] — 2026-10-02

### Ajouté
- Chargement automatique de la carte Lovelace par l'intégration : plus besoin de copier le fichier dans `www` ni d'ajouter une ressource au tableau de bord.
- Le composant de carte évite les enregistrements en double si une ancienne ressource manuelle est encore présente.

### Documentation
- Mise à jour des instructions d'installation de la carte pour le chargement automatique.

## [0.2.4] — 2026-10-01

### Ajouté
- Conseils d'entretien contextuels selon le statut de la plante et indication de l'ancienneté de la dernière mesure.
- Avec `show_history: true`, signalement indicatif d'une hausse d'humidité d'au moins 15 points pouvant correspondre à un arrosage ; l'événement reste une estimation.
- Option `show_history: true` pour visualiser la tendance d'humidité sur 24 h, avec une indication en hausse, en baisse ou stable. Désactivée par défaut pour limiter les appels à l'historique Home Assistant.
- Résumé visuel des plantes affichées, réparties par état : à arroser, très humides, en forme et indisponibles.
- Tri de la carte Lovelace par nom, humidité croissante ou statut de la plante.
- Filtres Lovelace pour afficher toutes les plantes, uniquement celles à arroser ou celles nécessitant une attention particulière.
- Option d'affichage compact pour réduire la hauteur de la carte.
- Les lignes de plantes ouvrent leurs détails Home Assistant au toucher ou au clavier ; cette action peut être désactivée.
- Options pour masquer les photos personnalisées et les indicateurs de batterie.
- Tests automatisés couvrant les nouveaux modes de tri et d'affichage.

### Fiabilité
- L'historique d'humidité ignore les états vides, `unknown` et `unavailable` au lieu de les convertir en 0 % ; ces états interrompent aussi la détection d'une hausse pour éviter de déduire un arrosage à travers une lacune de mesure.
- La courbe d'humidité respecte les horodatages réels des mesures lorsqu'ils sont disponibles, au lieu d'espacer artificiellement toutes les mesures de façon identique.
- Alertes d'arrosage et de batterie dédupliquées et vérifiées après le délai configuré.
- Gestion renforcée des valeurs de capteurs invalides ou indisponibles ; les mesures d'humidité et de batterie hors plage 0–100 % sont ignorées.
- Le capteur de statut considère également une humidité hors plage comme indisponible, en cohérence avec les alertes.
- Tests supplémentaires sur le réarmement des alertes de batterie après récupération.
- Carte Lovelace plus robuste face aux valeurs d'humidité et de batterie invalides, aux noms HTML, aux URL d'image non sûres et aux horodatages de capteur invalides.
- Les valeurs d'humidité hors plage 0–100 % ne sont pas utilisées pour remplir la jauge de la carte.
- Amélioration de l'accessibilité : une humidité indisponible n'est plus annoncée comme une valeur de 0 %.
- Validation automatisée Python et JavaScript dans GitHub Actions.

### Documentation
- Documentation des options de la carte et des paramètres de notification.

> Avant de publier cette version, valider le comportement dans une instance de développement Home Assistant.
