# Architecture du Runner de Verification

## Vue d'ensemble

Ce depot GitHub fournit une infrastructure de verification automatisee pour des projets de decompilation heberges sur GitLab. Le runner s'execute via GitHub Actions et produit des preuves immuables de compilation et de tests.

## Principes de conception

1. **Separation stricte des responsabilites**
   - GitHub Actions = infrastructure d'execution uniquement
   - GitLab = source de verite (code, binaires, documentation projet)
   - Aucune donnee projet ne transite par GitHub

2. **Reproductibilite**
   - Chaque verification cible un SHA GitLab exact (40 caracteres)
   - Environnement deterministe (dependances epinglees)
   - Preuves horodatees et hachees

3. **Tracabilite**
   - Chaque requete genere un artifact unique
   - Cycle de vie des requetes (pending -> completed/failed)
   - Journal technique maintenu dans docs/DEVLOG.md

## Composants

### Workflows GitHub Actions

- metroid-smoke.yml : Tests de fumee (Python pur, ~2 min)
- metroid-exact.yml : Compilation et analyse (LLVM 17 + AArch64, ~3-5 min)

### Scripts auxiliaires

- scripts/parse_request.py : Validation des requetes JSON
- scripts/generate_run_json.py : Generation des preuves
- scripts/check_status.py : Verification finale

### Structure des requetes

- requests/smoke/*.json : Requetes smoke (tests Python)
- requests/exact/*.json : Requetes exact (compilation LLVM)
- requests/completed/ : Requetes terminees (tous profils)

## Flux de verification

1. Creation de requete : JSON dans requests/<profil>/
2. Declenchement : Push vers GitHub -> workflow declenche
3. Clonage : GitLab clone au SHA specifie via HTTPS
4. Execution : Compilation et/ou tests
5. Preuve : Artifact uploade avec run.json + logs
6. Archivage : Requete deplacee vers completed/

## Securite

- Tokens stockes dans GitHub Secrets (jamais dans le code)
- Permissions minimales (lecture seule sur GitLab, write sur GitHub)
- Aucune ecriture vers GitLab depuis le runner
- Rotation des tokens documentee dans docs/OPERATIONS.md

## Limites connues

Voir docs/OPERATIONS.md pour les limites des plateformes et strategies de contournement.
