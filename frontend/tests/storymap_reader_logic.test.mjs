import assert from 'node:assert/strict'
import { test, describe } from 'node:test'
import {
  extractStorymapSlug,
  cleanStorymapUrl,
  getValidCameraTarget,
  calculateStepProgress,
  formatStepBadge,
  shouldStopAudioOnStepChange,
  formatAudioDuration,
} from '../src/utils/storymapReader.ts'

// ============================================================================
// SUITE DE TESTS - Logique du Lecteur Public de Storymap (Story 4.3)
// ============================================================================

describe('Story 4.3 - Extraction du slug de storymap (extractStorymapSlug)', () => {
  test('Extrait le slug depuis un query string simple ?storymap=rade-de-toulon', () => {
    assert.equal(extractStorymapSlug('?storymap=rade-de-toulon'), 'rade-de-toulon')
    assert.equal(extractStorymapSlug('?photo=123&storymap=rade-de-toulon'), 'rade-de-toulon')
    assert.equal(extractStorymapSlug('storymap=rade-de-toulon'), 'rade-de-toulon')
  })

  test('Extrait le slug depuis une instance URLSearchParams', () => {
    const params = new URLSearchParams('storymap=fort-de-balaguier&tab=decouverte')
    assert.equal(extractStorymapSlug(params), 'fort-de-balaguier')
  })

  test('Extrait le slug depuis un objet type Location (avec propriété search)', () => {
    const fakeLocation = { search: '?storymap=toulon-1944' }
    assert.equal(extractStorymapSlug(fakeLocation), 'toulon-1944')
  })

  test('Extrait le slug depuis un objet Location ayant un pathname /storymaps/slug et search vide (HUNTER-4.3-2)', () => {
    const fakeLocation = { pathname: '/storymaps/rade-de-toulon', search: '' }
    assert.equal(extractStorymapSlug(fakeLocation), 'rade-de-toulon')
  })

  test('Extrait le slug depuis une URL contenant une ancre fragment # (Verification Gap)', () => {
    assert.equal(extractStorymapSlug('?storymap=rade-de-toulon#chapitre-1'), 'rade-de-toulon')
    assert.equal(extractStorymapSlug('https://hierici.local/?storymap=rade-de-toulon#intro'), 'rade-de-toulon')
    assert.equal(extractStorymapSlug('/storymaps/rade-de-toulon#photos'), 'rade-de-toulon')
  })

  test('Extrait le slug depuis un chemin d\'accès /storymaps/rade-de-toulon', () => {
    assert.equal(extractStorymapSlug('/storymaps/rade-de-toulon'), 'rade-de-toulon')
    assert.equal(extractStorymapSlug('/storymaps/rade-de-toulon/'), 'rade-de-toulon')
  })

  test('Extrait le slug direct en texte brut', () => {
    assert.equal(extractStorymapSlug('rade-de-toulon-1944'), 'rade-de-toulon-1944')
  })

  test('Retourne null si la chaîne est vide, invalide ou sans paramètre storymap', () => {
    assert.equal(extractStorymapSlug(null), null)
    assert.equal(extractStorymapSlug(undefined), null)
    assert.equal(extractStorymapSlug(''), null)
    assert.equal(extractStorymapSlug('?photo=123'), null)
    assert.equal(extractStorymapSlug('https://example.com/'), null)
    assert.equal(extractStorymapSlug('?storymap='), null)
    assert.equal(extractStorymapSlug('?storymap=   '), null)
  })
})

describe('Story 4.3 - Nettoyage et synchronisation d\'URL (cleanStorymapUrl)', () => {
  test('Retire le paramètre storymap et conserve les autres paramètres', () => {
    const url = 'https://hierici.local/?photo=photo-123&storymap=rade-de-toulon'
    const cleaned = cleanStorymapUrl(url)
    assert.equal(cleaned, 'https://hierici.local/?photo=photo-123')
  })

  test('Nettoie complètement le query string s\'il ne contenait que storymap', () => {
    const url = 'https://hierici.local/?storymap=rade-de-toulon'
    const cleaned = cleanStorymapUrl(url)
    assert.equal(cleaned, 'https://hierici.local/')
  })

  test('Préserve le fragment d\'ancre #', () => {
    const url = '/carte?storymap=toulon#vue'
    const cleaned = cleanStorymapUrl(url)
    assert.equal(cleaned, '/carte#vue')
  })
})

describe('Story 4.3 - Normalisation et validation de caméra cible (getValidCameraTarget)', () => {
  const fallback = { lat: 43.12, lng: 5.93, zoom: 12, bearing: 0, pitch: 0 }

  test('Extrait correctement les coordonnées de caméra standard', () => {
    const step = {
      camera_lat: 43.115432,
      camera_lng: 5.923456,
      camera_zoom: 15.5,
      camera_bearing: 180,
      camera_pitch: 45,
    }
    const target = getValidCameraTarget(step, fallback)
    assert.deepEqual(target, {
      lat: 43.115432,
      lng: 5.923456,
      zoom: 15.5,
      bearing: 180,
      pitch: 45,
    })
  })

  test('Supporte les alias courts (lat, lng, zoom, bearing, pitch)', () => {
    const step = {
      lat: 43.10,
      lng: 5.90,
      zoom: 14,
      bearing: 90,
      pitch: 30,
    }
    const target = getValidCameraTarget(step, fallback)
    assert.equal(target.lat, 43.1)
    assert.equal(target.lng, 5.9)
    assert.equal(target.zoom, 14)
    assert.equal(target.bearing, 90)
    assert.equal(target.pitch, 30)
  })

  test('Clampe les valeurs hors limites (zoom > 24, pitch > 85, bearing >= 360)', () => {
    const step = {
      camera_lat: 95.0,
      camera_lng: -190.0,
      camera_zoom: 30.0,
      camera_bearing: 360.0,
      camera_pitch: 90.0,
    }
    const target = getValidCameraTarget(step, fallback)
    assert.equal(target.lat, 90)
    assert.equal(target.lng, -180)
    assert.equal(target.zoom, 24)
    assert.equal(target.bearing, 0)
    assert.equal(target.pitch, 85)
  })

  test('Utilise le repli (fallback) si l\'étape est vide ou incomplète', () => {
    const targetNull = getValidCameraTarget(null, fallback)
    assert.deepEqual(targetNull, fallback)

    const stepPartial = { camera_lat: 44.0 }
    const targetPartial = getValidCameraTarget(stepPartial, fallback)
    assert.equal(targetPartial.lat, 44.0)
    assert.equal(targetPartial.lng, fallback.lng)
    assert.equal(targetPartial.zoom, fallback.zoom)
  })
})

describe('Story 4.3 - Progression de lecture et badge d\'étape', () => {
  test('Calcule le pourcentage de progression selon l\'index et le nombre d\'étapes', () => {
    assert.equal(calculateStepProgress(0, 5), 0)
    assert.equal(calculateStepProgress(1, 5), 25)
    assert.equal(calculateStepProgress(2, 5), 50)
    assert.equal(calculateStepProgress(3, 5), 75)
    assert.equal(calculateStepProgress(4, 5), 100)
  })

  test('Gère les cas limites de progression (1 étape, 0 étape, index négatif, épilogue index >= total)', () => {
    assert.equal(calculateStepProgress(-1, 5), 0)
    assert.equal(calculateStepProgress(0, 1), 100)
    assert.equal(calculateStepProgress(0, 0), 0)
    assert.equal(calculateStepProgress(999, 4), 100)
  })

  test('Formate les libellés de badges pour chaque chapitre et conclusion', () => {
    assert.equal(formatStepBadge(-1, 4), 'Introduction')
    assert.equal(formatStepBadge(0, 4), 'Chapitre 1 sur 4')
    assert.equal(formatStepBadge(3, 4), 'Chapitre 4 sur 4')
    assert.equal(formatStepBadge(4, 4), 'Conclusion')
    assert.equal(formatStepBadge(999, 4), 'Conclusion')
    assert.equal(formatStepBadge(0, 0), 'Étape 1')
  })
})

describe('Story 4.3 - Règles d\'interruption sonore (shouldStopAudioOnStepChange)', () => {
  test('Interrompt l\'audio si une piste est active et que l\'étape change', () => {
    assert.equal(shouldStopAudioOnStepChange(0, 1, true), true)
    assert.equal(shouldStopAudioOnStepChange(2, 0, true), true)
  })

  test('N\'interrompt pas si aucune piste n\'est active', () => {
    assert.equal(shouldStopAudioOnStepChange(0, 1, false), false)
  })

  test('Ne coupe pas si l\'étape reste identique', () => {
    assert.equal(shouldStopAudioOnStepChange(1, 1, true), false)
  })
})

describe('Story 4.3 - Formatage de durée audio (formatAudioDuration)', () => {
  test('Formate les secondes en mm:ss', () => {
    assert.equal(formatAudioDuration(0), '0:00')
    assert.equal(formatAudioDuration(5), '0:05')
    assert.equal(formatAudioDuration(65), '1:05')
    assert.equal(formatAudioDuration(125), '2:05')
    assert.equal(formatAudioDuration(3600), '60:00')
  })

  test('Gère les entrées invalides, négatives ou Infinity (HUNTER-4.3-8)', () => {
    assert.equal(formatAudioDuration(-10), '0:00')
    assert.equal(formatAudioDuration(NaN), '0:00')
    assert.equal(formatAudioDuration(Infinity), '0:00')
    assert.equal(formatAudioDuration(-Infinity), '0:00')
  })
})
