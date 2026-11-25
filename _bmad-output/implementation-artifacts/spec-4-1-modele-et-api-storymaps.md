---
title: 'Story 4.1: Modèle de Données et API des Storymaps et Chapitres'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-4-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Actuellement, la plateforme HierIci permet de géoréférencer des photos et de les visualiser sur une carte, mais ne dispose d'aucune structure de données ni d'API pour composer des visites guidées thématiques séquentielles (storymaps) articulées en chapitres avec textes narratifs, cadrages cartographiques cinématographiques et documents sonores.

**Approach:** 
1. Concevoir et implémenter les modèles relationnels SQLAlchemy PostgreSQL `Storymap` et `StorymapStep` avec clé d'isolation multi-territoire (`territory_id`), relation ordonnée en cascade et gestion des statuts (`draft` / `published`).
2. Développer les schémas de validation Pydantic stricts pour les récits et les étapes, validant les coordonnées de caméra (lat, lng, zoom, bearing, pitch) et résolvant les URLs multimédias publiques (couverture, audio).
3. Développer les endpoints d'administration REST sécurisés (`/api/v1/admin/storymaps`) avec opérations CRUD, gestion des étapes et réordonnancement, ainsi que l'endpoint public (`/api/v1/public/storymaps/{slug}`) restreint aux seuls récits publiés du territoire actif.

## Boundaries & Constraints

**Always:**
- Chaque `Storymap` est rattachée obligatoirement à un `territory_id` (AD-2) et à un `author_user_id`.
- La route publique `GET /api/v1/public/storymaps/{slug}` (et `GET /api/v1/storymaps/{slug}`) ne renvoie que les storymaps ayant `status = 'published'` et appartenant au territoire actif (AD-5). Tout récit en statut `draft` ou appartenant à un autre territoire retourne une erreur 404 (RESOURCE_NOT_FOUND).
- Les étapes (`StorymapStep`) sont ordonnées séquentiellement via `step_order`. La suppression d'une storymap entraîne la suppression en cascade de ses étapes (`cascade="all, delete-orphan"`).
- La suppression d'une photo liée (`photo_id`) n'efface pas l'étape de la storymap mais passe `photo_id` à `NULL` (`ondelete="SET NULL"`).
- Les coordonnées cartographiques de la caméra de chaque étape sont strictement bornées : `lat` [-90, 90], `lng` [-180, 180], `zoom` [0, 24], `bearing` [0, 360], `pitch` [0, 85].
- Les routes d'administration `/api/v1/admin/storymaps` exigent un token JWT valide d'un utilisateur ayant le rôle `contributor` ou `superadmin`.

**Never:**
- Pas d'exposition de récits en brouillon (`draft`) sur les routes publiques.
- Pas de fuite de métadonnées sensibles (chemins de stockage internes non résolus, identifiants d'auteurs privés).
- Pas de dépendances cycliques ou de suppression orpheline entre les récits et leurs étapes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Création storymap admin valide | `POST /api/v1/admin/storymaps` avec titre, résumé, statut draft | Code 201, storymap créée rattachée au territoire actif avec slug auto-généré | 422 si titre manquant ou invalide |
| Création storymap avec étapes initiales | `POST /api/v1/admin/storymaps` incluant une liste d'étapes ordonnées | Code 201, storymap et ses `StorymapStep` persistées avec `step_order` séquentiel | 422 si coordonnées caméra hors bornes |
| Ajout / Modification d'étape | `POST/PUT /api/v1/admin/storymaps/{id}/steps` | Code 200/201, étape enregistrée avec cadrage caméra et lien photo/audio | 404 si storymap inexistante |
| Réordonnancement des étapes | `PUT /api/v1/admin/storymaps/{id}/steps/reorder` avec liste d'IDs ordonnés | Code 200, mise à jour atomique des `step_order` selon l'ordre reçu | 400/422 si IDs invalides ou manquants |
| Consultation publique d'une storymap publiée | `GET /api/v1/public/storymaps/{slug}` sur récit `published` | Code 200, retour complet de la storymap et de ses étapes ordonnées | N/A |
| Consultation publique d'une storymap en brouillon | `GET /api/v1/public/storymaps/{slug}` sur récit `draft` | Code 404 avec code d'erreur standard `STORYMAP_NOT_FOUND` | 404 masquant l'existence du brouillon |
| Consultation d'un récit d'un autre territoire | `GET /api/v1/public/storymaps/{slug}` sur un autre territoire | Code 404 (isolation multi-territoire stricte AD-2) | 404 |
| Suppression d'une storymap | `DELETE /api/v1/admin/storymaps/{id}` | Code 204, suppression de la storymap et cascade sur toutes ses étapes | 404 si inexistante |

</frozen-after-approval>

## Code Map

- `backend/app/models/storymap.py` -- Nouveaux modèles SQLAlchemy `Storymap` et `StorymapStep`, enum `StorymapStatus`.
- `backend/app/models/__init__.py` (ou `backend/app/core/init_db.py`) -- Enregistrement des nouveaux modèles pour synchronisation automatique `create_all`.
- `backend/app/schemas/storymap.py` -- Schémas Pydantic `StorymapStepCreate`, `StorymapStepUpdate`, `StorymapStepRead`, `StorymapCreate`, `StorymapUpdate`, `StorymapRead`, `StorymapPublicRead`, `StorymapReorderPayload`.
- `backend/app/api/v1/admin/storymaps.py` -- Endpoints administratifs sécurisés pour la gestion des récits et chapitres (`/api/v1/admin/storymaps`).
- `backend/app/api/v1/public/storymaps.py` -- Endpoint public sécurisé pour la consultation des récits publiés du territoire (`/api/v1/public/storymaps`).
- `backend/app/api/v1/__init__.py` -- Enregistrement des routeurs public et admin des storymaps.
- `backend/tests/test_storymaps.py` -- Suite de tests automatisés couvrant les modèles, validations, CRUD admin, réordonnancement, cascade et isolation territoriale.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/storymap.py` -- Créer les modèles SQLAlchemy `Storymap` et `StorymapStep` avec clés étrangères, index et cascades.
- [x] `backend/app/core/init_db.py` -- Importer les nouveaux modèles pour garantir leur création au démarrage.
- [x] `backend/app/schemas/storymap.py` -- Définir les schémas de validation Pydantic (Storymap et StorymapStep) avec normalisation des coordonnées et résolution d'URLs médias.
- [x] `backend/app/api/v1/admin/storymaps.py` -- Implémenter les routes admin (CRUD storymaps, gestion des étapes, réordonnancement).
- [x] `backend/app/api/v1/public/storymaps.py` -- Implémenter les routes publiques (liste des récits publiés et détail par slug).
- [x] `backend/app/api/v1/__init__.py` -- Enregistrer les routeurs dans l'API v1.
- [x] `backend/tests/test_storymaps.py` -- Écrire et exécuter la suite de tests automatisés validant tous les scénarios de la matrice I/O.

**Acceptance Criteria:**
- Given un auteur authentifié, When il envoie `POST /api/v1/admin/storymaps` avec des étapes ordonnées, Then la storymap et ses étapes sont sauvegardées dans le territoire actif.
- Given une storymap avec `status = 'published'`, When un visiteur appelle `GET /api/v1/public/storymaps/{slug}`, Then les détails et les étapes ordonnées de la storymap sont retournés avec code 200.
- Given une storymap avec `status = 'draft'`, When un visiteur non authentifié appelle `GET /api/v1/public/storymaps/{slug}`, Then l'API renvoie 404 (RESOURCE_NOT_FOUND).
- Given une storymap existante avec des étapes, When un administrateur supprime la storymap via `DELETE /api/v1/admin/storymaps/{id}`, Then la storymap et toutes ses étapes associées sont supprimées en cascade de la base de données.

## Implementation Notes

- **Modèles relationnels PostgreSQL :**
  - Table `storymaps` avec isolation territoriale (`territory_id`), auteur, statut (`StorymapStatus`), slug unique par territoire (`uq_storymaps_territory_slug`) et cascade vers `storymap_steps`.
  - Table `storymap_steps` avec clé optionnelle `photo_id` (`ondelete="SET NULL"`), Markdown narratif, coordonnées et angles de caméra (`camera_lat`, `camera_lng`, `camera_zoom`, `camera_bearing`, `camera_pitch`), et ordre séquentiel `step_order`.
- **Validation Pydantic & Sécurité des URLs :**
  - Bornes strictes sur coordonnées cartographiques et normalisation de l'azimut 360° vers 0°.
  - Résolution dynamique des URLs de couverture et d'audio (`resolve_media_url`) et masquage strict des chemins physiques internes sur les schémas publics (`exclude=True`).
- **Endpoints REST Admin & Publics :**
  - CRUD complet sécurisé (`/api/v1/admin/storymaps`) avec réordonnancement atomique par lot.
  - Endpoints publics (`/api/v1/public/storymaps` et `.../{slug}`) strictement réservés aux récits `published` du territoire actif, masquant toute photo liée qui ne serait pas elle-même publiée.

## Spec Change Log

## Review Triage Log

- **ISSUE-01 (Vérification et isolation multi-territoire de `photo_id`) :** Ajout de la validation territoriale `_validate_photo_id` garantissant que toute photo associée existe et appartient au territoire de la storymap, retournant 422 (`INVALID_PHOTO`).
- **ISSUE-02 (Étanchéité des photos non publiées sur le catalogue public) :** Factorisation de `_format_public_storymap` masquant toute photo liée dont le statut n'est pas `published` sur l'ensemble des endpoints publics (catalogue et détail).
- **ISSUE-03 (Validation stricte du réordonnancement des étapes) :** Remplacement de `payload: Any` par `StorymapReorderPayload`, suppression du default `= None` sur `current_user`, et rejet strict des doublons d'UUIDs (`len != set`).
- **ISSUE-04 (Réinitialisation des champs optionnels à None) :** Utilisation de `model_dump(exclude_unset=True)` dans les endpoints de mise à jour permettant de détacher des photos ou supprimer des pistes audio.
- **ISSUE-05 (Nettoyage de l'enregistrement en double du routeur) :** Suppression de l'inclusion redondante avec prefix `"/public"` dans `api/v1/__init__.py` pour éliminer les collisions d'identifiants OpenAPI.
- **ISSUE-06 (Protection contre le débordement de longueur de slug) :** Troncature de la base de slug à 240 caractères avant incrémentation du suffixe de collision (`VARCHAR(255)`).
- **ISSUE-07 (Couverture de tests enrichie) :** Ajout de 4 scénarios de tests couvrant le listing admin authentifié, la mise à jour/publication, le masquage des photos draft et le rejet des photos étrangères.

## Verification

- `pytest tests/test_storymaps.py` : 12/12 tests passés avec succès.
- `python3 -m unittest backend/tests/test_storymaps_logic.py` : 3/3 tests unitaires de logique passés.
- `python3 -m unittest backend/tests/test_geo_math.py` : 2/2 tests passés.
- `cd frontend && node node_modules/.bin/vue-tsc -b` : 100% OK sans erreur.

## Design Notes

- **Slug URL-friendly :** Le slug est déduit automatiquement du titre (ex: `histoire-du-tramway-1886`) avec suppression des accents et caractères spéciaux, garantissant une URL claire pour le partage et le SEO.
- **Réordonnancement atomique :** L'endpoint `PUT /api/v1/admin/storymaps/{id}/steps/reorder` reçoit un tableau d'identifiants d'étapes ordonnés `[uuid_1, uuid_2, ...]` et met à jour les champs `step_order` (0, 1, 2...) dans une seule transaction de base de données.

