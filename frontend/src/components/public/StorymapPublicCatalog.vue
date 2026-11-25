<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import type { Storymap } from '@/types/storymap'
import { storymapApi } from '@/services/api'
import {
  estimateReadingTime,
  formatReadingDuration,
  hasAudioContent,
  filterAndSortStorymaps,
  type StorymapSortOption,
} from '@/utils/storymapCatalog'

const props = withDefaults(
  defineProps<{
    territoryName?: string
    territorySlug?: string
  }>(),
  {
    territoryName: 'Territoire',
    territorySlug: '',
  }
)

const emit = defineEmits<{
  (e: 'select-storymap', slug: string): void
  (e: 'explore-map'): void
}>()

// État des données
const storymaps = ref<Storymap[]>([])
const isLoading = ref(true)
const errorMessage = ref<string | null>(null)
let abortController: AbortController | null = null

// Images de couverture en échec
const failedCovers = ref<Set<string>>(new Set())

// Filtres et tri avec debounce
const rawSearchInput = ref('')
const searchQuery = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const filterAudioOnly = ref(false)
const sortBy = ref<StorymapSortOption>('recent')

// Debounce de la saisie utilisateur (200ms)
watch(rawSearchInput, (newVal) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    searchQuery.value = newVal
  }, 200)
})

/**
 * Charge la liste publique des récits publiés
 */
async function loadPublicCatalog() {
  if (abortController) {
    abortController.abort()
  }
  abortController = new AbortController()

  isLoading.value = true
  errorMessage.value = null

  try {
    const res = await storymapApi.listPublicStorymaps(
      { page: 1, page_size: 100 },
      abortController.signal
    )
    storymaps.value = res.items || []
  } catch (err: any) {
    if (err.name === 'AbortError') return
    console.error('Erreur chargement catalogue storymaps:', err)
    errorMessage.value = 'Impossible de charger les parcours historiques du territoire.'
  } finally {
    isLoading.value = false
  }
}

// Récits filtrés et triés
const displayedStorymaps = computed(() => {
  return filterAndSortStorymaps(storymaps.value, {
    search: searchQuery.value,
    hasAudioOnly: filterAudioOnly.value,
    sortBy: sortBy.value,
  })
})

function resetFilters() {
  rawSearchInput.value = ''
  searchQuery.value = ''
  filterAudioOnly.value = false
  sortBy.value = 'recent'
}

function selectStory(slug: string) {
  emit('select-storymap', slug)
}

function onCoverError(storyId: string) {
  failedCovers.value.add(storyId)
}

function formatDate(isoDate?: string | null): string {
  if (!isoDate) return ''
  try {
    const d = new Date(isoDate)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
    })
  } catch {
    return ''
  }
}

// Réactivité au changement de territoire (AD-2)
watch(
  () => props.territorySlug,
  (newSlug) => {
    if (newSlug) {
      loadPublicCatalog()
    }
  }
)

onMounted(() => {
  loadPublicCatalog()
})

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (abortController) abortController.abort()
})
</script>

<template>
  <div class="w-full space-y-8 font-sans">
    <!-- En-tête de Présentation Territoriale -->
    <header class="relative rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900 to-sky-950/60 border border-slate-800 p-8 sm:p-10 shadow-2xl overflow-hidden">
      <!-- Ornement géohistorique en fond -->
      <div class="absolute -right-10 -bottom-10 opacity-10 text-[180px] pointer-events-none select-none font-serif">
        🧭
      </div>

      <div class="relative z-10 max-w-3xl space-y-4">
        <div class="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-sky-950/80 border border-sky-800 text-sky-400 text-xs font-semibold">
          <span>🏛️</span>
          <span>Patrimoine & Archives — {{ territoryName }}</span>
        </div>

        <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight leading-tight">
          Récits & Parcours Géohistoriques
        </h1>

        <p class="text-sm sm:text-base text-slate-300 leading-relaxed font-normal">
          Explorez l'évolution urbaine, maritime et patrimoniale de votre territoire à travers des visites immersives en scrollytelling synchronisant photographies d'archives, cadrages cartographiques 3D et documents sonores.
        </p>

        <div class="pt-2 flex flex-wrap items-center gap-4 text-xs font-medium text-slate-400">
          <span class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            {{ storymaps.length }} parcours disponible{{ storymaps.length > 1 ? 's' : '' }}
          </span>
          <span class="text-slate-600">•</span>
          <button
            type="button"
            class="text-sky-400 hover:text-sky-300 underline underline-offset-4 flex items-center gap-1 transition-colors"
            @click="emit('explore-map')"
          >
            <span>🗺️ Basculer sur la carte interactive générale</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Barre de Recherche, Filtres et Tri (affichée uniquement si le territoire comporte des récits) -->
    <div
      v-if="!isLoading && storymaps.length > 0"
      class="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-800 p-4 sm:p-5 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 shadow-lg"
    >
      <!-- Champ de recherche textuelle avec debounce -->
      <div class="relative flex-1">
        <span class="absolute inset-y-0 left-3.5 flex items-center text-slate-400 text-sm">
          🔍
        </span>
        <input
          v-model="rawSearchInput"
          type="text"
          placeholder="Rechercher un itinéraire, un lieu, une époque..."
          class="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-10 pr-10 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
        />
        <button
          v-if="rawSearchInput"
          type="button"
          class="absolute inset-y-0 right-3 flex items-center text-slate-400 hover:text-white text-xs"
          aria-label="Effacer la recherche"
          @click="resetFilters"
        >
          ✕
        </button>
      </div>

      <!-- Filtres et Options de Tri -->
      <div class="flex flex-wrap items-center gap-3">
        <!-- Filtre Audio -->
        <button
          type="button"
          class="px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center gap-2"
          :class="filterAudioOnly ? 'bg-sky-600 text-white border-sky-500 shadow-md shadow-sky-950' : 'bg-slate-950 text-slate-300 border-slate-800 hover:border-slate-700'"
          @click="filterAudioOnly = !filterAudioOnly"
        >
          <span>🎧</span>
          <span>Avec document sonore</span>
        </button>

        <!-- Sélecteur de tri -->
        <div class="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
          <span class="text-slate-500 text-[11px]">Trier :</span>
          <select
            v-model="sortBy"
            class="bg-transparent text-slate-200 focus:outline-none cursor-pointer text-xs"
          >
            <option value="recent" class="bg-slate-900 text-white">Plus récents</option>
            <option value="steps" class="bg-slate-900 text-white">Nombre d'étapes</option>
            <option value="title" class="bg-slate-900 text-white">Titre (A-Z)</option>
          </select>
        </div>
      </div>
    </div>

    <!-- État de Chargement -->
    <div
      v-if="isLoading"
      class="py-24 flex flex-col items-center justify-center space-y-4 text-center"
    >
      <div class="w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-sm font-medium text-slate-400">Chargement des parcours géohistoriques...</p>
    </div>

    <!-- État d'Erreur -->
    <div
      v-else-if="errorMessage"
      class="py-16 text-center space-y-4 bg-slate-900/60 rounded-2xl border border-rose-900/50 p-8"
    >
      <div class="text-3xl text-rose-400">⚠️</div>
      <p class="text-sm text-slate-300">{{ errorMessage }}</p>
      <button
        type="button"
        class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition-colors"
        @click="loadPublicCatalog"
      >
        Réessayer
      </button>
    </div>

    <!-- Grille des Storymaps Publiées -->
    <div
      v-else-if="displayedStorymaps.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8"
    >
      <article
        v-for="story in displayedStorymaps"
        :key="story.id"
        tabindex="0"
        role="button"
        class="group bg-slate-900/90 rounded-2xl border border-slate-800/80 hover:border-sky-500/50 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/40 focus:outline-none shadow-xl hover:shadow-2xl hover:shadow-sky-950/40 transition-all duration-300 flex flex-col overflow-hidden cursor-pointer"
        @click="selectStory(story.slug)"
        @keydown.enter="selectStory(story.slug)"
      >
        <!-- Vignette de couverture 16:9 -->
        <div class="relative aspect-video bg-slate-950 overflow-hidden">
          <img
            v-if="story.cover_image_url && !failedCovers.has(story.id)"
            :src="story.cover_image_url"
            :alt="story.title"
            loading="lazy"
            class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            @error="onCoverError(story.id)"
          />
          <div
            v-else
            class="w-full h-full flex items-center justify-center text-4xl text-slate-700 bg-gradient-to-br from-slate-900 to-slate-950 group-hover:scale-105 transition-transform duration-700"
          >
            🧭
          </div>

          <div class="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-transparent"></div>

          <!-- Badges sur la vignette -->
          <div class="absolute top-3 left-3 flex flex-wrap items-center gap-1.5">
            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-950/80 backdrop-blur-md text-sky-400 border border-slate-800 flex items-center gap-1 shadow-sm">
              <span>⏱️</span>
              <span>{{ formatReadingDuration(estimateReadingTime(story.steps_count ?? story.steps?.length ?? 0)) }}</span>
            </span>
          </div>

          <div class="absolute top-3 right-3 flex items-center gap-1.5">
            <span
              v-if="hasAudioContent(story)"
              class="px-2 py-1 rounded-full text-[10px] font-semibold bg-emerald-950/80 backdrop-blur-md text-emerald-300 border border-emerald-800 shadow-sm"
              title="Ce récit comporte des capsules sonores"
            >
              🎧 Audio
            </span>
          </div>

          <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-[11px] text-slate-300">
            <span class="font-semibold text-slate-200 flex items-center gap-1.5">
              <span>📑</span>
              <span>{{ story.steps_count ?? story.steps?.length ?? 0 }} chapitre{{ (story.steps_count ?? story.steps?.length ?? 0) > 1 ? 's' : '' }}</span>
            </span>
            <span v-if="story.created_at" class="text-slate-400 text-[10px]">
              {{ formatDate(story.created_at) }}
            </span>
          </div>
        </div>

        <!-- Contenu descriptif du récit -->
        <div class="p-5 flex-1 flex flex-col justify-between space-y-4">
          <div class="space-y-2">
            <h2 class="text-base sm:text-lg font-bold text-white group-hover:text-sky-400 transition-colors line-clamp-2 leading-snug">
              {{ story.title }}
            </h2>
            <p class="text-xs text-slate-400 line-clamp-3 leading-relaxed">
              {{ story.summary || 'Parcourez ce récit géohistorique à travers les archives visuelles et cartographiques du territoire.' }}
            </p>
          </div>

          <!-- Bouton d'action "Commencer la visite" -->
          <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span class="text-sky-400 font-semibold group-hover:underline flex items-center gap-1">
              <span>Commencer la visite</span>
              <span class="transition-transform group-hover:translate-x-1">→</span>
            </span>
            <span class="text-[10px] text-slate-500 font-mono">
              /{{ story.slug }}
            </span>
          </div>
        </div>
      </article>
    </div>

    <!-- État Aucun Résultat (Filtres sans match) -->
    <div
      v-else-if="storymaps.length > 0"
      class="py-20 text-center space-y-4 bg-slate-900/40 rounded-3xl border border-slate-800 p-8"
    >
      <div class="text-4xl text-slate-600">🔍</div>
      <div class="space-y-1">
        <h3 class="text-base font-bold text-white">Aucun itinéraire ne correspond à votre recherche</h3>
        <p class="text-xs text-slate-400 max-w-md mx-auto">
          Essayez d'autres mots-clés ou désactivez le filtre audio pour élargir les résultats.
        </p>
      </div>
      <button
        type="button"
        class="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition-colors"
        @click="resetFilters"
      >
        Réinitialiser les filtres
      </button>
    </div>

    <!-- État Vide Global (Territoire sans storymaps publiées) -->
    <div
      v-else
      class="py-24 text-center space-y-5 bg-slate-900/40 rounded-3xl border border-slate-800 p-8 sm:p-12 max-w-2xl mx-auto"
    >
      <div class="text-5xl">🧭</div>
      <div class="space-y-2">
        <h3 class="text-lg font-bold text-white">Aucun récit publié pour l'instant</h3>
        <p class="text-xs text-slate-400 leading-relaxed">
          Les conservateurs et auteurs du territoire préparent actuellement de nouveaux parcours immersifs. En attendant, explorez directement l'ensemble des photographies géolocalisées sur la carte interactive.
        </p>
      </div>
      <button
        type="button"
        class="px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-900/40 transition-all flex items-center gap-2 mx-auto"
        @click="emit('explore-map')"
      >
        <span>🗺️</span>
        <span>Explorer la photothèque sur la carte</span>
      </button>
    </div>
  </div>
</template>
