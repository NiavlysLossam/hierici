<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { Photo, PhotoStatus } from '@/types/photo'
import { photoApi, ApiError } from '@/services/api'
import { formatPhotoYear } from '@/utils/photoDate'
import PhotoFormModal from './PhotoFormModal.vue'

// État du catalogue
const photos = ref<Photo[]>([])
const totalPhotos = ref(0)
const currentPage = ref(1)
const pageSize = ref(15)
const totalPages = ref(1)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// Filtres
const searchQuery = ref('')
const statusFilter = ref<PhotoStatus | ''>('')
let searchDebounceTimeout: any = null

// Modale de création / édition
const isModalOpen = ref(false)
const selectedPhotoForEdit = ref<Photo | null>(null)

// Modale de confirmation de suppression
const isDeleteModalOpen = ref(false)
const photoToDelete = ref<Photo | null>(null)
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
  }, 4500)
}

// Chargement des photographies
async function loadPhotos() {
  isLoading.value = true
  errorMessage.value = null

  try {
    const res = await photoApi.listPhotos({
      page: currentPage.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      search: searchQuery.value || undefined,
    })

    photos.value = res.items
    totalPhotos.value = res.total
    totalPages.value = res.pages || 1
    currentPage.value = res.page
  } catch (err: any) {
    errorMessage.value = err.message || 'Impossible de charger le catalogue des photographies.'
    addToast(errorMessage.value || 'Erreur chargement', 'error')
  } finally {
    isLoading.value = false
  }
}

// Déclencheurs de filtrage avec debounce
watch(searchQuery, () => {
  clearTimeout(searchDebounceTimeout)
  searchDebounceTimeout = setTimeout(() => {
    currentPage.value = 1
    loadPhotos()
  }, 350)
})

watch(statusFilter, () => {
  currentPage.value = 1
  loadPhotos()
})

function changePage(newPage: number) {
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage
    loadPhotos()
  }
}

// Actions de gestion
function openCreateModal() {
  selectedPhotoForEdit.value = null
  isModalOpen.value = true
}

function openEditModal(photo: Photo) {
  selectedPhotoForEdit.value = photo
  isModalOpen.value = true
}

function handlePhotoSaved(savedPhoto: Photo) {
  // Recharger le catalogue pour refléter les ajouts/modifications
  loadPhotos()
}

function confirmDeletePhoto(photo: Photo) {
  photoToDelete.value = photo
  isDeleteModalOpen.value = true
}

async function executeDeletePhoto() {
  if (!photoToDelete.value) return

  isDeleting.value = true
  const deletedTitle = photoToDelete.value.title

  try {
    await photoApi.deletePhoto(photoToDelete.value.id)
    addToast(`Cliché "${deletedTitle}" supprimé avec succès.`, 'success')
    isDeleteModalOpen.value = false
    photoToDelete.value = null
    // Si on supprime le seul élément de la page courante, revenir à la page précédente
    if (photos.value.length === 1 && currentPage.value > 1) {
      currentPage.value--
    }
    await loadPhotos()
  } catch (err: any) {
    addToast(err.message || 'Erreur lors de la suppression du cliché', 'error')
  } finally {
    isDeleting.value = false
  }
}

onMounted(() => {
  loadPhotos()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Barre de titre & Actions principales -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
      <div>
        <div class="flex items-center gap-3">
          <h2 class="text-2xl font-extrabold text-white tracking-tight">Studio Catalogue</h2>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-950 text-sky-400 border border-sky-800">
            {{ totalPhotos }} cliché{{ totalPhotos > 1 ? 's' : '' }}
          </span>
        </div>
        <p class="text-xs text-slate-400 mt-1">
          Inventaire, géoréférencement directionnel et métadonnées des photographies patrimoniales.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="px-3 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors flex items-center gap-2"
          :disabled="isLoading"
          @click="loadPhotos"
          title="Actualiser le catalogue"
        >
          <span :class="isLoading ? 'animate-spin' : ''">🔄</span>
          <span>Actualiser</span>
        </button>

        <button
          type="button"
          class="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-lg shadow-sky-950/50 transition-all flex items-center gap-2"
          @click="openCreateModal"
        >
          <span class="text-base leading-none">＋</span>
          <span>Nouveau Cliché</span>
        </button>
      </div>
    </div>

    <!-- Bannière d'erreur de chargement API -->
    <div
      v-if="errorMessage"
      class="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center justify-between"
    >
      <div class="flex items-center gap-2">
        <span>⚠️</span>
        <span>{{ errorMessage }}</span>
      </div>
      <button
        type="button"
        class="px-3 py-1 bg-rose-900/60 hover:bg-rose-800 rounded font-medium transition"
        @click="loadPhotos"
      >
        Réessayer
      </button>
    </div>

    <!-- Barre de recherche et filtres -->
    <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
      <!-- Recherche texte -->
      <div class="relative flex-1">
        <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
          🔍
        </span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher par titre, description, auteur ou cote..."
          class="w-full bg-slate-950/80 border border-slate-700/80 rounded-lg pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-white"
          @click="searchQuery = ''"
        >
          ✕
        </button>
      </div>

      <!-- Filtre statut -->
      <div class="flex items-center gap-2">
        <label class="text-xs text-slate-400 whitespace-nowrap">Statut :</label>
        <select
          v-model="statusFilter"
          class="bg-slate-950/80 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
        >
          <option value="">Tous les statuts</option>
          <option value="draft">Brouillons uniquement</option>
          <option value="published">Publiés uniquement</option>
        </select>
      </div>
    </div>

    <!-- Tableau du catalogue -->
    <div class="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-slate-300">
          <thead class="bg-slate-950/70 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-800">
            <tr>
              <th scope="col" class="py-3 px-4 w-20">Aperçu</th>
              <th scope="col" class="py-3 px-4">Titre & Description</th>
              <th scope="col" class="py-3 px-4 w-32">Époque / Date</th>
              <th scope="col" class="py-3 px-4 w-36">Fonds / Cote</th>
              <th scope="col" class="py-3 px-4 w-36">Position & Azimut</th>
              <th scope="col" class="py-3 px-4 w-28">Statut</th>
              <th scope="col" class="py-3 px-4 w-28 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/80">
            <!-- Spinner chargement -->
            <tr v-if="isLoading">
              <td colspan="7" class="py-12 text-center text-slate-400">
                <div class="w-8 h-8 mx-auto border-2 border-sky-400 border-t-transparent rounded-full animate-spin mb-3"></div>
                Chargement du catalogue photographique...
              </td>
            </tr>

            <!-- Message vide -->
            <tr v-else-if="photos.length === 0">
              <td colspan="7" class="py-12 text-center text-slate-400">
                <div class="text-3xl mb-2">📂</div>
                <div class="font-medium text-slate-300">Aucun cliché trouvé</div>
                <p class="text-xs text-slate-500 mt-1">
                  {{ searchQuery || statusFilter ? 'Aucun résultat ne correspond à vos filtres.' : 'Commencez par ajouter votre premier cliché d\'archive.' }}
                </p>
                <button
                  v-if="!searchQuery && !statusFilter"
                  type="button"
                  class="mt-4 px-3 py-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg inline-flex items-center gap-1.5"
                  @click="openCreateModal"
                >
                  <span>＋</span>
                  <span>Ajouter une photographie</span>
                </button>
              </td>
            </tr>

            <!-- Lignes du tableau -->
            <tr
              v-for="photo in photos"
              :key="photo.id"
              class="hover:bg-slate-800/40 transition-colors group"
            >
              <!-- Vignette -->
              <td class="py-3 px-4">
                <div class="w-14 h-14 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center relative">
                  <img
                    v-if="photo.thumb_url || photo.image_thumb_url || photo.display_url"
                    :src="photo.thumb_url || photo.image_thumb_url || photo.display_url || ''"
                    :alt="photo.title"
                    class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                    loading="lazy"
                  />
                  <span v-else class="text-xl text-slate-600">📷</span>
                </div>
              </td>

              <!-- Titre & Description -->
              <td class="py-3 px-4 max-w-xs">
                <div class="font-semibold text-white truncate text-sm" :title="photo.title">
                  {{ photo.title }}
                </div>
                <p
                  v-if="photo.description"
                  class="text-slate-400 line-clamp-1 text-xs mt-0.5"
                  :title="photo.description"
                >
                  {{ photo.description }}
                </p>
                <div class="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                  <span v-if="photo.photographer">👤 {{ photo.photographer }}</span>
                  <span v-if="photo.license" class="text-slate-400">⚖️ {{ photo.license }}</span>
                </div>
              </td>

              <!-- Époque / Date -->
              <td class="py-3 px-4">
                <div v-if="photo.year_taken || photo.year" class="font-medium text-white">
                  {{ formatPhotoYear(photo.year_taken || photo.year, photo.is_exact_year) }}
                </div>
                <div v-if="photo.date_exact" class="text-[11px] text-slate-400">
                  {{ photo.date_exact }}
                </div>
                <div v-if="photo.period_label" class="text-[11px] text-sky-400/90 mt-0.5">
                  {{ photo.period_label }}
                </div>
                <div v-if="!photo.year_taken && !photo.year && !photo.period_label" class="text-slate-600">
                  —
                </div>
              </td>

              <!-- Fonds / Cote -->
              <td class="py-3 px-4">
                <div v-if="photo.archive_ref || photo.archive_reference" class="font-mono text-sky-300 font-semibold">
                  {{ photo.archive_ref || photo.archive_reference }}
                </div>
                <div v-if="photo.archive_source" class="text-[11px] text-slate-400 truncate max-w-[140px]" :title="photo.archive_source">
                  {{ photo.archive_source }}
                </div>
                <div v-if="!photo.archive_ref && !photo.archive_reference && !photo.archive_source" class="text-slate-600">
                  —
                </div>
              </td>

              <!-- Position & Azimut -->
              <td class="py-3 px-4">
                <div v-if="photo.latitude !== null && photo.latitude !== undefined && photo.longitude !== null && photo.longitude !== undefined" class="space-y-0.5">
                  <span class="inline-flex items-center gap-1 text-emerald-400 font-mono text-[11px]">
                    📍 {{ photo.latitude.toFixed(4) }}, {{ photo.longitude.toFixed(4) }}
                  </span>
                  <div class="text-[11px] text-slate-400 flex items-center gap-1">
                    <span>🧭</span>
                    <span>{{ photo.bearing !== null && photo.bearing !== undefined ? `${photo.bearing}°` : 'Sans azimut' }}</span>
                    <span v-if="photo.field_of_view">({{ photo.field_of_view }}°)</span>
                  </div>
                </div>
                <div v-else>
                  <span class="inline-flex items-center gap-1 text-amber-500 text-[11px]">
                    ⚠️ Non géolocalisé
                  </span>
                </div>
              </td>

              <!-- Statut -->
              <td class="py-3 px-4">
                <span
                  v-if="photo.status === 'published'"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Publié
                </span>
                <span
                  v-else
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-950/80 text-amber-400 border border-amber-800"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                  Brouillon
                </span>
              </td>

              <!-- Actions -->
              <td class="py-3 px-4 text-right whitespace-nowrap">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    type="button"
                    class="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded transition-colors"
                    title="Modifier la fiche"
                    @click="openEditModal(photo)"
                  >
                    ✏️ Modifier
                  </button>
                  <button
                    type="button"
                    class="p-1 text-xs text-rose-400 hover:text-rose-200 hover:bg-rose-950/60 rounded transition-colors"
                    title="Supprimer la fiche"
                    @click="confirmDeletePhoto(photo)"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="px-4 py-3 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div>
          Affichage de <span class="font-medium text-white">{{ photos.length }}</span> sur <span class="font-medium text-white">{{ totalPhotos }}</span> clichés
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="px-3 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            :disabled="currentPage <= 1 || isLoading"
            @click="changePage(currentPage - 1)"
          >
            ← Précédent
          </button>

          <span class="px-2">Page {{ currentPage }} / {{ totalPages }}</span>

          <button
            type="button"
            class="px-3 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            :disabled="currentPage >= totalPages || isLoading"
            @click="changePage(currentPage + 1)"
          >
            Suivant →
          </button>
        </div>
      </div>
    </div>

    <!-- Modale de création / édition PhotoFormModal -->
    <PhotoFormModal
      :is-open="isModalOpen"
      :photo-to-edit="selectedPhotoForEdit"
      @close="isModalOpen = false"
      @saved="handlePhotoSaved"
      @toast="addToast"
    />

    <!-- Modale de confirmation de suppression -->
    <div
      v-if="isDeleteModalOpen && photoToDelete"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
      @click.self="isDeleteModalOpen = false"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
        <div class="w-12 h-12 rounded-full bg-rose-950/80 border border-rose-800 flex items-center justify-center text-2xl text-rose-400 mx-auto">
          🗑️
        </div>

        <div class="text-center space-y-1.5">
          <h3 class="text-base font-bold text-white">Supprimer ce cliché d'archive ?</h3>
          <p class="text-xs text-slate-400">
            Cette action est irréversible. La fiche documentaire <strong class="text-slate-200">"{{ photoToDelete.title }}"</strong> ainsi que toutes ses déclinaisons d'images WebP associées seront définitivement détruites.
          </p>
        </div>

        <div class="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            class="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors"
            :disabled="isDeleting"
            @click="isDeleteModalOpen = false"
          >
            Annuler
          </button>
          <button
            type="button"
            class="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg shadow-lg shadow-rose-950/50 transition-all flex items-center gap-1.5"
            :disabled="isDeleting"
            @click="executeDeletePhoto"
          >
            <span v-if="isDeleting" class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>{{ isDeleting ? 'Suppression...' : 'Confirmer la suppression' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Conteneur des notifications Toast -->
    <div class="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto px-4 py-3 rounded-xl shadow-xl border text-xs font-medium flex items-center gap-2.5 transition-all animate-in slide-in-from-bottom-2 duration-200"
        :class="{
          'bg-emerald-950 border-emerald-800 text-emerald-200': toast.type === 'success',
          'bg-rose-950 border-rose-800 text-rose-200': toast.type === 'error',
          'bg-slate-900 border-slate-700 text-slate-200': toast.type === 'info',
        }"
      >
        <span>{{ toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️' }}</span>
        <span class="flex-1">{{ toast.message }}</span>
      </div>
    </div>
  </div>
</template>
