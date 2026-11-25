import assert from 'node:assert/strict'
import { test, describe } from 'node:test'
import { createViewConePolygon } from '../src/utils/geo.ts'
import { formatPhotoYear } from '../src/utils/photoDate.ts'

describe('Story 5.1 - Formatage de la datation avec certitude archivistique', () => {
  test('Affiche l\'année directe si is_exact_year est true', () => {
    assert.equal(formatPhotoYear(1914, true), '1914')
    assert.equal(formatPhotoYear(1895, true), '1895')
  })

  test('Préfixe par « Vers » si is_exact_year est false', () => {
    assert.equal(formatPhotoYear(1914, false), 'Vers 1914')
    assert.equal(formatPhotoYear(1900, false), 'Vers 1900')
  })

  test('Gère les cas limites (null, undefined, NaN)', () => {
    assert.equal(formatPhotoYear(null, true), null)
    assert.equal(formatPhotoYear(undefined, false), null)
    assert.equal(formatPhotoYear(NaN, true), null)
  })
})

describe('Story 5.1 - Projection métrique personnalisée du cône de vue', () => {
  test('Génère un cône avec distance métrique personnalisée', () => {
    const coneShort = createViewConePolygon(5.928, 43.124, 90, 60, 50)
    assert.equal(coneShort.properties.distance, 50)
    assert.equal(coneShort.geometry.type, 'Polygon')
    assert.ok(coneShort.geometry.coordinates[0].length > 3)

    const coneLong = createViewConePolygon(5.928, 43.124, 90, 60, 850)
    assert.equal(coneLong.properties.distance, 850)
    assert.equal(coneLong.geometry.type, 'Polygon')
  })
})

