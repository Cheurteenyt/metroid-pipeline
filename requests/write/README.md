# Write Relay Requests (GitHub-side entry point)

Ce répertoire est le point d'entrée **historique** du write relay : un fichier
JSON `github-write-request/v1` committé ici (sur `main`) déclenche le workflow
`Metroid Write Relay (v1.1)`.

**Point d'entrée recommandé (agents sans accès GitHub — ex. GPT 5.6)** :
déposer la demande côté GitLab, dans
`gitlab.com/cheurteen/metroid` → `requests/github-write/<request_id>.json`.
Le relay la récupère par polling (≤ 15 min) ou via
`workflow_dispatch(gitlab_request_id=...)`.

Référence complète : `docs/WRITE_RELAY_CONTRACT.md`.
Exemple de requête : `docs/samples/write-request-sample.json`.

Cycle de vie : une demande traitée est déplacée par le relay vers
`requests/completed/write/` (PASS) ou `requests/failed/write/` (sinon) —
c'est aussi le registre anti-replay : un `request_id` déjà traité est rejeté.
