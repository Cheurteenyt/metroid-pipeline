# Guide Complet: Jetons Affinés GitLab, Limites et Opportunités

**Version**: 1.0  
**Date**: 2026-09-02  
**Auteur**: Qwen 3.8 Max

## Résumé Exécutif

### État Actuel
- **Utilisation**: Seulement 1 permission GitLab (Code:Download pour cloner)
- **Potentiel inexploité**: 24 permissions disponibles
- **Problème principal**: GitLab limité à 400 min/mois vs GitHub illimité
- **Solution**: Déplacer les workflows lourds vers GitHub Actions

### Opportunités Clés
1. **Workflow exact sur GitHub Actions** - GPT-5.6 et Qwen peuvent faire de la vérification LLVM
2. **Auto-merge après validation** - Accélérer le workflow
3. **Création automatique d'issues** - Meilleure organisation

---

## 1. Permissions GitLab Affinées Disponibles

### 1.1 Opérations Git (Base)

| Resource | Permission | Description | Utilisé | Usage Potentiel |
|----------|-----------|-------------|---------|-----------------|
| **Code** | **Download** | Cloner/pull repository + LFS + archives | ✅ Oui | Le runner clone le repo |
| Code | Push | Push vers repository | ❌ Non | Non nécessaire (runner read-only) |
| Wiki | Read | Lire wiki du projet | ❌ Non | Documenter le projet |
| Snippet | Read | Lire snippets | ❌ Non | Partager du code |

### 1.2 Pipeline et CI/CD

| Resource | Permission | Description | Utilisé | Usage Potentiel |
|----------|-----------|-------------|---------|-----------------|
| Pipeline | Read | Voir les pipelines et jobs | ❌ Non | Monitorer les builds |
| Pipeline | Create | Créer des pipelines | ❌ Non | Déclencher des builds manuellement |
| Pipeline | Delete | Supprimer des pipelines | ❌ Non | Nettoyer les vieux pipelines |
| Job | Read | Voir les logs des jobs | ❌ Non | Debugger les builds |
| **Artifact** | **Read** | **Télécharger artifacts** | ❌ Non | **Récupérer les binaires compilés** |
| Runner | Read | Voir les runners | ❌ Non | Monitorer les runners |
| Runner | Create | Créer des runners | ❌ Non | Ajouter des runners custom |
| Runner | Delete | Supprimer des runners | ❌ Non | Gérer les runners |

### 1.3 Gestion du Projet

| Resource | Permission | Description | Utilisé | Usage Potentiel |
|----------|-----------|-------------|---------|-----------------|
| Project | Read | Lire métadonnées du projet | ❌ Non | Obtenir infos projet |
| Project | Create | Créer projets | ❌ Non | Créer sous-projets |
| Issue | Read | Lire issues | ❌ Non | Tracker les tâches |
| Issue | Create | Créer issues | ❌ Non | Créer tâches automatiquement |
| MergeRequest | Read | Lire merge requests | ❌ Non | Auditer les MRs |
| MergeRequest | Create | Créer merge requests | ❌ Non | Créer MRs automatiquement |
| **MergeRequest** | **Merge** | **Merger merge requests** | ❌ Non | **Auto-merge après validation** |

### 1.4 Registres de Packages et Containers

| Resource | Permission | Description | Utilisé | Usage Potentiel |
|----------|-----------|-------------|---------|-----------------|
| ContainerRepository | Read | Pull images Docker | ❌ Non | Utiliser des images custom |
| ContainerRepository | Delete | Supprimer images | ❌ Non | Nettoyer le registry |
| Package | Read | Télécharger packages | ❌ Non | Gérer les dépendances |
| DependencyProxy | Read | Proxy de dépendances | ❌ Non | Cache de packages |

### 1.5 Sécurité et Conformité

| Resource | Permission | Description | Utilisé | Usage Potentiel |
|----------|-----------|-------------|---------|-----------------|
| Attestation | Read | Lire attestations de sécurité | ❌ Non | Vérifier la conformité |
| Vulnerability | Read | Lire vulnérabilités | ❌ Non | Audit de sécurité |

---

## 2. Limites GitLab

### 2.1 Stockage

| Tier | Limite | Note |
|------|--------|------|
| **Free** | **10 GiB par projet** | Repo + LFS uniquement |
| Premium | 500 GiB par projet | |
| Ultimate | 500 GiB par projet | |

**Points importants:**
- Container registry et artifacts **ne comptent pas** dans la limite
- Si le repo dépasse 10GB, il devient **read-only**
- **Solution**: Utiliser Git LFS pour les binaires ou stockage externe

### 2.2 CI/CD Minutes

| Tier | Minutes/mois | Note |
|------|--------------|------|
| **Free** | **400 minutes** | Très limité |
| Premium | 2000 minutes | |
| Ultimate | 10000 minutes | |
| **Self-hosted runners** | **Illimité** | Pas de quota |

**Cost Factors (multiplicateurs):**

| Runner Type | Size | Cost Factor |
|-------------|------|-------------|
| Linux x86-64 | small | 1× |
| Linux x86-64 | medium | 2× |
| Linux x86-64 | large | 3× |
| Linux x86-64 | xlarge | 6× |
| Linux x86-64 | GPU | 7× |
| macOS M1 | medium | 6× |
| Windows | medium | 1× |

**Problème actuel:**
- 400 min/mois est **très limité**
- Ne peut pas faire de builds LLVM lourds sur GitLab CI
- Un build LLVM de 15 minutes = 15 min consommées
- **Solution**: Utiliser GitHub Actions (illimité pour repos publics)

### 2.3 Rate Limits

| Type | Limite | Note |
|------|--------|------|
| API authenticated | 2000 requêtes/minute | Par utilisateur |
| API unauthenticated | 60 requêtes/minute | Par IP |
| Git operations | Variable | Selon load |

**Impact**: Pas de problème pour notre usage actuel

### 2.4 Job Limits

| Paramètre | Limite | Note |
|-----------|--------|------|
| Max duration | 60 minutes/job | Configurable |
| Concurrent jobs | Variable | Selon tier |

**Problème potentiel**: Builds LLVM très longs (>1h)

---

## 3. Limites GitHub Actions

### 3.1 Repos Publics (Notre Cas)

| Ressource | Limite | Note |
|-----------|--------|------|
| **Minutes** | **Illimité** | ✅ Parfait |
| Storage | 10 GB par repo | |
| Jobs | Illimité | |

### 3.2 Repos Privés

| Tier | Minutes/mois |
|------|--------------|
| Free | 2000 |
| Pro | 3000 |
| Team | 50000 |

### 3.3 Rate Limits

| Type | Limite |
|------|--------|
| API authenticated | 5000 requêtes/heure |
| API unauthenticated | 60 requêtes/heure |

**Note**: Plus généreux que GitLab

---

## 4. Opportunités Inexploitées

### 4.1 Haute Priorité

#### 4.1.1 Workflow Exact sur GitHub Actions

**Description**: Créer `metroid-exact.yml` pour vérification LLVM

**Bénéfices:**
- GPT-5.6 et Qwen peuvent faire de la vérification exacte
- Illimité sur GitHub Actions
- Reproductible (même environnement à chaque fois)

**Effort**: Moyen (1-2 jours)  
**Impact**: Haut (augmente couverture rapidement)

#### 4.1.2 Auto-merge Après Validation

**Description**: Utiliser `MergeRequest:Merge` pour auto-merge

**Workflow:**
1. Créer une MR automatiquement après génération de code
2. Le workflow exact vérifie la compilation
3. Si EXACT, merger automatiquement la MR
4. Sinon, laisser en attente pour review manuel

**Bénéfices:**
- Accélère le workflow de décompilation
- Réduit le travail manuel

**Effort**: Faible (quelques heures)  
**Impact**: Moyen

#### 4.1.3 Création Automatique d'Issues

**Description**: Utiliser `Issue:Create` pour tracker les tâches

**Exemples:**
- Créer une issue pour chaque fonction non-EXACT
- Créer une issue pour chaque régression détectée
- Créer une issue pour chaque nouveau Rosetta Stone identifié

**Bénéfices:**
- Meilleure organisation du travail
- Tracking automatique

**Effort**: Faible  
**Impact**: Moyen

### 4.2 Priorité Moyenne

#### 4.2.1 Container Registry pour Images Custom

**Description**: Stockage d'images Docker avec LLVM pré-installé

**Bénéfices:**
- Builds plus rapides (cache)
- Environnement reproductible

**Effort**: Moyen  
**Impact**: Moyen

#### 4.2.2 Monitoring des Pipelines

**Description**: Utiliser `Pipeline:Read` pour monitorer

**Bénéfices:**
- Meilleure visibilité sur les builds
- Alertes en cas d'échec

**Effort**: Faible  
**Impact**: Faible

#### 4.2.3 Git LFS pour Binaires

**Description**: Stockage de `main.elf` dans LFS

**Bénéfices:**
- Accès facile aux binaires
- Pas de problème de taille de repo

**Effort**: Moyen  
**Impact**: Moyen

### 4.3 Priorité Basse

#### 4.3.1 Audit de Sécurité

**Description**: Utiliser `Vulnerability:Read`

**Bénéfices:**
- Sécurité du code

**Effort**: Moyen  
**Impact**: Faible pour ce projet

#### 4.3.2 Gestion des Runners

**Description**: Créer/supprimer runners dynamiquement

**Bénéfices:**
- Flexibilité

**Effort**: Élevé  
**Impact**: Faible (GitHub Actions suffit)

---

## 5. Stratégie Recommandée

### Phase 1: Immédiat (Cette semaine)

1. ✅ **Vérifier que smoke-0024 fonctionne correctement**
2. 🔄 **Créer `metroid-exact.yml` pour vérification LLVM sur GitHub Actions**
3. 🧪 **Tester sur 5-10 Rosetta Stones prioritaires**
4. 📈 **Objectif: augmenter couverture de 13.36% à 15-20%**

### Phase 2: Court terme (2-4 semaines)

1. 🔀 **Implémenter auto-merge après validation exact**
2. 📊 **Créer workflow regression pour détecter pertes**
3. 📦 **Utiliser Git LFS pour main.elf si nécessaire**
4. 📚 **Documenter toutes les permissions utilisables**

### Phase 3: Moyen terme (1-3 mois)

1. 🐳 **Container registry pour images LLVM pré-compilées**
2. 📈 **Dashboard de monitoring des pipelines**
3. 📝 **Création automatique d'issues pour tâches**
4. 🔗 **Intégration avec outils de tracking**

---

## 6. Recommandations pour les Tokens

### 6.1 Prochaine Rotation (dans 90 jours)

**Quand**: Expiration du token actuel  
**Quoi faire**: Créer token avec uniquement `read_repository`  
**Alternative**: Utiliser Project Access Token au lieu de PAT  
**Bénéfice**: Principe du moindre privilège

### 6.2 Tokens Multiples

**Idée**: Créer plusieurs tokens avec scopes différents

**Exemples:**
1. **Token read-only pour le runner**
   - Scopes: `read_repository`
   - Usage: Cloner le repo
   
2. **Token CI/CD pour pipelines**
   - Scopes: `Pipeline:Read`, `Artifact:Read`
   - Usage: Monitorer et télécharger artifacts
   
3. **Token admin pour gestion**
   - Scopes: `Project:Read`, `Issue:Create`, `MergeRequest:Merge`
   - Usage: Gérer les MRs et issues

**Bénéfice**: Sécurité par séparation des responsabilités

---

## 7. Conclusion

### État Actuel
- ✅ Infrastructure de base solide et fonctionnelle
- ✅ Runner smoke opérationnel (7/7 PASS)
- ✅ Secrets chiffrés, pas de tokens en clair

### Potentiel
- 🔓 **24 permissions inexploitées** sur GitLab
- 🚀 Possibilité de faire beaucoup plus avec l'infrastructure existante
- 📊 Amélioration significative de la productivité

### Priorité
- 🎯 **Déplacer LLVM vers GitHub Actions** (illimité)
- 🎯 Permettre à GPT-5.6 et Qwen de faire de la vérification exacte
- 🎯 Automatiser le workflow de décompilation

### Vision
- 🌟 Évoluer vers un système de décompilation automatisé complet
- 🌟 Augmenter la couverture de 13.36% à >50% en quelques mois
- 🌟 Réduire le travail manuel au minimum

---

**Document créé par**: Qwen 3.8 Max  
**Date**: 2026-09-02  
**Version**: 1.0