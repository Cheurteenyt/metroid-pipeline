# Politique de branches — metroid-pipeline

**Statut :** en vigueur depuis 2026-09-03
**Auteur :** GLM 5.3 Flash (`[GLM-5.3-Flash]`)
**Portée :** tout travail de développement destiné à `main`

---

## 1. Règle d'or

`main` est la **seule branche persistante** du dépôt GitHub.

Pendant le travail, une branche temporaire est autorisée. À la fin de chaque
tâche, il ne doit rester que `main` :

```text
GitHub
└── main
```

Aucune branche morte, aucune branche oubliée, aucune PR ouverte résiduelle.

---

## 2. Cycle de travail obligatoire

```text
START
 |
 |-- git fetch --all --prune
 |-- git ls-remote --heads origin          (inspecter les branches existantes)
 |-- main à jour
 |-- créer UNE branche : automation/glm-5.3-flash/<task-id>
 |-- modifier
 |-- tests
 |-- push GitHub (sur la branche de travail uniquement)
 |-- PR GitHub (titre préfixé [GLM-5.3-Flash], résumé, fichiers, tests, impact)
 |-- revue du diff + checks CI
 |-- merge (no-ff)
 |-- suppression de la branche
 |-- git fetch --all --prune
 |-- vérifier : branches distantes == {main}
END
```

Une tâche = une seule branche de travail. En cas d'échec, on corrige **sur la
même branche** : jamais `fix`, `fix2`, `fix-final`.

---

## 3. Automatisation — `.github/workflows/branch-pr.yml`

Le workflow `Branch PR Automation (GLM 5.3 Flash)` couvre le namespace
`automation/glm-5.3-flash/**` (branches de travail GLM **et** branches
`write-*` créées par le write relay) :

1. à chaque `push` sur une branche du namespace (hors `main`) : création de la
   PR vers `main` (ou réutilisation de la PR ouverte existante) ;
2. attente des checks externes (fail-closed : tout check en échec ⇒ **pas de
   merge**, la PR reste ouverte pour traitement contrôlé) ;
3. merge sans fast-forward (les commits `[GLM-5.3-Flash]` gardent leur
   identité dans l'historique de `main`) ;
4. suppression immédiate de la branche distante ;
5. rapport final : `git ls-remote --heads origin`.

Le workflow est **un véhicule** : il ne modifie aucun script-porte du write
relay, aucun schéma de preuve (`github-write-request/v1`,
`github-write-proof/v1`), et ne s'applique à aucun autre namespace
(`hardening/**`, branches Qwen/GPT — traitement manuel audité).

---

## 4. Interdictions

- **Push direct sur `main`** pour le travail ordinaire (exception : récupération
  d'urgence explicitement demandée par GPT-5.6 ou l'opérateur).
- **Force-push** sur `main` (interdiction absolue) et sur les branches
  temporaires (à éviter).
- Branches jetables : `tmp`, `tmp2`, `debug`, `fix-final`, `fix-final-2`,
  `test-branch-1`…
- **Suppression aveugle** d'une branche (voir §5).
- Considérer le problème résolu parce que la branche a disparu localement :
  le critère final est **distant** — `git ls-remote --heads origin`.

---

## 5. Préservation du travail des autres modèles

Avant toute suppression de branche, auditer :

```text
SHA du head / auteur / date / commits uniques / fichiers / contenu
→ déjà dans main ?  (git cherry, git patch-id, git merge-base)
   ├── oui                 → classification A : supprimer la ref (sans perte,
   │                         les commits restent atteignables depuis main)
   ├── utile non fusionné  → classification B : intégrer par PR, puis supprimer
   ├── obsolète            → classification C : documenter, puis supprimer
   └── ambigu              → classification D : inspecter avant décision
```

Une branche portant du travail `[qwen3.8-max]`, `[GLM-5.2]` ou `[GPT-5.6]`
n'est jamais supprimée sans cette matrice documentée. On préserve le travail
utile ; on ne supprime que le véhicule Git devenu inutile. Jamais de
duplication : si un correctif est déjà intégré (merge, cherry-pick, rebase
historique), ne pas le recopier une seconde fois.

---

## 6. Vérification de fin de tâche

```bash
git fetch --all --prune
git ls-remote --heads origin
```

`refs/heads/main` doit être la **seule** référence de branche distante. Le
contrôle de fin de tâche rapporte séparément :

- `branch cleanliness` : branches distantes == `{main}` ;
- `CI health` : état des workflows (smoke, exact, regression, regression-test) ;
- `write relay health` : registre `requests/completed|failed/write/` + verdicts
  `[bot] write-relay` sur `main`.

Les tags ne sont pas des branches : conservés s'ils marquent une release ou
une provenance, jamais créés pour « cacher » une branche supprimée.
