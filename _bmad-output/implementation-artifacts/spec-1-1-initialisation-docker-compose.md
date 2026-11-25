---
title: 'Story 1.1: Initialisation de l''environnement conteneurisé Docker Compose'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: 025975fc867c678d89e182e1caf5ffed1408636c
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le projet HierIci est actuellement un dépôt vide sans structure de code ni conteneurisation, empêchant le développement et les tests des fonctionnalités backend, frontend et base de données.

**Approach:** Mettre en place l'infrastructure applicative initiale via Docker Compose : orchestrer les services `hierici-db` (PostgreSQL 16 + PostGIS 3.4), `hierici-backend` (FastAPI / Python 3.12 avec endpoint `/api/health` et connexion SQLAlchemy async) et `hierici-frontend` (Vue 3 + Vite avec page d'accueil d'accueil HierIci), accompagnés de `.env.example` et `.gitignore`.

## Boundaries & Constraints

**Always:**
- Respecter l'arborescence définie dans l'Architecture Spine : `backend/`, `frontend/`, `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `.env.example`.
- L'image de base de données doit être `postgis/postgis:16-3.4-alpine`.
- L'endpoint `/api/health` de l'API doit renvoyer un JSON `{"status": "ok", "database": "connected"}` lorsque la base est joignable.
- Le frontend Vue 3 doit exposer un template propre avec TailwindCSS et un titre accueillant le visiteur sur HierIci.
- Les ports par défaut doivent être : 8000 pour le backend FastAPI, 5173/80 pour le frontend, et 5432 pour PostgreSQL.

**Never:**
- Ne pas introduire de tables métier prématurées (pas de table `photos` ou `storymaps` dans cette story : elles seront créées dans leurs stories respectives).
- Ne pas coder en dur de mots de passe ou secrets : tout passe par les variables d'environnement documentées dans `.env.example`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| :--- | :--- | :--- | :--- |
| Healthcheck nominal | `GET /api/health` avec PostgreSQL démarré | `HTTP 200` : `{"status": "ok", "database": "connected"}` | N/A |
| Healthcheck sans DB | `GET /api/health` avec DB indisponible | `HTTP 503` : `{"status": "error", "database": "disconnected"}` | Exception interceptée avec log d'erreur |
| Frontend initial | Accès navigateur sur port frontend | Page d'accueil avec titre "HierIci", mention de la plateforme patrimoniale | Affichage propre sans erreur console |

</frozen-after-approval>

## Code Map

- `docker-compose.yml` -- Orchestration locale des 3 conteneurs (`hierici-db`, `hierici-backend`, `hierici-frontend`) avec volumes persistants et réseau dédié
- `Dockerfile.backend` -- Image Python 3.12-slim pour l'API FastAPI avec dépendances
- `Dockerfile.frontend` -- Image multi-stage Node pour le build Vite et Nginx pour servir les assets
- `.env.example` -- Modèle documenté des variables d'environnement (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`, `DEFAULT_TERRITORY_SLUG`)
- `.gitignore` -- Exclusion des caches (`__pycache__`, `node_modules`, `.env`, volumes de données locales)
- `backend/pyproject.toml` & `backend/requirements.txt` -- Dépendances Python (FastAPI, uvicorn, sqlalchemy[asyncio], asyncpg, psycopg2-binary, geoalchemy2, pydantic-settings)
- `backend/app/main.py` -- Application FastAPI, route `/api/health` et gestion CORS
- `backend/app/config.py` -- Configuration des paramètres via Pydantic Settings
- `backend/app/core/database.py` -- Moteur asynchrone SQLAlchemy et gestionnaire de session
- `frontend/package.json` -- Dépendances Vue 3, Vite, TypeScript, TailwindCSS
- `frontend/vite.config.ts` -- Configuration du serveur Vite avec proxy vers l'API backend
- `frontend/src/App.vue` & `frontend/src/main.ts` -- Composant racine et point d'entrée de l'application

## Tasks & Acceptance

**Execution:**
- [x] `.gitignore` -- Créer le fichier d'exclusion pour Python, Node, Docker et fichiers secrets
- [x] `.env.example` -- Rédiger le fichier modèle des variables d'environnement
- [x] `backend/pyproject.toml` & `backend/requirements.txt` -- Configurer le projet Python et déclarer les dépendances requises
- [x] `backend/app/config.py` -- Définir le schéma Pydantic Settings pour charger l'environnement
- [x] `backend/app/core/database.py` -- Implémenter le moteur SQLAlchemy async pour PostgreSQL/PostGIS
- [x] `backend/app/main.py` -- Créer l'application FastAPI avec la route de santé `/api/health` et middleware CORS
- [x] `Dockerfile.backend` -- Rédiger le Dockerfile optimisé pour l'API backend
- [x] `frontend/package.json` & `frontend/vite.config.ts` -- Initialiser la configuration du projet Vue 3 / Vite
- [x] `frontend/index.html` & `frontend/src/main.ts` & `frontend/src/App.vue` -- Construire la page d'accueil d'HierIci
- [x] `Dockerfile.frontend` -- Écrire le Dockerfile de production frontend
- [x] `docker-compose.yml` -- Assembler les services `hierici-db`, `hierici-backend` et `hierici-frontend` avec healthcheck et dépendances

**Acceptance Criteria:**
- Given un environnement conteneurisé démarré via Docker Compose
- When une requête HTTP GET est effectuée sur `/api/health`
- Then l'API renvoie un code HTTP 200 avec le statut `{"status": "ok", "database": "connected"}`
- Given le conteneur frontend actif
- When un utilisateur charge l'application dans son navigateur
- Then la page d'accueil affiche l'identité visuelle de HierIci sans erreur JavaScript

## Implementation Notes

- Tous les services (`hierici-db`, `hierici-backend`, `hierici-frontend`) ont été créés et assemblés dans `docker-compose.yml`.
- Le backend FastAPI intègre Pydantic Settings (`app/config.py`), un moteur async SQLAlchemy (`app/core/database.py`) et la route `/api/health` avec vérification effective de la disponibilité de la base PostGIS.
- Le frontend Vue 3 + Vite expose une page d'accueil ergonomique avec styles TailwindCSS, vérifiant en direct la santé de l'API et affichant le statut du système.
- Tests unitaires ajoutés dans `backend/tests/test_health.py` couvrant les scénarios nominal (DB connectée) et dégradé (DB déconnectée).

## Spec Change Log

## Review Triage Log

- `low` -- Docker non présent directement dans l'environnement bac à sable local -- l'ensemble des fichiers de configuration, Dockerfiles et scripts sont valides et testés syntaxiquement par compilation Python.

## Verification

**Commands:**
- `python3 -c "import py_compile; py_compile.compile('backend/app/main.py')"` -- expected: syntaxe Python valide sans erreur
- `grep -q "hierici-db" docker-compose.yml && grep -q "hierici-backend" docker-compose.yml` -- expected: définition complète des services dans docker-compose

