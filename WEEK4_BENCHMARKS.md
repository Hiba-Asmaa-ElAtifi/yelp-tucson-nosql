# Week 4 — Benchmarks de performance et analyse de distribution

## 1. Objectif

Cette quatrième semaine du projet **Yelp Tucson NoSQL** est consacrée à l'évaluation des performances des requêtes MongoDB, à la comparaison de stratégies d'optimisation et à l'analyse de la distribution et de la cohérence des données.

Trois axes de comparaison ont été étudiés :

- **Q1 — Géolocalisation :** recherche géographique avec index `2dsphere` contre recherche sans index géospatial.

- **Q4 — Pagination des avis :** ancien index composé contre nouvel index composé, puis absence d’index composé adapté (index `_id_`) contre nouvel index composé.

- **Q5/Q6 — Notes des commerces :** recalcul complet contre calcul incrémental.

Les mesures ont été effectuées avec MongoDB dans Docker, sur la même base `yelp_tucson`.

L'objectif est d'évaluer l'effet de choix de conception sur les performances, de vérifier l'équivalence fonctionnelle des stratégies et de discuter des limites de l'architecture utilisée.

## 2. Environnement expérimental

| Élément | Configuration |
|---|---|
| Base de données | MongoDB 8.0.16 |
| Déploiement | Docker Compose |
| Base utilisée | `yelp_tucson` |
| Langage des benchmarks | Python 3.12 |
| Bibliothèque d'accès | PyMongo |
| Collection `businesses` | 9 261 documents |
| Collection `reviews` | 375 076 documents |
| Collection `users` | 117 497 documents |
| Collection `tips` | 49 876 documents |
| Collection `checkins` | 7 747 documents |

Les scripts de mesure sont conservés dans `src/benchmarks/`.

Le protocole comprend **3 exécutions d'échauffement et 20 mesures par stratégie et par scénario testé**.

Les indicateurs retenus sont :

- **Médiane :** temps central des exécutions mesurées, moins sensible aux valeurs extrêmes que la moyenne.

- **P95 :** percentile 95 des temps mesurés, utilisé pour observer les exécutions les plus lentes.

- **Équivalence fonctionnelle :** vérification que les stratégies comparées produisent les mêmes résultats attendus.

- **Plan d'exécution :** utilisation de `explain("executionStats")` pour analyser le travail effectué par MongoDB lorsque cela est applicable.

Les résultats sont exprimés en millisecondes (ms).

Les mesures ont été réalisées dans le même environnement local, mais les temps peuvent varier selon la charge de la machine, les caches et les conditions d'exécution.

Les caractéristiques détaillées du poste hôte (CPU, RAM, système d’exploitation), la configuration mémoire de MongoDB et les tailles des collections et index ne sont pas documentées dans les résultats fournis. Elles ne sont donc pas supposées ici.

## 3. Benchmark Q1 — Recherche géographique

### 3.1. Objectif

Comparer les performances d'une recherche géographique utilisant un index MongoDB `2dsphere` à celles d'une recherche sans cet index géospatial.

La recherche porte sur les commerces situés à une distance maximale de **2 000 mètres** d'un point de Tucson.

Le point utilisé possède les coordonnées suivantes, dans l'ordre longitude puis latitude :

```text
[-110.880452, 32.223236]
```

### 3.2. Méthodes

**Stratégie A — Avec index géospatial**

La requête utilise l'opérateur MongoDB `$near` et un index `2dsphere`.

MongoDB exploite son moteur géospatial pour identifier les commerces situés dans le rayon demandé.

**Stratégie B — Sans index géospatial**

Le script parcourt les documents des commerces et calcule les distances en Python à l'aide de la formule de Haversine.

Cette stratégie ne repose pas sur un index géospatial MongoDB.

**Précision méthodologique :** il s'agit d'une comparaison entre deux stratégies d'exécution différentes, et non de la même requête MongoDB exécutée successivement avec et sans index.

### 3.3. Protocole

Pour chaque stratégie :

- 3 exécutions d'échauffement ;

- 20 mesures de temps ;

- comparaison des identifiants des commerces retournés ;

- calcul de la médiane et du P95.

Les deux stratégies utilisent le même point central et le même rayon de recherche.

### 3.4. Résultats

| Indicateur | Avec index `2dsphere` | Sans index géospatial |
|---|---:|---:|
| Résultats retournés | 649 | 649 |
| Médiane | **10,489 ms** | 69,075 ms |
| P95 | **15,555 ms** | 82,117 ms |
| Mesures | 20 | 20 |

L'utilisation de l'index géospatial correspond à une accélération d'environ **6,6 fois sur la médiane**, dans les conditions de ce benchmark.

La vérification des identifiants a confirmé que les deux stratégies retournent exactement les mêmes **649 commerces**.

L'équivalence fonctionnelle est donc validée pour le périmètre testé.

### 3.5. Analyse du plan d'exécution

L'analyse `explain("executionStats")` de la requête indexée indique :

| Indicateur | Valeur |
|---|---:|
| Plan géospatial | `GEO_NEAR_2DSPHERE` |
| Documents retournés | 649 |
| Clés examinées | 1 014 |
| Documents examinés | 1 496 |

Ces résultats montrent que MongoDB utilise l'index géospatial pour exécuter la recherche.

L'index permet d'éviter un parcours applicatif complet de tous les commerces pour calculer leur distance au point central.

### 3.6. Interprétation et limites

Le benchmark met en évidence l'intérêt d'une indexation géospatiale pour les recherches de proximité.

Cependant, les deux stratégies n'utilisent pas exactement le même moteur de calcul :

- la première utilise une requête géospatiale MongoDB ;

- la seconde effectue un parcours et un calcul de distance en Python.

L'accélération observée représente donc le gain entre ces deux approches, et non uniquement le coût isolé de l'index.

Par ailleurs, le benchmark porte sur le **noyau géographique de Q1**. Il ne mesure pas tous les filtres métier possibles, notamment les horaires d'ouverture, les catégories et la pagination de la requête complète.

### 3.7. Preuves

Les fichiers suivants conservent les mesures et les vérifications :

- `results/week4/q1/q1_avec_index_mesures.csv`

- `results/week4/q1/q1_sans_index_mesures.csv`

- `results/week4/q1/q1_avec_index_explain.txt`

- `results/week4/q1/q1_avec_index_executionstats.png`

- `results/week4/q1/q1_equivalence_resultats.txt`

## 4. Benchmark Q4 — Pagination des avis

### 4.1. Objectif

Évaluer les performances de la pagination des avis récents d’un commerce, d’abord entre deux index composés, puis entre une stratégie sans index composé adapté et le nouvel index composé.

La requête utilise :

- un filtre sur `business_id` ;

- un tri par `date` décroissante ;

- un tri secondaire par `_id` croissant ;

- une pagination avec `skip()` et `limit()`.

### 4.2. Index comparés

**Ancien index :**

```javascript
{ business_id: 1, date: -1 }
```

**Nouvel index composé :**

```javascript
{ business_id: 1, date: -1, _id: 1 }
```

Le nouvel index a été ajouté sans supprimer l'index existant.

Les mesures utilisent `hint()` pour sélectionner explicitement l'index à comparer.

Cette méthode permet de comparer les deux plans d'accès sur la même requête.

### 4.3. Jeu de test

Le commerce sélectionné possède **2 223 avis**.

Son identifiant est :

```text
UCMSWPqzXjd7QHq7v8PJjQ
```

Pour la comparaison initiale entre les deux index composés, les pages testées sont :

- page 1 ;

- page 10 ;

- page 100 ;

- page 400.

Chaque page contient au maximum **5 avis**.

Pour chaque combinaison page/index de cette comparaison initiale, le benchmark effectue 3 échauffements et 20 mesures.

### 4.4. Résultats

| Page | Ancien index — médiane | Ancien index — P95 | Nouvel index — médiane | Nouvel index — P95 |
|---|---:|---:|---:|---:|
| 1 | 9,413 ms | 27,552 ms | **0,797 ms** | **1,008 ms** |
| 10 | 6,942 ms | 7,901 ms | **0,965 ms** | **1,286 ms** |
| 100 | 10,199 ms | 12,278 ms | **1,441 ms** | **2,100 ms** |
| 400 | 10,336 ms | 13,163 ms | **2,371 ms** | **3,385 ms** |

Le benchmark a produit **160 mesures** au total :

```text
2 index × 4 pages × 20 mesures = 160 mesures
```

Les deux stratégies ont retourné les mêmes identifiants, dans le même ordre, pour chaque page testée.

### 4.5. Analyse des plans d'exécution

Pour la première page, le plan observé avec l'ancien index comporte notamment les étapes suivantes :

```text
IXSCAN → FETCH → SORT
```

Ce plan examine :

- 2 223 clés ;

- 2 223 documents ;

pour retourner seulement 5 avis.

Avec le nouvel index, le plan observé comporte notamment :

```text
IXSCAN → FETCH → LIMIT
```

Il examine :

- 5 clés ;

- 5 documents ;

pour retourner les 5 avis demandés.

Le nouvel index correspond à la fois au filtre et à l'ordre de tri de la requête.

Il permet donc d'éviter le tri coûteux observé avec l'ancien index.

Les temps issus de `explain("executionStats")` correspondent à des exécutions ponctuelles et ne remplacent pas les médianes et P95 obtenus par les mesures répétées.

### 4.6. Comparaison complémentaire — Sans index composé vs index composé

Pour répondre à la comparaison demandée dans le protocole du projet, un benchmark supplémentaire a été réalisé sur la page 1, avec la même requête, le même commerce et une taille de page de 5 avis.

Deux stratégies ont été comparées avec `hint()` :

- **Sans index composé :** index MongoDB `_id_`.

- **Avec index composé :** `idx_reviews_business_date_id_week4`, correspondant à `{ business_id: 1, date: -1, _id: 1 }`.

Chaque stratégie a fait l'objet de **3 échauffements et 20 mesures**, soit **40 mesures** au total.

| Indicateur | Sans index composé (`_id_`) | Avec index composé |
|---|---:|---:|
| Médiane | 1 302,784 ms | **0,974 ms** |
| P95 | 1 943,571 ms | **1,985 ms** |
| Avis retournés | 5 | 5 |
| Résultats fonctionnellement identiques | Oui | Oui |

L'index composé réduit la latence médiane d'environ **99,93 %**, soit une accélération d'environ **1 338 fois** dans cet environnement de test.

L'équivalence fonctionnelle a été vérifiée : les deux stratégies retournent les mêmes identifiants d'avis dans le même ordre.

**Limites :** cette comparaison porte uniquement sur la première page. Le scénario « sans index composé » utilise l'index `_id_` et ne représente donc pas une collection dépourvue de tout index. Les résultats peuvent varier selon le cache et la charge de la machine.

**Fichiers de résultats :**

- `results/week4/q4/comparaison_finale/q4_mesures.csv`

- `results/week4/q4/comparaison_finale/q4_resume.csv`

**Script reproductible :** `src/benchmarks/benchmark_q4_comparaison_finale.py`.

### 4.7. Interprétation

Le nouvel index réduit fortement le temps médian de pagination :

| Page | Accélération approximative |
|---|---:|
| 1 | 11,8 fois |
| 10 | 7,2 fois |
| 100 | 7,1 fois |
| 400 | 4,4 fois |

L'amélioration est particulièrement importante pour la première page.

Le temps de réponse augmente toutefois avec la profondeur de pagination, même avec le nouvel index.

En effet, `skip()` doit avancer dans les résultats avant d'atteindre la page demandée.

Une **pagination par curseur**, fondée sur les dernières valeurs de `date` et `_id`, pourrait être étudiée comme amélioration future pour les pages profondes.

### 4.8. Limites

Les résultats concernent un commerce possédant 2 223 avis et des pages de cinq éléments.

Ils ne garantissent pas les mêmes gains pour tous les commerces ou pour d'autres tailles de pages.

Le benchmark mesure la pagination avec `skip()` et `limit()`. Il ne compare pas expérimentalement cette approche à une pagination par curseur.

### 4.9. Preuves

- `results/week4/q4/q4_mesures.csv`

- `results/week4/q4/q4_resume.csv`

- `results/week4/q4/q4_ancien_index_explain.txt`

- `results/week4/q4/q4_nouvel_index_explain.txt`

## 5. Benchmark Q5/Q6 — Calcul des notes

### 5.1. Objectif

Comparer le coût du recalcul complet des statistiques d'un commerce avec celui d'un calcul incrémental après l'ajout simulé d'un nouvel avis.

Le benchmark utilise un commerce possédant **2 223 avis**.

### 5.2. Stratégies

**Stratégie A — Recalcul complet**

MongoDB exécute une agrégation sur les avis du commerce pour recalculer :

- le nombre d'avis ;

- la somme des notes.

Le programme simule ensuite l'ajout d'une nouvelle note pour calculer la moyenne correspondante.

**Stratégie B — Calcul incrémental**

La nouvelle moyenne est obtenue à partir du nombre d'avis et de la moyenne précédents.

La formule utilisée est :

```text
nouvelle_moyenne =
    (ancien_nombre × ancienne_moyenne + nouvelle_note)
    / (ancien_nombre + 1)
```

Le calcul incrémental ne nécessite pas de relire tous les avis.

Le benchmark simule l'ajout d'une note de **5 étoiles**.

Aucun avis réel n'est inséré et aucune statistique métier n'est modifiée.

### 5.3. Protocole

Chaque stratégie est exécutée avec :

- 3 échauffements ;

- 20 mesures ;

- calcul de la médiane et du P95 ;

- vérification de l'équivalence des statistiques obtenues.

Le benchmark produit 40 mesures au total.

### 5.4. Résultats

| Indicateur | Recalcul complet | Calcul incrémental |
|---|---:|---:|
| Avis initiaux | 2 223 | 2 223 |
| Moyenne initiale | 4,391813 | 4,391813 |
| Nouvelle note simulée | 5 | 5 |
| Avis après simulation | 2 224 | 2 224 |
| Nouvelle moyenne | 4,392086 | 4,392086 |
| Médiane | 2,306518 ms | **0,000164 ms** |
| P95 | 2,519061 ms | **0,000317 ms** |
| Mesures | 20 | 20 |

**Équivalence fonctionnelle : validée.**

Les deux stratégies obtiennent le même nombre d'avis et la même moyenne après l'ajout simulé.

### 5.5. Interprétation

Le calcul incrémental évite de parcourir les avis existants.

Son coût arithmétique est constant par rapport au nombre d'avis déjà enregistrés.

À l'inverse, le recalcul complet doit interroger les avis du commerce et effectuer une agrégation.

Les mesures illustrent donc l'économie de calcul permise par une approche incrémentale.

### 5.6. Limites méthodologiques

Cette comparaison présente une limite importante : **les deux stratégies ne mesurent pas le même périmètre d'exécution**.

- Le recalcul complet inclut une agrégation MongoDB.

- Le calcul incrémental mesure uniquement une opération Python en mémoire.

- Les mesures n'incluent pas l'insertion d'un nouvel avis dans MongoDB.

- Elles n'incluent pas non plus l'écriture des statistiques mises à jour dans le document du commerce.

Les temps très faibles de l'opération Python doivent être interprétés avec prudence, car ils sont sensibles à la résolution et au bruit de mesure.

Par conséquent, les résultats démontrent un avantage du calcul incrémental sur le **coût du calcul**, mais ne permettent pas de quantifier le gain d'une opération complète d'ajout d'avis.

Une comparaison plus complète devrait mesurer deux procédures de mise à jour de bout en bout sur des données de test isolées.

### 5.7. Cohérence des statistiques

Le calcul incrémental suppose que les statistiques initiales sont exactes.

Si le nombre d'avis ou la moyenne stockée est incorrect, les mises à jour suivantes risquent de propager cette erreur.

Le recalcul complet permet de reconstruire les statistiques à partir des avis enregistrés.

Une architecture utilisant les mises à jour incrémentales devrait donc prévoir :

- des garanties de cohérence lors de l'ajout d'un avis ;

- une procédure de réconciliation périodique ;

- une gestion des échecs et des écritures concurrentes.

### 5.8. Preuves

- `results/week4/q5_q6/q5_q6_mesures.csv`

- `results/week4/q5_q6/q5_q6_resume.csv`

## 6. Distribution et réplication

### 6.1. Architecture actuelle

Le projet utilise une instance MongoDB exécutée dans Docker.

Deux commandes d'inspection ont été utilisées :

```javascript
db.adminCommand({ hello: 1 })
```

et :

```javascript
db.adminCommand({ getCmdLineOpts: 1 }).parsed
```

La première commande indique notamment :

```text
isWritablePrimary: true
readOnly: false
ok: 1
```

Elle ne présente pas de champ `setName`, normalement associé à l'identification d'un replica set.

La seconde retourne :

```javascript
{ net: { bindIp: "*" } }
```

Ces observations sont cohérentes avec une configuration **standalone**, sans replica set.

Le paramètre `bindIp` concerne les interfaces réseau sur lesquelles MongoDB écoute. Il ne constitue pas un mécanisme de distribution des données.

### 6.2. Conséquences de l'architecture actuelle

Dans l'architecture testée :

- les données sont hébergées sur une seule instance MongoDB ;

- aucune réplication entre plusieurs nœuds n'a été configurée ou mesurée ;

- aucun test de basculement automatique n'a été réalisé ;

- aucun test de partition réseau entre réplicas n'a été effectué.

Une panne de l'instance unique entraîne l'indisponibilité de la base jusqu'à son rétablissement.

Cette architecture est adaptée aux expérimentations locales, mais ne fournit pas de haute disponibilité par réplication.

### 6.3. Évolution vers un replica set

Une évolution vers un **replica set** permettrait d'introduire plusieurs copies des données.

Dans une architecture classique, un nœud primaire reçoit les écritures et les nœuds secondaires répliquent les opérations.

En cas de défaillance du primaire, une élection peut permettre à un autre nœud éligible de devenir primaire, sous réserve de disposer d'une majorité de votes.

Une telle architecture améliorerait la tolérance à certaines pannes, mais introduirait des contraintes de configuration et de cohérence.

Cette évolution n'a pas été mise en œuvre dans les expériences présentées.

### 6.4. Partitionnement et sharding

Le **sharding** permet de répartir les données entre plusieurs partitions hébergées sur différents nœuds.

Pour une plateforme de commerces et d'avis, plusieurs choix de clé de partitionnement pourraient être étudiés.

Par exemple :

- une répartition des avis à partir de `business_id` faciliterait certaines requêtes par commerce ;

- une clé trop concentrée sur quelques commerces très populaires pourrait toutefois créer des déséquilibres de charge ;

- les recherches géographiques distribuées nécessiteraient une analyse spécifique du routage des requêtes et des index.

Le choix d'une clé de sharding devrait tenir compte de la fréquence des requêtes, de la répartition des données et des risques de points chauds (**hot spots**).

Le sharding n'a pas été configuré dans le projet actuel.

## 7. Cohérence et analyse CAP

### 7.1. Cohérence lors de l'ajout d'un avis

L'ajout d'un avis et la modification des statistiques d'un commerce concernent deux documents distincts.

Une procédure simple peut effectuer :

1. l'insertion de l'avis dans `reviews` ;

2. le recalcul ou la mise à jour des statistiques dans `businesses`.

Sans mécanisme garantissant l'atomicité de l'ensemble, une interruption entre ces opérations peut laisser les statistiques temporairement incohérentes avec les avis enregistrés.

Par exemple, un nouvel avis peut être présent dans `reviews` alors que `computed_review_count` et `computed_average_stars` n'ont pas encore été mis à jour.

### 7.2. Stratégies possibles

**Recalcul complet**

Cette stratégie reconstruit les statistiques à partir des avis enregistrés.

Elle peut servir à corriger un écart entre les données sources et les statistiques conservées.

Son coût augmente toutefois avec le nombre d'avis à traiter.

**Mise à jour incrémentale**

Cette stratégie actualise les statistiques à partir des valeurs précédentes et de la nouvelle note.

Elle réduit le coût du calcul, mais nécessite des garanties contre les écritures concurrentes, les mises à jour perdues et les traitements partiellement exécutés.

**Transactions et réconciliation**

Une évolution vers des transactions multi-documents, dans une configuration MongoDB adaptée, pourrait garantir l'atomicité entre l'insertion d'un avis et la mise à jour du commerce.

Une procédure de réconciliation resterait utile pour vérifier périodiquement les statistiques.

Ces mécanismes sont proposés comme améliorations : ils n'ont pas été testés dans ce benchmark.

### 7.3. Analyse du théorème CAP

Le théorème CAP concerne les systèmes distribués soumis à une partition réseau.

Pendant une partition, un système distribué doit arbitrer entre :

- **C — Consistency :** fournir les garanties de cohérence considérées par le modèle CAP ;

- **A — Availability :** répondre aux requêtes malgré les défaillances considérées ;

- **P — Partition tolerance :** continuer à fonctionner dans un environnement où les communications entre nœuds peuvent être interrompues.

Notre instance MongoDB standalone ne constitue pas un cluster distribué.

Nous ne pouvons donc pas la classer expérimentalement comme « CP » ou « AP » à partir de nos tests.

### 7.4. Compromis dans une architecture MongoDB répliquée

Dans un replica set MongoDB, les choix de configuration influenceraient les garanties de lecture et d'écriture.

Les paramètres importants comprennent notamment :

- `writeConcern` : niveau d'accusé de réception demandé pour les écritures ;

- `readConcern` : garanties de visibilité et de cohérence des lectures ;

- `readPreference` : choix des nœuds utilisés pour les lectures.

Par exemple, des écritures confirmées par une majorité peuvent renforcer la durabilité face à certaines défaillances.

Des lectures depuis des secondaires peuvent, selon la configuration, observer des données en retard de réplication.

En cas de partition réseau, les possibilités d'écriture dépendent notamment de la disponibilité d'un primaire disposant du quorum nécessaire.

Ces considérations sont **théoriques pour notre projet actuel** : aucune expérience de partition réseau n'a été menée.

## 8. Synthèse et recommandations

| Sujet | Observation | Recommandation |
|---|---|---|
| Géolocalisation Q1 | Recherche indexée plus rapide dans notre comparaison | Conserver l'index `2dsphere` |
| Pagination Q4 | L'index composé évite un tri coûteux | Privilégier l'index correspondant au filtre et au tri |
| Pagination profonde | Coût croissant de `skip()` | Étudier la pagination par curseur |
| Notes Q5/Q6 | Calcul incrémental très peu coûteux en mémoire | Étudier une mise à jour incrémentale sûre |
| Cohérence | Risque d'écart entre avis et statistiques | Prévoir des garanties d'écriture et une réconciliation |
| Réplication | Architecture standalone | Étudier un replica set si la haute disponibilité devient nécessaire |
| Distribution | Absence de sharding | Évaluer le partitionnement uniquement si la charge le justifie |

Les optimisations d'indexation constituent les résultats expérimentaux les plus directement comparables de cette Week 4, particulièrement pour Q4.

Les améliorations proposées pour la cohérence et la distribution restent des pistes architecturales à évaluer.

## 9. Reproductibilité et limites générales

### 9.1. Scripts disponibles

Les scripts des benchmarks définitifs sont disponibles dans :

```text
src/benchmarks/
    benchmark_q1.py
    benchmark_q1_sans_index.py
    benchmark_q4.py
    benchmark_q5_q6.py
```

Les mesures et preuves sont conservées dans :

```text
results/week4/
    q1/
    q4/
    q5_q6/
    mongodb_hello.txt
    mongodb_configuration.txt
```

Les benchmarks ont été réalisés sur le même environnement de projet, avec échauffements et mesures répétées.

### 9.2. Commandes de reproduction des benchmarks

Les commandes suivantes doivent être exécutées depuis la racine du projet `yelp-tucson-nosql`, après avoir préparé la base `yelp_tucson` à l'aide du pipeline d'ingestion.

**1. Démarrer MongoDB :**

```powershell
docker compose up -d mongodb
```

**2. Reconstruire l'image Python :**

```powershell
docker compose build pipeline
```

**3. Exécuter les benchmarks :**

Benchmark Q1 avec index géospatial :

```powershell
docker compose run --rm pipeline python src/benchmarks/benchmark_q1.py
```

Benchmark Q1 sans index géospatial :

```powershell
docker compose run --rm pipeline python src/benchmarks/benchmark_q1_sans_index.py
```

Benchmark Q4 — comparaison des index :

```powershell
docker compose run --rm pipeline python src/benchmarks/benchmark_q4.py
```

Benchmark Q4 — sans index composé adapté (`_id_`) contre nouvel index composé, page 1 :

```powershell
docker compose run --rm pipeline python src/benchmarks/benchmark_q4_comparaison_finale.py
```

Benchmark Q5/Q6 — recalcul complet et calcul incrémental :

```powershell
docker compose run --rm pipeline python src/benchmarks/benchmark_q5_q6.py
```

Les résultats sont enregistrés dans `results/week4/`.

### 9.3. Conditions nécessaires

Pour reproduire les benchmarks sur une nouvelle installation, la base `yelp_tucson` doit être alimentée avec les mêmes données et les index nécessaires doivent être créés après l'ingestion.

**Prérequis pour Q1 — Index géospatial**

La recherche géographique indexée de Q1 nécessite un index `2dsphere` sur le champ `location` de la collection `businesses`.

Dans `mongosh`, exécuter :

```javascript
db.businesses.createIndex(
  { location: "2dsphere" },
  { name: "idx_businesses_location_2dsphere" }
)
```

**Prérequis pour Q4 — Index de pagination**

Le benchmark Q4 initial compare deux index composés sur la collection `reviews`. Le benchmark complémentaire utilise aussi l’index MongoDB `_id_`, créé par défaut, comme stratégie sans index composé adapté.

Dans `mongosh`, exécuter :

```javascript
db.reviews.createIndex(
  { business_id: 1, date: -1 },
  { name: "idx_reviews_business_date" }
)
db.reviews.createIndex(
  { business_id: 1, date: -1, _id: 1 },
  { name: "idx_reviews_business_date_id_week4" }
)
```

Ces trois index existent déjà dans l'environnement utilisé pour les mesures de Week 4. Il n'est donc pas nécessaire de les recréer dans cet environnement.

**Conditions de reproductibilité**

Pour reproduire les comparaisons dans des conditions similaires, il faut utiliser :

- les mêmes données ;

- les mêmes index et leurs noms exacts ;

- les mêmes paramètres de requête ;

- la même configuration MongoDB ;

- le même nombre d'échauffements et de mesures.

Les deux scripts Q4 sélectionnent explicitement les index avec `hint()`. Les noms déclarés dans `benchmark_q4.py` et `benchmark_q4_comparaison_finale.py` doivent donc correspondre à ceux présents dans MongoDB.

Les benchmarks Q1, Q4 et Q5/Q6 exécutent des mesures en lecture seule. Ils ne nécessitent pas de modifier les données métier.

Les performances peuvent varier selon la machine, la charge système et l'état du cache.

### 9.4. Limites générales

Les résultats représentent les conditions locales de ces exécutions et ne constituent pas une garantie de performance pour un déploiement de production.

En particulier :

- **Q1 :** la comparaison oppose une recherche géospatiale MongoDB à un parcours avec calcul de distance en Python.

- **Q4 :** les mesures concernent un commerce précis, quatre profondeurs de pagination et cinq avis par page.

- **Q5/Q6 :** la comparaison oppose une agrégation MongoDB à un calcul Python en mémoire, sans mesurer les écritures complètes.

- **Distribution :** aucune réplication ni partition réseau n'a été testée.

Les accélérations observées doivent être interprétées en tenant compte de ces limites.

## 10. Conclusion

La Week 4 a permis de mesurer concrètement l'impact de plusieurs choix de conception sur les performances de MongoDB.

Les résultats montrent l'intérêt de l'indexation géospatiale pour Q1 et d'un index composé adapté au filtre et au tri pour Q4.

Le benchmark Q5/Q6 illustre l'économie de calcul permise par une approche incrémentale, tout en soulignant la nécessité de maintenir la cohérence des statistiques.

L'analyse des plans d'exécution a permis d'expliquer les différences de performance, notamment l'élimination d'un tri coûteux grâce au nouvel index composé de Q4.

Enfin, l'inspection de l'environnement a confirmé une architecture MongoDB standalone. L'étude de la réplication, du sharding, des partitions réseau et des compromis CAP relève donc de l'analyse architecturale plutôt que d'expériences réalisées sur un cluster.

Ces travaux fournissent une base mesurée et reproductible pour discuter des performances, de la cohérence et des évolutions possibles du projet Yelp Tucson NoSQL.

La prochaine étape consiste à intégrer ces résultats dans le rapport final du groupe, à préparer les éléments de démonstration et à vérifier que les choix de conception peuvent être expliqués et défendus lors de la présentation orale.
