# Operations et Maintenance

## Configuration initiale

### Pre-requis
- Compte GitHub avec acces au depot
- Compte GitLab avec acces au projet source
- Tokens d'acces (voir ci-dessous)

### Tokens necessaires

#### Token GitLab (fine-grained)
- **Portee** : Projet specifique uniquement
- **Permissions** : read_repository
- **Expiration** : 90 jours (recommande)
- **Stockage** : GitHub Secret nomme GITLAB_TOKEN

**Creation** :
1. GitLab -> User Settings -> Access Tokens
2. Nom : github-runner-access
3. Expiration : 90 jours
4. Scope : read_repository uniquement
5. Creer et copier le token

**Ajout dans GitHub** :
1. GitHub -> Settings -> Secrets and variables -> Actions
2. New repository secret
3. Name : GITLAB_TOKEN
4. Value : coller le token GitLab
5. Add secret

#### Token GitHub (fine-grained)
- **Portee** : Depot metroid-pipeline uniquement
- **Permissions** : 
  - Repository permissions : Contents (Read and write)
  - Repository permissions : Metadata (Read)
  - Repository permissions : Actions (Read)
- **Stockage** : Utilise pour push depuis environnements externes

**Creation** :
1. GitHub -> Settings -> Developer settings -> Personal access tokens
2. Fine-grained tokens -> Generate new token
3. Repository access : Only select repositories -> Cheurteenyt/metroid-pipeline
4. Permissions : cocher celles listees ci-dessus
5. Generate token

## Rotation des tokens

### Quand rotater
- Expiration approchee (90 jours)
- Token potentiellement compromis
- Revue de securite periodique (recommande : tous les 90 jours)

### Procedure GitLab
1. Creer un nouveau token avec memes permissions
2. Mettre a jour le secret GitHub GITLAB_TOKEN
3. Tester avec une requete smoke
4. Revoquer l'ancien token dans GitLab

### Procedure GitHub
1. Creer un nouveau token fine-grained
2. Utiliser le nouveau token dans vos scripts/environnements
3. Revoquer l'ancien token

## Limites des plateformes

### GitHub Actions (depots publics)
- **Minutes** : Illimite
- **Stockage** : 10 GB par depot
- **Jobs** : Illimite
- **Rate limit API** : 5000 requetes/heure

**Impact** : Aucun souci pour notre usage actuel.

### GitLab CI/CD (free tier)
- **Minutes** : 400 minutes/mois
- **Stockage** : 10 GiB par projet
- **Rate limit API** : 2000 requetes/minute

**Impact** : Limite pour builds LLVM lourds. Solution : utiliser GitHub Actions (illimite).

## Troubleshooting

### Workflow ne se declenche pas

**Symptome** : Push de requete mais workflow ne demarre pas

**Solutions** :
1. Verifier le chemin : doit etre requests/<profil>/*.json
2. Verifier le format JSON (utiliser un validateur en ligne)
3. Verifier que le workflow existe : .github/workflows/metroid-<profil>.yml

### Compilation echoue

**Symptome** : compile_success: false dans run.json

**Solutions** :
1. Telecharger l'artifact et consulter compile_errors.txt
2. Problemes courants :
   - Includes manquants : ajouter les #include
   - Symboles indefinis : verifier les dependances
   - Erreurs de syntaxe : corriger le code
3. Re-lancer la verification apres correction

### Requete ne se deplace pas

**Symptome** : Requete reste dans requests/<profil>/ au lieu de completed/

**Solutions** :
1. Verifier les logs du workflow pour erreurs
2. Deplacer manuellement avec git mv
3. Commit et push

### Token GitLab rejete

**Symptome** : Erreur d'authentification lors du clonage

**Solutions** :
1. Verifier que le secret GitHub s'appelle exactement GITLAB_TOKEN
2. Verifier que le token GitLab a le scope read_repository
3. Verifier que le token n'a pas expire
4. Recreer le token si necessaire

## Monitoring

### Verification du statut des workflows
- GitHub -> Actions : voir tous les runs
- Filtrer par workflow (smoke ou exact)
- Consulter les logs en cas d'echec

### Verification du cycle de vie des requetes
Compter les requetes par statut avec ls et wc

### Verification des artifacts
- Chaque run genere un artifact proof-<request_id>
- Retention : 90 jours (configurable dans le workflow)
- Telechargeables depuis l'interface GitHub

## Bonnes pratiques

1. **Nommer les requetes sequentiellement** : exact-0001, exact-0002, etc.
2. **Documenter dans la description** : expliquer ce qui est teste
3. **Utiliser des SHAs specifiques** : pas main sauf pour tests
4. **Consulter DEVLOG.md** : pour voir les problemes rencontres et resolus
5. **Archiver regulierement** : nettoyer completed/ apres analyse

## Contact et support

Pour toute question ou probleme :
1. Consulter ce document (OPERATIONS.md)
2. Consulter le journal technique (DEVLOG.md)
3. Creer une issue dans ce depot GitHub
