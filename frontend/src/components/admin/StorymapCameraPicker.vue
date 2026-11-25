<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import maplibregl from 'maplibre-gl'
import { clampCameraCoordinates, normalizeBearing } from '@/utils/storymapStudio'

const props = withDefaults(
  defineProps<{
    cameraLat: number
    cameraLng: number
    cameraZoom?: number
    cameraBearing?: number
    cameraPitch?: number
    defaultCenter?: { lat: number; lng: number; zoom?: number } | null
  }>(),
  {
    cameraZoom: 13,
    cameraBearing: 0,
    cameraPitch: 0,
    defaultCenter: () => ({ lat: 43.1242, lng: 5.9328, zoom: 13 }),
  }
)

const emit = defineEmits<{
  (e: 'update:cameraLat', val: number): void
  (e: 'update:cameraLng', val: number): void
  (e: 'update:cameraZoom', val: number): void
  (e: 'update:cameraBearing', val: number): void
  (e: 'update:cameraPitch', val: number): void
  (
    e: 'capture',
    val: {
      camera_lat: number
      camera_lng: number
      camera_zoom: number
      camera_bearing: number
      camera_pitch: number
    }
  ): void
}>()

const mapContainerRef = ref<HTMLDivElement | null>(null)
let map: maplibregl.Map | null = null
let resizeObserver: ResizeObserver | null = null

const isMapReady = ref(false)
const capturedFeedback = ref(false)
let feedbackTimeout: ReturnType<typeof setTimeout> | null = null

// Coordonnées en temps réel lues depuis la caméra
const liveLat = ref(props.cameraLat)
const liveLng = ref(props.cameraLng)
const liveZoom = ref(props.cameraZoom)
const liveBearing = ref(props.cameraBearing)
const livePitch = ref(props.cameraPitch)

// Style raster libre OpenStreetMap
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

function updateLiveCameraState() {
  if (!map) return
  const center = map.getCenter()
  const coords = clampCameraCoordinates(
    center.lat,
    center.lng,
    map.getZoom(),
    map.getBearing(),
    map.getPitch()
  )
  liveLat.value = coords.camera_lat
  liveLng.value = coords.camera_lng
  liveZoom.value = coords.camera_zoom
  liveBearing.value = coords.camera_bearing
  livePitch.value = coords.camera_pitch
}

/**
 * Capture instantanément les paramètres caméra de la vue actuelle
 */
function captureCurrentView() {
  if (!map) return
  updateLiveCameraState()

  emit('update:cameraLat', liveLat.value)
  emit('update:cameraLng', liveLng.value)
  emit('update:cameraZoom', liveZoom.value)
  emit('update:cameraBearing', liveBearing.value)
  emit('update:cameraPitch', livePitch.value)

  emit('capture', {
    camera_lat: liveLat.value,
    camera_lng: liveLng.value,
    camera_zoom: liveZoom.value,
    camera_bearing: liveBearing.value,
    camera_pitch: livePitch.value,
  })

  // Feedback visuel temporaire
  capturedFeedback.value = true
  if (feedbackTimeout) clearTimeout(feedbackTimeout)
  feedbackTimeout = setTimeout(() => {
    capturedFeedback.value = false
  }, 2200)
}

/**
 * Teste le rendu cinématique via MapLibre flyTo
 */
function testFramingAnimation() {
  if (!map) return
  map.flyTo({
    center: [props.cameraLng, props.cameraLat],
    zoom: props.cameraZoom,
    bearing: props.cameraBearing,
    pitch: props.cameraPitch,
    duration: 1500,
    essential: true,
  })
}

/**
 * Ajuste manuellement le pitch ou le bearing via curseur
 */
function onSliderPitchChange(e: Event) {
  const target = e.target as HTMLInputElement
  const newPitch = Number(target.value)
  if (map && !isNaN(newPitch)) {
    map.setPitch(newPitch)
  }
}

function onSliderBearingChange(e: Event) {
  const target = e.target as HTMLInputElement
  const newBearing = Number(target.value)
  if (map && !isNaN(newBearing)) {
    map.setBearing(newBearing)
  }
}

function initMap() {
  if (!mapContainerRef.value || map) return

  const initialLat = props.cameraLat ?? props.defaultCenter?.lat ?? 43.1242
  const initialLng = props.cameraLng ?? props.defaultCenter?.lng ?? 5.9328
  const initialZoom = props.cameraZoom ?? props.defaultCenter?.zoom ?? 13
  const initialBearing = props.cameraBearing ?? 0
  const initialPitch = props.cameraPitch ?? 0

  map = new maplibregl.Map({
    container: mapContainerRef.value,
    style: OSM_STYLE,
    center: [initialLng, initialLat],
    zoom: initialZoom,
    bearing: initialBearing,
    pitch: initialPitch,
    maxPitch: 85,
    attributionControl: false,
  })

  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

  map.on('move', () => {
    updateLiveCameraState()
  })

  map.on('load', () => {
    isMapReady.value = true
    updateLiveCameraState()
    map?.resize()
  })
}

// Synchroniser la carte si les props changent depuis l'extérieur (ex: bascule de chapitre)
watch(
  () => [props.cameraLat, props.cameraLng, props.cameraZoom, props.cameraBearing, props.cameraPitch],
  ([lat, lng, zoom, bearing, pitch]) => {
    if (!map || !isMapReady.value) return
    const curCenter = map.getCenter()
    const dist = Math.abs(curCenter.lat - (lat as number)) + Math.abs(curCenter.lng - (lng as number))
    const zoomDiff = Math.abs(map.getZoom() - (zoom as number))
    const bearingDiff = Math.abs(map.getBearing() - (bearing as number))
    const pitchDiff = Math.abs(map.getPitch() - (pitch as number))

    // Si la cible diffère substantiellement (position, zoom, bearing ou pitch), recentrer
    if (dist > 0.0001 || zoomDiff > 0.1 || bearingDiff > 1 || pitchDiff > 1) {
      map.jumpTo({
        center: [lng as number, lat as number],
        zoom: zoom as number,
        bearing: bearing as number,
        pitch: pitch as number,
      })
      updateLiveCameraState()
    }
  }
)

onMounted(() => {
  nextTick(() => {
    initMap()
    if (mapContainerRef.value) {
      resizeObserver = new ResizeObserver(() => {
        map?.resize()
      })
      resizeObserver.observe(mapContainerRef.value)
    }
  })
})

onUnmounted(() => {
  if (feedbackTimeout) clearTimeout(feedbackTimeout)
  if (resizeObserver) resizeObserver.disconnect()
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="relative flex flex-col rounded-xl overflow-hidden border border-slate-800 bg-slate-900 shadow-inner">
    <!-- Barre d'outils et de contrôle du cadrage -->
    <div class="px-4 py-2.5 bg-slate-900/95 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
      <div class="flex items-center gap-2">
        <span class="text-base">🎥</span>
        <span class="font-semibold text-slate-200">Cadrage cartographique 3D</span>
        <span class="text-[11px] text-slate-400 hidden sm:inline">
          (Ajustez la vue, l'inclinaison et l'orientation)
        </span>
      </div>

      <div class="flex items-center gap-2">
        <!-- Bouton Tester flyTo -->
        <button
          type="button"
          class="px-2.5 py-1.5 rounded-lg font-medium text-sky-300 bg-sky-950/80 hover:bg-sky-900/80 border border-sky-800/80 transition-all flex items-center gap-1.5 shadow-sm"
          title="Simuler l'animation cinématographique flyTo vers le cadrage enregistré"
          @click="testFramingAnimation"
        >
          <span>🚀</span>
          <span>Tester le cadrage</span>
        </button>

        <!-- Bouton Capturer la vue actuelle -->
        <button
          type="button"
          class="px-3.5 py-1.5 rounded-lg font-semibold text-white transition-all flex items-center gap-1.5 shadow-md"
          :class="capturedFeedback ? 'bg-emerald-600 scale-105' : 'bg-amber-600 hover:bg-amber-500 shadow-amber-900/30'"
          title="Enregistrer le centre, zoom, azimut et inclinaison actuels pour cette étape"
          @click="captureCurrentView"
        >
          <span v-if="capturedFeedback">✓</span>
          <span v-else>📸</span>
          <span>{{ capturedFeedback ? 'Vue capturée !' : 'Capturer la vue actuelle' }}</span>
        </button>
      </div>
    </div>

    <!-- Conteneur MapLibre GL avec réticule central -->
    <div class="relative w-full h-80 sm:h-96">
      <div ref="mapContainerRef" class="w-full h-full"></div>

      <!-- Réticule central pour viser précisément -->
      <div class="absolute inset-0 pointer-events-none flex items-center justify-center">
        <div class="relative w-8 h-8 flex items-center justify-center">
          <div class="w-2 h-2 rounded-full bg-amber-400 border border-slate-950 shadow-md"></div>
          <div class="absolute w-6 h-0.5 bg-amber-400/60"></div>
          <div class="absolute h-6 w-0.5 bg-amber-400/60"></div>
        </div>
      </div>

      <!-- Badge Feedback de capture -->
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-2 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 translate-y-2 scale-95"
      >
        <div
          v-if="capturedFeedback"
          class="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-4 py-2 bg-emerald-900/95 border border-emerald-500 text-emerald-100 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-semibold backdrop-blur-md"
        >
          <span>✓</span>
          <span>Cadrage caméra enregistré avec succès</span>
        </div>
      </transition>

      <!-- Contrôles d'ajustement fin 3D (Pitch & Bearing) -->
      <div class="absolute bottom-3 left-3 z-10 bg-slate-950/90 backdrop-blur-md border border-slate-800 rounded-xl p-2.5 shadow-xl space-y-2 text-[11px] text-slate-300 w-52 sm:w-60">
        <div class="flex items-center justify-between font-mono text-[10px] text-slate-400">
          <span>Inclinaison 3D (Pitch)</span>
          <span class="text-amber-400 font-bold">{{ livePitch }}°</span>
        </div>
        <input
          type="range"
          min="0"
          max="85"
          step="1"
          :value="livePitch"
          class="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
          @input="onSliderPitchChange"
        />

        <div class="flex items-center justify-between font-mono text-[10px] text-slate-400 pt-1">
          <span>Orientation (Bearing)</span>
          <span class="text-sky-400 font-bold">{{ liveBearing }}°</span>
        </div>
        <input
          type="range"
          min="0"
          max="359"
          step="1"
          :value="liveBearing"
          class="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          @input="onSliderBearingChange"
        />
      </div>
    </div>

    <!-- Récapitulatif des paramètres caméra enregistrés pour l'étape -->
    <div class="px-4 py-2 bg-slate-950 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400 font-mono">
      <div class="flex items-center gap-3">
        <span class="text-slate-300 font-sans font-medium">Cadrage actif :</span>
        <span>Lat: <strong class="text-white">{{ cameraLat?.toFixed(4) ?? '0.0000' }}</strong></span>
        <span>Lng: <strong class="text-white">{{ cameraLng?.toFixed(4) ?? '0.0000' }}</strong></span>
        <span>Zoom: <strong class="text-white">{{ cameraZoom?.toFixed(1) ?? '13.0' }}</strong></span>
      </div>
      <div class="flex items-center gap-3">
        <span>Azimut: <strong class="text-sky-400">{{ cameraBearing?.toFixed(1) ?? '0.0' }}°</strong></span>
        <span>Inclinaison: <strong class="text-amber-400">{{ cameraPitch?.toFixed(1) ?? '0.0' }}°</strong></span>
      </div>
    </div>
  </div>
</template>
