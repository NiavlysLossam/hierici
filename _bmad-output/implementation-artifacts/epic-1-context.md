# Epic 1 Context: Socle Territorial, Authentification et Stockage Média

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Mettre en place le socle applicatif conteneurisé de HierIci, permettant aux administrateurs et contributeurs de s'authentifier de façon sécurisée, d'isoler strictement les données par territoire (multi-tenancy) et de manipuler les fichiers multimédias au travers d'un adaptateur de stockage hybride (disque local ou bucket S3).

## Stories

- Story 1.1: Initialisation de l'environnement conteneurisé Docker Compose
- Story 1.2: Modèle Territoire et Middleware d'Isolation Multi-Territoire
- Story 1.3: Authentification JWT et Contrôle d'Accès RBAC
- Story 1.4: Adaptateur de Stockage Média Abstrait Local & S3

## Requirements & Constraints

- **Multi-territoire natif** : Toutes les données doivent être cloisonnées par `territory_id`. Les requêtes publiques sont automatiquement filtrées sur le territoire actif résolu par middleware (en-tête, sous-domaine ou variable `DEFAULT_TERRITORY_SLUG`).
- **Authentification & Sécurité** : Mots de passe hachés avec Argon2id ou bcrypt. Tokens JWT avec rôle utilisateur (`superadmin`, `contributor`). Protection rate-limiting contre les attaques par force brute.
- **Stockage hybride** : Le stockage des fichiers doit être découplé du code métier via une interface abstraite `StorageDriver` avec implémentations `LocalStorageDriver` et `S3StorageDriver`.
- **Licence** : Code source sous licence libre MIT.

## Technical Decisions

- **Stack** : FastAPI (Python 3.12+), PostgreSQL 16 + PostGIS 3.4, SQLAlchemy 2.0 (async), Vue 3 + Vite.
- **Conteneurisation** : `docker-compose.yml` orchestrant les conteneurs `hierici-db`, `hierici-backend` et `hierici-frontend`.
- **Conventions d'API** : URLs REST au pluriel (`/api/v1/...`), corps JSON en camelCase, gestion d'erreurs au format RFC 7807 (Problem Details).

## Cross-Story Dependencies

- Story 1.1 (Docker & stack de base) est le prérequis indispensable pour l'exécution des Stories 1.2, 1.3 et 1.4.
- Story 1.2 (Territoire & middleware) est requise par Story 1.3 pour lier les utilisateurs à un territoire.

