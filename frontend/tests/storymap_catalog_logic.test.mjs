import assert from 'node:assert/strict'
import { test, describe } from 'node:test'
import {
  estimateReadingTime,
  formatReadingDuration,
  hasAudioContent,
  filterAndSortStorymaps,
} from '../src/utils/storymapCatalog.ts'

// ============================================================================
// SUITE DE TESTS - Logique du Catalogue Public des Récits (Story 4.4)
// ============================================================================

describe('Story 4.4 - Estimation du temps de visite (estimateReadingTime & formatReadingDuration)', () => {
  test('Calcule un temps estimé cohérent selon le nombre d\'étapes (~2.5 min/étape)', () => {
    assert.equal(estimateReadingTime(1), 3)
    assert.equal(estimateReadingTime(2), 5)
    assert.equal(estimateReadingTime(4), 10)
    assert.equal(estimateReadingTime(8), 20)
  })

  test('Gère les cas limites de nombre d\'étapes (0, négatif, NaN)', () => {
    assert.equal(estimateReadingTime(0), 2)
    assert.equal(estimateReadingTime(-3), 2)
    assert.equal(estimateReadingTime(NaN), 2)
  })

  test('Formate la durée en libellé convivial', () => {
    assert.equal(formatReadingDuration(10), '~10 min de visite')
    assert.equal(formatReadingDuration(5), '~5 min de visite')
    assert.equal(formatReadingDuration(0), '~2 min de visite')
    assert.equal(formatReadingDuration(-1), '~2 min de visite')
    assert.equal(formatReadingDuration(NaN), '~2 min de visite')
  })
})

describe('Story 4.4 - Détection des archives sonores (hasAudioContent)', () => {
  test('Retourne true si au moins une étape comporte un audio_url ou audio_file_path', () => {
    const storyWithAudio = {
      id: 's1',
      title: 'Rade de Toulon',
      steps: [
        { id: 'st1', step_order: 0, title: 'Intro' },
        { id: 'st2', step_order: 1, title: 'Arsenal', audio_url: '/media/audio.mp3' },
      ],
    }
    assert.equal(hasAudioContent(storyWithAudio), true)
  })

  test('Retourne false si aucune étape ne comporte de son', () => {
    const storyWithoutAudio = {
      id: 's2',
      title: 'Fort Balaguier',
      steps: [
        { id: 'st1', step_order: 0, title: 'Intro' },
        { id: 'st2', step_order: 1, title: 'Tour' },
      ],
    }
    assert.equal(hasAudioContent(storyWithoutAudio), false)
  })

  test('Gère les récits nuls, indéfinis ou sans étapes', () => {
    assert.equal(hasAudioContent(null), false)
    assert.equal(hasAudioContent(undefined), false)
    assert.equal(hasAudioContent({ id: 's3', title: 'Vide' }), false)
  })
})

describe('Story 4.4 - Filtrage et Tri des Récits (filterAndSortStorymaps)', () => {
  const sampleStories = [
    {
      id: '1',
      title: 'Toulon sous les bombes 1944',
      summary: 'La libération de la rade et le débarquement de Provence.',
      created_at: '2026-05-01T10:00:00Z',
      steps_count: 5,
      steps: [{ id: 'st1', audio_url: '/audio1.mp3' }],
    },
    {
      id: '2',
      title: 'L\'Arsenal Maritime à la Belle Époque',
      summary: 'Cent ans de construction navale militaire.',
      created_at: '2026-08-15T10:00:00Z',
      steps_count: 8,
      steps: [{ id: 'st2' }],
    },
    {
      id: '3',
      title: 'Balade historique à La Seyne-sur-Mer',
      summary: 'Des chantiers navals au Fort Balaguier.',
      created_at: '2026-02-10T10:00:00Z',
      steps_count: 3,
      steps: [{ id: 'st3', audio_url: '/audio3.mp3' }],
    },
  ]

  test('Filtre par recherche textuelle insensible à la casse sur le titre et le résumé', () => {
    const resTitle = filterAndSortStorymaps(sampleStories, { search: 'arsenal' })
    assert.equal(resTitle.length, 1)
    assert.equal(resTitle[0].id, '2')

    const resSummary = filterAndSortStorymaps(sampleStories, { search: 'débarquement' })
    assert.equal(resSummary.length, 1)
    assert.equal(resSummary[0].id, '1')

    // Test recherche sans accents / diacritiques ("debarquement" matche "débarquement")
    const resNoAccent = filterAndSortStorymaps(sampleStories, { search: 'debarquement' })
    assert.equal(resNoAccent.length, 1)
    assert.equal(resNoAccent[0].id, '1')

    const resAccentInsensitiveTitle = filterAndSortStorymaps(sampleStories, { search: 'epoque' })
    assert.equal(resAccentInsensitiveTitle.length, 1)
    assert.equal(resAccentInsensitiveTitle[0].id, '2')

    const resNone = filterAndSortStorymaps(sampleStories, { search: 'inconnu-xyz' })
    assert.equal(resNone.length, 0)
  })

  test('Gère le tri avec des titres manquants ou nuls', () => {
    const storiesWithNulls = [
      { id: 'a', title: null, created_at: '2026-01-01' },
      { id: 'b', title: 'Alpha', created_at: '2026-01-02' },
      { id: 'c', title: undefined, created_at: '2026-01-03' },
    ]
    const sorted = filterAndSortStorymaps(storiesWithNulls, { sortBy: 'title' })
    assert.equal(sorted.length, 3)
  })

  test('Filtre par présence de documents sonores (hasAudioOnly)', () => {
    const audioOnly = filterAndSortStorymaps(sampleStories, { hasAudioOnly: true })
    assert.equal(audioOnly.length, 2)
    const ids = audioOnly.map((s) => s.id)
    assert.ok(ids.includes('1'))
    assert.ok(ids.includes('3'))
    assert.ok(!ids.includes('2'))
  })

  test('Trie par date récente par défaut (recent)', () => {
    const sorted = filterAndSortStorymaps(sampleStories, { sortBy: 'recent' })
    assert.equal(sorted[0].id, '2') // 2026-08
    assert.equal(sorted[1].id, '1') // 2026-05
    assert.equal(sorted[2].id, '3') // 2026-02
  })

  test('Trie par nombre de chapitres décroissant (steps)', () => {
    const sorted = filterAndSortStorymaps(sampleStories, { sortBy: 'steps' })
    assert.equal(sorted[0].id, '2') // 8 chapitres
    assert.equal(sorted[1].id, '1') // 5 chapitres
    assert.equal(sorted[2].id, '3') // 3 chapitres
  })

  test('Trie par titre alphabétique (title)', () => {
    const sorted = filterAndSortStorymaps(sampleStories, { sortBy: 'title' })
    assert.equal(sorted[0].id, '3') // Balade...
    assert.equal(sorted[1].id, '2') // L'Arsenal...
    assert.equal(sorted[2].id, '1') // Toulon...
  })

  test('Gère les tableaux vides ou entrées invalides sans lever d\'exception', () => {
    assert.deepEqual(filterAndSortStorymaps(null), [])
    assert.deepEqual(filterAndSortStorymaps(undefined), [])
    assert.deepEqual(filterAndSortStorymaps([]), [])
  })
})

