# Contribuer à Plant Manager

Merci de contribuer à Plant Manager !

## Signaler un bug

Avant d'ouvrir une issue, vérifiez si le problème a déjà été signalé. Pour faciliter le diagnostic, indiquez :

- la version de Home Assistant ;
- la version de Plant Manager ;
- la méthode d'installation (HACS ou manuelle) ;
- les étapes pour reproduire le problème ;
- le résultat attendu et le résultat observé ;
- les extraits de journaux pertinents, après avoir retiré les informations privées.

Ne publiez jamais de jetons, mots de passe, URL privées, adresses IP publiques ou données personnelles.

## Proposer une fonctionnalité

Expliquez le besoin concret, le comportement attendu et, si possible, un exemple d'utilisation. Les propositions doivent rester cohérentes avec le fonctionnement de Home Assistant et la simplicité de configuration de l'intégration.

## Proposer une modification de code

1. Créez une branche dédiée à votre modification.
2. Gardez les changements ciblés et documentez tout changement visible par l'utilisateur.
3. Ajoutez ou adaptez les tests pour couvrir le comportement modifié.
4. Exécutez les vérifications locales avant d'ouvrir une pull request.

### Vérifications locales

```bash
python -m compileall -q custom_components/plant_manager tests
python -m unittest discover -s tests -v
node --check custom_components/plant_manager/www/plant-manager-card.js
node --check custom_components/plant_manager/www/plant-manager-detail-card.js
node --test tests/test_card.js tests/test_detail_card.js
python -m json.tool custom_components/plant_manager/manifest.json > /dev/null
python -m json.tool hacs.json > /dev/null
# Dans un vrai Home Assistant (pip install pytest-homeassistant-custom-component) :
python -m pytest
```

Les pull requests doivent expliquer le problème résolu, les changements apportés et la façon dont ils ont été testés.
