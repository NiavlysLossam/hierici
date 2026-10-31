---
title: "Product Brief: HierIci"
status: finalized
created: 2026-10-30
updated: 2026-10-31
---

# Product Brief: HierIci

## Executive Summary

**HierIci** est une plateforme web cartographique et narrative, libre et open source, dédiée à la valorisation et à la contextualisation de photographies historiques. Elle permet à des passionnés de patrimoine, à des historiens locaux et à des curateurs de géolocaliser des clichés anciens avec une précision directionnelle (position du photographe et angle de prise de vue), tout en offrant au grand public une double expérience : une exploration cartographique interactive libre et des récits immersifs guidés sous forme de *Storymaps* thématiques (scrollytelling associant cartes, textes, photographies et audio).

Aujourd'hui, des millions de photographies d'époque dorment dans les archives municipales, départementales ou chez des collectionneurs privés. Lorsqu'elles sont numérisées, elles demeurent souvent confinées dans des catalogues textuels austères ou exposées sur des cartes rudimentaires, dépourvues de mise en récit et désincarnées de la perspective réelle du photographe. 

HierIci comble ce fossé en alliant la rigueur du géoréférencement patrimonial à l'élégance du web moderne. Conçu dès l'origine pour être multi-territoires et facilement déployable, le projet s'ancre d'abord sur un territoire pilote (le bassin historique de son créateur) avant de pouvoir être réutilisé par d'autres communautés locales et acteurs culturels.

---

## The Problem

1. **La mémoire visuelle est fragmentée et décontextualisée** : Les sites d'archives numérisées proposent des listes de notices souvent arides. Sans spatialisation intuitive, le grand public ne parvient pas à appréhender la transformation concrète de ses rues et paysages.
2. **L'approximation du géoréférencement standard** : Les outils cartographiques habituels se contentent de poser une épingle sur un monument ou une adresse approximative. Or, une photo ancienne est une *perspective* : où se tenait le photographe ? Vers où regardait-il ? Cette information d'azimut est essentielle pour comprendre la vue et la confronter à la ville actuelle.
3. **Le vide narratif** : Découvrir des points isolés sur une carte ne suffit pas à transmettre une histoire. Les passionnés manquent d'un outil accessible pour scénariser des parcours historiques (ex. l'épopée industrielle d'une cité, le parcours d'une ligne de tramway disparue, la reconstruction après-guerre) sans devoir coder.
4. **Des outils existants vieillissants ou fermés** : Les initiatives artisanales existantes (ex. *beaubiat.fr/geolocaliserMarius*) ont prouvé la valeur de la démarche mais reposent sur des interfaces dépassées et peu adaptées aux mobiles. À l'opposé, les suites SIG professionnelles (comme ArcGIS StoryMaps) sont propriétaires, coûteuses et inaccessibles pour des projets citoyens ou associatifs libres.

---

## The Solution

HierIci propose une application web fluide, réactive et élégante, structurée autour de deux grandes expériences utilisateurs :

1. **Le Visualiseur Cartographique Immersif (Mode Libre)** :
   * Une carte interactive contemporaine (OpenStreetMap/fonds libres) affichant les clichés anciens sous forme de points dotés de **cônes d'orientation visuelle** (direction du regard).
   * Un système de regroupement (clustering) intelligent et de filtres (par époque, thématique, quartier).
   * Une fiche descriptive élégante pour chaque cliché : affichage haute définition, métadonnées documentées (auteur, année/période, source d'archives, licence), et lien direct vers le document original.

2. **Le Moteur de Storymaps (Mode Récit / Scrollytelling)** :
   * Une expérience guidée où le visiteur fait défiler un récit verticalement (*scrollytelling*).
   * À chaque étape, la carte effectue une transition cinématographique fluide (*flyTo*) vers l'emplacement exact, mettant en lumière la photo d'époque, accompagnée d'un texte d'analyse historique et d'un accompagnement sonore / audio optionnel (témoignages, ambiance d'époque).

3. **Une Architecture Libre et Multi-Territoire** :
   * Un socle 100 % open source (licence MIT) permettant une réutilisation et une appropriation communautaire sans restriction.
   * Une structure de données prête pour le partitionnement par territoire (attribut `territoire_id` / slug), exploitée d'abord sur une URL unique puis extensible à des sous-domaines (`territoire.hierici.fr`).

---

## What Makes This Different

* **Précision de prise de vue (Position + Azimut)** : Représentation graphique sur la carte du cône d'observation du photographe, et non un simple marqueur générique.
* **Dualité Exploration / Narration** : La même base de photos enrichies alimente à la fois la recherche libre et des parcours pédagogiques mis en scène.
* **Sobriété et souveraineté open-source** : Zéro dépendance aux géants du SIG propriétaire (Esri), solution légère, auto-hébergeable et pérenne.
* **Gouvernance et droits intégrés nativement** : Modèle de rôles pensé pour garantir la qualité scientifique et archivistique des données sans sacrifier la collaboration.

---

## Who This Serves

### 1. Le Grand Public & Curieux de Patrimoine (Visiteurs)
* **Profil** : Citoyens, touristes, passionnés d'histoire locale, scolaires.
* **Besoins** : Découvrir facilement ce qu'il y avait "ici autrefois", explorer sans friction sur smartphone ou ordinateur, se laisser conter une histoire vivante.
* **Critère de succès** : Navigation fluide sans accroc, plaisir de la découverte visuelle immédiate.

### 2. Les Contributeurs & Géoréférenceurs
* **Profil** : Le porteur de projet au lancement, puis des passionnés d'archives locales et collectionneurs identifiés.
* **Besoins** : Un outil intuitif pour téléverser une photo, pointer l'endroit sur la carte, orienter le curseur dans la direction de la prise de vue, et référencer les cotes d'archives.
* **Critère de succès** : Moins de 2 minutes pour géoréférencer et documenter précisément une photo.

### 3. Les Curateurs & Auteurs de Storymaps
* **Profil** : Historiens amateurs, enseignants, animateurs du patrimoine.
* **Besoins** : Un éditeur de parcours pour ordonner des étapes, écrire des textes riches, associer des extraits audios et ajuster les cadrages cartographiques.
* **Critère de succès** : Capacité à composer une storymap complète sans aucune compétence technique.

### 4. Les Collectivités & Communautés Partenaires (Futurs Territoires)
* **Profil** : Associations d'histoire locale ou petites communes souhaitant valoriser leur propre fonds photographique sous leur identité.
* **Besoins** : Pouvoir déployer ou activer une instance dédiée sans redévelopper une application.

---

## Success Criteria

1. **Territoire pilote opérationnel** : Déploiement d'une première instance fonctionnelle pour le territoire de Sylvain avec un corpus initial de **50 à 150 photos géolocalisées avec azimut**.
2. **Production de récits fondateurs** : Publication d'au moins **2 storymaps narratives complètes** (ex. histoire industrielle, mutations urbaines d'un quartier) intégrant texte, photos et pastilles sonores.
3. **Performance & Ergonomie** :
   * Affichage de la carte et des marqueurs en moins de 1,5 seconde.
   * Expérience de lecture de storymap fluide (60 fps sur transitions cartographiques) sur mobile et desktop.
4. **Extensibilité & Qualité du code** :
   * Projet publié sous licence libre **MIT**.
   * Documentation de déploiement permettant de configurer un nouveau territoire en quelques variables d'environnement.

---

## Scope

### In Scope (MVP V1)
* **Consultation cartographique publique** :
  * Carte interactive (tuiles vectorielles ou raster OpenStreetMap/CARTO).
  * Affichage des marqueurs de photos avec orientation visuelle (icône ou cône directionnel).
  * Fiche modale ou volet latéral de détail : photo plein écran, métadonnées (titre, date/fourchette, auteur, fonds d'archives source, lien externe, licence).
* **Lecteur de Storymaps (Scrollytelling)** :
  * Défilement vertical avec synchronisation de la carte (pan/zoom automatique).
  * Affichage des textes d'accompagnement et intégration de pistes audio (balise audio native HTML5 pour fichiers audio hébergés).
* **Gestion du stockage média (Adaptateur Hybride)** :
  * Stockage local sur disque / volume Docker persistant par défaut pour le MVP (déploiement et tests sans frais ni dépendance externe).
  * Architecture abstraite prête pour une bascule transparente sur stockage objet (S3, MinIO, Cloudflare R2) par simple variable d'environnement en production.
* **Gestion des utilisateurs & Sécurité (RBAC)** :
  * Rôles : Superadmin, Contributeur identifié, Visiteur anonyme.
  * Authentification sécurisée par email/mot de passe pour les contributeurs.
* **Studio d'administration & Contribution (Contributeur/Admin)** :
  * Formulaire de dépôt de photos et saisie des métadonnées temporelles et documentaires.
  * Outil interactif de géoréférencement : clic sur la carte + réglage de l'azimut (boussole/curseur rotatif).
  * Statut de publication (`brouillon` / `publié`).
  * Éditeur simple de Storymap : sélection de photos de la base, ordonnancement des chapitres, saisie des textes narratifs.
* **Préparation Multi-Territoire** :
  * Modèle de données intégrant l'attribut `territoire_id` / slug pour préfigurer le partitionnement par sous-domaine.

### Out of Scope (Exclus du MVP initial)
* Provisioning automatisé de sous-domaines DNS en libre-service (le multi-territoire est géré via le modèle de données et configuration serveur, sans automatisation DNS en V1).
* Moissonnage automatique des API d'archives (OAI-PMH, Gallica, OpenData départementaux) : l'import sera manuel ou via fichier tabulaire/CSV au démarrage.
* Recalage 3D automatique par intelligence artificielle / vision par ordinateur.
* Rephotographie comparative en direct avec caméra smartphone (avant/après en réalité augmentée).
* Espace de commentaires publics ou réseau social complexe.

---

## Vision (2-3 ans)

Si HierIci réussit son pari, la plateforme deviendra le carrefour libre de la mémoire spatiale locale :
1. **Un réseau fédéré de territoires** : Des dizaines de territoires, villes et vallées valorisant leurs trésors d'archives sur des instances interconnectées.
2. **Superposition temporelle dynamique (Curseur temporel)** : Glisser d'un clic entre le cadastre napoléonien, les vues aériennes IGN de 1950 et le plan actuel, sous les photos d'époque.
3. **Rephotographie participative in-situ** : Permettre aux promeneurs de se caler dans les pas exacts du photographe historique à l'aide de leur téléphone pour reprendre le cliché contemporain sous le même angle.
