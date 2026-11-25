# Epic 5 Context: Personnalisation Cartographique, Administration Générale & Vitrine Patrimoniale

<!-- Contexte technique et fonctionnel pour l'implémentation de l'Épic 5 suivant la méthode BMAD -->

## Goal

Permettre un paramétrage territorial fin (fonds de carte, centrage par défaut), doter la plateforme d'une console d'administration pour la gestion des contributeurs, raffiner l'expérience cartographique et les métadonnées de clichés (cône métrique, autocomplétion des sources), et accueillir les visiteurs avec une page d'accueil valorisant le patrimoine grâce aux archives historiques fournies.

## Stories

- **Story 5.1: Révision du Modèle de Métadonnées Photo et Cône de Vision Métrique**
  - Retrait des champs "époque/période" (`period_label`) et "date précise" (`date_exact`) dans les formulaires et schémas.
  - Ajout du booléen `is_exact_year` (défaut `true` si certifiée, `false` si approximative "vers XXXX").
  - Ajout de la longueur métrique du cône de vision `view_distance` (mètres, min: 20, max: 2000, défaut: 160).
  - Suggestions/tags réactifs pour le photographe et l'institution d'archives.
  - Mise à jour du sélecteur d'azimut avec réglage direct de la portée métrique du cône.
- **Story 5.2: Optimisation de l'Exploration Cartographique (Marqueurs Visibles & Fiche Latérale Droite)**
  - Agrandissement des marqueurs de photos sur la carte (icônes orientées et neutres avec contraste et lisibilité accrus).
  - Suppression de la popup intermédiaire MapLibre au clic : ouverture directe du volet latéral droit (`PhotoDetailDrawer.vue`).
  - Suppression du compteur de clichés et du badge de territoire en haut à droite.
  - Projection du cône de vue sur la carte utilisant la distance personnalisée de chaque cliché (`view_distance`).
- **Story 5.3: Console d'Administration Générale (Territoire, Contributeurs & Fonds de Carte)**
  - Configuration du centrage initial et du zoom par défaut du territoire (`center_lat`, `center_lng`, `default_zoom`).
  - Gestion des comptes contributeurs (liste, création d'invitations/comptes, activation/désactivation).
  - Gestion et sélection des fonds de carte disponibles (WMS / WMTS, tuiles vectorielles, XYZ).
- **Story 5.4: Page de Présentation / Vitrine Patrimoniale (Landing Page)**
  - Page d'accueil dédiée ("🏠 Accueil") valorisant le projet HierIci avec les 3 clichés d'archives Gallica BnF fournis.
  - Présentation des fonctionnalités clés (cônes de vue WebGL, scrollytelling immersif, géoréférencement).
  - Accès direct vers la Carte Découverte et les Récits.

## Requirements & Constraints

- **Multi-tenancy (AD-2) :** Toutes les opérations d'administration et de configuration de fonds de carte restent cloisonnées par `territory_id`.
- **Rétrocompatibilité :** Les colonnes en base de données `period_label` et `date_exact` restent tolérées en BDD (nullable) pour ne pas corrompre les données existantes, mais sont retirées des contrats de saisie et de l'affichage frontend au profit de `year_taken` + `is_exact_year`.
- **Performance WebGL 60fps (NFR-1) :** Les marqueurs agrandis et le calcul de cône métrique ne doivent induire aucune baisse de cadence sur MapLibre GL.
- **Sécurité RBAC (AD-5) :** La gestion des comptes utilisateurs et le paramétrage territorial sont réservés aux utilisateurs authentifiés avec le rôle approprié (`superadmin` ou `contributor` selon le périmètre).

## Technical Decisions

- **Modèle Photo :**
  - Ajout `is_exact_year: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)`
  - Ajout `view_distance: Mapped[int] = mapped_column(Integer, default=160, nullable=False)`
- **Modèle Territory :**
  - Ajout `basemaps: Mapped[list[dict] | None] = mapped_column(JSON, default=list, nullable=True)` pour stocker les fonds déclarés (WMS/WMTS, vecteurs, XYZ).
- **Photos d'illustration :**
  - Les 3 photographies fournies par l'utilisateur sont intégrées dans les assets publics (`frontend/public/images/landing/`) pour alimenter la vitrine patrimoniale.

