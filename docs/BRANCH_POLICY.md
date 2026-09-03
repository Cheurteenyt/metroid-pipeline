# Politique de branches — metroid-pipeline

**Statut :** v2, en vigueur depuis 2026-09-03 (mission GPT 5.6 « FINAL HARDENING »)
**Auteur :** GLM 5.3 Flash (`[GLM-5.3-Flash]`)
**Portée :** TOUS les modèles contributeurs (GPT 5.6, Qwen 3.8 Max, GLM 5.2, GLM 5.3 Flash)

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

## 2. Namespaces autorisés (exclusif — tout le reste est refusé)

Tous les modèles utilisent **le même mécanisme** :

```text
automation/<model-slug>/<task-id>
```

Slugs canoniques (le workflow refuse tout autre namespace, fail-closed) :

```text
automation/gpt-5-6/*
automation/qwen-3-8-max/*
automation/glm-5-2/*
automation/glm-5-3-flash/*
```

- Le slug suit l'identité du modèle : `[GPT-5.6]`→`gpt-5-6`, `[qwen3.8-max]`→
  `qwen-3-8-max`, `[GLM-5.2]`→`glm-5-2`, `[GLM-5.3-Flash]`→`glm-5-3-flash`.
- Les branches du write relay (`automation/glm-5-3-flash/write-<request-id>`
  et équivalents pour les autres identités relay) tombent dans le même
  namespace : elles sont traitées par le même workflow.
- Historique : le namespace pointillé `automation/glm-5.3-flash/*` (utilisé
  ponctuellement le 2026-09-03 avant cette v2) est **retiré** — ses branches
  ont été fusionnées (PR #4) et supprimées ; le workflow le refuse désormais.
- Branches interdites : `tmp`, `tmp2`, `debug`, `fix`, `fix2`, `fix-final`,
  `backup`, `old`, `test-branch`, tout namespace arbitraire.
- Une tâche = une seule branche. En cas d'échec, on corrige **sur la même
  branche** (nouveau push → la même PR est mise à jour) : jamais `fix2`,
  `fix-final`.

## 3. Cycle de travail obligatoire

```text
travail → UNE branche automation/<slug>/<task-id> → push GitHub
        → PR vers main (auto-créée ou réutilisée par le workflow)
        → checks (pr-tests + checks externes éventuels)
        → merge no-ff (uniquement si tout est vert)
        → suppression de la branche
        → vérification distante : GitHub = {main}
```

Le travail ordinaire ne va **jamais** directement sur `main`.

**Exceptions explicites** (uniques, documentées ici) :

1. Les commits de **registre** du write relay (`[bot] write-relay <id>:
   STATUS`) et d'état GitLab : c'est le mécanisme de preuve anti-replay, par
   design sur `main`.
2. Récupération d'urgence explicitement demandée par l'opérateur ou GPT 5.6.

Aucun force-push sur `main` (interdiction absolue).

## 4. Automatisation — `.github/workflows/branch-pr.yml`

Workflow `Branch PR Automation (all models)` — **identique pour tous les
modèles** (plus aucun traitement manuel différencié) :

| # | Garantie | Implémentation |
|---|---|---|
| 1 | Détection du push | `on: push` hors `main` (branches-ignore) |
| 2 | Namespace autorisé | garde `case` sur les 4 slugs ; refus sinon (run rouge) |
| 3 | Branche hors `main` | garde + `branches-ignore: [main]` |
| 4 | Branche présente sur origin | `git ls-remote --exit-code` |
| 5 | PR créée **ou réutilisée** | `gh pr list --head` puis création sinon ; jamais 2 PR pour la même branche |
| 6 | PR cible `main` | vérifiée à la création ET avant merge (`baseRefName`) |
| 7 | Checks attendus | job `pr-tests` (suite du dépôt sur le head) + checks externes éventuels |
| 8 | Check en échec ⇒ pas de merge | fail-closed, PR laissée ouverte |
| 9 | Timeout ⇒ pas de merge | `WAIT_CHECKS_SECONDS=300` puis refus |
| 10 | « 0 check » ⇒ pas de merge | un head sans aucun check-run est refusé (0 check ≠ validation) |
| 11 | SHA testé = SHA mergé | `headRefOid` de la PR doit être **exactement** le SHA dont les checks viennent d'être validés, sinon STOP (anti-course) |
| 12 | Merge no-ff uniquement | `gh pr merge --merge` après toutes les gardes |
| 13 | Suppression de branche + vérification | `push --delete` puis `ls-remote --exit-code` doit échouer |
| 14 | Aucune PR ouverte résiduelle | `gh pr list --head <branche> --state open` doit être vide après merge |

Le job `pr-tests` exécute sur **chaque** head poussé :
`python3 -m compileall -q scripts/` puis
`python3 scripts/test_write_validation.py` (dépendances épinglées identiques
au relay : `capstone==5.0.1`, `pytest==8.3.2`). Les changements purement
documentaires passent par le même check — le workflow n'a pas de mode
permissif.

Le workflow est **un véhicule** : il ne modifie aucun script-porte du write
relay, aucun schéma de preuve (`github-write-request/v1`,
`github-write-proof/v1`).

## 5. Chaîne write relay → PR (aucun véhicule permanent)

```text
GitLab request → relay v1.1 → automation/<slug>/<request-id> (à base_sha)
              → push → PR vers main (workflow §4)
              → checks → merge → suppression → GitHub = {main}
```

Après un PASS du relay, la branche d'automatisation n'est plus un état
terminal : elle est automatiquement proposée en PR et, si les checks passent,
fusionnée puis supprimée.

## 6. Préservation du travail des autres modèles

Avant toute suppression de branche (hors le cycle §3 qui supprime après
merge), auditer :

```text
SHA du head / auteur / date / merge-base avec main / commits uniques /
fichiers / diff / PR associée
→ classification A (déjà intégré : suppression sûre)
          B (utile non intégré : PR d'abord, puis suppression)
          C (obsolète : documenter puis supprimer)
          D (ambigu : NE PAS supprimer avant analyse)
```

Aucune branche Qwen, GPT, GLM 5.2 ou GLM 5.3 Flash n'est supprimée sans
cette analyse. La disparition d'une branche n'est pas une preuve de sécurité :
la preuve est que son contenu utile a été intégré, que sa PR a été
correctement traitée, puis que la branche distante a réellement disparu.

## 7. Vérification de fin de tâche

```bash
git fetch --all --prune
git ls-remote --heads origin          # doit lister refs/heads/main uniquement
git ls-remote --heads origin | wc -l  # doit retourner 1
```

Plus : **0 PR ouverte** liée aux tâches terminées (les PR fermées/mergées
restent dans l'historique GitHub — ne jamais le supprimer).
