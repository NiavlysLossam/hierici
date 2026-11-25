<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { photoApi } from '@/services/api'
import { createViewConePolygon, createEmptyFeatureCollection } from '@/utils/geo'
import type { PhotoGeoJsonFeatureCollection, PhotoGeoJsonFeature } from '@/types/photo'
import { getUrlPhotoId, computePhotoUrl, resolveLightboxImageUrl } from '@/utils/photoViewer'
import PhotoDetailDrawer from './PhotoDetailDrawer.vue'
import PhotoLightbox from './PhotoLightbox.vue'

const props = withDefaults(
  defineProps<{
    territoryCenter?: [number, number] // [lng, lat]
    defaultZoom?: number
    territoryName?: string
  }>(),
  {
    territoryCenter: () => [5.93, 43.12],
    defaultZoom: 13,
    territoryName: 'Territoire',
  }
)

const emit = defineEmits<{
  (e: 'select-photo', photoId: string, feature: PhotoGeoJsonFeature): void
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
let map: maplibregl.Map | null = null
let resizeObserver: ResizeObserver | null = null
let isMounted = false
let currentAbortController: AbortController | null = null
let currentHoveredPhotoId: string | null = null

const loading = ref(true)
const error = ref<string | null>(null)
const photosData = ref<PhotoGeoJsonFeatureCollection | null>(null)
const totalPublishedCount = ref(0)
const selectedPhotoId = ref<string | null>(null)

// Story 3.3 : Volet détaillé et Visionneuse HD
const isDrawerOpen = ref(false)
const isLightboxOpen = ref(false)
const activePhotoFeature = ref<PhotoGeoJsonFeature | null>(null)
const notFoundToast = ref<string | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | null = null
let pendingInitialPhotoId: string | null = null

const lightboxImageUrl = computed(() => {
  return resolveLightboxImageUrl(activePhotoFeature.value?.properties)
})

/**
 * Utilitaires de synchronisation URL sans rechargement
 */
function setUrlPhotoId(id: string | null, push = false) {
  const currentPhoto = getUrlPhotoId(window.location.search)
  if (currentPhoto === id) return
  const target = computePhotoUrl(window.location.href, id)
  if (push) {
    window.history.pushState(null, '', target)
  } else {
    window.history.replaceState(null, '', target)
  }
}

function showNotFoundToast(message = 'Photographie introuvable ou non publiée.') {
  notFoundToast.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    notFoundToast.value = null
  }, 4000)
}

// Filtres
const searchQuery = ref('')
const filterYearMin = ref<number | undefined>(undefined)
const filterYearMax = ref<number | undefined>(undefined)

// Style raster OSM libre et sans clé API
const mapStyle: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'osm-tiles': {
      type: 'raster',
      tiles: [
        'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
        'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
        'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributeurs',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: 'osm-tiles-layer',
      type: 'raster',
      source: 'osm-tiles',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
}

/**
 * Génère une icône Canvas 2D nette et vectorielle pour les marqueurs MapLibre
 * avec pointe directionnelle orientée (hasArrow = true) ou pastille neutre
 * Centrée strictement sur le centre (32, 32) pour éliminer tout déport orbital lors des rotations
 */
function createOrientedMarkerImage(hasArrow: boolean): ImageData {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return new ImageData(size, size)
  }

  const cx = size / 2
  const cy = size / 2
  const radius = 18

  // Ombre portée marquée pour détacher nettement le marqueur sur tout type de fond
  ctx.shadowColor = 'rgba(0, 0, 0, 0.65)'
  ctx.shadowBlur = 8
  ctx.shadowOffsetY = 3

  // Si marqueur orienté : pointe directionnelle vers le haut (0° = Nord)
  if (hasArrow) {
    ctx.beginPath()
    ctx.moveTo(cx - 10, cy - radius + 2)
    ctx.lineTo(cx, cy - radius - 13)
    ctx.lineTo(cx + 10, cy - radius + 2)
    ctx.closePath()
    ctx.fillStyle = '#0284c7'
    ctx.fill()
    ctx.lineWidth = 3
    ctx.strokeStyle = '#ffffff'
    ctx.stroke()
  }

  // Cercle principal
  ctx.beginPath()
  ctx.arc(cx, cy, radius, 0, Math.PI * 2)
  ctx.fillStyle = '#0284c7'
  ctx.fill()
  ctx.lineWidth = 3
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // Reset shadow for inner icon
  ctx.shadowColor = 'transparent'

  // Icône appareil photo au centre (agrandie et nette)
  ctx.fillStyle = '#ffffff'
  ctx.beginPath()
  if (ctx.roundRect) {
    ctx.roundRect(cx - 9, cy - 6, 18, 12, 2.5)
  } else {
    ctx.rect(cx - 9, cy - 6, 18, 12)
  }
  ctx.fill()

  // Viseur
  ctx.fillRect(cx - 4.5, cy - 9, 7, 3)

  // Objectif
  ctx.beginPath()
  ctx.arc(cx, cy + 0.5, 4.2, 0, Math.PI * 2)
  ctx.fillStyle = '#0284c7'
  ctx.fill()
  ctx.beginPath()
  ctx.arc(cx, cy + 0.5, 1.8, 0, Math.PI * 2)
  ctx.fillStyle = '#ffffff'
  ctx.fill()

  return ctx.getImageData(0, 0, size, size)
}

/**
 * Met à jour le polygone vectoriel du cône de vue WebGL sur la carte
 */
function updateViewCone(feature: PhotoGeoJsonFeature | null) {
  if (!map || !map.isStyleLoaded()) return
  const source = map.getSource('view-cone-source') as maplibregl.GeoJSONSource | undefined
  if (!source) return

  // Si un cliché spécifique est survolé, on utilise celui-ci ; sinon la photo activement sélectionnée
  const target =
    feature ||
    (selectedPhotoId.value
      ? (activePhotoFeature.value || photosData.value?.features.find((f) => f.properties.id === selectedPhotoId.value))
      : null)

  if (
    target &&
    target.properties?.bearing !== null &&
    target.properties?.bearing !== undefined
  ) {
    const coords = target.geometry.coordinates
    const polygon = createViewConePolygon(
      coords[0],
      coords[1],
      target.properties.bearing,
      target.properties.field_of_view ?? 60,
      target.properties.view_distance ?? 160,
      2
    )
    source.setData(polygon)
  } else {
    source.setData(createEmptyFeatureCollection())
  }
}

/**
 * Charge les données GeoJSON depuis l'API publique avec annulation des requêtes précédentes
 */
async function loadGeoJsonData() {
  if (currentAbortController) {
    currentAbortController.abort()
  }
  currentAbortController = new AbortController()

  loading.value = true
  error.value = null

  try {
    const data = await photoApi.getPublicPhotos(
      {
        search: searchQuery.value.trim() || undefined,
        year_min: filterYearMin.value,
        year_max: filterYearMax.value,
      },
      currentAbortController.signal
    )

    if (!isMounted) return

    photosData.value = data
    totalPublishedCount.value = data.features.length

    // Si la photo actuellement sélectionnée n'est plus dans les filtres, on réinitialise volet et URL
    if (
      selectedPhotoId.value &&
      !data.features.some((f) => f.properties.id === selectedPhotoId.value)
    ) {
      closeDrawer({ updateUrl: true, pushHistory: false })
    }

    if (map && map.isStyleLoaded()) {
      const source = map.getSource('photos') as maplibregl.GeoJSONSource | undefined
      if (source) {
        source.setData(data as any)
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      // Annulation normale par frappe ultérieure
      return
    }
    console.error('Erreur lors du chargement des données GeoJSON:', err)
    error.value = err.message || 'Impossible de charger les données photographiques.'
  } finally {
    if (isMounted) {
      loading.value = false
    }
  }
}

/**
 * Sélectionne une photo par son identifiant : met à jour le marqueur actif,
 * le cône de vue, le volet détaillé latéral et l'URL (?photo=uuid)
 */
async function selectPhotoById(
  id: string,
  options: { flyTo?: boolean; updateUrl?: boolean; pushHistory?: boolean } = {}
) {
  const { flyTo = true, updateUrl = true, pushHistory = true } = options
  selectedPhotoId.value = id

  // 1. Recherche dans les entités déjà chargées
  let feature = photosData.value?.features.find((f) => f.properties.id === id)

  // 2. Si absente (ex: accès direct via URL avec filtres ou hors emprise), tentative de récupération API
  if (!feature) {
    try {
      const photo = await photoApi.getPublicPhoto(id)
      // Garde anti race-condition si une autre photo a été sélectionnée entre-temps ou démontage
      if (selectedPhotoId.value !== id || !isMounted) return

      if (photo && photo.latitude != null && photo.longitude != null) {
        feature = {
          type: 'Feature',
          id: photo.id,
          geometry: {
            type: 'Point',
            coordinates: [photo.longitude, photo.latitude],
          },
          properties: {
            id: photo.id,
            title: photo.title,
            description: photo.description,
            photographer: photo.photographer,
            year_taken: photo.year_taken ?? photo.year,
            date_exact: photo.date_exact,
            period_label: photo.period_label,
            archive_source: photo.archive_source,
            archive_ref: photo.archive_ref ?? photo.archive_reference,
            original_source_url: photo.original_source_url ?? photo.source_url,
            license: photo.license,
            bearing: photo.bearing,
            field_of_view: photo.field_of_view ?? 60,
            view_distance: photo.view_distance,
            is_exact_year: photo.is_exact_year,
            image_thumb_url: photo.image_thumb_url ?? photo.thumb_url,
            image_display_url: photo.image_display_url ?? photo.display_url,
            image_original_url: photo.image_original_url ?? photo.original_url,
            created_at: photo.created_at,
            updated_at: photo.updated_at,
          },
        }
      }
    } catch {
      if (selectedPhotoId.value !== id || !isMounted) return
      showNotFoundToast('Photographie introuvable ou non publiée.')
      closeDrawer({ updateUrl: true, pushHistory: false })
      resetTerritoryView()
      return
    }
  }

  if (selectedPhotoId.value !== id || !isMounted) return

  if (!feature) {
    showNotFoundToast('Photographie introuvable ou non publiée.')
    closeDrawer({ updateUrl: true, pushHistory: false })
    resetTerritoryView()
    return
  }

  activePhotoFeature.value = feature
  isDrawerOpen.value = true

  const coords = feature.geometry.coordinates

  if (map && map.isStyleLoaded()) {
    updateViewCone(feature)
    if (flyTo) {
      map.flyTo({
        center: coords,
        zoom: Math.max(map.getZoom(), 15),
        duration: 800,
        essential: true,
      })
    }
  }

  if (updateUrl) {
    setUrlPhotoId(id, pushHistory)
  }

  emit('select-photo', id, feature)
}

/**
 * Ferme le volet détaillé et la lightbox, retire le paramètre ?photo de l'URL
 */
function closeDrawer(options: { updateUrl?: boolean; pushHistory?: boolean } = {}) {
  const { updateUrl = true, pushHistory = false } = options
  isDrawerOpen.value = false
  isLightboxOpen.value = false
  selectedPhotoId.value = null
  activePhotoFeature.value = null
  updateViewCone(null)

  if (updateUrl) {
    setUrlPhotoId(null, pushHistory)
  }
}

function handleCenterMap(coords: [number, number]) {
  if (!map) return
  map.flyTo({
    center: coords,
    zoom: Math.max(map.getZoom(), 15),
    duration: 600,
    essential: true,
  })
}

function handlePopState() {
  const photoId = getUrlPhotoId(window.location.search)
  if (photoId) {
    if (selectedPhotoId.value !== photoId) {
      selectPhotoById(photoId, { flyTo: true, updateUrl: false })
    }
  } else {
    if (selectedPhotoId.value || isDrawerOpen.value) {
      closeDrawer({ updateUrl: false })
    }
  }
}

/**
 * Initialise l'instance MapLibre GL et les couches vectorielles de clustering et d'azimut
 */
function initMap() {
  if (!mapContainer.value || !isMounted) return

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: mapStyle,
    center: props.territoryCenter,
    zoom: props.defaultZoom,
    maxZoom: 18,
    minZoom: 4,
    attributionControl: false,
  })

  // Contrôles de navigation et attribution
  map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'bottom-left')
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

  map.on('load', () => {
    if (!map || !isMounted) return

    // Enregistrement des icônes vectorielles personnalisées (avec et sans flèche d'orientation)
    map.addImage('marker-oriented', createOrientedMarkerImage(true), { pixelRatio: 2 })
    map.addImage('marker-neutral', createOrientedMarkerImage(false), { pixelRatio: 2 })

    // 1. Source et couches du cône de vue vectoriel WebGL (Story 3.2)
    // Placée en-dessous des marqueurs pour une lisibilité optimale
    map.addSource('view-cone-source', {
      type: 'geojson',
      data: createEmptyFeatureCollection(),
    })

    map.addLayer({
      id: 'view-cone-fill',
      type: 'fill',
      source: 'view-cone-source',
      paint: {
        'fill-color': '#0284c7',
        'fill-opacity': 0.28,
      },
    })

    map.addLayer({
      id: 'view-cone-stroke',
      type: 'line',
      source: 'view-cone-source',
      paint: {
        'line-color': '#0284c7',
        'line-width': 2,
        'line-opacity': 0.85,
        'line-dasharray': [2, 2],
      },
    })

    // 2. Source GeoJSON des photos avec clustering activé côté client
    map.addSource('photos', {
      type: 'geojson',
      data: (photosData.value as any) || { type: 'FeatureCollection', features: [] },
      cluster: true,
      clusterMaxZoom: 14, // Au-delà du zoom 14, les points individuels sont toujours affichés
      clusterRadius: 50,  // Rayon de regroupement en pixels
    })

    // 3. Couche des cercles de clusters (taille et palette selon densité)
    map.addLayer({
      id: 'clusters',
      type: 'circle',
      source: 'photos',
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': [
          'step',
          ['get', 'point_count'],
          '#0284c7', // < 10 clichés : sky-600
          10,
          '#0d9488', // 10 - 24 : teal-600
          25,
          '#d97706', // 25 - 49 : amber-600
          50,
          '#e11d48', // >= 50 : rose-600
        ],
        'circle-radius': [
          'step',
          ['get', 'point_count'],
          18,
          10,
          24,
          25,
          30,
          50,
          36,
        ],
        'circle-stroke-width': 3,
        'circle-stroke-color': '#ffffff',
        'circle-opacity': 0.92,
      },
    })

    // 4. Couche du décompte textuel à l'intérieur du cercle cluster
    map.addLayer({
      id: 'cluster-count',
      type: 'symbol',
      source: 'photos',
      filter: ['has', 'point_count'],
      layout: {
        'text-field': '{point_count_abbreviated}',
        'text-size': 13,
      },
      paint: {
        'text-color': '#ffffff',
      },
    })

    // 5. Couche des clichés individuels orientés (Story 3.2 : rotation dynamique selon l'azimut)
    map.addLayer({
      id: 'unclustered-oriented',
      type: 'symbol',
      source: 'photos',
      filter: ['all', ['!', ['has', 'point_count']], ['!=', ['get', 'bearing'], null]] as any,
      layout: {
        'icon-image': 'marker-oriented',
        'icon-size': 1.15,
        'icon-rotate': ['get', 'bearing'],
        'icon-rotation-alignment': 'map',
        'icon-allow-overlap': true,
        'icon-ignore-placement': true,
      },
    })

    // 6. Couche des clichés individuels neutres (sans azimut renseigné)
    map.addLayer({
      id: 'unclustered-neutral',
      type: 'symbol',
      source: 'photos',
      filter: ['all', ['!', ['has', 'point_count']], ['==', ['get', 'bearing'], null]] as any,
      layout: {
        'icon-image': 'marker-neutral',
        'icon-size': 1.15,
        'icon-allow-overlap': true,
        'icon-ignore-placement': true,
      },
    })

    // Clic sur un cluster : zoom automatique fluide pour éclater le groupe
    map.on('click', 'clusters', async (e) => {
      if (!map) return
      const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] })
      const clusterId = features[0]?.properties?.cluster_id
      if (clusterId === undefined) return

      const source = map.getSource('photos') as maplibregl.GeoJSONSource
      try {
        // Clore la fiche latérale précédente si l'utilisateur change d'emprise vers un groupe
        if (isDrawerOpen.value) {
          closeDrawer({ updateUrl: true, pushHistory: true })
        }

        const expansionZoom = await source.getClusterExpansionZoom(clusterId)
        const coords = (features[0].geometry as any).coordinates.slice()

        // Gestion du cas où les clichés partagent exactement les mêmes coordonnées GPS
        const currentZoom = map.getZoom()
        if (expansionZoom <= currentZoom || currentZoom >= 17) {
          map.easeTo({
            center: coords,
            zoom: Math.min(currentZoom + 1, 18),
            duration: 400,
          })
        } else {
          map.easeTo({
            center: coords,
            zoom: Math.min(expansionZoom, 17),
            duration: 500,
          })
        }
      } catch (err) {
        console.warn('Impossible de calculer le zoom de cluster:', err)
      }
    })

    // Gestion du clic sur un cliché individuel (orienté ou neutre)
    const handlePhotoClick = (e: maplibregl.MapMouseEvent) => {
      if (!map) return
      const features = map.queryRenderedFeatures(e.point, {
        layers: ['unclustered-oriented', 'unclustered-neutral'],
      })
      const feature = features[0]
      const featureId = feature?.properties?.id
      if (!featureId) return

      selectPhotoById(featureId, { flyTo: false, updateUrl: true, pushHistory: true })
    }

    map.on('click', 'unclustered-oriented', handlePhotoClick)
    map.on('click', 'unclustered-neutral', handlePhotoClick)

    // Fermeture ergonomique du volet au clic sur le fond de carte (zone sans marqueur ni groupe)
    map.on('click', (e) => {
      if (!map || !isDrawerOpen.value) return
      const features = map.queryRenderedFeatures(e.point, {
        layers: ['unclustered-oriented', 'unclustered-neutral', 'clusters'],
      })
      if (features.length === 0) {
        closeDrawer({ updateUrl: true, pushHistory: true })
      }
    })

    // Gestion du survol dynamique : réactif même entre clichés contigus (Story 3.2 / ISSUE-02)
    const handlePhotoMouseMove = (e: maplibregl.MapMouseEvent) => {
      if (!map) return
      const features = map.queryRenderedFeatures(e.point, {
        layers: ['unclustered-oriented', 'unclustered-neutral'],
      })
      const featureId = features[0]?.properties?.id
      if (featureId) {
        map.getCanvas().style.cursor = 'pointer'
        if (featureId !== currentHoveredPhotoId) {
          currentHoveredPhotoId = featureId
          const fullFeature = photosData.value?.features.find((f) => f.properties.id === featureId)
          if (fullFeature) {
            updateViewCone(fullFeature)
          }
        }
      }
    }

    const handlePhotoMouseLeave = () => {
      if (!map) return
      map.getCanvas().style.cursor = ''
      currentHoveredPhotoId = null
      updateViewCone(null)
    }

    map.on('mousemove', 'unclustered-oriented', handlePhotoMouseMove)
    map.on('mouseleave', 'unclustered-oriented', handlePhotoMouseLeave)
    map.on('mousemove', 'unclustered-neutral', handlePhotoMouseMove)
    map.on('mouseleave', 'unclustered-neutral', handlePhotoMouseLeave)

    map.on('mouseenter', 'clusters', () => {
      if (map) map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'clusters', () => {
      if (map) map.getCanvas().style.cursor = ''
    })

    // Traitement du paramètre URL initial (?photo=uuid) dès le chargement complet de la carte
    const initialPhotoId = pendingInitialPhotoId || getUrlPhotoId()
    if (initialPhotoId) {
      selectPhotoById(initialPhotoId, { flyTo: true, updateUrl: false })
      pendingInitialPhotoId = null
    }
  })

  // Surveillance des redimensionnements de fenêtre et de conteneur
  resizeObserver = new ResizeObserver(() => {
    map?.resize()
  })
  resizeObserver.observe(mapContainer.value)
}

/**
 * Recentre la vue sur l'emprise du territoire
 */
function resetTerritoryView() {
  if (!map) return
  map.flyTo({
    center: props.territoryCenter,
    zoom: props.defaultZoom,
    essential: true,
  })
}

// Surveillance des changements de filtres avec debounce
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchQuery, filterYearMin, filterYearMax], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadGeoJsonData()
  }, 300)
})

// Surveillance du changement de territoire actif
watch(
  () => props.territoryCenter,
  (newCenter) => {
    if (map && newCenter) {
      map.flyTo({
        center: newCenter,
        zoom: props.defaultZoom,
      })
      loadGeoJsonData()
    }
  }
)

onMounted(async () => {
  isMounted = true
  pendingInitialPhotoId = getUrlPhotoId()
  window.addEventListener('popstate', handlePopState)

  await loadGeoJsonData()
  if (isMounted) {
    initMap()
  }
})

onUnmounted(() => {
  isMounted = false
  window.removeEventListener('popstate', handlePopState)

  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
  if (currentAbortController) {
    currentAbortController.abort()
    currentAbortController = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (map) {
    map.remove()
    map = null
  }
})

defineExpose({
  resize: () => map?.resize(),
  resetView: resetTerritoryView,
  refresh: loadGeoJsonData,
  selectPhoto: (photoId: string) => {
    selectPhotoById(photoId, { flyTo: true, updateUrl: true, pushHistory: true })
  },
  closePhoto: () => {
    closeDrawer({ updateUrl: true, pushHistory: true })
  },
})
</script>

<template>
  <div class="relative w-full h-[calc(100vh-140px)] min-h-[500px] flex flex-col rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
    <!-- Barre Supérieure d'Exploration & Filtres -->
    <div class="absolute top-4 left-4 right-4 z-10 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
      <!-- Groupe Filtres & Recherche -->
      <div class="flex flex-wrap items-center gap-2 pointer-events-auto bg-slate-900/90 backdrop-blur-md p-2 rounded-xl border border-slate-700/80 shadow-xl text-xs">
        <!-- Recherche textuelle -->
        <div class="relative flex items-center">
          <span class="absolute left-2.5 text-slate-400">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Rechercher un monument, auteur..."
            class="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 w-52 sm:w-64 transition-colors"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="absolute right-2 text-slate-400 hover:text-white"
            @click="searchQuery = ''"
          >
            ✕
          </button>
        </div>

        <!-- Filtre Période / Année -->
        <div class="hidden sm:flex items-center gap-1.5 pl-2 border-l border-slate-700/80 text-slate-300">
          <span>Année :</span>
          <input
            v-model.number="filterYearMin"
            type="number"
            placeholder="Min"
            class="w-16 px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-sky-500 text-center"
          />
          <span class="text-slate-500">-</span>
          <input
            v-model.number="filterYearMax"
            type="number"
            placeholder="Max"
            class="w-16 px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-sky-500 text-center"
          />
        </div>

        <!-- Bouton Reset Filtres si actifs -->
        <button
          v-if="searchQuery || filterYearMin !== undefined || filterYearMax !== undefined"
          type="button"
          class="px-2 py-1.5 text-sky-400 hover:text-sky-300 font-semibold"
          @click="searchQuery = ''; filterYearMin = undefined; filterYearMax = undefined"
        >
          Effacer
        </button>
      </div>
    </div>

    <!-- Conteneur Cartographique MapLibre GL -->
    <div ref="mapContainer" class="flex-1 w-full h-full relative z-0"></div>

    <!-- État Vide lorsque aucun résultat ne correspond aux filtres -->
    <div
      v-if="!loading && totalPublishedCount === 0"
      class="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 px-4 py-2.5 rounded-xl bg-slate-900/95 border border-slate-700/80 text-xs text-slate-300 shadow-xl flex items-center gap-3"
    >
      <span>🔎 Aucune photographie publiée ne correspond aux critères de recherche.</span>
      <button
        v-if="searchQuery || filterYearMin !== undefined || filterYearMax !== undefined"
        type="button"
        class="px-2 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium text-[11px]"
        @click="searchQuery = ''; filterYearMin = undefined; filterYearMax = undefined"
      >
        Réinitialiser les filtres
      </button>
    </div>

    <!-- Indicateur de Chargement -->
    <div
      v-if="loading"
      class="absolute bottom-6 left-6 z-20 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700 text-xs text-sky-400 shadow-lg"
    >
      <svg class="animate-spin w-4 h-4 text-sky-400" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <span>Actualisation des photographies...</span>
    </div>

    <!-- Message d'Erreur -->
    <div
      v-if="error"
      class="absolute bottom-6 left-6 right-6 z-20 p-3 rounded-xl bg-rose-950/90 border border-rose-800 text-xs text-rose-300 shadow-xl flex items-center justify-between"
    >
      <span>⚠️ {{ error }}</span>
      <button
        type="button"
        class="px-2 py-1 bg-rose-800 hover:bg-rose-700 text-white rounded font-medium"
        @click="loadGeoJsonData"
      >
        Réessayer
      </button>
    </div>

    <!-- Toast Notification Photo introuvable -->
    <div
      v-if="notFoundToast"
      class="absolute top-20 left-1/2 -translate-x-1/2 z-40 px-4 py-2.5 rounded-xl bg-slate-900/95 border border-amber-500/60 text-xs text-amber-200 shadow-2xl flex items-center gap-2"
    >
      <span>⚠️</span>
      <span>{{ notFoundToast }}</span>
      <button
        type="button"
        class="ml-2 text-slate-400 hover:text-white"
        @click="notFoundToast = null"
      >
        ✕
      </button>
    </div>

    <!-- Volet Détaillé Contextuel (Story 3.3) -->
    <PhotoDetailDrawer
      :is-open="isDrawerOpen"
      :is-lightbox-open="isLightboxOpen"
      :photo="activePhotoFeature?.properties ?? null"
      :coordinates="activePhotoFeature?.geometry.coordinates ?? null"
      @close="closeDrawer"
      @open-lightbox="isLightboxOpen = true"
      @center-map="handleCenterMap"
    />

    <!-- Visionneuse Plein Écran Haute Définition (Story 3.3) -->
    <PhotoLightbox
      :is-open="isLightboxOpen"
      :image-url="lightboxImageUrl"
      :title="activePhotoFeature?.properties.title ?? ''"
      :photographer="activePhotoFeature?.properties.photographer"
      :year="activePhotoFeature?.properties.year_taken"
      :period-label="activePhotoFeature?.properties.period_label"
      :archive-source="activePhotoFeature?.properties.archive_source"
      :archive-ref="activePhotoFeature?.properties.archive_ref"
      :license="activePhotoFeature?.properties.license"
      @close="isLightboxOpen = false"
    />
  </div>
</template>

<style scoped>
:deep(.maplibregl-ctrl-group) {
  background-color: rgb(15 23 42 / 0.9) !important;
  border: 1px solid rgb(51 65 85) !important;
  border-radius: 0.75rem !important;
  overflow: hidden;
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.3) !important;
}

:deep(.maplibregl-ctrl-group button) {
  border-bottom: 1px solid rgb(51 65 85) !important;
}

:deep(.maplibregl-ctrl-group button:last-child) {
  border-bottom: none !important;
}

:deep(.maplibregl-ctrl-group button:hover) {
  background-color: rgb(30 41 59) !important;
}

:deep(.maplibregl-ctrl-icon) {
  filter: invert(1);
}
</style>
