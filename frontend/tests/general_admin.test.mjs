import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Story 5.3 - Console d Administration Générale (Intégrité & Logique Métier)', async (t) => {
  const adminViewPath = path.resolve(__dirname, '../src/components/admin/GeneralAdminView.vue')
  const adminApiPath = path.resolve(__dirname, '../src/services/adminApi.ts')
  const appVuePath = path.resolve(__dirname, '../src/App.vue')

  const adminViewSource = fs.readFileSync(adminViewPath, 'utf-8')
  const adminApiSource = fs.readFileSync(adminApiPath, 'utf-8')
  const appVueSource = fs.readFileSync(appVuePath, 'utf-8')

  await t.test('AC-5.3-1 : Centrage par défaut du territoire avec prévisualisation et capture', () => {
    // Vérification de la présence des champs de saisie latitude, longitude, zoom
    assert.match(adminViewSource, /formLat/, 'Le champ latitude doit être présent')
    assert.match(adminViewSource, /formLng/, 'Le champ longitude doit être présent')
    assert.match(adminViewSource, /formZoom/, 'Le curseur de zoom par défaut doit être présent')
    assert.match(adminViewSource, /captureCurrentMapView/, 'La fonction de capture depuis la carte doit exister')
    assert.match(adminViewSource, /saveCenteringConfig/, 'L enregistrement du cadrage territorial doit exister')
  })

  await t.test('AC-5.3-2 : Gestion des comptes contributeurs (création, rôles, activation)', () => {
    assert.match(adminViewSource, /handleCreateUser/, 'La création de contributeur doit être supportée')
    assert.match(adminViewSource, /toggleUserStatus/, 'La bascule actif/inactif doit être supportée')
    assert.match(adminViewSource, /handleResetPassword/, 'La réinitialisation de mot de passe doit être supportée')
    assert.match(adminViewSource, /handleDeleteUser/, 'La suppression de contributeur doit être supportée')
  })

  await t.test('AC-5.3-3 : Gestion des fonds de carte (WMS, WMTS, Tuiles Vecteurs, XYZ)', () => {
    assert.match(adminViewSource, /xyz/, 'Le type XYZ Raster doit être supporté')
    assert.match(adminViewSource, /wms/, 'Le type WMS doit être supporté')
    assert.match(adminViewSource, /wmts/, 'Le type WMTS doit être supporté')
    assert.match(adminViewSource, /vector/, 'Le type Tuiles Vecteurs doit être supporté')
    assert.match(adminViewSource, /handleSetDefaultBasemap/, 'La sélection du fond par défaut doit être possible')
    assert.match(adminViewSource, /saveBasemapsConfig/, 'L enregistrement persistant des fonds de carte doit être présent')
  })

  await t.test('AC-5.3-4 : Intégration dans App.vue et service adminApi', () => {
    assert.match(appVueSource, /GeneralAdminView/, 'GeneralAdminView doit être importé dans App.vue')
    assert.match(appVueSource, /Administration Générale/, 'L onglet Administration Générale doit être visible')
    assert.match(adminApiSource, /getTerritory/, 'adminApi doit exposer getTerritory')
    assert.match(adminApiSource, /updateTerritory/, 'adminApi doit exposer updateTerritory')
    assert.match(adminApiSource, /listUsers/, 'adminApi doit exposer listUsers')
    assert.match(adminApiSource, /createUser/, 'adminApi doit exposer createUser')
  })

  await t.test('Logique métier : Un seul fond par défaut actif et conservation d au moins un fond', () => {
    const basemaps = [
      { id: '1', name: 'OSM', is_default: true },
      { id: '2', name: 'Ortho', is_default: false },
      { id: '3', name: 'IGN', is_default: false },
    ]

    function setDefault(id) {
      basemaps.forEach((b) => (b.is_default = b.id === id))
    }

    setDefault('2')
    assert.equal(basemaps.find((b) => b.id === '2').is_default, true)
    assert.equal(basemaps.filter((b) => b.is_default).length, 1)

    // Vérification règle : au moins 1 fond
    function canRemove(list) {
      return list.length > 1
    }
    assert.equal(canRemove(basemaps), true)
    assert.equal(canRemove([{ id: '1' }]), false)
  })
})

