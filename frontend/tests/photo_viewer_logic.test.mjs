import assert from 'node:assert/strict'
import { test, describe } from 'node:test'
import {
  getUrlPhotoId,
  computePhotoUrl,
  clampZoom,
  calculateZoomToCursor,
  resolveDisplayImageUrl,
  resolveLightboxImageUrl,
} from '../src/utils/photoViewer.ts'

describe('Story 3.3 - Deep Linking & URL Synchronization Logic', () => {
  test('Extrait correctement le photoId depuis les paramètres de recherche', () => {
    const search = '?photo=018f3a5b-9d4e-7b3f-8c2a-9e1d5a7b3c2d&tab=decouverte'
    const photoId = getUrlPhotoId(search)
    assert.equal(photoId, '018f3a5b-9d4e-7b3f-8c2a-9e1d5a7b3c2d')
  })

  test('Retourne null si aucun paramètre photo n\'est présent', () => {
    const search = '?tab=decouverte'
    const photoId = getUrlPhotoId(search)
    assert.equal(photoId, null)
  })

  test('Ajoute le paramètre ?photo tout en conservant les autres paramètres', () => {
    const current = 'https://hierici.local/explore?territory=toulon'
    const updated = computePhotoUrl(current, 'uuid-456')
    assert.equal(updated, '/explore?territory=toulon&photo=uuid-456')
  })

  test('Retire le paramètre ?photo lors de la fermeture', () => {
    const current = 'https://hierici.local/explore?territory=toulon&photo=uuid-456'
    const updated = computePhotoUrl(current, null)
    assert.equal(updated, '/explore?territory=toulon')
  })

  test('Retire complètement le query string si ?photo était le seul paramètre', () => {
    const current = 'https://hierici.local/?photo=uuid-456'
    const updated = computePhotoUrl(current, null)
    assert.equal(updated, '/')
  })
})

describe('Story 3.3 - Lightbox Zoom & Pan Math', () => {
  test('Le zoom reste contraint dans les bornes autorisées [0.5, 6.0]', () => {
    assert.equal(clampZoom(0.1), 0.5)
    assert.equal(clampZoom(10.0), 6.0)
    assert.equal(clampZoom(2.5), 2.5)
  })

  test('Le zoom centré maintient le point visé sous le curseur', () => {
    // Curseur à x=100, y=50 par rapport au centre, zoom initial 1.0, pan 0,0
    const zoomIn = calculateZoomToCursor(1.0, 2.0, 100, 50, 0, 0)
    assert.equal(zoomIn.zoom, 2.0)
    // À 2x, pour que le point sous la souris reste à x=100 :
    // 100 - (100 - 0)*2 = -100
    assert.equal(zoomIn.panX, -100)
    assert.equal(zoomIn.panY, -50)

    // Dézoom inverse pour revenir au centre
    const zoomOut = calculateZoomToCursor(zoomIn.zoom, 0.5, 100, 50, zoomIn.panX, zoomIn.panY)
    assert.equal(zoomOut.zoom, 1.0)
    assert.equal(zoomOut.panX, 0)
    assert.equal(zoomOut.panY, 0)
  })

  test('Double-clic bascule entre 1x et 2.5x', () => {
    function toggleDoubleClick(currentZoom) {
      return currentZoom > 1.1 ? 1.0 : 2.5
    }
    assert.equal(toggleDoubleClick(1.0), 2.5)
    assert.equal(toggleDoubleClick(2.5), 1.0)
    assert.equal(toggleDoubleClick(4.0), 1.0)
  })
})

describe('Story 3.3 - Patrimonial Metadata & Resolution Fallbacks', () => {
  test('Résolution de l\'image d\'affichage : display en priorité, fallback sur thumb', () => {
    const photoWithDisplay = {
      image_display_url: '/media/display.webp',
      image_thumb_url: '/media/thumb.webp',
    }
    assert.equal(resolveDisplayImageUrl(photoWithDisplay), '/media/display.webp')

    const photoWithoutDisplay = {
      image_thumb_url: '/media/thumb.webp',
    }
    assert.equal(resolveDisplayImageUrl(photoWithoutDisplay), '/media/thumb.webp')
  })

  test('Résolution de la visionneuse HD : original en priorité, fallback sur display', () => {
    const photoComplete = {
      image_original_url: '/media/original.jpg',
      image_display_url: '/media/display.webp',
    }
    assert.equal(resolveLightboxImageUrl(photoComplete), '/media/original.jpg')

    const photoWithoutOriginal = {
      image_display_url: '/media/display.webp',
      image_thumb_url: '/media/thumb.webp',
    }
    assert.equal(resolveLightboxImageUrl(photoWithoutOriginal), '/media/display.webp')
  })

  test('Aucun identifiant sensible ni chemin brut de fichier n\'est requis dans la vue', () => {
    const publicPhotoProps = {
      id: 'uuid-public',
      title: 'Port de Toulon 1905',
      archive_source: 'Archives Municipales',
      archive_ref: '41Fi12',
      license: 'Domaine Public',
    }
    assert.equal(publicPhotoProps.author_user_id, undefined)
    assert.equal(publicPhotoProps.file_original_path, undefined)
    assert.equal(publicPhotoProps.license, 'Domaine Public')
  })
})
