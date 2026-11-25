<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import maplibregl from 'maplibre-gl'
import type { Storymap, StorymapStep } from '@/types/storymap'
import type { Photo } from '@/types/photo'
import { storymapApi } from '@/services/api'
import {
  extractStorymapSlug,
  getValidCameraTarget,
  calculateStepProgress,
  formatStepBadge,
  shouldStopAudioOnStepChange,
  formatAudioDuration,
  type CameraTarget,
} from '@/utils/storymapReader'
import { renderMarkdownPreview } from '@/utils/storymapStudio'
import { resolveDisplayImageUrl, resolveLightboxImageUrl } from '@/utils/photoViewer'
import PhotoLightbox from './PhotoLightbox.vue'

const props = withDefaults(
  defineProps<{
    slug?: string | null
    storymap?: Storymap | null
    defaultCenter?: { lat: number; lng: number; zoom?: number } | null
  }>(),
  {
    slug: null,
    storymap: null,
    defaultCenter: () => ({ lat: 43.1242, lng: 5.9328, zoom: 13 }),
  }
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select-photo', photoId: string): void
}>()

// État du récit
const currentStorymap = ref<Storymap | null>(props.storymap || null)
const isLoading = ref(!props.storymap && !!props.slug)
const errorMessage = ref<string | null>(null)
const activeStepIndex = ref<number>(-1) // -1 = Hero / Intro, 0..N-1 = Étapes, >= N = Épilogue
const isFullscreen = ref(false)

// Références DOM
const mapContainerRef = ref<HTMLDivElement | null>(null)
const scrollyContainerRef = ref<HTMLDivElement | null>(null)
const audioRefs = ref<Map<number, HTMLAudioElement>>(new Map())

// MapLibre
let map: maplibregl.Map | null = null
let currentMarker: maplibregl.Marker | null = null
let observer: IntersectionObserver | null = null
let resizeObserver: ResizeObserver | null = null

// Lecteur audio actif
const playingStepIndex = ref<number | null>(null)
const audioErrorStepIndex = ref<number | null>(null)
const audioCurrentTime = ref<number>(0)
const audioDuration = ref<number>(0)
const isAudioPlaying = ref(false)

// Visionneuse HD Lightbox
const lightboxPhoto = ref<Photo | null>(null)
const isLightboxOpen = ref(false)

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

// Étapes triées
const sortedSteps = computed<StorymapStep[]>(() => {
  if (!currentStorymap.value?.steps) return []
  return [...currentStorymap.value.steps].sort((a, b) => a.step_order - b.step_order)
})

// Progression de lecture globale
const readingProgress = computed(() => {
  return calculateStepProgress(activeStepIndex.value, sortedSteps.value.length)
})

// Badge d'en-tête
const activeStepBadge = computed(() => {
  return formatStepBadge(activeStepIndex.value, sortedSteps.value.length)
})

/**
 * Charge les détails de la storymap par son slug
 */
async function loadStorymap(slugToLoad: string) {
  isLoading.value = true
  errorMessage.value = null

  try {
    const data = await storymapApi.getPublicStorymap(slugToLoad)
    currentStorymap.value = data
    activeStepIndex.value = -1

    // Rendre le conteneur disponible dans le DOM avant d'initialiser l'IntersectionObserver
    isLoading.value = false
    await nextTick()
    initializeMap()
    setupObserver()
  } catch (err: any) {
    console.error('Erreur de chargement de la storymap:', err)
    if (err.status === 404 || err.message?.includes('404')) {
      errorMessage.value = "Ce récit patrimonial est introuvable ou n'a pas encore été publié."
    } else {
      errorMessage.value = "Impossible de charger ce récit. Veuillez vérifier votre connexion."
    }
    isLoading.value = false
  }
}

/**
 * Initialise la carte MapLibre GL
 */
function initializeMap() {
  if (!mapContainerRef.value || map) return

  const initialTarget = getInitialCameraTarget()

  map = new maplibregl.Map({
    container: mapContainerRef.value,
    style: OSM_STYLE,
    center: [initialTarget.lng, initialTarget.lat],
    zoom: initialTarget.zoom,
    bearing: initialTarget.bearing,
    pitch: initialTarget.pitch,
    attributionControl: false,
  })

  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
  map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right')

  map.on('load', () => {
    updateActiveCameraAndMarker(activeStepIndex.value)
  })

  if (mapContainerRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      map?.resize()
    })
    resizeObserver.observe(mapContainerRef.value)
  }
}

/**
 * Détermine la cible de caméra initiale (première étape ou centre territoire)
 */
function getInitialCameraTarget(): CameraTarget {
  if (sortedSteps.value.length > 0) {
    return getValidCameraTarget(sortedSteps.value[0], props.defaultCenter ?? undefined)
  }
  return getValidCameraTarget(null, props.defaultCenter ?? undefined)
}

/**
 * Configure l'IntersectionObserver pour synchroniser le défilement et la caméra
 */
function setupObserver() {
  if (typeof IntersectionObserver === 'undefined') return
  observer?.disconnect()

  observer = new IntersectionObserver(
    (entries) => {
      let bestEntry: IntersectionObserverEntry | null = null
      let maxRatio = 0

      for (const entry of entries) {
        if (entry.isIntersecting && entry.intersectionRatio > maxRatio) {
          maxRatio = entry.intersectionRatio
          bestEntry = entry
        }
      }

      if (bestEntry) {
        const stepIdxStr = (bestEntry.target as HTMLElement).dataset.stepIndex
        if (stepIdxStr !== undefined) {
          const newIndex = parseInt(stepIdxStr, 10)
          if (!isNaN(newIndex) && newIndex !== activeStepIndex.value) {
            handleStepTransition(newIndex)
          }
        }
      }
    },
    {
      root: scrollyContainerRef.value,
      rootMargin: '-20% 0px -40% 0px',
      threshold: [0.2, 0.5, 0.8],
    }
  )

  // Observer toutes les cartes d'étapes ainsi que le Hero
  if (scrollyContainerRef.value) {
    const cards = scrollyContainerRef.value.querySelectorAll<HTMLElement>('[data-step-index]')
    cards.forEach((card) => observer?.observe(card))
  }
}

/**
 * Gère la transition cinématique vers une nouvelle étape
 */
function handleStepTransition(newIndex: number) {
  // Couper l'audio en cours s'il y a transition vers une autre étape
  if (shouldStopAudioOnStepChange(activeStepIndex.value, newIndex, isAudioPlaying.value)) {
    stopCurrentAudio()
  }

  activeStepIndex.value = newIndex
  updateActiveCameraAndMarker(newIndex)
}

/**
 * Anime la caméra MapLibre GL et positionne le marqueur de la photo active
 */
function updateActiveCameraAndMarker(stepIndex: number) {
  if (!map) return

  let target: CameraTarget
  let photoToMark: Photo | null = null

  if (stepIndex >= 0 && stepIndex < sortedSteps.value.length) {
    const step = sortedSteps.value[stepIndex]
    target = getValidCameraTarget(step, props.defaultCenter ?? undefined)
    photoToMark = step.photo || null
  } else if (stepIndex >= sortedSteps.value.length && sortedSteps.value.length > 0) {
    // Épilogue : Conserver la caméra sur le dernier chapitre
    const lastStep = sortedSteps.value[sortedSteps.value.length - 1]
    target = getValidCameraTarget(lastStep, props.defaultCenter ?? undefined)
    photoToMark = lastStep.photo || null
  } else {
    // Hero ou Introduction : Cadrer sur la première étape ou le centre
    target = getInitialCameraTarget()
  }

  // Animation cinématique à 60fps
  map.flyTo({
    center: [target.lng, target.lat],
    zoom: target.zoom,
    bearing: target.bearing,
    pitch: target.pitch,
    duration: 2200,
    essential: true,
    curve: 1.42,
  })

  // Gestion du marqueur de photo sur la carte
  if (currentMarker) {
    currentMarker.remove()
    currentMarker = null
  }

  if (
    photoToMark &&
    typeof photoToMark.latitude === 'number' &&
    typeof photoToMark.longitude === 'number'
  ) {
    const lat = photoToMark.latitude
    const lng = photoToMark.longitude
    const markerEl = document.createElement('div')
    markerEl.className =
      'w-8 h-8 rounded-full bg-sky-500 border-2 border-white shadow-xl flex items-center justify-center text-white text-xs font-bold cursor-pointer transition-transform hover:scale-125 animate-bounce'
    markerEl.innerHTML = '📷'
    markerEl.title = photoToMark.title

    markerEl.addEventListener('click', () => {
      if (photoToMark) openLightbox(photoToMark)
    })

    currentMarker = new maplibregl.Marker({ element: markerEl })
      .setLngLat([lng, lat])
      .addTo(map)
  }
}

/**
 * Navigation vers l'étape précédente ou suivante
 */
function navigateStep(direction: 'prev' | 'next') {
  const total = sortedSteps.value.length
  let targetIndex = activeStepIndex.value

  if (direction === 'prev') {
    if (activeStepIndex.value >= total) {
      targetIndex = total - 1
    } else {
      targetIndex = Math.max(-1, activeStepIndex.value - 1)
    }
  } else {
    targetIndex = Math.min(total - 1, activeStepIndex.value + 1)
  }

  scrollToStep(targetIndex)
}

/**
 * Fait défiler le panneau vers une étape donnée
 */
function scrollToStep(stepIndex: number) {
  if (!scrollyContainerRef.value) return

  const targetCard = scrollyContainerRef.value.querySelector<HTMLElement>(
    `[data-step-index="${stepIndex}"]`
  )
  if (targetCard) {
    targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

/**
 * Gestion du lecteur audio
 */
function toggleStepAudio(index: number, audioUrl: string) {
  const currentAudio = audioRefs.value.get(index)
  if (!currentAudio) return

  audioErrorStepIndex.value = null

  if (playingStepIndex.value === index && isAudioPlaying.value) {
    currentAudio.pause()
    isAudioPlaying.value = false
  } else {
    // Si une autre piste était active, on la coupe
    stopCurrentAudio()

    playingStepIndex.value = index
    currentAudio
      .play()
      .then(() => {
        isAudioPlaying.value = true
        audioErrorStepIndex.value = null
      })
      .catch((err) => {
        console.warn('Lecture audio bloquée ou échouée:', err)
        isAudioPlaying.value = false
        audioErrorStepIndex.value = index
      })
  }
}

function onAudioError(index: number) {
  audioErrorStepIndex.value = index
  if (playingStepIndex.value === index) {
    isAudioPlaying.value = false
  }
}

function stopCurrentAudio() {
  if (playingStepIndex.value !== null) {
    const audio = audioRefs.value.get(playingStepIndex.value)
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
  }
  isAudioPlaying.value = false
  playingStepIndex.value = null
  audioCurrentTime.value = 0
}

function onAudioTimeUpdate(index: number, event: Event) {
  if (playingStepIndex.value === index) {
    const target = event.target as HTMLAudioElement
    audioCurrentTime.value = target.currentTime
    audioDuration.value = target.duration || 0
  }
}

function onAudioEnded(index: number) {
  if (playingStepIndex.value === index) {
    isAudioPlaying.value = false
    audioCurrentTime.value = 0
  }
}

function seekAudio(event: Event) {
  if (playingStepIndex.value === null) return
  const audio = audioRefs.value.get(playingStepIndex.value)
  if (!audio) return
  const input = event.target as HTMLInputElement
  const newTime = parseFloat(input.value)
  audio.currentTime = newTime
  audioCurrentTime.value = newTime
}

function registerAudioRef(index: number, el: any) {
  if (el) {
    audioRefs.value.set(index, el as HTMLAudioElement)
  } else {
    audioRefs.value.delete(index)
  }
}

/**
 * Ouverture de la visionneuse plein écran pour examiner les détails HD
 */
function openLightbox(photo: Photo) {
  lightboxPhoto.value = photo
  isLightboxOpen.value = true
  emit('select-photo', photo.id)
}

function closeLightbox() {
  isLightboxOpen.value = false
  lightboxPhoto.value = null
}

/**
 * Quitter le lecteur
 */
function handleExit() {
  stopCurrentAudio()
  emit('close')
}

/**
 * Bascule plein écran navigateur
 */
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => null)
    isFullscreen.value = true
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(() => null)
    }
    isFullscreen.value = false
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

/**
 * Navigation clavier
 */
function handleKeydown(event: KeyboardEvent) {
  if (isLightboxOpen.value) return // Priorité à la lightbox si ouverte

  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA', 'BUTTON', 'SELECT'].includes(target.tagName)) {
    return
  }

  if (event.key === 'Escape') {
    handleExit()
  } else if (event.key === 'ArrowDown' || event.key === 'PageDown') {
    event.preventDefault()
    navigateStep('next')
  } else if (event.key === 'ArrowUp' || event.key === 'PageUp') {
    event.preventDefault()
    navigateStep('prev')
  }
}

watch(
  () => props.slug,
  (newSlug) => {
    if (newSlug) {
      loadStorymap(newSlug)
    }
  }
)

watch(
  () => props.storymap,
  (newStorymap) => {
    if (newStorymap) {
      currentStorymap.value = newStorymap
      nextTick(() => {
        initializeMap()
        setupObserver()
      })
    }
  }
)

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('fullscreenchange', onFullscreenChange)

  if (props.storymap) {
    nextTick(() => {
      initializeMap()
      setupObserver()
    })
  } else if (props.slug) {
    loadStorymap(props.slug)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  stopCurrentAudio()
  observer?.disconnect()
  resizeObserver?.disconnect()
  currentMarker?.remove()
  map?.remove()
  map = null
})
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-950 text-slate-100 flex flex-col overflow-hidden font-sans select-none">
    <!-- Barre Supérieure de Contrôle & Progression -->
    <header
      class="h-14 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-6 flex items-center justify-between z-30 shadow-lg relative"
    >
      <!-- Bouton Quitter & Titre -->
      <div class="flex items-center space-x-3 sm:space-x-4 min-w-0">
        <button
          type="button"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 hover:border-slate-600 text-xs font-semibold transition-all shadow-sm"
          title="Quitter le récit et revenir à la carte (Échap)"
          @click="handleExit"
        >
          <span>←</span>
          <span class="hidden sm:inline">Quitter</span>
        </button>

        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm">📖</span>
            <h2 class="text-xs sm:text-sm font-bold text-white truncate max-w-[200px] sm:max-w-md">
              {{ currentStorymap?.title || 'Récit patrimonial' }}
            </h2>
          </div>
          <p class="text-[10px] text-slate-400 font-medium">
            {{ activeStepBadge }}
          </p>
        </div>
      </div>

      <!-- Contrôles Droite : Navigation, Audio & Plein Écran -->
      <div class="flex items-center space-x-2">
        <!-- Contrôles d'étapes précédent / suivant -->
        <div class="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs">
          <button
            type="button"
            class="p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition-colors disabled:opacity-30 disabled:pointer-events-none"
            :disabled="activeStepIndex <= -1"
            title="Étape précédente (Flèche Haut)"
            @click="navigateStep('prev')"
          >
            ↑
          </button>
          <span class="px-2 font-mono text-[11px] text-sky-400">
            {{ activeStepIndex < 0 ? '0' : (activeStepIndex >= sortedSteps.length ? sortedSteps.length : activeStepIndex + 1) }} / {{ sortedSteps.length }}
          </span>
          <button
            type="button"
            class="p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition-colors disabled:opacity-30 disabled:pointer-events-none"
            :disabled="activeStepIndex >= sortedSteps.length - 1"
            title="Étape suivante (Flèche Bas)"
            @click="navigateStep('next')"
          >
            ↓
          </button>
        </div>

        <!-- Témoin d'audio en cours -->
        <button
          v-if="isAudioPlaying"
          type="button"
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/80 border border-emerald-700 text-emerald-400 text-[11px] font-semibold animate-pulse"
          title="Piste sonore active - Cliquer pour couper"
          @click="stopCurrentAudio"
        >
          <span>🔊</span>
          <span class="hidden md:inline">Audio en cours</span>
        </button>

        <!-- Bascule Plein écran -->
        <button
          type="button"
          class="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors text-xs"
          :title="isFullscreen ? 'Quitter le plein écran' : 'Plein écran'"
          @click="toggleFullscreen"
        >
          ⛶
        </button>
      </div>

      <!-- Ligne de Progression Horizontale -->
      <div class="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-800">
        <div
          class="h-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all duration-300 ease-out"
          :style="{ width: `${readingProgress}%` }"
        ></div>
      </div>
    </header>

    <!-- Zone Principale : Carte MapLibre GL en Arrière-Plan + Volet Narratif Déroulant -->
    <div class="flex-1 relative w-full h-full overflow-hidden">
      <!-- Conteneur Carte MapLibre GL Plein Écran -->
      <div ref="mapContainerRef" class="absolute inset-0 w-full h-full z-0"></div>

      <!-- État de Chargement Initial -->
      <div
        v-if="isLoading"
        class="absolute inset-0 z-40 bg-slate-950/90 flex flex-col items-center justify-center p-6 space-y-4"
      >
        <div class="w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm font-medium text-slate-300">Immersion dans le récit historique...</p>
      </div>

      <!-- État d'Erreur (404 / Non publié) -->
      <div
        v-else-if="errorMessage"
        class="absolute inset-0 z-40 bg-slate-950/95 flex flex-col items-center justify-center p-6 text-center space-y-5"
      >
        <div class="w-16 h-16 rounded-full bg-rose-950/80 border border-rose-800 text-rose-400 flex items-center justify-center text-3xl shadow-xl">
          ⚠️
        </div>
        <div class="max-w-md space-y-2">
          <h3 class="text-lg font-bold text-white">Récit introuvable</h3>
          <p class="text-xs text-slate-400">{{ errorMessage }}</p>
        </div>
        <button
          type="button"
          class="px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs transition-all shadow-lg shadow-sky-900/40"
          @click="handleExit"
        >
          ← Retourner à la carte d'exploration
        </button>
      </div>

      <!-- Panneau Déroulant Narratif (Scrollytelling Vertical) -->
      <div
        v-else
        ref="scrollyContainerRef"
        class="absolute inset-0 z-10 overflow-y-auto px-4 sm:px-8 py-10 pointer-events-none scroll-smooth flex flex-col items-start"
      >
        <div class="w-full max-w-lg space-y-24 pointer-events-auto">
          <!-- CARTE HERO : Présentation du Récit -->
          <article
            data-step-index="-1"
            class="scrolly-step-card min-h-[60vh] flex flex-col justify-center bg-slate-950/90 backdrop-blur-md rounded-2xl border border-slate-800 p-6 sm:p-8 shadow-2xl space-y-6 transition-all duration-500"
            :class="activeStepIndex === -1 ? 'ring-2 ring-sky-500/50 shadow-sky-950/50' : 'opacity-85 hover:opacity-100'"
          >
            <!-- Image de couverture -->
            <div
              v-if="currentStorymap?.cover_image_url"
              class="relative rounded-xl overflow-hidden aspect-video bg-slate-900 border border-slate-800 shadow-inner group"
            >
              <img
                :src="currentStorymap.cover_image_url"
                :alt="currentStorymap.title"
                class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              />
              <div class="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent"></div>
              <div class="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-950/80 backdrop-blur-sm text-[10px] font-bold text-sky-400 border border-slate-700">
                <span>📍 Récit Géolocalisé</span>
              </div>
            </div>

            <div class="space-y-3">
              <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-950/80 text-sky-400 border border-sky-800">
                ✨ Visite Découverte
              </span>
              <h1 class="text-2xl sm:text-3xl font-black text-white tracking-tight leading-snug">
                {{ currentStorymap?.title }}
              </h1>
              <p
                v-if="currentStorymap?.summary"
                class="text-sm text-slate-300 leading-relaxed font-normal"
              >
                {{ currentStorymap.summary }}
              </p>
            </div>

            <!-- Fiche méta & invitation au scroll -->
            <div class="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
              <div class="flex items-center gap-3">
                <span>📚 {{ sortedSteps.length }} chapitres</span>
                <span v-if="sortedSteps.some((s) => s.audio_url)">🎧 Audio inclus</span>
              </div>
              <button
                type="button"
                class="text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1 group"
                @click="scrollToStep(0)"
              >
                <span>Commencer</span>
                <span class="group-hover:translate-y-0.5 transition-transform">↓</span>
              </button>
            </div>
          </article>

          <!-- CARTES DE CHAPITRES (Storymap Steps) -->
          <article
            v-for="(step, idx) in sortedSteps"
            :key="step.id"
            :data-step-index="idx"
            class="scrolly-step-card min-h-[60vh] flex flex-col justify-center bg-slate-950/90 backdrop-blur-md rounded-2xl border p-6 sm:p-7 shadow-2xl space-y-5 transition-all duration-500"
            :class="activeStepIndex === idx ? 'border-sky-500/80 ring-2 ring-sky-500/30 shadow-sky-950/50' : 'border-slate-800/80 opacity-80 hover:opacity-100'"
          >
            <!-- Badge & Titre du Chapitre -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span
                  class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-colors"
                  :class="activeStepIndex === idx ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-400'"
                >
                  Chapitre {{ idx + 1 }}
                </span>
                <span class="text-[10px] text-slate-500 font-mono">
                  {{ step.camera_zoom ? `Zoom ${step.camera_zoom.toFixed(1)}x` : '' }}
                </span>
              </div>
              <h2 class="text-lg sm:text-xl font-bold text-white tracking-tight">
                {{ step.title }}
              </h2>
            </div>

            <!-- Photographie Patrimoniale d'Archive liée -->
            <div
              v-if="step.photo"
              class="rounded-xl overflow-hidden bg-slate-900 border border-slate-800 shadow-md space-y-2 group"
            >
              <div
                class="relative aspect-[4/3] overflow-hidden cursor-zoom-in bg-slate-950"
                @click="openLightbox(step.photo)"
              >
                <img
                  :src="resolveDisplayImageUrl(step.photo) || ''"
                  :alt="step.photo.title"
                  loading="lazy"
                  class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <!-- Overlay d'agrandissement -->
                <div class="absolute inset-0 bg-slate-950/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span class="px-3 py-1.5 rounded-xl bg-slate-900/90 backdrop-blur-sm text-xs font-semibold text-white border border-slate-700 shadow-lg flex items-center gap-1.5">
                    🔍 Agrandir HD
                  </span>
                </div>
              </div>

              <!-- Légende & Métadonnées d'archive -->
              <div class="p-3 bg-slate-900/80 text-[11px] text-slate-300 space-y-1">
                <div class="font-semibold text-slate-100 flex items-center justify-between">
                  <span class="truncate">{{ step.photo.title }}</span>
                  <span v-if="step.photo.year || step.photo.year_taken" class="text-sky-400 font-mono text-[10px] pl-2">
                    {{ step.photo.year || step.photo.year_taken }}
                  </span>
                </div>
                <div class="flex items-center justify-between text-[10px] text-slate-400">
                  <span v-if="step.photo.photographer">Auteur : {{ step.photo.photographer }}</span>
                  <span v-if="step.photo.bearing !== undefined && step.photo.bearing !== null" class="font-mono text-emerald-400">
                    Azimut : {{ step.photo.bearing }}°
                  </span>
                </div>
              </div>
            </div>

            <!-- Contenu Narratif Markdown -->
            <div
              v-if="step.content_markdown"
              class="prose prose-invert prose-sm text-xs sm:text-sm text-slate-300 leading-relaxed font-normal"
              v-html="renderMarkdownPreview(step.content_markdown)"
            ></div>

            <!-- Lecteur Audio Synchronisé (si document sonore présent) -->
            <div
              v-if="step.audio_url"
              class="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2.5"
            >
              <audio
                :ref="(el) => registerAudioRef(idx, el)"
                :src="step.audio_url"
                preload="metadata"
                @timeupdate="(e) => onAudioTimeUpdate(idx, e)"
                @ended="() => onAudioEnded(idx)"
                @error="() => onAudioError(idx)"
              ></audio>

              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <button
                    type="button"
                    class="w-9 h-9 rounded-full bg-sky-600 hover:bg-sky-500 text-white flex items-center justify-center text-sm shadow-md transition-all active:scale-95"
                    :title="playingStepIndex === idx && isAudioPlaying ? 'Mettre en pause' : 'Écouter le document sonore'"
                    @click="toggleStepAudio(idx, step.audio_url!)"
                  >
                    <span v-if="playingStepIndex === idx && isAudioPlaying">⏸</span>
                    <span v-else class="pl-0.5">▶</span>
                  </button>
                  <div>
                    <div class="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>Archive Sonore</span>
                      <span
                        v-if="playingStepIndex === idx && isAudioPlaying"
                        class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"
                      ></span>
                    </div>
                    <div class="text-[10px] text-slate-400 font-mono">
                      <span v-if="playingStepIndex === idx">
                        {{ formatAudioDuration(audioCurrentTime) }} / {{ formatAudioDuration(audioDuration) }}
                      </span>
                      <span v-else>Document d'archive audio</span>
                    </div>
                  </div>
                </div>

                <span class="text-xs">🎧</span>
              </div>

              <!-- Message d'erreur discret si la piste échoue -->
              <div v-if="audioErrorStepIndex === idx" class="text-[10px] text-rose-400 flex items-center gap-1 pt-1">
                <span>⚠️</span>
                <span>Document sonore momentanément indisponible</span>
              </div>

              <!-- Curseur de progression audio si actif -->
              <div v-if="playingStepIndex === idx" class="pt-1">
                <input
                  type="range"
                  min="0"
                  :max="audioDuration || 100"
                  step="0.5"
                  :disabled="!audioDuration || audioDuration <= 0"
                  :value="audioCurrentTime"
                  class="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500 disabled:opacity-50"
                  @input="seekAudio"
                />
              </div>
            </div>
          </article>

          <!-- CARTE DE CONCLUSION / ÉPILOGUE -->
          <article
            data-step-index="999"
            class="scrolly-step-card min-h-[60vh] flex flex-col justify-center bg-slate-950/90 backdrop-blur-md rounded-2xl border border-slate-800 p-6 sm:p-8 shadow-2xl text-center space-y-5"
          >
            <div class="text-3xl">🎉</div>
            <div class="space-y-2">
              <h3 class="text-xl font-bold text-white">Fin du voyage géohistorique</h3>
              <p class="text-xs text-slate-300">
                Vous avez parcouru l'intégralité des chapitres de ce récit.
              </p>
            </div>

            <div class="flex flex-col sm:flex-row items-center justify-center gap-3 pt-3">
              <button
                type="button"
                class="w-full sm:w-auto px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
                @click="scrollToStep(-1)"
              >
                ↺ Revoir depuis le début
              </button>
              <button
                type="button"
                class="w-full sm:w-auto px-5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition-all shadow-lg shadow-sky-900/40"
                @click="handleExit"
              >
                ← Découvrir d'autres clichés sur la carte
              </button>
            </div>
          </article>
        </div>
      </div>
    </div>

    <!-- Visionneuse HD Plein Écran (PhotoLightbox) -->
    <PhotoLightbox
      v-if="lightboxPhoto"
      :is-open="isLightboxOpen"
      :image-url="resolveLightboxImageUrl(lightboxPhoto)"
      :title="lightboxPhoto.title"
      :photographer="lightboxPhoto.photographer"
      :year="lightboxPhoto.year ?? lightboxPhoto.year_taken"
      :period-label="lightboxPhoto.period_label"
      :archive-source="lightboxPhoto.archive_source"
      :archive-ref="lightboxPhoto.archive_ref ?? lightboxPhoto.archive_reference"
      :license="lightboxPhoto.license"
      @close="closeLightbox"
    />
  </div>
</template>

<style scoped>
/* Scrollbar personnalisée discrète pour le panneau scrollytelling */
.scrolly-step-card {
  will-change: transform, opacity;
}
</style>
