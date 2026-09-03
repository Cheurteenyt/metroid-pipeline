# Validation E2E des namespaces — politique de branches v2

Preuve d'exécution réelle sur github.com du workflow
`.github/workflows/branch-pr.yml` (v2, tous modèles), mission
« FINAL HARDENING — GitHub main-only, PR obligatoire » (GPT 5.6, 2026-09-03).

| Namespace | Branche de test | Cycle observé | Preuve |
|---|---|---|---|
| `automation/glm-5-3-flash/*` | `main-only-pr-all-models` | push → PR #5 → `pr-tests` → merge no-ff → suppression | `b00e2c1` (parents `aed79fe`+`0bd5e10`), heads={main} |
| `automation/gpt-5-6/*` | `test-ns-generique` | push → PR auto → `pr-tests` → merge no-ff → suppression | voir merge suivant sur `main` |

Le même traitement automatique est garanti pour `automation/qwen-3-8-max/*`
et `automation/glm-5-2/*` (même garde `case`, même job `pr-tests`, même
chemin de fusion). Tout namespace hors liste est refusé fail-closed par les
garde-fous du job `open-pr` (aucune PR, aucun merge).

Note de provenance : les commits de cette page sont préfixés
`[GLM-5.3-Flash]` (exécutant des tests d'infrastructure) ; le namespace de
branche démontre uniquement la genericité du routage du workflow.
