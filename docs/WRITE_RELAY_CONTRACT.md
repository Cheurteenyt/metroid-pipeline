# Contrat du Write Relay (v1.1)

Canal de mutation contrôlé : **GitLab (source de vérité) → GitHub Actions (agent
d'écriture contrôlé)**. Un modèle autorisé peut demander une modification de
`Cheurteenyt/metroid-pipeline` sans posséder lui-même le droit `push` : GitHub
Actions valide la demande, crée une branche d'automation, applique le patch,
exécute les tests, produit une preuve, puis — seulement après succès — commit
et push la branche. Le merge dans `main` reste manuel (humain).

## 1. Architecture

```
GPT 5.6 / qwen3.8-max / GLM 5.2 (ou humain)
   |
   | dépose requests/github-write/<id>.json        (GitLab, append-only)
   v
GitLab cheurteen/metroid  (source de vérité des demandes)
   |
   | ① push GitHub sur requests/write/*.json       (chemin historique)
   | ② polling cron 15 min / ③ dispatch par id     (transport GitLab)
   v
GitHub Actions (metroid-write-relay.yml, v1.1)
   |
   | validation déclarative -> anti-replay -> base_sha
   | branche automation/<model>/<id> créée À base_sha
   | application patch -> tests porte -> preuve
   | commit + push branche (seulement si tout est vert)
   | registre completed|failed + état GitLab sur main ([bot])
   v
branche automation/* + proof/github-write/<id>/run.json (artifact)
+ requests/completed|failed/write/<id>.json (registre sur main)
```

Règles d'or conservées du système existant :

* `discovery != acceptance`, `heuristic != proof`, `semantic != exact`
* `"patch appliqué" != "patch correct"` — la preuve n'affirme que ce qu'elle
  démontre.
* Le runner n'écrit **jamais** dans GitLab (cf. `ARCHITECTURE.md`).

## 2. Entrées (transports)

| # | Transport | Déclencheur | Qui |
|---|-----------|-------------|-----|
| 1 | push GitHub `requests/write/*.json` sur `main` | automatique | humain / agent avec accès GitHub |
| 2 | `workflow_dispatch` + `request_file` (chemin GitHub) | manuel | humain |
| 3 | `workflow_dispatch` + `gitlab_request_id` | manuel | humain (fetch explicite) |
| 4 | polling cron toutes les 15 min | automatique | GitLab → GitHub, autonome |

**Convention GitLab** : les demandes vivent dans
`gitlab.com/cheurteen/metroid` → `requests/github-write/*.json`
(append-only, jamais supprimées — journal immuable). La sélection de polling
prend la première demande (tri lexicographique) non présente dans le registre
GitHub. Authentification : secret GitHub `GITLAB_SSH_KEY_B64` (clé de déploiement
Ed25519, lecture seule), repli `GITLAB_TOKEN`, repli HTTPS anonyme.

## 3. Format de requête `github-write-request/v1`

Fichier JSON (≤ 100 Ko) :

```json
{
  "schema": "github-write-request/v1",
  "request_id": "write-2026-09-03-demo",
  "target_repo": "Cheurteenyt/metroid-pipeline",
  "target_branch": "advisory — ignorée, la branche est dérivée",
  "base_sha": "<40 hex — HEAD GitHub main au moment de la rédaction>",
  "author_model": "GPT 5.6",
  "operation": "create",
  "files": [
    {"path": "docs/example.md", "patch": "# contenu complet du fichier\n"}
  ],
  "commit_message": "[GPT-5.6] add example doc",
  "required_checks": ["python-tests"]
}
```

Le `patch` est le **contenu complet** du fichier cible (pas un diff unifié).

## 4. Règles de validation (scripts/validate_write_request.py)

1. `schema` exactement `github-write-request/v1`.
2. `request_id` : `[a-zA-Z0-9_-]{1,64}`, non vide, `unknown` réservé.
3. `target_repo` exactement `Cheurteenyt/metroid-pipeline`.
4. `author_model` ∈ `GPT 5.6` | `qwen3.8-max` | `GLM 5.2`.
5. `base_sha` : exactement 40 hex minuscules ; existence + correspondance
   vérifiées par le workflow (§6).
6. `operation` ∈ `patch` | `create` | `delete` :
   * `patch`  : le fichier DOIT exister (remplacement du contenu) ;
   * `create` : le fichier NE DOIT PAS exister ;
   * `delete` : le fichier DOIT exister et `patch` être `""`.
7. `files` : 1 à 10 fichiers ; chemins normalisés puis vérifiés :
   * allowlist stricte de caractères `[A-Za-z0-9._/-]` (pas d'espaces,
     backslashes, deux-points, caractères de contrôle) ;
   * refus des chemins absolus, `..` (y compris nu ou imbriqué), doublons ;
   * **denylist** : `.github/**`, `.git/**`, `.gitmodules`, `.gitlab-ci.yml`,
     `secrets/**`, `proof/**`, `requests/**` (registre & cycle de vie),
     `.env*`, `*.pem`, `*.key`, et les scripts-portes du pipeline
     (`validate_write_request.py`, `apply_write_patch.py`,
     `generate_write_proof.py`, `test_write_validation.py`,
     `fetch_gitlab_write_requests.py`, `check_status.py`, `parse_request.py`,
     `generate_run_json.py`, `parse_regression_request.py`,
     `generate_regression_run_json.py`, `regression_compare.py`,
     `test_regression_negative.py`).
     **Le relay ne peut pas affaiblir ses propres gardes-fous** ; les workflows
     ne sont modifiables que par commit humain direct.
8. Tailles : ≤ 10 000 octets/fichier, ≤ 50 000 octets total,
   ≤ 2 000 lignes total ; pas d'octet NUL.
9. `commit_message` : doit commencer par le préfixe du modèle
   (`[GPT-5.6]` / `[qwen3.8-max]` / `[GLM-5.2]`), avoir un sujet, puis est
   normalisé sur une ligne (le workflow l'utilise tel quel — jamais brut).
10. `required_checks` : uniquement `python-tests` (rejet fail-closed de toute
    valeur inconnue — une exigence non exécutable est un rejet, pas un
    avertissement).

## 5. Anti-replay (ÉTAPE 8)

Trois couches indépendantes :

1. **Registre** : `requests/completed/write/<id>.json` (PASS) ou
   `requests/failed/write/<id>.json` (échec/rejet) committés sur `main` par le
   relay (`[bot] write-relay <id>: <STATUS>`). Toute demande dont l'id figure
   dans le registre est rejetée (`anti_replay_replayed_request`) — une requête
   terminée ne peut jamais être re-jouée ; un nouvel essai = nouveau `request_id`.
2. **Branche** : `git ls-remote --heads origin automation/<model>/<id>` — si la
   branche existe déjà, rejet (`anti_replay_branch_exists`), y compris si le
   registre a perdu une course.
3. **Concurrence** : groupe global `metroid-write-relay`,
   `cancel-in-progress: false` — les runs se sérialisent ; la vérification
   registre à l'intérieur du run referme la fenêtre de course.

Le polling saute en plus toute demande déjà connue du registre (silence, pas
d'échec) et maintient `requests/state/gitlab-head.json` pour n'interroger
GitLab (ls-remote bon marché) que lorsque son `main` a avancé.

## 6. Sémantique `base_sha` (ÉTAPE 4 — FINITE par transport)

La branche d'automation est **créée à** `base_sha`
(`git checkout -b <branche> <base_sha>`) : le HEAD de la branche cible
correspond donc exactement au `base_sha` déclaré.

| Transport | Vérification additionnelle | Échec |
|---|---|---|
| push GitHub | `parent(commit porteur) == base_sha` | `base_sha_mismatch_push_parent` |
| dispatch fichier / GitLab | `origin/main == base_sha` au moment du run | `base_sha_mismatch_main_moved` |
| tous | `git cat-file -e base_sha^{commit}` | `base_sha_not_found` |

En cas de divergence : `REJECTED`, **aucun push**, aucun mutation. L'auteur
ré-émet une demande avec un `base_sha` frais (nouveau `request_id`).

## 7. Cycle d'exécution (ÉTAPE 4)

1. checkout complet (`fetch-depth: 0`) ;
2. re-vérification `base_sha` (§6) ;
3. création de la branche `automation/<model-slug>/<request_id>` À `base_sha` ;
4. application stricte des opérations autorisées
   (`scripts/apply_write_patch.py`) — refus des symlinks sortants du dépôt,
   des cibles manquantes/existantes selon l'opération ;
5. **vérification post-application** : `git status --porcelain` doit montrer
   exactement les chemins demandés (rien d'autre) ;
6. tests porte : tous `scripts/test_*.py` (pytest, convention standalone si
   « no tests collected »), dépendances épinglées
   (`capstone==5.0.1`, `pytest==8.3.2`) ;
7. preuve ; 8. commit (`[bot]`, message normalisé) ; 9. push branche.

**Fail-closed** : tests FAIL → aucun push. Validation UNKNOWN → aucun push.
Erreur d'application → aucun push. Le job passe en rouge sur tout rejet/échec
(visibility-first).

## 8. Preuve `github-write-proof/v1` (ÉTAPES 5 & 9)

`proof/github-write/<request_id>/run.json` (artifact GitHub, rétention 30 j) :

```json
{
  "schema": "github-write-proof/v1",
  "profile": "write",
  "request_id": "...",
  "author_model": "GPT 5.6",
  "repository": "Cheurteenyt/metroid-pipeline",
  "source": "gitlab|github-push|github-file",
  "source_repo": "gitlab.com/cheurteen/metroid",
  "requested_source_commit": "<head GitLab au fetch>",
  "request_file_sha256": "...",
  "base_sha": "...", "actual_base_sha": "...", "result_sha": "...",
  "branch": "automation/gpt-5.6/...",
  "operation": "create",
  "files_requested": 1,
  "files_changed": ["docs/example.md"],
  "required_checks": ["python-tests"],
  "checks_executed": ["python-tests"],
  "tests": {"expected": 2, "executed": 2, "passed": 2, "failed": 0},
  "push_confirmed": true,
  "stage": "pushed",
  "status": "PASS",
  "fail_reason": "",
  "timestamp_utc": "2026-09-03T...Z"
}
```

* `stage` (états explicites, monotones) : `rejected → validated → branched →
  applied → tested → committed → pushed`.
* `status` :
  * **PASS** — uniquement si : stage `pushed` ET `push_confirmed` ET
    `base_sha == actual_base_sha` ET `files_changed == files_requested > 0` ET
    `tests.expected > 0`, `executed == expected`, `failed == 0`, ET
    `python-tests` exécuté s'il est exigé.
  * **REJECTED** — refusé avant toute mutation (validation, anti-replay,
    base_sha). Preuve générée quand même, avec `request_id` si extrait.
  * **FAIL** — arrêté après acceptation (branche/apply/tests/commit/push).
  * **UNKNOWN** — données incohérentes ou stage non canonique (fail-closed).
* PASS est **impossible** si : requête absente, SHA incorrect, validation
  partielle, test attendu non exécuté, test échoué, commit absent, push non
  confirmé. `tests_expected == 0 → jamais PASS` (règle maison
  `PROOF_CONTRACT.md`).
* Vérification finale : `scripts/check_status.py` (profil `write`) rejoue ces
  invariants — un seul système de validation, pas de duplication.

`PASS` ne signifie PAS : patch correct, décompilation vérifiée, ou prêt à
merger. Il signifie uniquement : appliqué + testé + poussé sur la branche
d'automation.

## 9. Registre et cycle de vie

| Sortie | Emplacement sur `main` |
|---|---|
| PASS | `requests/completed/write/<id>.json` |
| FAIL / REJECTED | `requests/failed/write/<id>.json` |
| État GitLab | `requests/state/gitlab-head.json` |

Le registre est **append-only** (l'archivage retire la demande de
`requests/write/`) ; les commits de registre `[bot]` ne déclenchent pas le
relay (les suppressions sont exclues du détection `--diff-filter=ACMR`).

## 10. Procédure de déclenchement depuis GitLab (résumé opérationnel)

1. Lire le HEAD GitHub `main` (API publique `GET /repos/Cheurteenyt/
   metroid-pipeline/commits/main` ou dernier registre) → `base_sha`.
2. Écrire `requests/github-write/<request_id>.json` sur GitLab `main`
   (schéma §3).
3. Attendre le poll (≤ 15 min) ou demander un `workflow_dispatch
   (gitlab_request_id=...)`.
4. Lire le résultat : branche `automation/<model>/<id>` sur GitHub, artifact
   `write-proof-<id>`, registre sur `main`.

## 11. Limites connues et risques résiduels

* **Déploiement du relay lui-même** : modifier `.github/workflows/` exige un
  commit humain direct sur `main` — le relay ne peut pas se mettre à jour
  (par conception).
* **Requête push-side non identifiable** (JSON cassé) : rejetée et prouvée
  (`unidentified-<run_id>`) mais non enregistrable au registre (pas d'id
  fiable) ; le fichier reste sur `main` jusqu'à nettoyage humain.
* **Merge manuel** : la branche d'automation n'est pas mergée automatiquement
  (v1 : `GPT request → branche + preuve`) ; la revue humaine reste le verrou
  final.
* **Tests porte** : les nouveaux fichiers `scripts/test_*.py` peuvent être
  ajoutés via le relay (bruit possible) mais jamais les fichiers-portes
  existants (denylist).
* **Secrets** : `GITLAB_SSH_KEY_B64` est une clé de déploiement en lecture
  seule ; si elle est compromise, rotation côté GitLab et mise à jour du
  secret GitHub. La clé privée partagée dans un canal de chat pendant
  l'audit doit être considérée comme compromise et révoquée.
* **Courses registre** : si le push du registre échoue (course sur `main`),
  la demande n'est pas enregistrée ; le replay suivant est alors stoppé par
  la couche branche (n° 2) puis re-registré.
* Horloge/fuseau : `timestamp_utc` en UTC ISO-8601 ; dérivé de l'horloge du
  runner (non signée).
