# Journal Technique du Runner

Ce document capitalise les problemes rencontres et les solutions apportees lors du developpement et de la maintenance de l'infrastructure de verification. L'objectif est d'eviter de redecouvrir les memes problemes et d'aider les futurs mainteneurs.

## Format des entrees

Chaque entree suit le format :
- **Date** : quand le probleme a ete rencontre
- **Probleme** : description du symptome
- **Cause** : analyse de la cause racine
- **Solution** : correctif applique
- **Lecon** : ce qu'il faut retenir pour la suite

---

## 2026-09-01 : Bootstrap du runner smoke

### Probleme
Les tests smoke echouaient avec des erreurs d'import Python et des problemes de PATH.

### Cause
1. PYTHONPATH non configure correctement pour pytest
2. Certains tests etaient des scripts autonomes (pas de fonctions test_*)
3. YAML duplique entre les steps
4. Python 3.12 a supprime distutils, utilise par capstone 5.0.1

### Solution
1. Configurer PYTHONPATH avec chemin absolu : /tmp/metroid/switch/scripts
2. Ajouter fallback : si pytest retourne exit code 5, executer le script directement
3. Factoriser le YAML dans des scripts separes
4. Epingler setuptools==69.0.3 pour fournir distutils

### Lecon
- Toujours tester avec Python 3.12+ (distutils deprecated)
- Prevoir les deux modes : pytest et scripts autonomes
- Factoriser le YAML des que possible

---

## 2026-09-02 : Cycle de vie des requetes

### Probleme
Les requetes restaient dans pending/ meme apres execution reussie.

### Cause
Le workflow tentait de commit le deplacement avec GITHUB_TOKEN mais le push echouait (permissions insuffisantes).

### Solution
1. Ajouter permissions: contents: write dans le workflow
2. Utiliser git mv au lieu de mv pour que git detecte le renommage
3. Ajouter || echo "Push failed" pour ne pas bloquer le workflow si push echoue
4. Documenter le deplacement manuel en fallback

### Lecon
- Toujours verifier que GITHUB_TOKEN a les permissions necessaires
- Prevoir un fallback manuel pour les operations automatiques
- Logger les echecs de push sans bloquer le workflow

---

## 2026-09-02 : Workflow exact Phase A

### Probleme
Le workflow de compilation echouait car les chemins de fichiers etaient incorrects.

### Cause
1. Les fichiers C++ etaient dans switch/src/auto/, pas switch/src/
2. Le workflow cherchait les fichiers dans le mauvais repertoire
3. Les includes relatifs ne fonctionnaient pas

### Solution
1. Explorer la structure GitLab pour trouver les vrais chemins
2. Mettre a jour la documentation avec les bons chemins
3. Ajouter -I /tmp/metroid/switch/src dans les flags de compilation
4. Creer des requetes de test avec les vrais chemins

### Lecon
- Toujours verifier la structure reelle du repo avant de coder
- Documenter les chemins exacts dans la doc
- Tester avec des fichiers reels, pas des exemples fictifs

---

## 2026-09-02 : Token GitLab fine-grained

### Probleme
Le clonage GitLab echouait avec "Access denied" malgre un token valide.

### Cause
Le token fine-grained n'avait pas la permission Code:Download, necessaire pour le clonage HTTPS.

### Solution
1. Editer le token dans GitLab
2. Ajouter la permission Code:Download
3. Re-tester le workflow

### Lecon
- Les tokens fine-grained GitLab ont des permissions tres granulaires
- Pour le clonage, il faut Code:Download (pas juste read_repository)
- Toujours tester immediatement apres creation/modification d'un token

---

## 2026-09-02 : Reorganisation de la documentation

### Probleme
La documentation devenait difficile a naviguer avec des informations dupliquees et des donnees projet dans le repo public.

### Cause
1. Plusieurs fichiers avec des informations similaires
2. Pas de separation claire entre doc infra (publique) et doc projet (privee)
3. Pas d'index unique pour naviguer

### Solution
1. Creer une structure claire :
   - ARCHITECTURE.md : vue d'ensemble
   - WORKFLOWS.md : usage des workflows
   - OPERATIONS.md : configuration et maintenance
   - DEVLOG.md : journal technique (ce fichier)
   - PROOF_CONTRACT.md : schema des preuves (existant)
2. Supprimer les fichiers redondants
3. Documenter la separation GitHub (infra) vs GitLab (projet)

### Lecon
- Organiser la doc des le debut pour eviter la dette technique
- Separer clairement public (infra) et prive (projet)
- Maintenir un journal technique pour capitaliser l'experience

---

## Bonnes pratiques generales

### Quand ajouter une entree au DEVLOG
- Probleme non trivial (> 30 min de debug)
- Solution qui pourrait servir a d'autres
- Changement d'architecture ou de workflow
- Lecon importante a retenir

### Format recommande
Garder les entrees concises (5-10 lignes par section) et actionnables.

### Maintenance
- Relire le DEVLOG avant de commencer un nouveau developpement
- Ajouter une entree apres chaque resolution de probleme
- Archiver les vieilles entrees si le journal devient trop long (> 50 entrees)

---

## 2026-09-03 — Write relay v1.1 : trois leçons de debug (GLM 5.2)

### Bug 1 : `source` d'un env-file avec valeur non quotée
- Symptôme : les 2 premiers runs du relay échouaient à l'étape "Detect" sans raison visible.
- Cause : `AUTHOR_MODEL=GLM 5.2` (espace) non quoté dans le fichier sourcé → bash exécute `5.2` comme commande → exit 127 sous `bash -e`.
- Leçon : générer les env-files avec des valeurs quotées, ou les éviter (GITHUB_ENV + JSON normalisé). Un nom avec espace casse tout.

### Bug 2 : sémantique `base_sha` invérifiable sur le chemin push
- Symptôme : toute requête push aurait été rejetée `base_sha_mismatch`.
- Cause : le workflow comparait base_sha au HEAD du checkout = le commit porteur de la requête, SHA inconnu de l'auteur au moment de rédiger.
- Leçon : la branche d'automation se crée À `base_sha` ; en mode push on vérifie `parent(commit requête) == base_sha`. Définir la sémantique avant le code.

### Durcissement appliqué
- Anti-replay à 3 couches (registre completed/failed + ls-remote branche + concurrence globale).
- Auto-protection : denylist des scripts-portes, proof/, requests/ — le relay ne peut pas s'affaiblir.
- Transport GitLab (polling 15 min + dispatch par id) : GPT 5.6 n'a plus besoin d'écrire sur GitHub.
- Preuve `github-write-proof/v1` avec `stage` explicite et PASS impossible si un invariant manque.
