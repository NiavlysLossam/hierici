import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { formatPhotoYear } from '../src/utils/photoDate.ts'
import { getUrlPhotoId, computePhotoUrl } from '../src/utils/photoViewer.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Story 5.2 - Découverte cartographique & Fiche latérale droite (Intégrité & Utilitaires)', async (t) => {
  const mapViewerPath = path.resolve(__dirname, '../src/components/public/PublicMapViewer.vue')
  const drawerPath = path.resolve(__dirname, '../src/components/public/PhotoDetailDrawer.vue')
  const mapViewerSource = fs.readFileSync(mapViewerPath, 'utf-8')
  const drawerSource = fs.readFileSync(drawerPath, 'utf-8')

  await t.test('AC-5.2-1 : Les marqueurs WebGL ont une icône agrandie (icon-size 1.15) et sprite 64x64', () => {
    assert.match(mapViewerSource, /'icon-size': 1\.15/, 'icon-size doit être réglé à 1.15 pour les couches de clichés')
    assert.match(mapViewerSource, /const size = 64/, 'Le canvas de génération d icône doit être de 64x64px')
    assert.match(mapViewerSource, /const radius = 18/, 'Le rayon du marqueur doit être défini à 18px')
    assert.match(mapViewerSource, /ctx\.arc\(cx, cy, radius, 0, Math\.PI \* 2\)/, 'Le cercle du marqueur doit utiliser le rayon agrandi')
    assert.match(mapViewerSource, /ctx\.lineWidth = 3/, 'Le contour blanc doit avoir une épaisseur de 3px')
  })

  await t.test('AC-5.2-2 : Élimination totale de la popup MapLibre au profit du volet latéral', () => {
    // Vérification de l'absence totale de l'ancienne popup MapLibre
    assert.ok(!mapViewerSource.includes('activePopup'), 'activePopup ne doit plus exister dans le composant')
    assert.ok(!mapViewerSource.includes('showPhotoPopup'), 'showPhotoPopup doit être totalement supprimé')
    assert.ok(!mapViewerSource.includes('.hierici-map-popup'), 'Les styles orphelins de popup doivent être purgés')

    // Vérification du volet latéral dans le template
    assert.match(mapViewerSource, /<PhotoDetailDrawer/, 'Le composant PhotoDetailDrawer doit être intégré au template')
  })

  await t.test('AC-5.2-2 (Fix Blind Hunter P1) : Le conteneur du tiroir ne s effondre pas à height 0 sur desktop', () => {
    // L'ancien bug était class="relative z-30" sans hauteur, causant une hauteur calculée de 0px sur desktop
    assert.ok(
      !drawerSource.includes('<div v-if="isOpen && photo" class="relative z-30">'),
      'Le conteneur racine ne doit pas être un div relative sans hauteur'
    )
    assert.match(
      drawerSource,
      /class="absolute inset-0 pointer-events-none z-30"/,
      'Le conteneur racine doit occuper 100% de la surface pour que aside en h-full fonctionne'
    )
  })

  await t.test('AC-5.2-3 : Suppression du badge compteur et nom de territoire en haut à droite', () => {
    assert.ok(
      !mapViewerSource.includes('Badge Décompte & Recentrage'),
      'Le bloc Badge Décompte & Recentrage doit être retiré du template'
    )
    assert.ok(
      !mapViewerSource.includes('totalPublishedCount > 0 ? \'bg-emerald-400 animate-pulse\' : \'bg-slate-500\''),
      'La pastille animée de décompte de photos ne doit plus figurer dans la barre d exploration'
    )
  })

  await t.test('AC-5.2-4 : Prise en compte rigoureuse de view_distance et is_exact_year', () => {
    // Vérification du cône avec coalescence nulle
    assert.match(
      mapViewerSource,
      /target\.properties\.view_distance \?\? 160/,
      'updateViewCone doit utiliser la coalescence nulle ?? 160'
    )
    // Vérification de la transmission dans selectPhotoById API fallback
    assert.match(
      mapViewerSource,
      /view_distance: photo\.view_distance/,
      'selectPhotoById doit transférer view_distance'
    )
    assert.match(
      mapViewerSource,
      /is_exact_year: photo\.is_exact_year/,
      'selectPhotoById doit transférer is_exact_year'
    )
  })

  await t.test('Ergonomie : Clôture du volet au clic sur cluster et sur fond de carte', () => {
    assert.match(
      mapViewerSource,
      /if \(isDrawerOpen\.value\) \{\s*closeDrawer\(\{ updateUrl: true, pushHistory: true \}\)\s*\}/,
      'Le clic sur un cluster doit fermer le volet ouvert'
    )
    assert.match(
      mapViewerSource,
      /if \(features\.length === 0\) \{\s*closeDrawer\(\{ updateUrl: true, pushHistory: true \}\)\s*\}/,
      'Le clic sur le fond de carte doit fermer le volet ouvert'
    )
  })

  await t.test('Utilitaires : Formatage d année et gestion des paramètres d URL', () => {
    assert.equal(formatPhotoYear(1914, true), '1914')
    assert.equal(formatPhotoYear(1914, false), 'Vers 1914')

    const searchWithPhoto = computePhotoUrl('http://localhost:5173/?territoire=toulon', 'uuid-abc')
    assert.equal(getUrlPhotoId(new URL(searchWithPhoto, 'http://localhost:5173').search), 'uuid-abc')

    const searchClean = computePhotoUrl('http://localhost:5173/?territoire=toulon&photo=uuid-abc', null)
    assert.equal(getUrlPhotoId(new URL(searchClean, 'http://localhost:5173').search), null)
  })
})
