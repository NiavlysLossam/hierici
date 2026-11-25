---
title: 'Story 1.2: Modèle Territoire et Middleware d''Isolation Multi-Territoire'
type: 'feature'
created: '2026-10-31'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Actuellement, l'API ne possède aucune notion de territoire ni modèle de données spatial. Sans cloisonnement territorial dès la base, les futures données de photos et storymaps risqueraient d'être mélangées ou nécessiteraient une refonte lourde lors du passage au multi-domaine.

**Approach:** Créer le modèle relationnel `Territory` sous SQLAlchemy/PostGIS, initialiser le territoire pilote par défaut (seed automatique), et implémenter le middleware FastAPI qui résout le territoire actif (en-tête `X-Territory-Slug`, sous-domaine ou variable `DEFAULT_TERRITORY_SLUG`), l'injecte dans le contexte de la requête (`request.state.territory`) et expose l'endpoint `/api/v1/territory/current`.

## Boundaries & Constraints

**Always:**
- La table doit s'appeler `territories` avec les champs : `id` (UUIDv7/UUID), `slug` (string unique), `name` (string), `center_lat` (float), `center_lng` (float), `default_zoom` (int), `created_at` (datetime UTC).
- Le middleware territorial doit injecter `request.state.territory` pour les routes de l'API `/api/v1/*` (sauf `/api/health` et `/docs` qui restent neutres).
- Si un slug de territoire explicite est fourni mais n'existe pas en base, l'API doit renvoyer une erreur `HTTP 404 Not Found` au format RFC 7807 (Problem Details).
- Si la base est vierge au démarrage, le système initialise automatiquement le territoire par défaut correspondant à `DEFAULT_TERRITORY_SLUG` (ex. `"territoire-pilote"`, centré sur le territoire de Sylvain avec coordonnées par défaut).

**Never:**
- Ne pas créer de dépendance circulaire entre le middleware et les futurs modèles de photos ou d'utilisateurs.
- Ne pas autoriser de requête publique sans territoire associé (garantie d'étanchéité multi-territoire).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| :--- | :--- | :--- | :--- |
| Résolution par défaut | `GET /api/v1/territory/current` sans header | `HTTP 200` : Territoire résolu via `DEFAULT_TERRITORY_SLUG` | Crée le territoire par défaut s'il n'existe pas |
| Résolution par header valide | `GET /api/v1/territory/current` avec `X-Territory-Slug: toulon` | `HTTP 200` : Données du territoire `toulon` | N/A |
| Résolution territoire inexistant | `GET /api/v1/territory/current` avec `X-Territory-Slug: inconnu` | `HTTP 404` avec `{"error": {"code": "TERRITORY_NOT_FOUND", ...}}` | Format RFC 7807 |
| Route d'infrastructure | `GET /api/health` | `HTTP 200` sans exiger de territoire | Ignoré par le filtre territorial |

</frozen-after-approval>

## Code Map

- `backend/app/models/base.py` & `backend/app/models/territory.py` -- Modèle SQLAlchemy `Territory` et enregistrement des métadonnées
- `backend/app/schemas/territory.py` -- Schémas Pydantic `TerritoryRead` et `TerritoryCreate`
- `backend/app/core/territory.py` -- Middleware FastAPI de résolution du territoire actif et injection dans `request.state`
- `backend/app/core/init_db.py` -- Initialisation de l'extension PostGIS et création du territoire pilote initial si la base est vide
- `backend/app/api/v1/public/territory.py` -- Endpoint `GET /api/v1/territory/current` renvoyant le territoire actif
- `backend/app/main.py` -- Enregistrement du middleware territorial, des événements de démarrage et inclusion du router v1
- `backend/tests/test_territory.py` -- Tests unitaires et d'intégration validant la résolution et le format d'erreur 404

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/territory.py` -- Créer la classe modèle `Territory` avec `id`, `slug`, `name`, `center_lat`, `center_lng`, `default_zoom`
- [x] `backend/app/schemas/territory.py` -- Définir le schéma Pydantic de sérialisation pour l'API
- [x] `backend/app/core/init_db.py` -- Implémenter la création automatique des tables et le seed du territoire pilote
- [x] `backend/app/core/territory.py` -- Implémenter le middleware de résolution du territoire (`X-Territory-Slug`, sous-domaine, ou fallback)
- [x] `backend/app/api/v1/public/territory.py` -- Exposer l'endpoint `/api/v1/territory/current`
- [x] `backend/app/main.py` -- Brancher le middleware et le router territorial dans l'application FastAPI
- [x] `backend/tests/test_territory.py` -- Écrire les tests vérifiant le bon fonctionnement du middleware et des statuts 200/404

**Acceptance Criteria:**
- Given une base PostGIS initialisée
- When une requête `GET /api/v1/territory/current` est envoyée
- Then l'API renvoie HTTP 200 avec le nom, le slug et les coordonnées du territoire actif
- Given une requête avec `X-Territory-Slug: inexistant`
- When l'API traite la requête
- Then elle renvoie HTTP 404 avec une structure JSON d'erreur normalisée

## Implementation Notes

- Modèle SQLAlchemy `Territory` créé avec table `territories` et champs complets d'ancrage cartographique.
- `init_db()` s'exécute automatiquement au démarrage de FastAPI via le gestionnaire de cycle de vie `lifespan` : active PostGIS si nécessaire, génère les tables et initialise le `Territoire Pilote` si la base est vide.
- Middleware / dépendance `get_current_territory` implémenté : résout selon header `X-Territory-Slug`, sous-domaine hôte, ou variable `DEFAULT_TERRITORY_SLUG`. En cas d'inconnu, lève HTTP 404 au format RFC 7807.
- Endpoint public `/api/v1/territory/current` exposé et consommé par le frontend Vue 3.
- Tests unitaires créés dans `backend/tests/test_territory.py` couvrant les scénarios d'extraction et d'endpoints.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m py_compile backend/app/models/territory.py backend/app/schemas/territory.py backend/app/core/territory.py` -- expected: compilation sans erreur
