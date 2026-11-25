<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { Storymap, StorymapStatus } from '@/types/storymap'
import { storymapApi } from '@/services/api'
import StorymapEditorModal from './StorymapEditorModal.vue'

const props = withDefaults(
  defineProps<{
    territoryCenter?: { lat: number; lng: number; zoom?: number } | null
    territoryId?: string | null
  }>(),
  {
    territoryCenter: () => ({ lat: 43.1242, lng: 5.9328, zoom: 13 }),
    territoryId: null,
  }
)

const emit = defineEmits<{
  (e: 'view-public', slug: string): void
}>()

// État de la liste
const storymaps = ref<Storymap[]>([])
const totalStorymaps = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const totalPages = ref(1)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// Filtres
const searchQuery = ref('')
const statusFilter = ref<StorymapStatus | ''>('')
let searchDebounceTimeout: any = null

// Modale d'édition
const isEditorModalOpen = ref(false)
const selectedStorymapId = ref<string | null>(null)

// Confirmation de suppression
const isDeleteModalOpen = ref(false)
const storymapToDelete = ref<Storymap | null>(null)
const isDeleting = ref(false)

// Notifications Toast
interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}
const toasts = ref<Toast[]>([])
let toastCounter = 0

function addToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  const id = ++toastCounter
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }, 4000)
}

/**
 * Charge les storymaps depuis l'API
 */
async function loadStorymaps() {
  isLoading.value = true
  errorMessage.value = null

  try {
    const res = await storymapApi.listStorymaps({
      page: currentPage.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      search: searchQuery.value || undefined,
    })

    storymaps.value = res.items
    totalStorymaps.value = res.total
    totalPages.value = res.pages || 1
    currentPage.value = res.page
  } catch (err: any) {
    errorMessage.value = err.message || 'Impossible de charger les storymaps.'
    addToast(errorMessage.value || 'Erreur', 'error')
  } finally {
    isLoading.value = false
  }
}

// Filtre debounce
watch(searchQuery, () => {
  clearTimeout(searchDebounceTimeout)
  searchDebounceTimeout = setTimeout(() => {
    currentPage.value = 1
    loadStorymaps()
  }, 350)
})

watch(statusFilter, () => {
  currentPage.value = 1
  loadStorymaps()
})

function changePage(newPage: number) {
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage
    loadStorymaps()
  }
}

// Actions
function openCreateModal() {
  selectedStorymapId.value = null
  isEditorModalOpen.value = true
}

function openEditModal(storymap: Storymap) {
  selectedStorymapId.value = storymap.id
  isEditorModalOpen.value = true
}

function onStorymapSaved(saved: Storymap) {
  addToast(`Récit "${saved.title}" enregistré avec succès.`, 'success')
  loadStorymaps()
}

function confirmDelete(storymap: Storymap) {
  storymapToDelete.value = storymap
  isDeleteModalOpen.value = true
}

async function handleDeleteConfirmed() {
  if (!storymapToDelete.value) return
  isDeleting.value = true
  try {
    await storymapApi.deleteStorymap(storymapToDelete.value.id)
    addToast(`Récit "${storymapToDelete.value.title}" supprimé.`, 'info')
    isDeleteModalOpen.value = false
    storymapToDelete.value = null
    await loadStorymaps()
  } catch (err: any) {
    addToast(err.message || 'Erreur lors de la suppression.', 'error')
  } finally {
    isDeleting.value = false
  }
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

onMounted(() => {
  loadStorymaps()
})
</script>

<template>
  <div class="space-y-6 font-sans">
    <!-- Barre de contrôle supérieure -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800 backdrop-blur-md shadow-lg">
      <div>
        <h2 class="text-xl font-black text-white flex items-center gap-2">
          <span>📖</span>
          <span>Storymaps & Récits Territoriaux</span>
          <span class="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-slate-800 text-sky-400 border border-slate-700">
            {{ totalStorymaps }} récit{{ totalStorymaps > 1 ? 's' : '' }}
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Composez des parcours immersifs associant chapitres narratifs, cadrages 3D MapLibre et documents sonores.
        </p>
      </div>

      <button
        type="button"
        class="px-4 py-2.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-sky-900/40 flex items-center justify-center gap-2 transition-all self-start md:self-auto"
        @click="openCreateModal"
      >
        <span class="text-base font-bold">+</span>
        <span>Nouveau récit</span>
      </button>
    </div>

    <!-- Barre de Recherche & Filtres -->
    <div class="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
      <div class="w-full sm:w-80 relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher par titre, résumé..."
          class="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
        />
        <span class="absolute left-3 top-2.5 text-xs text-slate-500">🔍</span>
      </div>

      <!-- Filtres Statut -->
      <div class="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs w-full sm:w-auto">
        <button
          type="button"
          class="flex-1 sm:flex-none px-3 py-1 rounded-lg font-medium transition-colors"
          :class="statusFilter === '' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          @click="statusFilter = ''"
        >
          Tous
        </button>
        <button
          type="button"
          class="flex-1 sm:flex-none px-3 py-1 rounded-lg font-medium transition-colors"
          :class="statusFilter === 'published' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          @click="statusFilter = 'published'"
        >
          Publiés
        </button>
        <button
          type="button"
          class="flex-1 sm:flex-none px-3 py-1 rounded-lg font-medium transition-colors"
          :class="statusFilter === 'draft' ? 'bg-amber-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          @click="statusFilter = 'draft'"
        >
          Brouillons
        </button>
      </div>
    </div>

    <!-- État de chargement -->
    <div v-if="isLoading" class="text-center py-16 space-y-3">
      <div class="w-8 h-8 border-3 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      <p class="text-xs text-slate-400">Chargement des récits...</p>
    </div>

    <!-- Aucun récit trouvé -->
    <div
      v-else-if="storymaps.length === 0"
      class="text-center py-16 bg-slate-900/30 rounded-2xl border border-dashed border-slate-800 p-8 space-y-3"
    >
      <span class="text-4xl">🗺️</span>
      <h3 class="text-base font-bold text-white">Aucune storymap trouvée</h3>
      <p class="text-xs text-slate-400 max-w-md mx-auto">
        {{ searchQuery || statusFilter ? 'Aucun résultat ne correspond à vos filtres de recherche.' : 'Commencez par concevoir votre première visite narrative en scrollytelling.' }}
      </p>
      <button
        v-if="!searchQuery && !statusFilter"
        type="button"
        class="mt-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold shadow-md transition-colors"
        @click="openCreateModal"
      >
        Créer un récit
      </button>
    </div>

    <!-- Grille des Storymaps -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="story in storymaps"
        :key="story.id"
        class="group bg-slate-900/70 border border-slate-800 hover:border-slate-700 rounded-2xl overflow-hidden shadow-md hover:shadow-xl transition-all flex flex-col justify-between"
      >
        <!-- Couverture & Badges -->
        <div>
          <div class="relative h-44 bg-slate-950 overflow-hidden">
            <img
              v-if="story.cover_image_url"
              :src="story.cover_image_url"
              :alt="story.title"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-3xl text-slate-700 bg-gradient-to-br from-slate-900 to-slate-950">
              🧭
            </div>

            <!-- Badges superposés -->
            <div class="absolute top-3 left-3 flex items-center gap-2">
              <span
                class="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold uppercase backdrop-blur-md shadow-sm"
                :class="story.status === 'published' ? 'bg-emerald-950/90 text-emerald-300 border border-emerald-800' : 'bg-amber-950/90 text-amber-300 border border-amber-800'"
              >
                {{ story.status === 'published' ? 'Publié' : 'Brouillon' }}
              </span>
            </div>

            <div class="absolute bottom-3 right-3">
              <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-950/85 backdrop-blur-md text-slate-200 border border-slate-800 flex items-center gap-1.5 shadow-sm">
                <span>📑</span>
                <span>{{ story.steps_count ?? story.steps?.length ?? 0 }} chapitre{{ (story.steps_count ?? story.steps?.length ?? 0) > 1 ? 's' : '' }}</span>
              </span>
            </div>
          </div>

          <!-- Contenu descriptif -->
          <div class="p-4 space-y-2">
            <h3 class="text-sm font-bold text-white line-clamp-1 group-hover:text-sky-400 transition-colors" :title="story.title">
              {{ story.title }}
            </h3>
            <p class="text-[11px] font-mono text-slate-500">
              /{{ story.slug }}
            </p>
            <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed">
              {{ story.summary || 'Aucun résumé disponible pour ce parcours historique.' }}
            </p>
          </div>
        </div>

        <!-- Pied de carte avec actions -->
        <div class="px-4 py-3 bg-slate-950/60 border-t border-slate-800/80 flex items-center justify-between text-xs">
          <span class="text-[11px] text-slate-500">
            Mis à jour le {{ formatDate(story.updated_at) }}
          </span>

          <div class="flex items-center gap-2">
            <button
              v-if="story.status === 'published'"
              type="button"
              class="px-2.5 py-1 rounded-lg font-medium text-sky-300 hover:text-white bg-sky-950/80 hover:bg-sky-900 border border-sky-800 transition-colors flex items-center gap-1"
              title="Consulter le récit dans le lecteur public"
              @click="emit('view-public', story.slug)"
            >
              <span>👁️</span>
              <span>Voir</span>
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded-lg font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
              @click="openEditModal(story)"
            >
              Éditer
            </button>
            <button
              type="button"
              class="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/50 transition-colors"
              title="Supprimer ce récit"
              @click="confirmDelete(story)"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-4">
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-30"
        :disabled="currentPage === 1"
        @click="changePage(currentPage - 1)"
      >
        Précédent
      </button>
      <span class="text-xs text-slate-400 font-mono px-3">
        {{ currentPage }} / {{ totalPages }}
      </span>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-30"
        :disabled="currentPage === totalPages"
        @click="changePage(currentPage + 1)"
      >
        Suivant
      </button>
    </div>

    <!-- Modale Éditeur de Storymap -->
    <StorymapEditorModal
      :is-open="isEditorModalOpen"
      :storymap-id="selectedStorymapId"
      :territory-center="territoryCenter"
      :territory-id="territoryId"
      @close="isEditorModalOpen = false"
      @saved="onStorymapSaved"
    />

    <!-- Modale de Confirmation de Suppression -->
    <div
      v-if="isDeleteModalOpen && storymapToDelete"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
      @click.self="isDeleteModalOpen = false"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <span>⚠️</span>
          <span>Confirmer la suppression</span>
        </h3>
        <p class="text-xs text-slate-300 leading-relaxed">
          Êtes-vous sûr de vouloir supprimer définitivement le récit
          <strong class="text-white">"{{ storymapToDelete.title }}"</strong> ?
          Toutes ses étapes associées seront également effacées (suppression en cascade).
        </p>

        <div class="flex items-center justify-end gap-3 pt-3">
          <button
            type="button"
            class="px-3.5 py-1.5 text-xs text-slate-400 hover:text-white"
            @click="isDeleteModalOpen = false"
          >
            Annuler
          </button>
          <button
            type="button"
            class="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md flex items-center gap-1.5"
            :disabled="isDeleting"
            @click="handleDeleteConfirmed"
          >
            <span v-if="isDeleting" class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>Supprimer définitivement</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Notifications Toasts flottantes -->
    <div class="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto px-4 py-2.5 rounded-xl text-xs font-semibold shadow-xl border backdrop-blur-md transition-all flex items-center gap-2"
        :class="[
          t.type === 'success' ? 'bg-emerald-950/90 text-emerald-300 border-emerald-800' : '',
          t.type === 'error' ? 'bg-rose-950/90 text-rose-300 border-rose-800' : '',
          t.type === 'info' ? 'bg-sky-950/90 text-sky-300 border-sky-800' : '',
        ]"
      >
        <span v-if="t.type === 'success'">✓</span>
        <span v-else-if="t.type === 'error'">⚠️</span>
        <span v-else>ℹ️</span>
        <span>{{ t.message }}</span>
      </div>
    </div>
  </div>
</template>
