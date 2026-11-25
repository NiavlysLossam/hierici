---
status: final
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-hierici-2026-10-31/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/briefs/brief-hierici-2026-10-30/brief.md
  - _bmad-output/planning-artifacts/briefs/brief-hierici-2026-10-30/addendum.md
---

# hierici - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for hierici, decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- **FR-1**: Le système doit afficher une carte interactive basée sur des fonds libres (OpenStreetMap / tuiles vectorielles) avec regroupement automatique des points (clustering) selon le niveau de zoom. (Realizes UJ-1)
- **FR-2**: Le système doit afficher chaque photo sous forme d'un marqueur indiquant graphiquement son azimut, et projeter sur la carte un cône de vue polygonale lorsque le marqueur est sélectionné ou survolé. (Realizes UJ-1)
- **FR-3**: Le système doit ouvrir un volet ou modal de détail au clic sur un marqueur, affichant la photo en grand format et toutes ses métadonnées documentées. (Realizes UJ-1)
- **FR-4**: Le système doit synchroniser la position de la caméra cartographique (centre, niveau de zoom) avec l'étape visible à l'écran lors du défilement vertical du lecteur de Storymap. (Realizes UJ-3)
- **FR-5**: Le système doit présenter pour chaque étape de la Storymap le titre, le texte formaté (markdown) et un lecteur audio compact si un fichier sonore est attaché à l'étape. (Realizes UJ-3)
- **FR-6**: Le système doit proposer une page ou un tiroir listant toutes les Storymaps publiées du territoire avec titre, vignette de couverture, description courte et durée estimée de lecture. (Realizes UJ-3)
- **FR-7**: L'administrateur ou le contributeur doit pouvoir téléverser un ou plusieurs fichiers images (`.jpg`, `.jpeg`, `.png`, `.webp`) jusqu'à 25 Mo depuis son poste avec génération automatique de 3 déclinaisons (original, display WebP 2048px, thumb WebP 400px). (Realizes UJ-2)
- **FR-8**: L'interface de saisie d'une photo doit comporter une carte interactive permettant de définir le point de prise de vue et l'orientation de l'objectif (azimut 0-359°) par manipulation directe. (Realizes UJ-2)
- **FR-9**: Le formulaire doit permettre de documenter avec précision le contexte archivistique et historique du cliché (titre, année/période, photographe, fonds d'archives, cote, licence, URL source). (Realizes UJ-2)
- **FR-10**: L'auteur doit pouvoir créer une nouvelle Storymap, ajouter des étapes, modifier leur ordre par glisser-déposer et définir les paramètres de chaque étape (cadrage caméra, photo associée, texte markdown, audio). (Realizes UJ-3)
- **FR-11**: Le système doit permettre aux administrateurs et contributeurs de se connecter via un identifiant (email) et un mot de passe sécurisé (hachage Argon2id/bcrypt, tokens JWT). (Realizes UJ-2)
- **FR-12**: Le système doit faire respecter trois niveaux de privilèges : Superadmin, Contributeur, Visiteur anonyme. (Realizes UJ-2)
- **FR-13**: Le système doit encapsuler l'écriture et la récupération des fichiers multimédias derrière une interface abstraite (`StorageDriver`) permettant le stockage sur disque local ou sur stockage objet S3 par configuration d'environnement. (Realizes UJ-2)
- **FR-14**: Toutes les tables principales (photos, storymaps, contributeurs) doivent comporter une référence explicite `territoire_id` / slug pour assurer l'étanchéité multi-territoire. (Realizes UJ-1, UJ-2)

### NonFunctional Requirements

- **NFR-1 (Performance & Fluidité)**: Temps de chargement initial de la carte < 1.5s sur 4G standard ; transitions cartographiques (`flyTo`) fluides à 60 fps sur navigateurs modernes (WebGL).
- **NFR-2 (Sécurité & Intégrité)**: Hachage robuste des mots de passe (Argon2id/bcrypt), validation et assainissement des fichiers uploadés (anti-malware/strip EXIF script), protection contre les injections SQL (ORM) et failles XSS (Markdown désinfecté).
- **NFR-3 (Responsive Design)**: Interface 100% utilisable sur mobile (≥ 360px de largeur) et desktop.
- **NFR-4 (Licence & Droits)**: Code sous licence MIT ; préservation obligatoire des mentions de crédits et licences sur les photos.

### Additional Requirements

- **Socle & Starter Template (AD-Stack)**: Mise en place d'un monorepo ou dépôt structuré avec Docker Compose orchestrant : API FastAPI (Python 3.12+), Frontend Vue 3 + Vite + TailwindCSS, et Base de données PostgreSQL 16 + PostGIS 3.4. (Impact direct sur Epic 1 Story 1).
- **Format de données géospatiales (AD-1)**: Coordonnées en EPSG:4326 (WGS84). L'API expose un GeoJSON standard `FeatureCollection` pour les points de photos. Le calcul trigonométrique/vectoriel du cône de vue est exécuté côté client en WebGL.
- **Middleware Multi-Territoire (AD-2)**: Résolution du territoire actif au niveau du middleware HTTP FastAPI (header `X-Territory-Slug`, sous-domaine, ou `DEFAULT_TERRITORY_SLUG`).
- **Pattern Storage Adapter (AD-3)**: Interface abstraite `StorageDriver` avec `LocalStorageDriver` (volume local `/app/uploads`) et `S3StorageDriver` (boto3 vers MinIO/S3/R2).
- **Pipeline de compression d'images (AD-4)**: Bibliothèque Pillow exécutant la création asynchrone ou synchrone des 3 tailles d'image.

### UX Design Requirements

*(Aucun document UX dédié séparé n'a été produit ; les exigences d'interface et d'interaction sont directement intégrées dans le PRD et l'Architecture : visualiseur cartographique plein écran, marqueurs orientés, cônes dynamiques, tiroir scrollytelling synchronisé, boussole d'orientation interactive dans le formulaire d'upload).*

### FR Coverage Map

- **FR-1**: Epic 3 - Affichage cartographique et clustering libre
- **FR-2**: Epic 3 - Marqueur orienté et cône de vue WebGL
- **FR-3**: Epic 3 - Fiche détaillée et métadonnées d'archives
- **FR-4**: Epic 4 - Défilement scrollytelling et synchronisation caméra (flyTo)
- **FR-5**: Epic 4 - Textes riches et lecteur audio synchronisé
- **FR-6**: Epic 4 - Catalogue des Storymaps publiques du territoire
- **FR-7**: Epic 2 - Téléversement de photos et optimisation WebP (3 tailles)
- **FR-8**: Epic 2 - Outil interactif de géoréférencement et azimut (boussole)
- **FR-9**: Epic 2 - Formulaire de métadonnées temporelles et d'archives
- **FR-10**: Epic 4 - Studio d'édition et ordonnancement de Storymaps
- **FR-11**: Epic 1 - Authentification sécurisée (Argon2/JWT)
- **FR-12**: Epic 1 - Contrôle d'accès RBAC (Superadmin, Contributeur, Visiteur)
- **FR-13**: Epic 1 - Adaptateur de stockage hybride (Local et S3)
- **FR-14**: Epic 1 - Partitionnement multi-territoire des données

## Epic List

### Epic 1: Socle Territorial, Authentification et Stockage Média
Permettre aux administrateurs et contributeurs de s'authentifier de façon sécurisée, d'isoler les données par territoire et d'assurer une gestion pérenne et découplée des fichiers multimédias via un adaptateur de stockage hybride.
**FRs couvertes:** FR-11, FR-12, FR-13, FR-14

### Epic 2: Ingestion & Géoréférencement Directionnel des Photos
Permettre aux contributeurs de téléverser des photographies d'archives haute définition, de renseigner leur contexte documentaire et de définir précisément le point de prise de vue et l'azimut (orientation de 0° à 359°) via une interface cartographique interactive.
**FRs couvertes:** FR-7, FR-8, FR-9

### Epic 3: Exploration Cartographique Interactive & Visualisation Patrimoniale
Permettre au grand public d'explorer le territoire sur une carte interactive fluide avec clustering automatique, de visualiser l'orientation des clichés par des cônes de vue vectoriels et de consulter les fiches détaillées des photos en haute résolution.
**FRs couvertes:** FR-1, FR-2, FR-3

### Epic 4: Création & Découverte de Storymaps Narratives (Scrollytelling & Audio)
Permettre aux auteurs de composer des parcours historiques guidés pas-à-pas, et au public de vivre une expérience de visite immersive où la carte s'anime et se déplace automatiquement au rythme du défilement du récit avec textes et documents sonores.
**FRs couvertes:** FR-4, FR-5, FR-6, FR-10



## Epic 1: Socle Territorial, Authentification et Stockage Média

Permettre aux administrateurs et contributeurs de s'authentifier de façon sécurisée, d'isoler les données par territoire et d'assurer une gestion pérenne et découplée des fichiers multimédias via un adaptateur de stockage hybride.

### Story 1.1: Initialisation de l'environnement conteneurisé Docker Compose

As a développeur ou administrateur système,
I want démarrer l'ensemble des services de l'application (backend FastAPI, frontend Vue 3, base de données PostgreSQL/PostGIS) via une commande unique,
So that l'environnement de développement et de déploiement soit reproductible, isolé et immédiatement opérationnel.

**Acceptance Criteria:**

**Given** un poste de travail avec Docker et Docker Compose installés
**When** l'utilisateur exécute la commande `docker compose up -d`
**Then** trois conteneurs démarrent avec succès : `hierici-db` (PostgreSQL 16 + PostGIS 3.4), `hierici-backend` (FastAPI Python 3.12) et `hierici-frontend` (Vite / Vue 3)
**And** l'API backend répond `HTTP 200` sur la route de santé `/api/health` avec statut de connexion DB `connected`
**And** le frontend répond sur le port local configuré et affiche la page d'accueil de l'application.

---

### Story 1.2: Modèle Territoire et Middleware d'Isolation Multi-Territoire

As a superadministrateur,
I want que chaque requête et chaque donnée soient systématiquement cloisonnées par un identifiant de territoire,
So that l'application puisse héberger plusieurs territoires distincts sans risque de fuite de données entre eux.

**Acceptance Criteria:**

**Given** la base de données initialisée avec la table `territories` (champs : `id`, `slug`, `name`, `center_lat`, `center_lng`, `default_zoom`, `created_at`)
**When** une requête HTTP parvient à l'API backend
**Then** le middleware territorial résout le territoire actif selon l'en-tête `X-Territory-Slug`, le sous-domaine hôte, ou la variable `DEFAULT_TERRITORY_SLUG`
**And** si le slug résolu existe en base, l'objet territoire est injecté dans le contexte de la requête (`request.state.territory`)
**And** si aucun territoire ne correspond, l'API renvoie une erreur `HTTP 404 Territory Not Found` au format RFC 7807.

---

### Story 1.3: Authentification JWT et Contrôle d'Accès RBAC

As a contributeur ou administrateur,
I want m'authentifier avec mon adresse email et mon mot de passe pour obtenir un jeton d'accès sécurisé,
So that mes droits d'administration et de contribution soient vérifiés à chaque requête protégée.

**Acceptance Criteria:**

**Given** un utilisateur existant en base avec mot de passe haché (Argon2id ou bcrypt) et un rôle assigné (`superadmin` ou `contributor`) rattaché à un territoire
**When** l'utilisateur soumet ses identifiants valides sur l'endpoint `POST /api/v1/auth/login`
**Then** le système retourne un jeton JWT d'accès valide contenant l'identifiant utilisateur, son rôle et son territoire
**And** l'accès aux routes `/api/v1/admin/*` sans jeton valide renvoie `HTTP 401 Unauthorized`
**And** un contributeur tentant d'accéder à une action réservée au superadmin reçoit `HTTP 403 Forbidden`
**And** 5 échecs consécutifs d'authentification sur le même compte déclenchent un blocage temporaire par rate-limiting.

---

### Story 1.4: Adaptateur de Stockage Média Abstrait Local & S3

As a système backend,
I want manipuler les fichiers téléversés au travers d'une interface de stockage unifiée,
So that les fichiers soient enregistrés sur le disque local en développement et sur un bucket S3 en production sans modifier le code métier.

**Acceptance Criteria:**

**Given** l'interface abstraite `StorageDriver` définissant les méthodes `save(file, destination_path)`, `delete(path)` et `get_url(path)`
**When** la variable d'environnement `STORAGE_DRIVER` est configurée à `local`
**Then** le pilote `LocalStorageDriver` écrit les fichiers dans le volume persistant `/app/uploads` et génère des URLs relatives statiques
**When** la variable `STORAGE_DRIVER` est configurée à `s3` avec les identifiants de bucket
**Then** le pilote `S3StorageDriver` transmet les fichiers via l'API S3 (compatible MinIO / Cloudflare R2 / AWS) et génère des URLs de stockage distantes
**And** une suite de tests unitaires valide le comportement identique des deux pilotes sur les opérations de création, lecture et suppression.

---

## Epic 2: Ingestion & Géoréférencement Directionnel des Photos

Permettre aux contributeurs de téléverser des photographies d'archives haute définition, de renseigner leur contexte documentaire et de définir précisément le point de prise de vue et l'azimut (orientation de 0° à 359°) via une interface cartographique interactive.

### Story 2.1: Modèle de Données Photo et API de Gestion

As a contributeur identifié,
I want créer, consulter, modifier et supprimer des fiches photos rattachées à mon territoire,
So that la base patrimoniale soit alimentée et maintenue à jour.

**Acceptance Criteria:**

**Given** un utilisateur authentifié avec le rôle `contributor` ou `superadmin`
**When** il envoie une requête `POST /api/v1/admin/photos` avec les données d'une photo (titre, localisation géographique, statut `draft` ou `published`)
**Then** un enregistrement est créé dans la table `photos` avec son `territory_id` automatique et un identifiant unique (UUID)
**And** les requêtes de consultation `GET /api/v1/admin/photos` ne retournent que les photos du territoire de l'utilisateur
**And** la suppression d'une photo `DELETE /api/v1/admin/photos/{id}` supprime l'enregistrement en base et déclenche la suppression des fichiers physiques associés via le `StorageDriver`.

---

### Story 2.2: Téléversement et Pipeline de Compression d'Images WebP

As a contributeur téléversant un scan haute résolution (jusqu'à 25 Mo),
I want que l'application prenne en charge le fichier et génère automatiquement des versions optimisées pour le web,
So that les images s'affichent rapidement sur mobile et desktop tout en préservant le fichier original d'archive.

**Acceptance Criteria:**

**Given** un fichier image valide (`.jpg`, `.png`, `.webp`) ne dépassant pas 25 Mo
**When** le fichier est envoyé via l'endpoint d'upload `POST /api/v1/admin/photos/upload`
**Then** le pipeline de traitement (Pillow) génère 3 déclinaisons de l'image :
  1. `original` : fichier source intact conservé dans le stockage
  2. `display` : image redimensionnée à maximum 2048px en WebP (qualité 85)
  3. `thumb` : vignette redimensionnée à maximum 400px en WebP (qualité 80)
**And** les métadonnées EXIF potentiellement vulnérables sont désinfectées lors de la conversion
**And** si le fichier dépasse 25 Mo ou n'est pas un format image reconnu, l'API renvoie `HTTP 400 Bad Request` avec un message d'erreur explicite.

---

### Story 2.3: Interface d'Administration de Saisie des Métadonnées d'Archives

As a contributeur ou curateur,
I want renseigner l'ensemble des informations documentaires d'un cliché dans un formulaire web ergonomique,
So that le contexte historique, les sources et les droits de réutilisation soient scrupuleusement enregistrés.

**Acceptance Criteria:**

**Given** un contributeur accédant au formulaire d'édition d'une photo dans le studio d'administration
**When** il remplit les champs documentaires : Titre (obligatoire), Année ou date exacte (ex: 1912), Période, Photographe/Atelier, Fonds d'archives, Cote d'inventaire, URL de la notice source et Licence (menu déroulant : Domaine Public, Licence Ouverte, etc.)
**Then** les données sont validées côté client et persistées en base via l'API
**And** le contributeur peut choisir d'enregistrer la fiche avec le statut `draft` (brouillon privé) ou `published` (visible sur la carte publique)
**And** si le statut `published` est sélectionné alors que les coordonnées géographiques sont absentes, l'interface bloque l'enregistrement et invite à géolocaliser le cliché.

---

### Story 2.4: Sélecteur Cartographique Interactif pour le Point GPS et l'Azimut

As a contributeur géoréférençant un cliché historique,
I want cliquer sur une carte interactive pour placer la position du photographe et manipuler une boussole pour orienter son angle de vue,
So that la perspective exacte de la prise de vue soit fidèlement enregistrée.

**Acceptance Criteria:**

**Given** le formulaire d'édition photo affichant la carte interactive centrée sur le territoire
**When** le contributeur clique sur un point de la carte
**Then** un marqueur de position est placé et les champs `latitude` et `longitude` sont mis à jour (précision 6 décimales)
**When** le contributeur fait tourner le curseur d'azimut (boussole rotative ou champ numérique de 0° à 359°)
**Then** un cône de vue vectoriel pivote en temps réel sur la carte autour du marqueur pour visualiser la direction du regard
**And** le contributeur peut ajuster le champ de vision angulaire (défaut : 60°)
**And** à l'enregistrement, les valeurs `latitude`, `longitude`, `bearing` et `field_of_view` sont sauvegardées dans l'enregistrement de la photo.

---

## Epic 3: Exploration Cartographique Interactive & Visualisation Patrimoniale

Permettre au grand public d'explorer le territoire sur une carte interactive fluide avec clustering automatique, de visualiser l'orientation des clichés par des cônes de vue vectoriels et de consulter les fiches détaillées des photos en haute résolution.

### Story 3.1: Visualiseur Cartographique Public et Clustering Vectoriel

As a visiteur du grand public,
I want explorer la carte interactive de mon territoire et voir les photos regroupées en clusters dynamiques selon mon niveau de zoom,
So that je puisse facilement découvrir les concentrations de photos historiques sans que la carte ne soit encombrée.

**Acceptance Criteria:**

**Given** un visiteur accédant à la page d'accueil de HierIci sur navigateur desktop ou mobile
**When** la carte MapLibre GL JS se charge
**Then** les données publiques sont récupérées depuis l'API sous forme de GeoJSON `FeatureCollection` (filtrées par `status = 'published'` et territoire actif)
**And** les photos géographiquement proches sont regroupées en pastilles de clusters indiquant le nombre de clichés disponibles
**And** le clic sur un cluster zoome automatiquement sur la zone pour éclater les points
**And** le temps de chargement initial de la carte et des données est inférieur à 1,5 seconde.

---

### Story 3.2: Rendu des Marqueurs Orientés et Projection des Cônes de Vue WebGL

As a visiteur examinant un secteur cartographique,
I want voir la direction de prise de vue indiquée sur les marqueurs et voir s'afficher le cône d'observation du photographe au survol ou au clic,
So that je comprenne immédiatement quelle partie de la ville ou du paysage était cadrée dans l'objectif.

**Acceptance Criteria:**

**Given** des photos affichées sous forme de marqueurs individuels dégroupés sur la carte
**When** une photo dispose d'un azimut renseigné (ex: 90°)
**Then** le marqueur présente une icône ou une pointe orientée visuellement dans la direction correspondante (vers l'Est)
**When** le visiteur clique ou survole le marqueur d'une photo
**Then** un polygone vectoriel semi-transparent représentant le cône de vue (angle de 60°, portée visuelle de 150m à l'échelle) se projette sur la carte depuis le point de prise de vue
**And** le rendu WebGL s'exécute à 60 fps sans saccade sur mobile et ordinateur.

---

### Story 3.3: Fiche Détaillée du Cliché et Visionneuse Plein Écran

As a passionné d'histoire locale ou citoyen curieux,
I want ouvrir la fiche complète d'une photo sélectionnée pour la regarder en haute définition et lire son contexte d'archives,
So that je puisse examiner les détails historiques du lieu et vérifier la source du document.

**Acceptance Criteria:**

**Given** un marqueur sélectionné sur la carte
**When** le visiteur clique sur le marqueur ou sur l'aperçu rapide
**Then** un volet latéral (desktop) ou une feuille modale (mobile) s'ouvre avec : le titre, l'image WebP optimisée (`display`), la date/période, le photographe, le fonds d'archives et la cote, la licence et le lien vers la notice d'origine
**When** le visiteur clique sur l'image
**Then** une visionneuse plein écran s'ouvre permettant de zoomer et de naviguer dans l'image haute définition
**And** l'URL du navigateur intègre l'identifiant de la photo (ex: `?photo=uuid`), permettant de partager la vue exacte par lien direct.

---

## Epic 4: Création & Découverte de Storymaps Narratives (Scrollytelling & Audio)

Permettre aux auteurs de composer des parcours historiques guidés pas-à-pas, et au public de vivre une expérience de visite immersive où la carte s'anime et se déplace automatiquement au rythme du défilement du récit avec textes et documents sonores.

### Story 4.1: Modèle de Données et API des Storymaps et Chapitres

As a auteur de storymap,
I want créer et gérer des récits thématiques composés de chapitres séquentiels via une API dédiée,
So that la structure narrative de mes visites guidées soit stockée et consultable de manière ordonnée.

**Acceptance Criteria:**

**Given** les tables `storymaps` (titre, résumé, couverture, statut) et `storymap_steps` (ordre, titre étape, texte markdown, lien photo optionnel, fichier audio optionnel, coordonnées caméra lat/lng/zoom/bearing/pitch)
**When** un auteur authentifié crée ou modifie une storymap sur `POST /api/v1/admin/storymaps`
**Then** la storymap et ses étapes ordonnées sont sauvegardées dans le territoire actif
**And** la route publique `GET /api/v1/public/storymaps/{slug}` retourne la storymap et ses étapes uniquement si son statut est `published`.

---

### Story 4.2: Studio d'Édition et d'Ordonnancement des Storymaps

As a curateur ou auteur de contenu historique,
I want concevoir un parcours narratif en agençant des étapes, en associant des photos géolocalisées et en capturant les cadrages cartographiques,
So that je puisse composer une visite guidée interactive complète sans compétences en programmation.

**Acceptance Criteria:**

**Given** l'interface d'édition de Storymap dans le panneau d'administration
**When** l'auteur ajoute une étape, saisit un texte explicatif en Markdown et sélectionne une photo existante dans la photothèque du territoire
**Then** la photo et ses métadonnées sont associées à l'étape
**When** l'auteur ajuste la carte intégrée (zoom, centrage sur le monument) et clique sur *"Capturer la vue actuelle"*
**Then** les coordonnées cartographiques de la caméra (`lat`, `lng`, `zoom`, `bearing`) sont enregistrées pour cette étape
**And** l'auteur peut téléverser un fichier audio (`.mp3`) d'archive ou de commentaire vocal pour l'étape
**And** l'auteur peut réordonner les étapes par simple glisser-déposer (*drag and drop*).

---

### Story 4.3: Lecteur Public de Storymap en Scrollytelling avec Caméra Synchronisée et Audio

As a visiteur découvrant une Storymap thématique,
I want faire défiler la page verticalement et voir la carte se déplacer automatiquement d'un lieu à un autre au fil de la lecture,
So that je vive une expérience de récit spatio-temporel fluide et captivante.

**Acceptance Criteria:**

**Given** un visiteur ouvrant une Storymap publiée (ex: `/storymaps/histoire-industrielle`)
**When** il fait défiler la page vers le bas (*scrollytelling*)
**Then** au franchissement de chaque étape, la carte réalise une transition cinématographique fluide (`flyTo`) vers le cadrage enregistré de l'étape
**And** la photo associée à l'étape s'affiche en grand format avec sa légende et son texte narratif
**When** l'étape comporte une piste sonore
**Then** un lecteur audio compact permet d'écouter le document sonore, et la lecture se coupe proprement si l'utilisateur défile vers une autre étape ayant son propre audio
**And** l'expérience est entièrement responsive et fluide sur écran smartphone.

---

### Story 4.4: Catalogue Public des Récits et Navigation Territoriale

As a visiteur arrivant sur le site,
I want consulter la liste des visites et récits thématiques disponibles pour mon territoire,
So that je puisse choisir un sujet historique qui m'intéresse (ex. histoire industrielle, tracé du tramway, métamorphose d'un quartier).

**Acceptance Criteria:**

**Given** la page catalogue des Storymaps publiques du territoire (`/storymaps`)
**When** le visiteur accède à la page
**Then** toutes les Storymaps publiées du territoire s'affichent sous forme de cartes d'accroche élégantes comprenant : vignette de couverture, titre, résumé, nombre d'étapes et durée estimée de lecture
**When** le visiteur clique sur une storymap
**Then** le lecteur immersif plein écran de la storymap s'ouvre instantanément
**And** un bouton de retour permet de regagner la carte générale d'exploration libre à tout instant.

---

## Epic 5: Personnalisation Cartographique, Administration Générale & Vitrine Patrimoniale

Permettre un paramétrage territorial fin (fonds de carte, centrage par défaut), doter la plateforme d'une console d'administration pour la gestion des contributeurs, raffiner l'expérience cartographique et les métadonnées de clichés (cône métrique, autocomplétion des sources), et accueillir les visiteurs avec une page d'accueil valorisant le patrimoine grâce aux archives historiques.

### Story 5.1: Révision du Modèle de Métadonnées Photo et Cône de Vision Métrique

As a contributeur ou archiviste saisissant un cliché,
I want renseigner la précision de l'année, bénéficier de suggestions pour les photographes et institutions, et ajuster la portée métrique du cône de vue,
So that les fiches soient conformes aux pratiques archivistiques et que la profondeur de champ sur la carte reflète la réalité de la prise de vue.

**Acceptance Criteria:**
- **Given** le modèle et le formulaire de gestion d'une photo
- **When** le contributeur édite les métadonnées
- **Then** les champs "époque/période" et "date précise" ne sont plus présentés
- **And** une option booléenne "Année précise ?" (`is_exact_year`) permet d'indiquer si l'année est certifiée ou approximative
- **And** les champs "Institution d'archives" et "Photographe" proposent une liste déroulante / suggestions basées sur les valeurs déjà enregistrées dans le territoire
- **And** un curseur permet de régler la distance du cône de vision (`view_distance`, entre 20 et 2000 mètres, défaut 160m) avec prévisualisation dynamique sur la carte.

---

### Story 5.2: Optimisation de l'Exploration Cartographique (Marqueurs Visibles & Fiche Latérale Droite)

As a visiteur explorant la carte interactive,
I want repérer instantanément les photos grâce à des marqueurs bien visibles et consulter la fiche détaillée directement dans un panneau latéral droit sans popup intermédiaire,
So that la navigation soit directe, claire et débarrassée d'éléments d'en-tête superflus.

**Acceptance Criteria:**
- **Given** la carte découverte publique
- **When** les photos sont affichées sur la carte
- **Then** les marqueurs orientés et neutres ont une taille agrandie et un contraste renforcé pour une visibilité optimale
- **When** le visiteur clique sur un marqueur
- **Then** aucune popup intermédiaire MapLibre ne s'affiche ; le volet latéral droit (`PhotoDetailDrawer`) s'ouvre immédiatement avec la fiche complète
- **And** le cône de vue projeté utilise la distance métrique personnalisée `view_distance` de la photo
- **And** le badge de décompte et le nom de territoire en haut à droite sont retirés de la carte.

---

### Story 5.3: Console d'Administration Générale (Territoire, Contributeurs & Fonds de Carte)

As a administrateur de territoire ou superadministrateur,
I want configurer le centrage initial de la carte, gérer les comptes de contributeurs et choisir les fonds de carte (WMS, WMTS, tuiles vectorielles, XYZ),
So that le territoire soit entièrement personnalisable et son équipe de rédaction autonome.

**Acceptance Criteria:**
- **Given** un utilisateur authentifié avec le rôle approprié accédant à la console d'administration
- **When** l'administrateur configure le territoire
- **Then** il peut ajuster ou capturer les coordonnées (`center_lat`, `center_lng`) et le niveau de zoom par défaut de la carte
- **And** il peut ajouter, modifier le rôle, ou désactiver des comptes contributeurs pour le territoire
- **And** il peut configurer et activer les fonds de carte disponibles (WMS/WMTS, tuiles vecteur, XYZ) avec un fond actif par défaut.

---

### Story 5.4: Page de Présentation / Vitrine Patrimoniale (Landing Page)

As a visiteur découvrant la plateforme HierIci,
I want accéder à une page d'accueil élégante illustrée par de superbes photographies historiques qui m'explique les concepts clés (cônes de vue, géolocalisation, storymaps),
So that je comprenne immédiatement la valeur du projet et puisse plonger dans la carte ou les récits en un clic.

**Acceptance Criteria:**
- **Given** un internaute arrivant sur le site ou cliquant sur l'onglet "🏠 Accueil"
- **When** la page d'accueil s'affiche
- **Then** un visuel d'accroche et des sections thématiques mettent en valeur les photographies patrimoniales fournies (fonds Gallica BnF)
- **And** les fonctionnalités majeures (cônes d'azimut, scrollytelling sonore, archives géolocalisées) sont présentées de manière accessible
- **And** des boutons d'appel à l'action permettent de basculer instantanément vers la Carte Découverte ou le Catalogue des Récits.
