---
title: 'Story 1.4: Adaptateur de Stockage Média Abstrait Local & S3'
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

**Problem:** Le backend ne dispose pas encore de mécanisme pour enregistrer, récupérer ou supprimer des fichiers multimédias de façon découplée. Si le code métier écrivait directement sur le disque, il serait impossible de basculer en production sur un stockage objet (S3, MinIO, Cloudflare R2) sans réécrire l'application.

**Approach:** Implémenter le pattern Adaptateur de Stockage (*Storage Driver*) avec une interface abstraite `StorageDriver`, une implémentation `LocalStorageDriver` (écrivant dans `/app/uploads` et servi statiquement par FastAPI) et une implémentation `S3StorageDriver` (communiquant via l'API standard S3 avec gestion d'endpoint personnalisé), ainsi qu'une factory `get_storage_driver()` et une suite de tests unitaires complète.

## Boundaries & Constraints

**Always:**
- Définir l'interface abstraite `StorageDriver` avec les méthodes asynchrones : `save(content: bytes, path: str, content_type: str = "application/octet-stream") -> str`, `read(path: str) -> bytes`, `delete(path: str) -> bool`, `exists(path: str) -> bool`, et `get_url(path: str) -> str`.
- `LocalStorageDriver` écrit dans `settings.LOCAL_STORAGE_PATH` (défaut `/app/uploads`), crée automatiquement les sous-dossiers nécessaires, et `get_url(path)` renvoie l'URL accessible `/uploads/{path}`.
- En mode local, FastAPI doit monter `/uploads` en fichiers statiques (`StaticFiles`) pour que les fichiers soient immédiatement accessibles par les navigateurs web.
- `S3StorageDriver` doit supporter tout endpoint compatible S3 (AWS S3, MinIO auto-hébergé, Cloudflare R2, Scaleway Object Storage) via `settings.S3_ENDPOINT_URL`, `settings.S3_BUCKET_NAME`, `settings.S3_ACCESS_KEY_ID`, `settings.S3_SECRET_ACCESS_KEY`.
- La factory `get_storage_driver()` doit instancier le bon pilote selon `settings.STORAGE_DRIVER` (`local` ou `s3`).

**Never:**
- Ne pas coder en dur d'appels à `open()` ou `boto3` dans les futurs services métier : tout passera par l'injection de `get_storage_driver()`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| :--- | :--- | :--- | :--- |
| Sauvegarde locale | `driver.save(b"hello", "test/file.txt")` avec driver local | Fichier créé dans `/app/uploads/test/file.txt`, retourne `/uploads/test/file.txt` | Crée les dossiers parents si absents |
| Lecture locale | `driver.read("test/file.txt")` | Retourne `b"hello"` | Lève `FileNotFoundError` si absent |
| Suppression locale | `driver.delete("test/file.txt")` | Supprime le fichier, retourne `True` | Retourne `False` si déjà inexistant |
| Vérification existence | `driver.exists("test/file.txt")` | Retourne `True` ou `False` | N/A |
| URL statique locale | `driver.get_url("photos/photo.webp")` | Retourne `/uploads/photos/photo.webp` | N/A |

</frozen-after-approval>

## Code Map

- `backend/app/services/storage/base.py` -- Interface abstraite `StorageDriver`
- `backend/app/services/storage/local.py` -- Implémentation `LocalStorageDriver`
- `backend/app/services/storage/s3.py` -- Implémentation `S3StorageDriver`
- `backend/app/services/storage/__init__.py` -- Factory `get_storage_driver()` et export des classes
- `backend/app/main.py` -- Montage statique `/uploads` quand `STORAGE_DRIVER == "local"`
- `backend/tests/test_storage.py` -- Tests unitaires validant `LocalStorageDriver` et `S3StorageDriver` (avec mocks)

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/services/storage/base.py` -- Définir l'interface abstraite `StorageDriver`
- [x] `backend/app/services/storage/local.py` -- Implémenter `LocalStorageDriver`
- [x] `backend/app/services/storage/s3.py` -- Implémenter `S3StorageDriver`
- [x] `backend/app/services/storage/__init__.py` -- Implémenter la factory `get_storage_driver()`
- [x] `backend/app/main.py` -- Monter le répertoire `/uploads` en fichiers statiques
- [x] `backend/tests/test_storage.py` -- Rédiger les tests unitaires couvrant les opérations de stockage

**Acceptance Criteria:**
- Given la configuration par défaut avec `STORAGE_DRIVER=local`
- When un fichier est sauvegardé via le pilote
- Then le fichier est écrit sur le disque dans le volume `/app/uploads` et accessible en lecture par son URL `/uploads/...`
- Given une opération de suppression sur un fichier existant
- When la méthode `delete()` est invoquée
- Then le fichier est effacé du stockage et `exists()` renvoie False

## Implementation Notes

- Interface `StorageDriver` définie avec méthodes asynchrones (`save`, `read`, `delete`, `exists`, `get_url`).
- `LocalStorageDriver` gère l'écriture sécurisée dans `LOCAL_STORAGE_PATH` (avec protection contre path traversal) et génère des URLs relatives `/uploads/...`.
- `S3StorageDriver` interagit avec l'API AWS S3 standard via `boto3`, supportant les buckets cloud (Scaleway, Cloudflare R2, MinIO, AWS).
- `get_storage_driver()` instancie dynamiquement le bon pilote en cache selon `settings.STORAGE_DRIVER`.
- FastAPI monte `/uploads` en fichiers statiques (`StaticFiles`) lorsque le mode local est actif.
- Tests unitaires complets dans `backend/tests/test_storage.py` couvrant les deux implémentations.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 -m py_compile backend/app/services/storage/*.py` -- expected: compilation sans erreur
