import assert from 'node:assert/strict'
import { test, describe } from 'node:test'
import {
  normalizeBearing,
  clampCameraCoordinates,
  reorderStepsLocally,
  detachPhotoFromStep,
  validateAudioFile,
  renderMarkdownPreview,
} from '../src/utils/storymapStudio.ts'

// ============================================================================
// SUITE DE TESTS - Logique du Studio Storymap
// ============================================================================

describe('Story 4.2 - Logique de réordonnancement des chapitres', () => {
  const sampleSteps = [
    { id: 'step-1', title: 'Prologue', step_order: 0 },
    { id: 'step-2', title: 'Le Port Militaire', step_order: 1 },
    { id: 'step-3', title: "L'Arsenal Maritime", step_order: 2 },
    { id: 'step-4', title: 'Épilogue', step_order: 3 },
  ]

  test("Déplace l'étape 3 vers la position 1 (glisser-déposer)", () => {
    const reordered = reorderStepsLocally(sampleSteps, 2, 0)
    assert.equal(reordered.length, 4)
    assert.equal(reordered[0].id, 'step-3')
    assert.equal(reordered[0].step_order, 0)
    assert.equal(reordered[1].id, 'step-1')
    assert.equal(reordered[1].step_order, 1)
    assert.equal(reordered[2].id, 'step-2')
    assert.equal(reordered[2].step_order, 2)
    assert.equal(reordered[3].id, 'step-4')
    assert.equal(reordered[3].step_order, 3)
  })

  test("Déplace une étape d'un cran vers le haut (bouton monter)", () => {
    const reordered = reorderStepsLocally(sampleSteps, 1, 0)
    assert.equal(reordered[0].id, 'step-2')
    assert.equal(reordered[1].id, 'step-1')
    assert.equal(reordered[0].step_order, 0)
    assert.equal(reordered[1].step_order, 1)
  })

  test('Ignore les déplacements hors limites (toIndex < 0 ou toIndex >= length)', () => {
    const unchanged1 = reorderStepsLocally(sampleSteps, 0, -1)
    assert.deepEqual(unchanged1, sampleSteps)

    const unchanged2 = reorderStepsLocally(sampleSteps, 3, 4)
    assert.deepEqual(unchanged2, sampleSteps)
  })

  test("Garantit que la liste des IDs extraite pour l'API reorder est ordonnée sans perte", () => {
    const reordered = reorderStepsLocally(sampleSteps, 3, 1)
    const payloadIds = reordered.map((s) => s.id)
    assert.deepEqual(payloadIds, ['step-1', 'step-4', 'step-2', 'step-3'])
  })
})

describe('Story 4.2 - Validation et capture de la caméra cartographique 3D', () => {
  test('Borne les coordonnées extrêmes et normalise le bearing', () => {
    const captured = clampCameraCoordinates(95.5, 192.3, 26.5, 360.0, 95.0)
    assert.equal(captured.camera_lat, 90.0)
    assert.equal(captured.camera_lng, 180.0)
    assert.equal(captured.camera_zoom, 24.0)
    assert.equal(captured.camera_bearing, 0.0)
    assert.equal(captured.camera_pitch, 85.0)
  })

  test("Normalise les angles d'azimut négatifs ou supérieurs à 360°", () => {
    assert.equal(normalizeBearing(-45), 315)
    assert.equal(normalizeBearing(450), 90)
    assert.equal(normalizeBearing(360), 0)
    assert.equal(normalizeBearing(0), 0)
  })

  test('Valide les cadrages conformes', () => {
    const coords = clampCameraCoordinates(43.1242, 5.9328, 14.5, 120.0, 45.0)
    assert.equal(coords.camera_lat, 43.1242)
    assert.equal(coords.camera_lng, 5.9328)
    assert.equal(coords.camera_zoom, 14.5)
    assert.equal(coords.camera_bearing, 120.0)
    assert.equal(coords.camera_pitch, 45.0)
  })

  test('Rejette les inclinaisons pitch supérieures à 85° en les bornant', () => {
    const coords = clampCameraCoordinates(43.12, 5.93, 12.0, 0.0, 89.0)
    assert.equal(coords.camera_pitch, 85.0)
  })
})

describe("Story 4.2 - Documents sonores & dissociation de photos d'archives", () => {
  test('Accepte les fichiers audio conformes (.mp3, .m4a, .ogg, .wav <= 50Mo)', () => {
    const mp3 = validateAudioFile({ name: 'narration_chapitre1.mp3', size: 12 * 1024 * 1024, type: 'audio/mpeg' })
    assert.equal(mp3.valid, true)

    const wav = validateAudioFile({ name: 'ambiance_port.WAV', size: 45 * 1024 * 1024, type: 'audio/wav' })
    assert.equal(wav.valid, true)

    const ogg = validateAudioFile({ name: 'guide_vocal.ogg', size: 5 * 1024 * 1024, type: 'audio/ogg' })
    assert.equal(ogg.valid, true)
  })

  test('Rejette les fichiers audio dépassant 50 Mo', () => {
    const tooLarge = validateAudioFile({ name: 'long_audio.mp3', size: 52 * 1024 * 1024, type: 'audio/mpeg' })
    assert.equal(tooLarge.valid, false)
    assert.match(tooLarge.error, /50 Mo/i)
  })

  test("Rejette les formats d'extension non autorisés", () => {
    const exe = validateAudioFile({ name: 'malware.exe', size: 1024, type: 'application/octet-stream' })
    assert.equal(exe.valid, false)

    const sh = validateAudioFile({ name: 'script.sh', size: 500, type: 'text/x-shellscript' })
    assert.equal(sh.valid, false)
  })

  test('Rejette les types MIME incompatibles', () => {
    const fakeAudio = validateAudioFile({ name: 'fake.mp3', size: 1024, type: 'image/png' })
    assert.equal(fakeAudio.valid, false)
    assert.match(fakeAudio.error, /MIME/i)
  })

  test("Détache proprement une photo liée sans altérer les autres attributs de l'étape", () => {
    const stepWithPhoto = {
      id: 'step-10',
      title: 'Quai Cronstadt',
      content_markdown: 'Texte narratif',
      photo_id: 'photo-uuid-123',
      photo: { id: 'photo-uuid-123', title: 'Le Port en 1900' },
      camera_lat: 43.12,
      camera_lng: 5.93,
    }
    const detached = detachPhotoFromStep(stepWithPhoto)
    assert.equal(detached.photo_id, null)
    assert.equal(detached.photo, null)
    assert.equal(detached.title, 'Quai Cronstadt')
    assert.equal(detached.camera_lat, 43.12)
  })
})

describe('Story 4.2 - Sécurité et rendu Markdown', () => {
  test('Neutralise les balises scripts malveillantes', () => {
    const malicious = '<script>alert("hack")</script>'
    const rendered = renderMarkdownPreview(malicious)
    assert.ok(!rendered.includes('<script>'))
    assert.ok(rendered.includes('&lt;script&gt;'))
  })

  test('Rend les enrichissements typographiques (titres, gras, italique, listes, citations)', () => {
    const md = '## Titre 2\nTexte **important** et *subtil*.\n- Item liste\n> Citation'
    const rendered = renderMarkdownPreview(md)
    assert.ok(rendered.includes('<h2 class="text-lg font-bold text-sky-300 mt-4 mb-2">Titre 2</h2>'))
    assert.ok(rendered.includes('<strong class="text-white font-bold">important</strong>'))
    assert.ok(rendered.includes('<em class="text-slate-300 italic">subtil</em>'))
    assert.ok(rendered.includes('<li class="ml-4 list-disc text-slate-200">Item liste</li>'))
    assert.ok(rendered.includes('<blockquote class="border-l-4 border-sky-500 pl-3 py-1 my-2 text-slate-300 italic bg-slate-800/40 rounded-r">Citation</blockquote>'))
  })
})
