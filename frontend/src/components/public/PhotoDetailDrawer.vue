<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import type { PhotoGeoJsonProperties, Photo } from '@/types/photo'
import { resolveDisplayImageUrl } from '@/utils/photoViewer'
import { formatPhotoYear } from '@/utils/photoDate'

// On accepte soit une PhotoGeoJsonProperties, soit une entité Photo
const props = withDefaults(
  defineProps<{
    isOpen: boolean
    photo: PhotoGeoJsonProperties | Photo | null
    coordinates?: [number, number] | null
    isLightboxOpen?: boolean
  }>(),
  {
    photo: null,
    coordinates: null,
    isLightboxOpen: false,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'open-lightbox'): void
  (e: 'center-map', coordinates: [number, number]): void
}>()

const copyFeedback = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null

// Résolution unifiée des propriétés
const title = computed(() => props.photo?.title ?? 'Photographie historique')
const description = computed(() => props.photo?.description ?? null)
const photographer = computed(() => props.photo?.photographer ?? null)
const yearTaken = computed(() => (props.photo as any)?.year_taken ?? (props.photo as any)?.year ?? null)
const isExactYear = computed(() => (props.photo as any)?.is_exact_year ?? true)
const formattedYear = computed(() => formatPhotoYear(yearTaken.value, isExactYear.value))
const dateExact = computed(() => props.photo?.date_exact ?? null)
const periodLabel = computed(() => props.photo?.period_label ?? null)
const archiveSource = computed(() => props.photo?.archive_source ?? null)
const archiveRef = computed(() => props.photo?.archive_ref ?? (props.photo as any)?.archive_reference ?? null)
const originalSourceUrl = computed(() => props.photo?.original_source_url ?? (props.photo as any)?.source_url ?? null)
const license = computed(() => props.photo?.license ?? 'Domaine Public')
const bearing = computed(() => props.photo?.bearing ?? null)
const fieldOfView = computed(() => props.photo?.field_of_view ?? 60)
const viewDistance = computed(() => (props.photo as any)?.view_distance ?? 160)

const displayImageUrl = computed(() => resolveDisplayImageUrl(props.photo))

const resolvedCoordinates = computed<[number, number] | null>(() => {
  if (props.coordinates) return props.coordinates
  if (!props.photo) return null
  const p = props.photo as any
  if (p.longitude != null && p.latitude != null) {
    return [p.longitude, p.latitude]
  }
  if (p.location?.coordinates) {
    return p.location.coordinates
  }
  return null
})

/**
 * Copie dans le presse-papiers le lien direct de partage (?photo=id)
 */
async function copyShareLink() {
  if (!props.photo?.id) return

  const url = new URL(window.location.href)
  url.searchParams.set('photo', props.photo.id)

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(url.toString())
    } else {
      // Fallback si l'API clipboard n'est pas autorisée
      const input = document.createElement('input')
      input.value = url.toString()
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }

    copyFeedback.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copyFeedback.value = false
    }, 2500)
  } catch (err) {
    console.warn('Impossible de copier dans le presse-papiers:', err)
  }
}

function handleCenterMap() {
  if (resolvedCoordinates.value) {
    emit('center-map', resolvedCoordinates.value)
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (props.isOpen && !props.isLightboxOpen && e.key === 'Escape') {
    emit('close')
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      window.addEventListener('keydown', handleKeyDown)
    } else {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }
)

onMounted(() => {
  if (props.isOpen) {
    window.addEventListener('keydown', handleKeyDown)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  if (copyTimer) clearTimeout(copyTimer)
})
</script>

<template>
  <div v-if="isOpen && photo" class="absolute inset-0 pointer-events-none z-30">
    <!-- Backdrop assombri uniquement sur mobile -->
    <div
      class="fixed inset-0 bg-slate-950/60 backdrop-blur-xs md:hidden z-30 pointer-events-auto transition-opacity"
      @click="emit('close')"
    ></div>

    <!-- Tiroir / Bottom Sheet -->
    <aside
      class="fixed md:absolute z-40 transition-all duration-300 ease-out pointer-events-auto
             bottom-0 inset-x-0 md:inset-x-auto md:right-0 md:top-0 md:bottom-0
             w-full md:w-[420px] max-h-[85vh] md:max-h-full h-auto md:h-full
             bg-slate-900/95 backdrop-blur-md border-t md:border-t-0 md:border-l border-slate-700/80
             shadow-2xl flex flex-col rounded-t-2xl md:rounded-none overflow-hidden text-slate-100"
      role="dialog"
      aria-modal="true"
      :aria-label="`Fiche patrimoniale : ${title}`"
    >
      <!-- Poignée de glissement tactile pour mobile -->
      <div class="md:hidden pt-3 pb-1 flex justify-center cursor-pointer" @click="emit('close')">
        <div class="w-12 h-1.5 bg-slate-600 rounded-full"></div>
      </div>

      <!-- En-tête du volet -->
      <header class="px-5 py-3.5 border-b border-slate-800 flex items-start justify-between gap-3 shrink-0">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-1.5 mb-1 text-[11px]">
            <span
              v-if="formattedYear"
              class="px-2 py-0.5 rounded font-medium bg-sky-950 text-sky-300 border border-sky-800"
            >
              📅 {{ formattedYear }}
            </span>
            <span
              v-if="photographer"
              class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 truncate max-w-[180px]"
              :title="photographer"
            >
              👤 {{ photographer }}
            </span>
          </div>
          <h2 class="text-base font-bold text-white leading-snug line-clamp-2">
            {{ title }}
          </h2>
        </div>

        <button
          type="button"
          class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors shrink-0"
          title="Fermer la fiche (Échap)"
          @click="emit('close')"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      <!-- Corps défilant du volet -->
      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-5 text-xs">
        <!-- Aperçu de l'image avec déclencheur Lightbox -->
        <div
          v-if="displayImageUrl"
          class="relative group rounded-xl overflow-hidden border border-slate-700/80 bg-slate-950 shadow-md cursor-pointer aspect-4/3 flex items-center justify-center"
          @click="emit('open-lightbox')"
        >
          <img
            :src="displayImageUrl"
            :alt="title"
            class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />

          <!-- Superposition hover invitant à la visionneuse HD -->
          <div class="absolute inset-0 bg-slate-950/50 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1.5 text-white p-3 text-center">
            <span class="text-2xl drop-shadow">🔍</span>
            <span class="font-semibold text-xs drop-shadow">Explorer en plein écran HD</span>
            <span class="text-[10px] text-slate-300">Zoom et déplacement détaillés</span>
          </div>

          <!-- Badge discret en bas à droite -->
          <div class="absolute bottom-2 right-2 px-2 py-1 rounded bg-slate-900/80 backdrop-blur-xs text-[10px] font-medium text-slate-300 border border-slate-700/80 flex items-center gap-1 group-hover:hidden">
            <span>🔍 Plein écran</span>
          </div>
        </div>

        <!-- Boutons d'Action Rapide (Partager, Plein écran, Centrer) -->
        <div class="grid grid-cols-2 gap-2">
          <!-- Bouton Partager le lien direct -->
          <button
            type="button"
            class="px-3 py-2 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-200 hover:text-white font-medium transition-colors flex items-center justify-center gap-1.5 relative"
            @click="copyShareLink"
          >
            <span v-if="!copyFeedback">🔗 Partager la vue</span>
            <span v-else class="text-emerald-400 font-semibold flex items-center gap-1">
              ✓ Lien copié !
            </span>
          </button>

          <!-- Bouton Plein écran -->
          <button
            type="button"
            class="px-3 py-2 rounded-xl border border-sky-700/60 bg-sky-900/40 hover:bg-sky-800/60 text-sky-200 hover:text-white font-medium transition-colors flex items-center justify-center gap-1.5"
            @click="emit('open-lightbox')"
          >
            <span>⛶ Visionneuse HD</span>
          </button>
        </div>

        <!-- Description Historique si disponible -->
        <section v-if="description" class="space-y-1.5 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <h3 class="font-bold text-slate-300 uppercase tracking-wider text-[10px]">
            Contexte historique & description
          </h3>
          <p class="text-slate-300 leading-relaxed whitespace-pre-line text-xs">
            {{ description }}
          </p>
        </section>

        <!-- Métadonnées d'Archives & Patrimoniales (Obligatoires selon NFR-4) -->
        <section class="space-y-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <h3 class="font-bold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <span>🏛️ Métadonnées d'archives</span>
          </h3>

          <div class="space-y-2 text-xs">
            <!-- Fonds d'archives -->
            <div class="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2">
              <span class="text-slate-400">Fonds d'archives</span>
              <span class="font-medium text-white text-right">
                {{ archiveSource || 'Non spécifié' }}
              </span>
            </div>

            <!-- Cote d'archive -->
            <div class="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2">
              <span class="text-slate-400">Cote / Référence</span>
              <span class="font-mono font-bold text-sky-400 text-right">
                {{ archiveRef || 'Non coté' }}
              </span>
            </div>

            <!-- Photographe -->
            <div v-if="photographer" class="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2">
              <span class="text-slate-400">Photographe / Auteur</span>
              <span class="font-medium text-white text-right">
                {{ photographer }}
              </span>
            </div>

            <!-- Date de prise de vue -->
            <div class="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2">
              <span class="text-slate-400">Date de prise de vue</span>
              <span class="font-medium text-white text-right">
                {{ formattedYear || dateExact || periodLabel || 'Inconnue' }}
              </span>
            </div>

            <!-- Licence patrimoniale (NFR-4) -->
            <div class="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2">
              <span class="text-slate-400">Licence patrimoniale</span>
              <span class="px-2 py-0.5 rounded font-medium text-[11px] bg-slate-800 text-slate-200 border border-slate-700 text-right">
                {{ license }}
              </span>
            </div>

            <!-- Lien vers la notice originale d'archives -->
            <div v-if="originalSourceUrl" class="pt-1 flex items-center justify-between">
              <span class="text-slate-400">Notice originale</span>
              <a
                :href="originalSourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="text-sky-400 hover:text-sky-300 underline font-medium flex items-center gap-1 text-right"
              >
                <span>Consulter la notice d'origine</span>
                <span class="text-[10px]">↗</span>
              </a>
            </div>
          </div>
        </section>

        <!-- Données Géographiques & Prise de Vue -->
        <section class="space-y-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <h3 class="font-bold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <span>🧭 Prise de vue & orientation</span>
          </h3>

          <div class="grid grid-cols-2 gap-2 text-xs">
            <!-- Azimut (Direction) -->
            <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <div class="text-[10px] text-slate-400">Azimut (Regard)</div>
              <div class="font-bold text-sky-400 font-mono mt-0.5">
                {{ bearing != null ? `${bearing}°` : 'Non orienté' }}
              </div>
            </div>

            <!-- Champ de vision -->
            <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <div class="text-[10px] text-slate-400">Champ angulaire</div>
              <div class="font-bold text-slate-200 font-mono mt-0.5">
                {{ fieldOfView }}°
              </div>
            </div>

            <!-- Portée métrique du cône -->
            <div v-if="bearing != null" class="col-span-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div class="text-[10px] text-slate-400">Portée du cône de vision</div>
              <div class="font-bold text-amber-400 font-mono">
                {{ viewDistance }} mètres
              </div>
            </div>
          </div>

          <!-- Coordonnées géographiques -->
          <div v-if="resolvedCoordinates" class="flex items-center justify-between text-xs pt-1">
            <span class="text-slate-400 font-mono text-[11px]">
              GPS : {{ resolvedCoordinates[1].toFixed(5) }}, {{ resolvedCoordinates[0].toFixed(5) }}
            </span>
            <button
              type="button"
              class="text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
              @click="handleCenterMap"
            >
              <span>Centrer</span>
              <span>🎯</span>
            </button>
          </div>
        </section>
      </div>
    </aside>
  </div>
</template>
