# Runner de Verification pour Projets de Decompilation

Infrastructure de verification automatisee via GitHub Actions pour des projets de decompilation heberges sur GitLab.

## Vue d'ensemble

Ce depot fournit un **runner externe** qui :
- Clone un projet GitLab a un SHA specifique
- Execute des tests et/ou des compilations
- Produit des preuves immuables (artifacts)
- Archive les requetes traitees

**Important** : Ce depot ne contient AUCUNE donnee projet (code, binaires, metriques). Toute la connaissance projet reside sur GitLab.

## Documentation

### Pour commencer

1. **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** : Principes de conception et vue d'ensemble
2. **[WORKFLOWS.md](docs/WORKFLOWS.md)** : Comment utiliser les workflows smoke et exact
3. **[OPERATIONS.md](docs/OPERATIONS.md)** : Configuration, tokens, troubleshooting
4. **[DEVLOG.md](docs/DEVLOG.md)** : Journal technique (problemes rencontres et solutions)
5. **[PROOF_CONTRACT.md](docs/PROOF_CONTRACT.md)** : Schema des preuves generees

### Workflows disponibles

#### Smoke Tests (metroid-smoke.yml)
Tests de fumee rapides pour valider les scripts Python sans compilation LLVM.
- Duree : environ 2 minutes
- Declenchement : Push dans requests/smoke/
- [Documentation detaillee](docs/WORKFLOWS.md#workflow-smoke-metroid-smokeyml)

#### Exact Verification (metroid-exact.yml)
Compilation et analyse structurelle de fichiers C++ avec LLVM 17 + AArch64.
- Duree : environ 3-5 minutes
- Declenchement : Push dans requests/exact/
- [Documentation detaillee](docs/WORKFLOWS.md#workflow-exact-metroid-exactyml)

## Utilisation rapide

### Creer une requete smoke

Ecrire le fichier requests/smoke/smoke-0001.json avec le format JSON documente dans WORKFLOWS.md, puis commit et push.

Le workflow se declenche automatiquement. Apres environ 2 minutes, consulter l'artifact proof_smoke-0001.

### Creer une requete exact

Ecrire le fichier requests/exact/exact-0001.json avec le format JSON documente dans WORKFLOWS.md, puis commit et push.

Apres environ 3-5 minutes, consulter l'artifact proof_exact-0001.

## Structure du depot

- .github/workflows/ : Workflows GitHub Actions (metroid-smoke.yml, metroid-exact.yml)
- requests/ : Requetes de verification (smoke/, exact/, completed/)
- scripts/ : Scripts auxiliaires (parse_request.py, generate_run_json.py, check_status.py)
- docs/ : Documentation (ARCHITECTURE.md, WORKFLOWS.md, OPERATIONS.md, DEVLOG.md, PROOF_CONTRACT.md)

## Securite

- **Tokens** : Stockes dans GitHub Secrets, jamais dans le code
- **Permissions** : Minimales (lecture GitLab, ecriture GitHub)
- **Isolation** : Aucune donnee projet ne transite par ce depot
- **Rotation** : Documentee dans OPERATIONS.md

## Limites et contraintes

Voir OPERATIONS.md pour les details sur :
- Limites GitHub Actions et GitLab CI/CD
- Procedures de rotation des tokens
- Troubleshooting des problemes courants

## Support

1. Consulter la documentation dans docs/
2. Consulter le journal technique (DEVLOG.md) pour les problemes connus
3. Creer une issue dans ce depot

## Licence

Infrastructure de verification. Le projet source (sur GitLab) a sa propre licence.
