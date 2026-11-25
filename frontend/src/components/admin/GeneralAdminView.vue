<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { adminApi } from '@/services/adminApi'
import type {
  TerritoryAdmin,
  BasemapConfig,
  AdminUser,
  BasemapType,
} from '@/types/admin'

const props = defineProps<{
  currentUserEmail?: string
}>()

const activeTab = ref<'centering' | 'users' | 'basemaps'>('centering')

// État Territoire & Centrage
const loading = ref(false)
const savingTerritory = ref(false)
const territory = ref<TerritoryAdmin | null>(null)
const formName = ref('')
const formLat = ref(43.1242)
const formLng = ref(5.928)
const formZoom = ref(13)

// Mini-carte MapLibre
const mapContainer = ref<HTMLDivElement | null>(null)
let previewMap: maplibregl.Map | null = null

// État Utilisateurs / Contributeurs
const users = ref<AdminUser[]>([])
const loadingUsers = ref(false)
const isCreateUserModalOpen = ref(false)
const isResetPasswordModalOpen = ref(false)
const selectedUserForReset = ref<AdminUser | null>(null)
const newPasswordInput = ref('')

const newUserForm = ref({
  full_name: '',
  email: '',
  password: '',
})

// État Fonds de Carte
const basemaps = ref<BasemapConfig[]>([])
const savingBasemaps = ref(false)
const isAddBasemapOpen = ref(false)

const newBasemapForm = ref<{
  name: string
  type: BasemapType
  url: string
  attribution: string
  is_default: boolean
}>({
  name: '',
  type: 'xyz',
  url: '',
  attribution: '',
  is_default: false,
})

// Toast notification
const toastMessage = ref<string | null>(null)
const toastType = ref<'success' | 'error'>('success')
let toastTimer: any = null

function showToast(msg: string, type: 'success' | 'error' = 'success') {
  toastMessage.value = msg
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastMessage.value = null
  }, 4000)
}

async function loadTerritoryData() {
  loading.value = true
  try {
    const data = await adminApi.getTerritory()
    territory.value = data
    formName.value = data.name
    formLat.value = data.center_lat
    formLng.value = data.center_lng
    formZoom.value = data.default_zoom
    basemaps.value = JSON.parse(JSON.stringify(data.basemaps || []))

    await nextTick()
    initPreviewMap()
  } catch (err: any) {
    showToast(err.message || 'Erreur lors du chargement de la configuration.', 'error')
  } finally {
    loading.value = false
  }
}

async function loadUsersData() {
  loadingUsers.value = true
  try {
    users.value = await adminApi.listUsers()
  } catch (err: any) {
    showToast(err.message || 'Erreur lors du chargement des contributeurs.', 'error')
  } finally {
    loadingUsers.value = false
  }
}

function initPreviewMap() {
  if (!mapContainer.value) return
  if (previewMap) {
    previewMap.remove()
    previewMap = null
  }

  const defaultBasemap = basemaps.value.find((b) => b.is_default) || basemaps.value[0]
  const tileUrl = defaultBasemap?.url || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

  const mapStyle: maplibregl.StyleSpecification = {
    version: 8,
    sources: {
      'preview-tiles': {
        type: 'raster',
        tiles: [tileUrl],
        tileSize: 256,
        attribution: defaultBasemap?.attribution || '© OpenStreetMap contributors',
      },
    },
    layers: [
      {
        id: 'preview-layer',
        type: 'raster',
        source: 'preview-tiles',
      },
    ],
  }

  previewMap = new maplibregl.Map({
    container: mapContainer.value,
    style: mapStyle,
    center: [formLng.value, formLat.value],
    zoom: formZoom.value,
  })

  previewMap.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')

  // Marqueur du centre
  new maplibregl.Marker({ color: '#0284c7' })
    .setLngLat([formLng.value, formLat.value])
    .addTo(previewMap)
}

function captureCurrentMapView() {
  if (!previewMap) return
  const center = previewMap.getCenter()
  const zoom = Math.round(previewMap.getZoom())
  formLat.value = Number(center.lat.toFixed(6))
  formLng.value = Number(center.lng.toFixed(6))
  formZoom.value = zoom
  showToast('Cadrage capturé depuis la carte !')
}

async function saveCenteringConfig() {
  if (!territory.value) return
  savingTerritory.value = true
  try {
    const updated = await adminApi.updateTerritory({
      name: formName.value.trim(),
      center_lat: formLat.value,
      center_lng: formLng.value,
      default_zoom: formZoom.value,
    })
    territory.value = updated
    showToast('Cadrage territorial enregistré avec succès !')
  } catch (err: any) {
    showToast(err.message || 'Impossible d enregistrer le cadrage.', 'error')
  } finally {
    savingTerritory.value = false
  }
}

async function handleCreateUser() {
  if (!newUserForm.value.email || !newUserForm.value.password || !newUserForm.value.full_name) {
    showToast('Veuillez renseigner tous les champs.', 'error')
    return
  }
  try {
    const created = await adminApi.createUser({
      email: newUserForm.value.email,
      password: newUserForm.value.password,
      full_name: newUserForm.value.full_name,
      role: 'contributor',
    })
    users.value.unshift(created)
    isCreateUserModalOpen.value = false
    newUserForm.value = { email: '', password: '', full_name: '' }
    showToast('Contributeur créé avec succès !')
  } catch (err: any) {
    showToast(err.message || 'Erreur lors de la création du contributeur.', 'error')
  }
}

async function toggleUserStatus(user: AdminUser) {
  try {
    const updated = await adminApi.updateUser(user.id, {
      is_active: !user.is_active,
    })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
    showToast(`Compte ${updated.is_active ? 'activé' : 'désactivé'} avec succès.`)
  } catch (err: any) {
    showToast(err.message || 'Action impossible sur ce compte.', 'error')
  }
}

function openResetPasswordModal(user: AdminUser) {
  selectedUserForReset.value = user
  newPasswordInput.value = ''
  isResetPasswordModalOpen.value = true
}

async function handleResetPassword() {
  if (!selectedUserForReset.value || !newPasswordInput.value.trim()) return
  try {
    await adminApi.updateUser(selectedUserForReset.value.id, {
      password: newPasswordInput.value.trim(),
    })
    isResetPasswordModalOpen.value = false
    showToast('Mot de passe mis à jour avec succès !')
  } catch (err: any) {
    showToast(err.message || 'Erreur lors de la réinitialisation.', 'error')
  }
}

async function handleDeleteUser(user: AdminUser) {
  if (!confirm(`Êtes-vous sûr de vouloir supprimer le compte de ${user.full_name} (${user.email}) ?`)) {
    return
  }
  try {
    await adminApi.deleteUser(user.id)
    users.value = users.value.filter((u) => u.id !== user.id)
    showToast('Compte contributeur supprimé.')
  } catch (err: any) {
    showToast(err.message || 'Impossible de supprimer ce compte.', 'error')
  }
}

function handleSetDefaultBasemap(bmId: string) {
  basemaps.value.forEach((b) => {
    b.is_default = b.id === bmId
  })
}

function handleRemoveBasemap(bmId: string) {
  if (basemaps.value.length <= 1) {
    showToast('Le territoire doit conserver au moins un fond de carte.', 'error')
    return
  }
  basemaps.value = basemaps.value.filter((b) => b.id !== bmId)
  if (!basemaps.value.some((b) => b.is_default)) {
    basemaps.value[0].is_default = true
  }
}

function handleAddBasemap() {
  if (!newBasemapForm.value.name.trim() || !newBasemapForm.value.url.trim()) {
    showToast('Veuillez renseigner le nom et l URL du flux.', 'error')
    return
  }
  const newBm: BasemapConfig = {
    id: `bm-${Date.now()}`,
    name: newBasemapForm.value.name.trim(),
    type: newBasemapForm.value.type,
    url: newBasemapForm.value.url.trim(),
    attribution: newBasemapForm.value.attribution.trim() || null,
    is_default: newBasemapForm.value.is_default,
  }
  if (newBm.is_default) {
    basemaps.value.forEach((b) => (b.is_default = false))
  }
  basemaps.value.push(newBm)
  newBasemapForm.value = {
    name: '',
    type: 'xyz',
    url: '',
    attribution: '',
    is_default: false,
  }
  isAddBasemapOpen.value = false
  showToast('Fond de carte ajouté à la liste locale. Pensez à enregistrer !')
}

async function saveBasemapsConfig() {
  savingBasemaps.value = true
  try {
    const updated = await adminApi.updateTerritory({
      basemaps: basemaps.value,
    })
    territory.value = updated
    basemaps.value = JSON.parse(JSON.stringify(updated.basemaps || []))
    initPreviewMap()
    showToast('Fonds de carte enregistrés avec succès !')
  } catch (err: any) {
    showToast(err.message || 'Erreur lors de l enregistrement des fonds de carte.', 'error')
  } finally {
    savingBasemaps.value = false
  }
}

function handleTabChange(tab: 'centering' | 'users' | 'basemaps') {
  activeTab.value = tab
  if (tab === 'centering') {
    nextTick(() => {
      if (previewMap) previewMap.resize()
      else initPreviewMap()
    })
  } else if (tab === 'users') {
    loadUsersData()
  }
}

onMounted(() => {
  loadTerritoryData()
})

onUnmounted(() => {
  if (previewMap) {
    previewMap.remove()
    previewMap = null
  }
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8 space-y-6">
    <!-- En-tête -->
    <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
      <div>
        <h1 class="text-2xl font-bold text-white flex items-center gap-2">
          <span>⚙️</span> Administration Générale
        </h1>
        <p class="text-sm text-slate-400 mt-1">
          Cadrage géographique, gestion des accès contributeurs et sources cartographiques du territoire.
        </p>
      </div>

      <!-- Navigation par onglets -->
      <div class="flex items-center gap-1 bg-slate-900 p-1.5 rounded-xl border border-slate-800">
        <button
          type="button"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
          :class="activeTab === 'centering' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'"
          @click="handleTabChange('centering')"
        >
          <span>🎯</span> Centrage Carte
        </button>
        <button
          type="button"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
          :class="activeTab === 'users' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'"
          @click="handleTabChange('users')"
        >
          <span>👥</span> Contributeurs
        </button>
        <button
          type="button"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
          :class="activeTab === 'basemaps' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'"
          @click="handleTabChange('basemaps')"
        >
          <span>🗺️</span> Fonds de Carte
        </button>
      </div>
    </div>

    <!-- Toast Notification -->
    <div
      v-if="toastMessage"
      class="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl border shadow-2xl flex items-center gap-3 text-sm animate-fade-in"
      :class="toastType === 'success' ? 'bg-emerald-950 border-emerald-600/80 text-emerald-200' : 'bg-rose-950 border-rose-600/80 text-rose-200'"
    >
      <span>{{ toastType === 'success' ? '✅' : '⚠️' }}</span>
      <span>{{ toastMessage }}</span>
      <button type="button" class="ml-2 hover:opacity-80" @click="toastMessage = null">✕</button>
    </div>

    <!-- Onglet 1 : Cadrage Cartographique -->
    <div v-show="activeTab === 'centering'" class="space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Formulaire de cadrage -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <h2 class="text-base font-semibold text-white flex items-center gap-2">
            <span>🎯</span> Coordonnées et Zoom initial
          </h2>
          <p class="text-xs text-slate-400 leading-relaxed">
            Ces paramètres définissent la position par défaut affichée aux visiteurs lors de l'ouverture de la carte découverte et des récits.
          </p>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Nom du territoire</label>
            <input
              v-model="formName"
              type="text"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Latitude</label>
              <input
                v-model.number="formLat"
                type="number"
                min="-90"
                max="90"
                step="0.0001"
                class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:border-sky-500 focus:outline-none"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Longitude</label>
              <input
                v-model.number="formLng"
                type="number"
                min="-180"
                max="180"
                step="0.0001"
                class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:border-sky-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between text-xs text-slate-300 mb-1">
              <span>Zoom par défaut</span>
              <span class="font-bold text-sky-400">Niveau {{ formZoom }}</span>
            </div>
            <input
              v-model.number="formZoom"
              type="range"
              min="1"
              max="22"
              class="w-full accent-sky-500 cursor-pointer"
            />
          </div>

          <div class="pt-2 flex flex-col gap-2">
            <button
              type="button"
              class="w-full px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-xl text-xs font-semibold border border-slate-700 transition-colors flex items-center justify-center gap-2"
              @click="captureCurrentMapView"
            >
              <span>📸</span> Capturer la vue actuelle de la carte
            </button>
            <button
              type="button"
              :disabled="savingTerritory"
              class="w-full px-4 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 text-white rounded-xl text-xs font-semibold shadow-lg transition-colors flex items-center justify-center gap-2"
              @click="saveCenteringConfig"
            >
              <span>💾</span> {{ savingTerritory ? 'Enregistrement...' : 'Enregistrer le cadrage' }}
            </button>
          </div>
        </div>

        <!-- Prévisualisation interactive MapLibre -->
        <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col min-h-[420px] relative">
          <div class="px-4 py-2.5 bg-slate-950/80 border-b border-slate-800 text-xs text-slate-400 flex items-center justify-between">
            <span class="font-semibold text-slate-200">Aperçu en direct (déplacez et zoomez pour cadrer)</span>
            <span>Repère bleu = centre configuré</span>
          </div>
          <div ref="mapContainer" class="flex-1 w-full h-full min-h-[380px]"></div>
        </div>
      </div>
    </div>

    <!-- Onglet 2 : Gestion des Contributeurs -->
    <div v-show="activeTab === 'users'" class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold text-white flex items-center gap-2">
          <span>👥</span> Équipe de contribution patrimoniale
        </h2>
        <button
          type="button"
          class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold shadow-lg transition-colors flex items-center gap-2"
          @click="isCreateUserModalOpen = true"
        >
          <span>➕</span> Nouveau Contributeur
        </button>
      </div>

      <!-- Tableau des contributeurs -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <table class="w-full text-left text-xs text-slate-300">
          <thead class="bg-slate-950 text-slate-400 border-b border-slate-800 font-semibold uppercase tracking-wider">
            <tr>
              <th class="px-4 py-3">Contributeur</th>
              <th class="px-4 py-3">Email</th>
              <th class="px-4 py-3">Rôle</th>
              <th class="px-4 py-3">Statut</th>
              <th class="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            <tr v-if="loadingUsers">
              <td colspan="5" class="px-4 py-8 text-center text-slate-500">Chargement des utilisateurs...</td>
            </tr>
            <tr v-else-if="users.length === 0">
              <td colspan="5" class="px-4 py-8 text-center text-slate-500">Aucun contributeur enregistré sur ce territoire.</td>
            </tr>
            <tr v-for="user in users" :key="user.id" class="hover:bg-slate-800/40 transition-colors">
              <td class="px-4 py-3.5 font-medium text-white flex items-center gap-2">
                <span class="w-7 h-7 rounded-full bg-sky-950 border border-sky-800 text-sky-300 flex items-center justify-center font-bold text-xs">
                  {{ user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U' }}
                </span>
                <span>{{ user.full_name }}</span>
              </td>
              <td class="px-4 py-3.5 text-slate-300 font-mono">{{ user.email }}</td>
              <td class="px-4 py-3.5">
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border"
                  :class="user.role === 'superadmin' ? 'bg-amber-950/80 text-amber-300 border-amber-800' : 'bg-slate-800 text-slate-300 border-slate-700'"
                >
                  {{ user.role === 'superadmin' ? 'Superadmin' : 'Contributeur' }}
                </span>
              </td>
              <td class="px-4 py-3.5">
                <span
                  class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium"
                  :class="user.is_active ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="user.is_active ? 'bg-emerald-400' : 'bg-rose-400'"></span>
                  {{ user.is_active ? 'Actif' : 'Désactivé' }}
                </span>
              </td>
              <td class="px-4 py-3.5 text-right space-x-1">
                <button
                  type="button"
                  :disabled="props.currentUserEmail === user.email"
                  class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-xs border border-slate-700 transition-colors"
                  :title="props.currentUserEmail === user.email ? 'Action interdite sur votre propre compte' : (user.is_active ? 'Désactiver le compte' : 'Activer le compte')"
                  @click="toggleUserStatus(user)"
                >
                  {{ user.is_active ? 'Désactiver' : 'Activer' }}
                </button>
                <button
                  type="button"
                  class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700 transition-colors"
                  title="Réinitialiser le mot de passe"
                  @click="openResetPasswordModal(user)"
                >
                  🔑
                </button>
                <button
                  type="button"
                  :disabled="props.currentUserEmail === user.email"
                  class="px-2.5 py-1 rounded bg-rose-950/60 hover:bg-rose-900 disabled:opacity-40 disabled:cursor-not-allowed text-rose-200 text-xs border border-rose-800 transition-colors"
                  :title="props.currentUserEmail === user.email ? 'Suppression interdite sur votre propre compte' : 'Supprimer ce contributeur'"
                  @click="handleDeleteUser(user)"
                >
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Onglet 3 : Fonds de Carte -->
    <div v-show="activeTab === 'basemaps'" class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-base font-semibold text-white flex items-center gap-2">
            <span>🗺️</span> Fonds de carte disponibles
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">
            Configurez les flux cartographiques (WMS, WMTS, tuiles vecteurs ou XYZ raster OSM/IGN) proposés aux visiteurs.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition-colors flex items-center gap-1.5"
            @click="isAddBasemapOpen = !isAddBasemapOpen"
          >
            <span>➕</span> Ajouter une source
          </button>
          <button
            type="button"
            :disabled="savingBasemaps"
            class="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 text-white rounded-xl text-xs font-semibold shadow-lg transition-colors flex items-center gap-1.5"
            @click="saveBasemapsConfig"
          >
            <span>💾</span> {{ savingBasemaps ? 'Enregistrement...' : 'Enregistrer les fonds' }}
          </button>
        </div>
      </div>

      <!-- Formulaire d'ajout rapide -->
      <div v-if="isAddBasemapOpen" class="bg-slate-900 border border-sky-900/60 rounded-2xl p-5 space-y-4 animate-fade-in">
        <h3 class="text-sm font-semibold text-sky-300">Ajouter un nouveau flux cartographique</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Nom du fond</label>
            <input
              v-model="newBasemapForm.name"
              type="text"
              placeholder="Ex: Orthophoto IGN 2024"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Type de service</label>
            <select
              v-model="newBasemapForm.type"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            >
              <option value="xyz">XYZ Raster (OSM, Esri, etc.)</option>
              <option value="wmts">WMTS (Géoportail / IGN)</option>
              <option value="wms">WMS (Flux SIG standard)</option>
              <option value="vector">Tuiles Vecteurs (Mapbox / MVT)</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Attribution légale</label>
            <input
              v-model="newBasemapForm.attribution"
              type="text"
              placeholder="Ex: © IGN / Géoportail"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">URL du flux ou modèle de tuiles</label>
          <input
            v-model="newBasemapForm.url"
            type="text"
            placeholder="https://.../{z}/{x}/{y}.png"
            class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div class="flex items-center justify-between pt-2">
          <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
            <input v-model="newBasemapForm.is_default" type="checkbox" class="accent-sky-500" />
            <span>Définir comme fond cartographique par défaut</span>
          </label>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-3 py-1.5 bg-slate-800 text-slate-300 hover:text-white rounded-lg text-xs"
              @click="isAddBasemapOpen = false"
            >
              Annuler
            </button>
            <button
              type="button"
              class="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold"
              @click="handleAddBasemap"
            >
              Ajouter à la liste
            </button>
          </div>
        </div>
      </div>

      <!-- Liste des fonds configurés -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="bm in basemaps"
          :key="bm.id"
          class="bg-slate-900 border rounded-2xl p-4 flex flex-col justify-between transition-all"
          :class="bm.is_default ? 'border-sky-500 shadow-lg shadow-sky-950/50' : 'border-slate-800 hover:border-slate-700'"
        >
          <div>
            <div class="flex items-start justify-between gap-2">
              <h3 class="text-sm font-bold text-white">{{ bm.name }}</h3>
              <span
                class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider"
                :class="bm.type === 'xyz' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-purple-950 text-purple-300 border border-purple-800'"
              >
                {{ bm.type }}
              </span>
            </div>
            <p class="text-xs text-slate-400 font-mono break-all mt-2 line-clamp-2">
              {{ bm.url }}
            </p>
            <p v-if="bm.attribution" class="text-[11px] text-slate-500 mt-1">
              {{ bm.attribution }}
            </p>
          </div>

          <div class="pt-4 border-t border-slate-800/80 mt-4 flex items-center justify-between">
            <button
              v-if="!bm.is_default"
              type="button"
              class="text-xs text-slate-400 hover:text-sky-300 flex items-center gap-1 font-medium transition-colors"
              @click="handleSetDefaultBasemap(bm.id)"
            >
              <span>☆</span> Définir par défaut
            </button>
            <span v-else class="text-xs text-sky-400 font-semibold flex items-center gap-1">
              <span>⭐</span> Fond par défaut
            </span>

            <button
              type="button"
              class="text-xs text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-950/40 rounded transition-colors"
              title="Supprimer ce fond"
              @click="handleRemoveBasemap(bm.id)"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modale Création Contributeur -->
    <div
      v-if="isCreateUserModalOpen"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <span>➕</span> Créer un compte contributeur
        </h3>
        <p class="text-xs text-slate-400">
          Ce compte permettra à l'historien ou archiviste d'ajouter et géoréférencer des clichés sur ce territoire.
        </p>

        <form class="space-y-3" @submit.prevent="handleCreateUser">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Nom complet</label>
            <input
              v-model="newUserForm.full_name"
              type="text"
              required
              placeholder="Ex: Jeanne Delattre"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Adresse email</label>
            <input
              v-model="newUserForm.email"
              type="email"
              required
              placeholder="jeanne@archives-territoire.fr"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Mot de passe temporaire</label>
            <input
              v-model="newUserForm.password"
              type="password"
              required
              minlength="6"
              placeholder="Au moins 6 caractères"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div class="pt-3 flex justify-end gap-2">
            <button
              type="button"
              class="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-lg text-xs"
              @click="isCreateUserModalOpen = false"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold shadow-lg"
            >
              Créer le compte
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modale Réinitialisation Mot de Passe -->
    <div
      v-if="isResetPasswordModalOpen && selectedUserForReset"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-sm p-6 space-y-4 shadow-2xl">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <span>🔑</span> Nouveau mot de passe
        </h3>
        <p class="text-xs text-slate-400">
          Définir un nouveau mot de passe pour <strong>{{ selectedUserForReset.full_name }}</strong> ({{ selectedUserForReset.email }}).
        </p>

        <form class="space-y-3" @submit.prevent="handleResetPassword">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Nouveau mot de passe</label>
            <input
              v-model="newPasswordInput"
              type="password"
              required
              minlength="6"
              placeholder="Au moins 6 caractères"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div class="pt-3 flex justify-end gap-2">
            <button
              type="button"
              class="px-4 py-2 bg-slate-800 text-slate-300 hover:text-white rounded-lg text-xs"
              @click="isResetPasswordModalOpen = false"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold shadow-lg"
            >
              Modifier
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
