<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import maplibregl from 'maplibre-gl'
import {
  createViewConePolygon,
  createEmptyFeatureCollection,
  roundCoordinate,
  normalizeBearing,
  clampFov,
} from '@/utils/geo'
import { photoApi } from '@/services/api'

const props = withDefaults(
  defineProps<{
    latitude: number | null
    longitude: number | null
    bearing: number | null
    fieldOfView?: number
    viewDistance?: number
    defaultCenter?: { lat: number; lng: number; zoom?: number } | null
  }>(),
  {
    fieldOfView: 60,
    viewDistance: 160,
    defaultCenter: () => ({ lat: 43.1242, lng: 5.9328, zoom: 14 }), // Défaut Toulon
  }
)

const emit = defineEmits<{
  (e: 'update:latitude', val: number | null): void
  (e: 'update:longitude', val: number | null): void
  (e: 'update:bearing', val: number | null): void
  (e: 'update:fieldOfView', val: number): void
  (e: 'update:viewDistance', val: number): void
  (
    e: 'change',
    val: {
      latitude: number | null
      longitude: number | null
      bearing: number | null
      fieldOfView: number
      viewDistance?: number
    }
  ): void
}>()

const mapContainerRef = ref<HTMLDivElement | null>(null)
let map: maplibregl.Map | null = null
let marker: maplibregl.Marker | null = null
let resizeObserver: ResizeObserver | null = null

const isMapReady = ref(false)

// Coordonnées locales pour réactivité instantanée
const currentLat = computed(() => (props.latitude !== null && !isNaN(props.latitude) ? props.latitude : null))
const currentLng = computed(() => (props.longitude !== null && !isNaN(props.longitude) ? props.longitude : null))
const currentBearing = computed(() => normalizeBearing(props.bearing ?? 0))
const currentFov = computed(() => clampFov(props.fieldOfView ?? 60))
const currentDistance = computed(() => Math.max(20, Math.min(2000, props.viewDistance ?? 160)))

const hasCoordinates = computed(() => currentLat.value !== null && currentLng.value !== null)

// Direction cardinale lisible
const cardinalDirection = computed(() => {
  const b = currentBearing.value
  if (b >= 337.5 || b < 22.5) return 'Nord (N)'
  if (b >= 22.5 && b < 67.5) return 'Nord-Est (NE)'
  if (b >= 67.5 && b < 112.5) return 'Est (E)'
  if (b >= 112.5 && b < 157.5) return 'Sud-Est (SE)'
  if (b >= 157.5 && b < 202.5) return 'Sud (S)'
  if (b >= 202.5 && b < 247.5) return 'Sud-Ouest (SO)'
  if (b >= 247.5 && b < 292.5) return 'Ouest (O)'
  return 'Nord-Ouest (NO)'
})

// Configuration du style OpenStreetMap libre
const OSM_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributeurs',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: 'osm-tiles',
      type: 'raster',
      source: 'osm',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
}

/**
 * Met à jour les couches vectorielles du cône de vue GeoJSON sur la carte
 */
function updateViewConeLayer(
  overrideLat?: number | null,
  overrideLng?: number | null,
  overrideBearing?: number,
  overrideFov?: number,
  overrideDistance?: number
) {
  if (!map || !map.isStyleLoaded()) return

  const source = map.getSource('view-cone-source') as maplibregl.GeoJSONSource | undefined
  if (!source) return

  const lat = overrideLat !== undefined ? overrideLat : currentLat.value
  const lng = overrideLng !== undefined ? overrideLng : currentLng.value
  const bearing = overrideBearing !== undefined ? overrideBearing : currentBearing.value
  const fov = overrideFov !== undefined ? overrideFov : currentFov.value
  const dist = overrideDistance !== undefined ? overrideDistance : currentDistance.value

  if (lat !== null && lng !== null) {
    const conePolygon = createViewConePolygon(
      lng,
      lat,
      bearing,
      fov,
      dist,
      2
    )
    source.setData(conePolygon)
  } else {
    source.setData(createEmptyFeatureCollection())
  }
}

let isDragging = false

/**
 * Initialise ou met à jour la position du marqueur sur la carte
 */
function updateMarkerPosition() {
  if (!map || isDragging) return

  if (currentLat.value !== null && currentLng.value !== null) {
    const lngLat: [number, number] = [currentLng.value, currentLat.value]

    if (!marker) {
      // Création d'un élément HTML personnalisé pour le marqueur avec indicateur de cap
      const el = document.createElement('div')
      el.className = 'hierici-camera-marker'
      el.innerHTML = `
        <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-sky-500 text-white shadow-xl border-2 border-white cursor-grab active:cursor-grabbing hover:scale-110 transition-transform">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20">
            <path d="M4 5a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V7a2 2 0 00-2-2h-1.586a1 1 0 01-.707-.293l-1.121-1.121A2 2 0 0011.172 3H8.828a2 2 0 00-1.414.586L6.293 4.707A1 1 0 015.586 5H4zm6 9a3 3 0 110-6 3 3 0 010 6z" />
          </svg>
        </div>
      `

      marker = new maplibregl.Marker({
        element: el,
        draggable: true,
      })
        .setLngLat(lngLat)
        .addTo(map)

      marker.on('dragstart', () => {
        isDragging = true
      })

      marker.on('drag', () => {
        if (!marker) return
        const pos = marker.getLngLat().wrap()
        const lat = roundCoordinate(pos.lat, 6)
        const lng = roundCoordinate(pos.lng, 6)
        emit('update:latitude', lat)
        emit('update:longitude', lng)
        updateViewConeLayer(lat, lng)
      })

      marker.on('dragend', () => {
        isDragging = false
        if (!marker) return
        const pos = marker.getLngLat().wrap()
        const lat = roundCoordinate(pos.lat, 6)
        const lng = roundCoordinate(pos.lng, 6)
        emitCoordinatesChange(lat, lng, currentBearing.value, currentFov.value)
        updateViewConeLayer(lat, lng)
      })
    } else {
      marker.setLngLat(lngLat)
    }
  } else {
    if (marker) {
      marker.remove()
      marker = null
    }
  }

  updateViewConeLayer()
}

/**
 * Notifie le parent des changements de coordonnées
 */
function emitCoordinatesChange(
  lat: number | null,
  lng: number | null,
  bearing: number | null,
  fov: number
) {
  emit('update:latitude', lat)
  emit('update:longitude', lng)
  emit('update:bearing', bearing)
  emit('update:fieldOfView', fov)
  emit('change', {
    latitude: lat,
    longitude: lng,
    bearing,
    fieldOfView: fov,
    viewDistance: currentDistance.value,
  })
}

/**
 * Gère le clic direct sur le canvas cartographique
 */
function handleMapClick(e: maplibregl.MapMouseEvent) {
  const lat = roundCoordinate(e.lngLat.lat, 6)
  const lng = roundCoordinate(e.lngLat.lng, 6)

  // Si aucun bearing n'était encore défini, on initialise à 0° (Nord)
  const bearingToUse = props.bearing ?? 0

  emitCoordinatesChange(lat, lng, bearingToUse, currentFov.value)
}

/**
 * Recentre la vue sur le marqueur ou le territoire actif
 */
function centerOnMarker() {
  if (!map) return
  if (currentLat.value !== null && currentLng.value !== null) {
    map.flyTo({
      center: [currentLng.value, currentLat.value],
      zoom: 16,
      duration: 800,
    })
  } else if (props.defaultCenter) {
    map.flyTo({
      center: [props.defaultCenter.lng, props.defaultCenter.lat],
      zoom: props.defaultCenter.zoom || 14,
      duration: 800,
    })
  }
}

/**
 * Efface le pointement géographique du cliché
 */
function clearPosition() {
  if (marker) {
    marker.remove()
    marker = null
  }
  emitCoordinatesChange(null, null, props.bearing, currentFov.value)
}

/**
 * Met à jour l'azimut depuis les contrôles interactifs
 */
function setBearing(val: number) {
  const norm = normalizeBearing(val)
  emit('update:bearing', norm)
  emit('change', {
    latitude: currentLat.value,
    longitude: currentLng.value,
    bearing: norm,
    fieldOfView: currentFov.value,
    viewDistance: currentDistance.value,
  })
  updateViewConeLayer()
}

/**
 * Met à jour l'ouverture angulaire (FOV)
 */
function setFieldOfView(val: number) {
  const clamped = clampFov(val)
  emit('update:fieldOfView', clamped)
  emit('change', {
    latitude: currentLat.value,
    longitude: currentLng.value,
    bearing: currentBearing.value,
    fieldOfView: clamped,
    viewDistance: currentDistance.value,
  })
  updateViewConeLayer()
}

/**
 * Met à jour la portée métrique du cône de vision
 */
function setViewDistance(val: number) {
  const clamped = Math.max(20, Math.min(2000, isNaN(val) ? 160 : Math.round(val)))
  emit('update:viewDistance', clamped)
  emit('change', {
    latitude: currentLat.value,
    longitude: currentLng.value,
    bearing: currentBearing.value,
    fieldOfView: currentFov.value,
    viewDistance: clamped,
  })
  updateViewConeLayer(undefined, undefined, undefined, undefined, clamped)
}

/**
 * Modification manuelle de la latitude
 */
function handleManualLatInput(e: Event) {
  const target = e.target as HTMLInputElement
  const raw = target.value.trim()
  if (raw === '') {
    emit('update:latitude', null)
    return
  }
  const val = parseFloat(raw)
  if (!isNaN(val) && val >= -90 && val <= 90) {
    const lat = roundCoordinate(val, 6)
    emit('update:latitude', lat)
    emit('change', {
      latitude: lat,
      longitude: currentLng.value,
      bearing: currentBearing.value,
      fieldOfView: currentFov.value,
      viewDistance: currentDistance.value,
    })
  }
}

/**
 * Modification manuelle de la longitude
 */
function handleManualLngInput(e: Event) {
  const target = e.target as HTMLInputElement
  const raw = target.value.trim()
  if (raw === '') {
    emit('update:longitude', null)
    return
  }
  const val = parseFloat(raw)
  if (!isNaN(val) && val >= -180 && val <= 180) {
    const lng = roundCoordinate(val, 6)
    emit('update:longitude', lng)
    emit('change', {
      latitude: currentLat.value,
      longitude: lng,
      bearing: currentBearing.value,
      fieldOfView: currentFov.value,
      viewDistance: currentDistance.value,
    })
  }
}

onMounted(() => {
  if (!mapContainerRef.value) return

  // Calcul du centre initial
  let initialCenter: [number, number] = [5.9328, 43.1242]
  let initialZoom = 14

  if (props.latitude !== null && props.longitude !== null) {
    initialCenter = [props.longitude, props.latitude]
    initialZoom = 16
  } else if (props.defaultCenter) {
    initialCenter = [props.defaultCenter.lng, props.defaultCenter.lat]
    initialZoom = props.defaultCenter.zoom || 14
  }

  // Instanciation de MapLibre GL
  map = new maplibregl.Map({
    container: mapContainerRef.value,
    style: OSM_STYLE,
    center: initialCenter,
    zoom: initialZoom,
    pitch: 0,
    bearing: 0,
    attributionControl: false,
  })

  // Ajout des contrôles de zoom et boussole intégrés
  map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
  map.addControl(
    new maplibregl.AttributionControl({
      compact: true,
      customAttribution: 'Données cartographiques © OpenStreetMap',
    }),
    'bottom-right'
  )

  map.on('load', () => {
    if (!map) return

    // Ajout de la source GeoJSON pour le cône de vue
    map.addSource('view-cone-source', {
      type: 'geojson',
      data: createEmptyFeatureCollection(),
    })

    // Remplissage semi-transparent du cône
    map.addLayer({
      id: 'view-cone-fill',
      type: 'fill',
      source: 'view-cone-source',
      layout: {},
      paint: {
        'fill-color': '#0ea5e9',
        'fill-opacity': 0.35,
      },
    })

    // Bordure vectorielle du cône
    map.addLayer({
      id: 'view-cone-stroke',
      type: 'line',
      source: 'view-cone-source',
      layout: {
        'line-cap': 'round',
        'line-join': 'round',
      },
      paint: {
        'line-color': '#0284c7',
        'line-width': 2,
        'line-dasharray': [2, 2],
      },
    })

    isMapReady.value = true

    // Initialisation du marqueur et du cône si déjà géolocalisé
    updateMarkerPosition()
    updateViewConeLayer()

    // Si la photo n'est pas encore géolocalisée, résolution du territoire actif pour recentrage
    if (currentLat.value === null || currentLng.value === null) {
      photoApi
        .getCurrentTerritory()
        .then((terr) => {
          if (terr && map && (currentLat.value === null || currentLng.value === null)) {
            map.flyTo({
              center: [terr.center_lng, terr.center_lat],
              zoom: terr.default_zoom || 14,
              duration: 500,
            })
          }
        })
        .catch(() => {})
    }
  })

  map.on('click', handleMapClick)

  // Observation des redimensionnements pour synchroniser le canvas WebGL
  resizeObserver = new ResizeObserver(() => {
    map?.resize()
  })
  resizeObserver.observe(mapContainerRef.value)

  // Force le resize après le rendu du modal
  nextTick(() => {
    setTimeout(() => {
      map?.resize()
    }, 150)
  })
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (marker) {
    marker.remove()
    marker = null
  }
  if (map) {
    map.remove()
    map = null
  }
})

// Réaction aux changements de coordonnées externes
watch(
  () => [props.latitude, props.longitude],
  ([newLat, newLng], [oldLat, oldLng]) => {
    if (isMapReady.value) {
      updateMarkerPosition()
      if (
        newLat !== null &&
        newLng !== null &&
        (oldLat === null || oldLng === null || oldLat === undefined)
      ) {
        centerOnMarker()
      }
    }
  }
)

// Réaction aux changements d'orientation, d'ouverture angulaire ou de portée
watch(
  () => [props.bearing, props.fieldOfView, props.viewDistance],
  () => {
    if (isMapReady.value) {
      updateViewConeLayer()
    }
  }
)

// Méthode publique exposée pour redimensionner la carte lors du changement d'onglet
defineExpose({
  resize: () => {
    map?.resize()
  },
  centerOnMarker,
})
</script>

<template>
  <div class="space-y-4">
    <!-- Barre d'état du positionnement -->
    <div class="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800">
      <div class="flex items-center gap-2.5">
        <span
          class="flex h-3 w-3 rounded-full"
          :class="hasCoordinates ? 'bg-emerald-400 animate-pulse' : 'bg-amber-500'"
        ></span>
        <div>
          <span class="text-xs font-semibold text-white">
            {{ hasCoordinates ? 'Position définie' : 'Non géolocalisé' }}
          </span>
          <span v-if="hasCoordinates" class="text-xs font-mono text-sky-400 ml-2">
            {{ currentLat?.toFixed(6) }}°, {{ currentLng?.toFixed(6) }}°
          </span>
          <p v-else class="text-[11px] text-slate-400">
            Cliquez sur la carte ou glissez le marqueur pour placer la prise de vue.
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="hasCoordinates"
          type="button"
          class="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors flex items-center gap-1.5"
          @click="centerOnMarker"
          title="Centrer la carte sur le marqueur"
        >
          <span>🎯</span>
          <span>Centrer</span>
        </button>

        <button
          v-if="hasCoordinates"
          type="button"
          class="px-2.5 py-1 text-xs font-medium text-rose-400 hover:text-rose-300 bg-rose-950/50 hover:bg-rose-900/60 border border-rose-800/80 rounded-lg transition-colors flex items-center gap-1.5"
          @click="clearPosition"
          title="Supprimer la géolocalisation pour ce cliché"
        >
          <span>✕</span>
          <span>Effacer la position</span>
        </button>
      </div>
    </div>

    <!-- Conteneur de la Carte MapLibre GL -->
    <div class="relative w-full h-80 sm:h-96 rounded-xl overflow-hidden border border-slate-700/80 shadow-inner bg-slate-950">
      <div ref="mapContainerRef" class="w-full h-full"></div>

      <!-- Indicateur d'aide flottant -->
      <div
        v-if="!hasCoordinates"
        class="absolute top-3 left-3 z-10 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 shadow-md flex items-center gap-2 pointer-events-none"
      >
        <span class="text-sky-400 text-sm">📍</span>
        <span>Cliquez sur la carte pour positionner le cliché</span>
      </div>
    </div>

    <!-- Saisie numérique directe des coordonnées -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
          Latitude WGS84 (6 décimales)
        </label>
        <input
          type="number"
          step="0.000001"
          min="-90"
          max="90"
          placeholder="Ex: 43.124500"
          :value="currentLat ?? ''"
          @input="handleManualLatInput"
          class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm font-mono"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
          Longitude WGS84 (6 décimales)
        </label>
        <input
          type="number"
          step="0.000001"
          min="-180"
          max="180"
          placeholder="Ex: 5.928500"
          :value="currentLng ?? ''"
          @input="handleManualLngInput"
          class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm font-mono"
        />
      </div>
    </div>

    <!-- Contrôles interactifs de l'azimut et du cône de vue -->
    <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <span>🧭</span>
          <span>Orientation de prise de vue (Azimut & Cône)</span>
        </h4>
        <span class="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
          {{ currentBearing }}° — {{ cardinalDirection }}
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
        <!-- Boussole rotative visuelle -->
        <div class="md:col-span-3 flex flex-col items-center justify-center p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
          <div
            class="relative w-20 h-20 rounded-full border-2 border-slate-700 bg-slate-900 flex items-center justify-center shadow-md transition-transform duration-200"
            :style="{ transform: `rotate(${currentBearing}deg)` }"
          >
            <!-- Aiguille de la boussole -->
            <div class="absolute top-1.5 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[24px] border-b-rose-500"></div>
            <div class="absolute bottom-1.5 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[24px] border-t-slate-500"></div>
            <div class="w-2.5 h-2.5 rounded-full bg-white z-10 shadow"></div>
          </div>
          <span class="text-[10px] font-mono text-slate-400 mt-2">Cap : {{ currentBearing }}°</span>
        </div>

        <!-- Réglages Azimut (Curseur + Raccourcis cardinaux) -->
        <div class="md:col-span-9 space-y-3">
          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-xs">
              <span class="text-slate-300 font-medium">Curseur d'azimut (0° à 359°)</span>
              <div class="flex items-center gap-2">
                <input
                  type="number"
                  min="0"
                  max="359"
                  :value="currentBearing"
                  @input="setBearing(Number(($event.target as HTMLInputElement).value))"
                  class="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-right text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
                <span class="text-slate-400">degrés</span>
              </div>
            </div>

            <input
              type="range"
              min="0"
              max="359"
              step="1"
              :value="currentBearing"
              @input="setBearing(Number(($event.target as HTMLInputElement).value))"
              class="w-full accent-sky-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
            />
          </div>

          <!-- Raccourcis cardinaux rapides -->
          <div class="flex items-center gap-2 pt-1">
            <span class="text-[11px] text-slate-400 mr-1">Raccourcis :</span>
            <button
              type="button"
              class="px-2.5 py-1 text-xs rounded border transition-colors font-medium"
              :class="currentBearing === 0 ? 'bg-sky-600 border-sky-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'"
              @click="setBearing(0)"
            >
              Nord (0°)
            </button>
            <button
              type="button"
              class="px-2.5 py-1 text-xs rounded border transition-colors font-medium"
              :class="currentBearing === 90 ? 'bg-sky-600 border-sky-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'"
              @click="setBearing(90)"
            >
              Est (90°)
            </button>
            <button
              type="button"
              class="px-2.5 py-1 text-xs rounded border transition-colors font-medium"
              :class="currentBearing === 180 ? 'bg-sky-600 border-sky-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'"
              @click="setBearing(180)"
            >
              Sud (180°)
            </button>
            <button
              type="button"
              class="px-2.5 py-1 text-xs rounded border transition-colors font-medium"
              :class="currentBearing === 270 ? 'bg-sky-600 border-sky-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'"
              @click="setBearing(270)"
            >
              Ouest (270°)
            </button>
          </div>
        </div>
      </div>

      <!-- Ouverture angulaire (Champ de vision - FOV) -->
      <div class="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-0.5">
          <label class="block text-xs font-medium text-slate-300">
            Ouverture du champ de vision (FOV) : <strong class="text-sky-400 font-mono">{{ currentFov }}°</strong>
          </label>
          <p class="text-[11px] text-slate-500">
            Standard: 60° (focale normale 50mm) • 90° (grand angle) • 35° (téléobjectif). Borné entre 10° et 120°.
          </p>
        </div>

        <div class="flex items-center gap-3">
          <input
            type="range"
            min="10"
            max="120"
            step="5"
            :value="currentFov"
            @input="setFieldOfView(Number(($event.target as HTMLInputElement).value))"
            class="w-36 sm:w-44 accent-sky-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
          />
          <input
            type="number"
            min="10"
            max="120"
            :value="currentFov"
            @input="setFieldOfView(Number(($event.target as HTMLInputElement).value))"
            class="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-right text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
          <span class="text-xs text-slate-400">°</span>
        </div>
      </div>

      <!-- Longueur / Portée du cône de vision (mètres) -->
      <div class="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-0.5">
          <label class="block text-xs font-medium text-slate-300">
            Longueur du cône de vision : <strong class="text-amber-400 font-mono">{{ currentDistance }} m</strong>
          </label>
          <p class="text-[11px] text-slate-500">
            Ajustez la portée visuelle selon le sujet : vue rapprochée (50-100m) ou panorama lointain (500-1500m).
          </p>
        </div>

        <div class="flex items-center gap-3">
          <input
            type="range"
            min="20"
            max="2000"
            step="10"
            :value="currentDistance"
            @input="setViewDistance(Number(($event.target as HTMLInputElement).value))"
            class="w-36 sm:w-44 accent-amber-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
          />
          <input
            type="number"
            min="20"
            max="2000"
            step="10"
            :value="currentDistance"
            @input="setViewDistance(Number(($event.target as HTMLInputElement).value))"
            class="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-right text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
          <span class="text-xs text-slate-400">m</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Style personnalisé pour le marqueur photo MapLibre */
.hierici-camera-marker {
  cursor: grab;
}
.hierici-camera-marker:active {
  cursor: grabbing;
}
</style>
