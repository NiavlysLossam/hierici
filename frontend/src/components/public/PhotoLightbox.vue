<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { clampZoom, calculateZoomToCursor } from '@/utils/photoViewer'

const props = withDefaults(
  defineProps<{
    isOpen: boolean
    imageUrl: string
    title: string
    photographer?: string | null
    year?: number | null
    periodLabel?: string | null
    archiveSource?: string | null
    archiveRef?: string | null
    license?: string | null
  }>(),
  {
    photographer: null,
    year: null,
    periodLabel: null,
    archiveSource: null,
    archiveRef: null,
    license: null,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)

// État de transformation : zoom & déplacement
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const isDragging = ref(false)
const isWheelZooming = ref(false)
const isImageLoaded = ref(false)
const hasLoadError = ref(false)
const showInfo = ref(true)
let wheelTimer: ReturnType<typeof setTimeout> | null = null

// Gestion du glissement (pointer events)
let dragStartX = 0
let dragStartY = 0
let initialPinchDistance = 0
let initialPinchZoom = 1

const minZoom = 0.5
const maxZoom = 6

const transformStyle = computed(() => ({
  transform: `translate3d(${panX.value}px, ${panY.value}px, 0) scale(${zoom.value})`,
  transformOrigin: 'center center',
  transition: isDragging.value || isWheelZooming.value ? 'none' : 'transform 0.15s ease-out',
}))

function resetView() {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

function handleZoomIn() {
  zoom.value = Number(clampZoom(zoom.value * 1.35, minZoom, maxZoom).toFixed(2))
}

function handleZoomOut() {
  zoom.value = Number(clampZoom(zoom.value / 1.35, minZoom, maxZoom).toFixed(2))
}

/**
 * Zoom centré sur la position du curseur
 */
function handleWheel(e: WheelEvent) {
  e.preventDefault()
  if (!containerRef.value) return

  isWheelZooming.value = true
  if (wheelTimer) clearTimeout(wheelTimer)
  wheelTimer = setTimeout(() => {
    isWheelZooming.value = false
  }, 100)

  const rect = containerRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left - rect.width / 2
  const mouseY = e.clientY - rect.top - rect.height / 2
  const factor = e.deltaY < 0 ? 1.2 : 0.833

  const result = calculateZoomToCursor(
    zoom.value,
    factor,
    mouseX,
    mouseY,
    panX.value,
    panY.value,
    minZoom,
    maxZoom
  )
  zoom.value = result.zoom
  panX.value = result.panX
  panY.value = result.panY
}

/**
 * Double clic / double tap : bascule entre 1x et 2.5x
 */
function handleDoubleClick(e: MouseEvent) {
  if (!containerRef.value) return
  if (zoom.value > 1.1) {
    resetView()
  } else {
    const rect = containerRef.value.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - rect.width / 2
    const mouseY = e.clientY - rect.top - rect.height / 2
    const targetZoom = 2.5
    const ratio = targetZoom / zoom.value
    panX.value = mouseX - (mouseX - panX.value) * ratio
    panY.value = mouseY - (mouseY - panY.value) * ratio
    zoom.value = targetZoom
  }
}

/**
 * Gestion du pan par Pointer Events
 */
function handlePointerDown(e: PointerEvent) {
  // Éviter que les points tactiles secondaires ne perturbent le glissement
  if (e.pointerType === 'touch' && !e.isPrimary) return
  // Clic gauche uniquement
  if (e.button !== 0) return
  isDragging.value = true
  dragStartX = e.clientX - panX.value
  dragStartY = e.clientY - panY.value

  const el = containerRef.value
  if (el) {
    el.setPointerCapture(e.pointerId)
  }
}

function handlePointerMove(e: PointerEvent) {
  if (!isDragging.value) return
  panX.value = e.clientX - dragStartX
  panY.value = e.clientY - dragStartY
}

function handlePointerUp(e: PointerEvent) {
  if (!isDragging.value) return
  isDragging.value = false
  const el = containerRef.value
  if (el && el.hasPointerCapture(e.pointerId)) {
    el.releasePointerCapture(e.pointerId)
  }
}

/**
 * Support tactile multipoint (Pinch-to-zoom)
 */
function handleTouchStart(e: TouchEvent) {
  if (e.touches.length === 2) {
    const t1 = e.touches[0]
    const t2 = e.touches[1]
    initialPinchDistance = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY)
    initialPinchZoom = zoom.value
  }
}

function handleTouchMove(e: TouchEvent) {
  if (e.touches.length === 2 && initialPinchDistance > 0) {
    e.preventDefault()
    const t1 = e.touches[0]
    const t2 = e.touches[1]
    const currentDistance = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY)
    const factor = currentDistance / initialPinchDistance
    const newZoom = Math.min(Math.max(initialPinchZoom * factor, minZoom), maxZoom)
    zoom.value = Number(newZoom.toFixed(2))
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (!props.isOpen) return
  if (e.key === 'Escape') {
    e.stopImmediatePropagation()
    e.preventDefault()
    emit('close')
  } else if (e.key === '+' || e.key === '=') {
    handleZoomIn()
  } else if (e.key === '-' || e.key === '_') {
    handleZoomOut()
  } else if (e.key === '0' || e.key.toLowerCase() === 'r') {
    resetView()
  }
}

watch(
  () => props.imageUrl,
  () => {
    resetView()
    isImageLoaded.value = false
    hasLoadError.value = false
  }
)

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      resetView()
      isImageLoaded.value = false
      hasLoadError.value = false
      window.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    } else {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.isOpen) {
    window.addEventListener('keydown', handleKeyDown)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  document.body.style.overflow = ''
  if (wheelTimer) {
    clearTimeout(wheelTimer)
    wheelTimer = null
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex flex-col bg-slate-950/95 backdrop-blur-md select-none overflow-hidden"
        role="dialog"
        aria-modal="true"
        :aria-label="`Visionneuse plein écran : ${title}`"
      >
        <!-- Barre Supérieure d'En-tête et Contrôles -->
        <header class="relative z-20 flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800 text-white shadow-lg">
          <div class="flex items-center space-x-3 min-w-0 pr-4">
            <span class="text-xl">🔍</span>
            <div class="min-w-0">
              <h2 class="text-sm sm:text-base font-bold truncate leading-tight">
                {{ title }}
              </h2>
              <p class="text-xs text-slate-400 truncate flex items-center gap-2">
                <span v-if="year || periodLabel">
                  📅 {{ [year, periodLabel].filter(Boolean).join(' • ') }}
                </span>
                <span v-if="photographer" class="truncate">
                  👤 {{ photographer }}
                </span>
                <span v-if="archiveRef" class="truncate font-mono text-[11px] text-sky-400">
                  📁 {{ archiveRef }}
                </span>
              </p>
            </div>
          </div>

          <!-- Boutons d'Action & Zoom -->
          <div class="flex items-center space-x-1 sm:space-x-2 shrink-0">
            <!-- Niveau de Zoom Actuel -->
            <span class="hidden sm:inline-block px-2 py-1 rounded bg-slate-800 text-[11px] font-mono text-slate-300">
              {{ Math.round(zoom * 100) }}%
            </span>

            <button
              type="button"
              class="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
              title="Zoom arrière (-)"
              @click="handleZoomOut"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
              </svg>
            </button>

            <button
              type="button"
              class="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
              title="Zoom avant (+)"
              @click="handleZoomIn"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>

            <button
              type="button"
              class="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors text-xs font-semibold"
              title="Réinitialiser la vue (100% / R)"
              @click="resetView"
            >
              1:1
            </button>

            <button
              type="button"
              class="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors text-xs"
              :title="showInfo ? 'Masquer la légende' : 'Afficher la légende'"
              @click="showInfo = !showInfo"
            >
              ℹ️
            </button>

            <div class="h-6 w-px bg-slate-700 mx-1"></div>

            <button
              type="button"
              class="p-2 text-slate-300 hover:text-white hover:bg-rose-900/60 rounded-lg transition-colors"
              title="Fermer la visionneuse (Échap)"
              @click="emit('close')"
            >
              <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </header>

        <!-- Zone Interactive Principale (Pan & Zoom) -->
        <main
          ref="containerRef"
          class="relative flex-1 w-full h-full flex items-center justify-center overflow-hidden touch-none"
          :class="isDragging ? 'cursor-grabbing' : (zoom > 1 ? 'cursor-grab' : 'cursor-default')"
          @wheel="handleWheel"
          @dblclick="handleDoubleClick"
          @pointerdown="handlePointerDown"
          @pointermove="handlePointerMove"
          @pointerup="handlePointerUp"
          @pointercancel="handlePointerUp"
          @touchstart="handleTouchStart"
          @touchmove="handleTouchMove"
        >
          <!-- Indicateur de Chargement -->
          <div
            v-if="!isImageLoaded && !hasLoadError"
            class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-sky-400 z-10"
          >
            <svg class="animate-spin w-8 h-8" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <span class="text-xs text-slate-300">Chargement de l'image haute définition...</span>
          </div>

          <!-- Message d'erreur de chargement -->
          <div
            v-if="hasLoadError"
            class="text-rose-400 text-sm p-4 bg-rose-950/80 rounded-xl border border-rose-800 text-center max-w-md"
          >
            <p class="font-bold">Impossible de charger l'image haute définition.</p>
            <p class="text-xs text-slate-400 mt-1">Le fichier d'archives est indisponible ou inaccessible.</p>
          </div>

          <!-- Image Haute Définition -->
          <img
            v-show="!hasLoadError"
            ref="imageRef"
            :src="imageUrl"
            :alt="title"
            class="max-w-[90vw] max-h-[85vh] object-contain select-none pointer-events-none drop-shadow-2xl transition-opacity duration-300"
            :class="isImageLoaded ? 'opacity-100' : 'opacity-0'"
            :style="transformStyle"
            draggable="false"
            @load="isImageLoaded = true"
            @error="hasLoadError = true"
          />
        </main>

        <!-- Bandeau Inférieur d'Informations & Aide -->
        <footer
          v-if="showInfo"
          class="relative z-20 px-4 py-2.5 bg-slate-900/85 border-t border-slate-800 text-xs text-slate-300 flex flex-wrap items-center justify-between gap-2 shadow-lg"
        >
          <div class="flex items-center gap-3">
            <span v-if="archiveSource" class="text-slate-400">
              Fonds : <strong class="text-slate-200">{{ archiveSource }}</strong>
            </span>
            <span v-if="license" class="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 border border-slate-700">
              {{ license }}
            </span>
          </div>

          <div class="text-[11px] text-slate-400 hidden md:flex items-center gap-3">
            <span>🖱️ Molette : Zoom</span>
            <span>👆 Glisser : Panoramique</span>
            <span>✨ Double-clic : Zoom rapide</span>
            <span>⌨️ Échap : Fermer</span>
          </div>
        </footer>
      </div>
    </Transition>
  </Teleport>
</template>
