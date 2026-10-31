# Addendum : Détails d'Analyse et Notes Techniques pour HierIci

Ce document consigne les réflexions, matrices et choix techniques approfondis recueillis durant la phase de cadrage. Ces éléments serviront directement d'entrées pour la rédaction du PRD (`bmad-prd`) et de l'Architecture (`bmad-architecture`).

---

## 1. Matrice Détaillée des Rôles et Permissions (RBAC)

| Rôle | Périmètre | Droits d'écriture | Droits de publication | Droits d'administration |
| :--- | :--- | :--- | :--- | :--- |
| **Superadmin** | Global (multi-territoires) | Tout | Tout | Création de territoires, gestion des comptes admins, configuration système |
| **Admin Territoire / Curateur** | Territoire assigné | Photos, Storymaps, Métadonnées | Validation et passage en `published` des contributions | Gestion des contributeurs locaux du territoire |
| **Contributeur Identifié** | Territoire assigné | Upload photo, géoréférencement, création de brouillon storymap | Limité à ses propres brouillons (soumission pour validation) | Aucun |
| **Visiteur Public** | Global ou sous-domaine | Aucun | Aucun (Lecture seule) | Aucun |

*Note d'implémentation :* Pour le MVP où Sylvain est l'unique contributeur/administrateur, le rôle actif possédera à la fois les prérogatives de Superadmin et de Curateur, mais la table des permissions en base de données sera isolée pour accueillir sereinement d'autres utilisateurs sans refonte de schéma.

---

## 2. Spécification Préliminaire du Géoréférencement & Modèle de Données Photo

Une photographie historique possède des caractéristiques distinctes d'un simple POI cartographique :

### Coordonnées et Direction
* **Position de prise de vue** : Latitude / Longitude (WGS84, `EPSG:4326`).
* **Azimut (`bearing`)** : Nombre entier entre 0° et 359° (0° = Nord, 90° = Est, 180° = Sud, 270° = Ouest).
* **Champ de vision (`field_of_view`)** : Angle d'ouverture en degrés (valeur par défaut suggérée : 45° ou 60° pour un objectif standard).
* **Distance focale / portée visuelle indicative (optionnelle)** : Estimation de la distance visible pour tracer un cône visuel proportionné sur la carte.

### Métadonnées Temporelles
* **Type de date** : `exact` (ex: 1912-04-14), `year` (ex: 1912), `range` (ex: 1910-1920), ou `period` (ex: "Belle Époque", "Entre-deux-guerres").
* **Date normalisée de tri** : Année entière (`1912`) pour permettre le filtrage chronologique et le tri par ordre chronologique même lorsque la date est imprécise.

### Métadonnées Documentaires & Archivistiques
* **Titre / Légende** : Titre court descriptif.
* **Description détaillée** : Contexte historique, détails visibles sur le cliché.
* **Auteur / Photographe** : Nom de l'atelier ou du photographe (ex: "Marius Bar", "Félix Nadar", "Inconnu").
* **Institution / Fonds d'archives** : Nom de l'archive de conservation (ex: "Archives Municipales de...", "Archives Départementales", "Collection particulière").
* **Cote / Référence d'inventaire** : Numéro ou identifiant d'archive.
* **Lien permanent (Ark / URL source)** : Redirection vers la notice officielle de conservation.
* **Licence de réutilisation** : Mention des droits (ex: "Domaine Public", "Licence Ouverte", "CC-BY", "Usage soumis à autorisation").

---

## 3. Mécanisme du Scrollytelling (Storymap)

### Anatomie d'un Chapitre (Étape de Storymap)
Chaque étape du récit contient :
1. **Identifiant d'ordre** : Index séquentiel du chapitre.
2. **Cadrage Caméra** :
   * Centre géographique cible (`lat`, `lng`).
   * Niveau de zoom (`zoom`).
   * Orientation de caméra (`pitch` / `bearing` si la librairie cartographique le permet).
3. **Média principal mis en exergue** : Référence vers une photo de la base (avec option d'affichage en superposition, zoom dans l'image, ou comparaison).
4. **Contenu textuel** : Titre du chapitre, corps du récit en markdown (paragraphes, citations d'archives).
5. **Média sonore (optionnel)** : Fichier audio (mp3/ogg), durée, transcription textuelle pour l'accessibilité.

---

## 4. Analyse des Références & Alternatives Étudiées

* **`beaubiat.fr/geolocaliserMarius`** :
  * *Points forts* : Démarche pionnière remarquable, excellente densité de clichés sur Toulon/Marseille.
  * *Limites constatées* : Interface utilisateur vieillissante, expérience mobile difficile, manque de parcours scénarisés / storymaps, popups denses masquant la carte.
* **Esri StoryMaps / ArcGIS** :
  * *Points forts* : Référence ergonomique en matière de scrollytelling cartographique.
  * *Limites* : Écosystème totalement propriétaire, tarifs prohibitifs pour les particuliers/associations, dépendance forte au cloud fermé d'Esri.
* **Smapshot (HEIG-VD, Suisse)** :
  * *Points forts* : Géoréférencement 3D par calcul de perspective sur modèle de terrain numérique.
  * *Limites* : Complexité technique très élevée, nécessite un MNT (modèle numérique de terrain) 3D, moins axé sur la vulgarisation grand public et le scrollytelling narratif.

---

## 5. Stratégie de Stockage Média (Adaptateur Hybride)

* **Approche retenue** : Pattern *Storage Adapter* / *Driver*.
* **Driver par défaut (MVP & Local)** : `LocalStorageDriver` écrivant dans un répertoire monté (`/uploads`). Avantages : zéro coût, zéro clé d'API, auto-hébergement instantané (`docker compose up`).
* **Driver Cloud/Production** : `S3StorageDriver` compatible avec l'API AWS S3 standard (fonctionne avec AWS, MinIO auto-hébergé, Cloudflare R2, Scaleway, OVH).
* **Bascule** : Pilotée par variables d'environnement (`STORAGE_DRIVER=local|s3`).


