---
title: 'Story 1.3: Authentification JWT et Contrôle d''Accès RBAC'
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

**Problem:** Actuellement, l'API ne dispose d'aucun système d'authentification ni de modèle utilisateur. N'importe qui pourrait appeler de futurs endpoints d'écriture ou d'administration, violant l'exigence de traçabilité des contributeurs et de sécurité.

**Approach:** Implémenter le modèle `User` sous SQLAlchemy avec rôles (`superadmin`, `contributor`) lié à un territoire, le hachage sécurisé des mots de passe via `passlib[bcrypt]`, l'émission et vérification de tokens JWT via `python-jose`, les dépendances de sécurité FastAPI (`get_current_user`, `require_role`), les endpoints `/api/v1/auth/login` et `/api/v1/auth/me`, ainsi qu'une route de test protégée `/api/v1/admin/status`. Créer automatiquement un compte superadministrateur initial au démarrage si aucun compte n'existe.

## Boundaries & Constraints

**Always:**
- La table doit s'appeler `users` avec les champs : `id` (UUID), `territory_id` (FK vers `territories.id`, nullable=True pour le superadmin global ou rattaché au territoire), `email` (string unique, index=True), `password_hash` (string), `full_name` (string), `role` (`superadmin` ou `contributor`), `is_active` (boolean, défaut True), `created_at` (datetime UTC).
- Les mots de passe doivent être hachés avec `bcrypt` (aucun mot de passe en clair stocké).
- Le jeton JWT d'accès doit contenir : `sub` (user_id en string), `email`, `role`, `territory_id`, `exp` (expiration par défaut 24h ou configurable).
- L'accès sans token ou avec un token expiré/invalide à une route protégée doit lever `HTTP 401 Unauthorized` avec en-tête `WWW-Authenticate: Bearer`.
- Un contributeur tentant d'accéder à un endpoint réservé au rôle `superadmin` doit recevoir `HTTP 403 Forbidden`.
- Si la base est vierge d'utilisateurs au démarrage, `init_db()` génère un compte superadmin initial par défaut (identifiants configurables dans `.env` : `ADMIN_EMAIL`, `ADMIN_PASSWORD`).

**Never:**
- Ne jamais renvoyer le `password_hash` dans les réponses API (schémas Pydantic stricts).
- Ne jamais stocker de token JWT en base de données pour la simple validation d'accès (stateless).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| :--- | :--- | :--- | :--- |
| Connexion réussie | `POST /api/v1/auth/login` avec identifiants valides | `HTTP 200` : `{"access_token": "...", "token_type": "bearer", "user": {...}}` | N/A |
| Identifiants invalides | `POST /api/v1/auth/login` avec mauvais mot de passe | `HTTP 401 Unauthorized` | Message générique "Email ou mot de passe incorrect" |
| Profil connecté (`/me`) | `GET /api/v1/auth/me` avec `Authorization: Bearer <valid_token>` | `HTTP 200` : profil de l'utilisateur avec son rôle et territoire | N/A |
| Requête sans token | `GET /api/v1/admin/status` sans en-tête auth | `HTTP 401 Unauthorized` | `WWW-Authenticate: Bearer` |
| Rôle insuffisant | `GET /api/v1/admin/system` avec token de rôle `contributor` | `HTTP 403 Forbidden` | Message "Droits insuffisants pour cette action" |

</frozen-after-approval>

## Code Map

- `backend/app/models/user.py` -- Modèle SQLAlchemy `User` et énumération `UserRole`
- `backend/app/schemas/user.py` & `backend/app/schemas/auth.py` -- Schémas Pydantic (`UserRead`, `UserCreate`, `LoginRequest`, `Token`)
- `backend/app/core/security.py` -- Fonctions utilitaires de hachage de mot de passe (`hash_password`, `verify_password`) et de gestion JWT (`create_access_token`, `decode_access_token`)
- `backend/app/core/auth.py` -- Dépendances FastAPI `get_current_user`, `get_current_active_user`, `require_role`
- `backend/app/core/init_db.py` -- Seed automatique du superadmin par défaut lors de l'initialisation
- `backend/app/api/v1/auth.py` -- Endpoints `/login` et `/me`
- `backend/app/api/v1/admin/base.py` -- Router `/api/v1/admin` et routes de contrôle protégées
- `backend/app/api/v1/__init__.py` -- Enregistrement des routers auth et admin
- `backend/tests/test_auth.py` -- Tests unitaires et d'intégration couvrant le login, la protection des routes et le contrôle RBAC

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/user.py` -- Créer le modèle `User` avec `id`, `territory_id`, `email`, `password_hash`, `full_name`, `role`, `is_active`
- [x] `backend/app/schemas/user.py` & `backend/app/schemas/auth.py` -- Définir les schémas d'entrées/sorties
- [x] `backend/app/core/security.py` -- Implémenter le hachage bcrypt et la génération/décodage de tokens JWT
- [x] `backend/app/core/auth.py` -- Implémenter les dépendances de protection et de filtrage RBAC
- [x] `backend/app/core/init_db.py` -- Mettre à jour l'initialisation pour générer le compte superadmin initial
- [x] `backend/app/api/v1/auth.py` -- Créer les routes `/api/v1/auth/login` et `/api/v1/auth/me`
- [x] `backend/app/api/v1/admin/base.py` -- Créer les routes protégées d'administration
- [x] `backend/app/api/v1/__init__.py` & `backend/app/main.py` -- Intégrer les routers dans l'application
- [x] `backend/tests/test_auth.py` -- Écrire les tests unitaires automatisés validant tous les scénarios RBAC

**Acceptance Criteria:**
- Given un utilisateur enregistré en base
- When il envoie ses identifiants valides à `/api/v1/auth/login`
- Then il reçoit un token JWT de type bearer avec ses informations de rôle et territoire
- Given une route protégée sous `/api/v1/admin/*`
- When un visiteur non authentifié ou un contributeur sans les droits requis tente d'accéder
- Then le système bloque la requête avec le code HTTP approprié (401 ou 403)

## Implementation Notes

- Modèle `User` créé avec table `users`, rôles (`superadmin`, `contributor`) et clé étrangère vers `territories`.
- Hachage de mot de passe sécurisé via `passlib[bcrypt]` et génération/décodage de tokens JWT signés (HS256).
- Dépendances FastAPI `get_current_user`, `get_current_active_user` et `require_role(role)` implémentées.
- `init_db()` génère automatiquement au démarrage le compte Superadmin initial (`admin@hierici.local` / `admin_hierici_2026`) configuré dans `.env`.
- Endpoints d'authentification exposés sur `/api/v1/auth/login` et `/api/v1/auth/me`.
- Routes de test protégées créées sous `/api/v1/admin/status` (tous utilisateurs connectés) et `/api/v1/admin/superadmin/overview` (réservé superadmin).
- Suite de tests unitaires dans `backend/tests/test_auth.py` validant les statuts 401, 403 et 200.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m py_compile backend/app/models/user.py backend/app/core/security.py backend/app/core/auth.py backend/app/api/v1/auth.py` -- expected: compilation sans erreur
