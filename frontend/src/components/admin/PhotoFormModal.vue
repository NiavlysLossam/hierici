<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { Photo, PhotoCreatePayload, PhotoUpdatePayload, PhotoStatus, PhotoLicense } from '@/types/photo'
import { PHOTO_LICENSES } from '@/types/photo'
import { photoApi, ApiError } from '@/services/api'
import PhotoLocationPicker from './PhotoLocationPicker.vue'

const props = defineProps<{
  isOpen: boolean
  photoToEdit?: Photo | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', photo: Photo): void
  (e: 'toast', message: string, type?: 'success' | 'error' | 'info'): void
}>()

// État du formulaire
const form = ref<{
  id?: string
  title: string
  description: string
  photographer: string
  year_taken: number | null
  is_exact_year: boolean
  date_exact: string
  period_label: string
  archive_source: string
  archive_ref: string
  original_source_url: string
  license: PhotoLicense | string
  latitude: number | null
  longitude: number | null
  bearing: number | null
  field_of_view: number
  view_distance: number
  status: PhotoStatus
  thumb_url?: string | null
  display_url?: string | null
  original_url?: string | null
}>({
  title: '',
  description: '',
  photographer: '',
  year_taken: null,
  is_exact_year: true,
  date_exact: '',
  period_label: '',
  archive_source: '',
  archive_ref: '',
  original_source_url: '',
  license: 'Domaine Public',
  latitude: null,
  longitude: null,
  bearing: null,
  field_of_view: 60,
  view_distance: 160,
  status: 'draft',
})

const suggestions = ref<{ photographers: string[]; archive_sources: string[] }>({
  photographers: [],
  archive_sources: [],
})

async function loadSuggestions() {
  try {
    const res = await photoApi.getMetadataSuggestions()
    suggestions.value = res
  } catch (err) {
    console.warn('Impossible de charger les suggestions de métadonnées:', err)
  }
}

const isSubmitting = ref(false)
const isUploadingImage = ref(false)
const uploadProgress = ref(false)
const localImagePreview = ref<string | null>(null)
const selectedImageFile = ref<File | null>(null)
const errorMessage = ref<string | null>(null)
const activeTab = ref<'document' | 'geo' | 'media'>('document')
const fileInputRef = ref<HTMLInputElement | null>(null)
const locationPickerRef = ref<InstanceType<typeof PhotoLocationPicker> | null>(null)

// Initialisation du formulaire lors du changement de prop photoToEdit
watch(
  () => props.photoToEdit,
  (newVal) => {
    errorMessage.value = null
    localImagePreview.value = null
    selectedImageFile.value = null

    if (newVal) {
      form.value = {
        id: newVal.id,
        title: newVal.title || '',
        description: newVal.description || '',
        photographer: newVal.photographer || '',
        year_taken: newVal.year_taken ?? newVal.year ?? null,
        is_exact_year: newVal.is_exact_year ?? true,
        date_exact: newVal.date_exact || '',
        period_label: newVal.period_label || '',
        archive_source: newVal.archive_source || '',
        archive_ref: newVal.archive_ref ?? newVal.archive_reference ?? '',
        original_source_url: newVal.original_source_url ?? newVal.source_url ?? '',
        license: newVal.license || 'Domaine Public',
        latitude: newVal.latitude ?? null,
        longitude: newVal.longitude ?? null,
        bearing: newVal.bearing ?? null,
        field_of_view: newVal.field_of_view ?? 60,
        view_distance: newVal.view_distance ?? 160,
        status: newVal.status || 'draft',
        thumb_url: newVal.thumb_url ?? newVal.image_thumb_url ?? null,
        display_url: newVal.display_url ?? newVal.image_display_url ?? null,
        original_url: newVal.original_url ?? newVal.image_original_url ?? null,
      }
    } else {
      // Réinitialisation pour création
      form.value = {
        title: '',
        description: '',
        photographer: '',
        year_taken: null,
        is_exact_year: true,
        date_exact: '',
        period_label: '',
        archive_source: '',
        archive_ref: '',
        original_source_url: '',
        license: 'Domaine Public',
        latitude: null,
        longitude: null,
        bearing: null,
        field_of_view: 60,
        view_distance: 160,
        status: 'draft',
        thumb_url: null,
        display_url: null,
        original_url: null,
      }
    }
  },
  { immediate: true }
)

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      loadSuggestions()
    }
    if (open && !props.photoToEdit) {
      form.value = {
        title: '',
        description: '',
        photographer: '',
        year_taken: null,
        is_exact_year: true,
        date_exact: '',
        period_label: '',
        archive_source: '',
        archive_ref: '',
        original_source_url: '',
        license: 'Domaine Public',
        latitude: null,
        longitude: null,
        bearing: null,
        field_of_view: 60,
        view_distance: 160,
        status: 'draft',
        thumb_url: null,
        display_url: null,
        original_url: null,
      }
      localImagePreview.value = null
      selectedImageFile.value = null
      activeTab.value = 'document'
    }
  }
)

// Redimensionnement de la carte lors du basculement vers l'onglet Géoréférencement
watch(activeTab, (newTab) => {
  if (newTab === 'geo') {
    nextTick(() => {
      setTimeout(() => {
        locationPickerRef.value?.resize()
      }, 50)
    })
  }
})

const parseNullableNumber = (v: any): number | null => {
  if (v === null || v === undefined || String(v).trim() === '') return null
  const num = Number(v)
  return isNaN(num) ? null : num
}

// Détection de présence de coordonnées géographiques complètes
const hasCoordinates = computed(() => {
  const lat = parseNullableNumber(form.value.latitude)
  const lng = parseNullableNumber(form.value.longitude)
  return lat !== null && lng !== null
})

// Détection du blocage de publication sans coordonnées
const isPublishBlocked = computed(() => {
  return form.value.status === 'published' && !hasCoordinates.value
})

const canSubmit = computed(() => {
  return (
    form.value.title.trim().length > 0 &&
    !isPublishBlocked.value &&
    !isSubmitting.value &&
    !isUploadingImage.value
  )
})

const currentPreviewUrl = computed(() => {
  if (localImagePreview.value) {
    return localImagePreview.value
  }
  return form.value.display_url || form.value.thumb_url || null
})

// Gestion du téléversement d'image
async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    await processFile(target.files[0])
  }
}

async function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    await processFile(event.dataTransfer.files[0])
  }
}

async function processFile(file: File) {
  if (!file.type.startsWith('image/')) {
    errorMessage.value = 'Seuls les fichiers images (JPEG, PNG, TIFF, WebP) sont autorisés.'
    return
  }

  // 25 Mo limite
  if (file.size > 25 * 1024 * 1024) {
    errorMessage.value = 'Le fichier dépasse la taille maximale de 25 Mo.'
    return
  }

  errorMessage.value = null
  selectedImageFile.value = file

  // Aperçu local immédiat
  const reader = new FileReader()
  reader.onload = (e) => {
    localImagePreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)

  // Si la photo existe déjà en base, on déclenche directement l'upload API pour actualisation immédiate
  if (form.value.id) {
    try {
      isUploadingImage.value = true
      uploadProgress.value = true
      const uploadRes = await photoApi.uploadPhotoImage(form.value.id, file)
      form.value.thumb_url = uploadRes.thumb_url
      form.value.display_url = uploadRes.display_url
      form.value.original_url = uploadRes.original_url
      localImagePreview.value = null
      emit('toast', 'Image téléversée et déclinaisons WebP générées avec succès !', 'success')
      if (uploadRes.photo) {
        emit('saved', uploadRes.photo)
      }
    } catch (err: any) {
      errorMessage.value = err.message || "Erreur lors de l'upload de l'image"
      emit('toast', errorMessage.value || 'Erreur upload', 'error')
    } finally {
      isUploadingImage.value = false
      uploadProgress.value = false
    }
  }
}

// Soumission du formulaire
async function handleSubmit() {
  errorMessage.value = null

  if (!form.value.title.trim()) {
    errorMessage.value = 'Le titre du cliché est obligatoire.'
    return
  }

  // Règle d'or de la spec : Aucune publication sans coordonnées GPS
  if (form.value.status === 'published' && !hasCoordinates.value) {
    errorMessage.value = 'Coordonnées GPS obligatoires pour publier. Veuillez renseigner la latitude et la longitude ou conserver le statut brouillon.'
    emit('toast', errorMessage.value, 'error')
    activeTab.value = 'geo'
    return
  }

  const lat = parseNullableNumber(form.value.latitude)
  const lng = parseNullableNumber(form.value.longitude)
  if ((lat === null) !== (lng === null)) {
    errorMessage.value = 'La latitude et la longitude doivent être renseignées ensemble.'
    emit('toast', errorMessage.value, 'error')
    activeTab.value = 'geo'
    return
  }

  try {
    isSubmitting.value = true

    let savedPhoto: Photo

    if (form.value.id) {
      // Mise à jour de la photo existante
      const payload: PhotoUpdatePayload = {
        title: form.value.title.trim(),
        description: form.value.description.trim() || null,
        photographer: form.value.photographer.trim() || null,
        year_taken: form.value.year_taken ? Number(form.value.year_taken) : null,
        is_exact_year: form.value.is_exact_year,
        archive_source: form.value.archive_source.trim() || null,
        archive_ref: form.value.archive_ref.trim() || null,
        original_source_url: form.value.original_source_url.trim() || null,
        license: form.value.license,
        latitude: lat,
        longitude: lng,
        bearing: parseNullableNumber(form.value.bearing),
        field_of_view: Number(form.value.field_of_view || 60),
        view_distance: Number(form.value.view_distance || 160),
        status: form.value.status,
      }

      savedPhoto = await photoApi.updatePhoto(form.value.id, payload)
      emit('toast', `Fiche "${savedPhoto.title}" mise à jour avec succès.`, 'success')
    } else {
      // Création d'une nouvelle photo
      const payload: PhotoCreatePayload = {
        title: form.value.title.trim(),
        description: form.value.description.trim() || null,
        photographer: form.value.photographer.trim() || null,
        year_taken: form.value.year_taken ? Number(form.value.year_taken) : null,
        is_exact_year: form.value.is_exact_year,
        archive_source: form.value.archive_source.trim() || null,
        archive_ref: form.value.archive_ref.trim() || null,
        original_source_url: form.value.original_source_url.trim() || null,
        license: form.value.license,
        latitude: lat,
        longitude: lng,
        bearing: parseNullableNumber(form.value.bearing),
        field_of_view: Number(form.value.field_of_view || 60),
        view_distance: Number(form.value.view_distance || 160),
        status: form.value.status,
      }

      savedPhoto = await photoApi.createPhoto(payload)

      // Si un fichier image a été sélectionné pour cette nouvelle photo, on le téléverse immédiatement
      if (selectedImageFile.value) {
        try {
          isUploadingImage.value = true
          const uploadRes = await photoApi.uploadPhotoImage(savedPhoto.id, selectedImageFile.value)
          if (uploadRes.photo) {
            savedPhoto = uploadRes.photo
          }
        } catch (uploadErr: any) {
          emit(
            'toast',
            `Fiche créée mais échec du traitement de l'image : ${uploadErr.message}`,
            'error'
          )
        }
      }

      emit('toast', `Nouveau cliché "${savedPhoto.title}" enregistré avec succès.`, 'success')
    }

    emit('saved', savedPhoto)
    emit('close')
  } catch (err: any) {
    if (err instanceof ApiError) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = err.message || "Une erreur inattendue s'est produite lors de la sauvegarde."
    }
    emit('toast', errorMessage.value || 'Erreur', 'error')
  } finally {
    isSubmitting.value = false
    isUploadingImage.value = false
  }
}
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
    @click.self="emit('close')"
  >
    <div
      class="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150"
      role="dialog"
      aria-modal="true"
    >
      <!-- En-tête de la modale -->
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
        <div class="flex items-center space-x-3">
          <div
            class="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
            :class="form.id ? 'bg-indigo-950/80 text-indigo-400 border border-indigo-700' : 'bg-emerald-950/80 text-emerald-400 border border-emerald-700'"
          >
            {{ form.id ? '✏️' : '📸' }}
          </div>
          <div>
            <h2 class="text-lg font-bold text-white tracking-tight">
              {{ form.id ? 'Modifier le cliché d\'archive' : 'Nouveau cliché patrimonial' }}
            </h2>
            <p class="text-xs text-slate-400">
              {{ form.id ? 'Mise à jour des métadonnées et du géoréférencement' : 'Saisie documentaire et rattachement au territoire actif' }}
            </p>
          </div>
        </div>

        <button
          type="button"
          class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          @click="emit('close')"
          aria-label="Fermer la boîte de dialogue"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Alerte de blocage publication sans GPS -->
      <div
        v-if="isPublishBlocked"
        class="bg-amber-950/80 border-b border-amber-800/80 px-6 py-3 flex items-center gap-3 text-amber-200 text-sm"
      >
        <span class="text-xl">⚠️</span>
        <div>
          <strong class="font-semibold text-amber-300">Coordonnées GPS obligatoires pour publier</strong>
          <p class="text-xs text-amber-200/90 mt-0.5">
            Vous avez sélectionné le statut <em>Publié</em>, mais ce cliché ne dispose pas encore de latitude/longitude.
            Renseignez ses coordonnées dans l'onglet <strong>Géolocalisation</strong> ou basculez le statut sur <strong>Brouillon (draft)</strong>.
          </p>
        </div>
      </div>

      <!-- Alerte d'erreur générique -->
      <div
        v-if="errorMessage && !isPublishBlocked"
        class="bg-rose-950/80 border-b border-rose-800/80 px-6 py-3 flex items-center gap-3 text-rose-200 text-sm"
      >
        <span class="text-xl">❌</span>
        <div class="flex-1 text-xs">
          {{ errorMessage }}
        </div>
      </div>

      <!-- Navigation par onglets -->
      <div class="flex border-b border-slate-800 bg-slate-900/60 px-6 pt-2 gap-2 text-sm">
        <button
          type="button"
          class="px-4 py-2.5 font-medium border-b-2 transition-all flex items-center gap-2"
          :class="activeTab === 'document' ? 'border-sky-500 text-sky-400 bg-slate-800/40' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'document'"
        >
          <span>📜</span>
          <span>Notice & Métadonnées</span>
        </button>
        <button
          type="button"
          class="px-4 py-2.5 font-medium border-b-2 transition-all flex items-center gap-2"
          :class="activeTab === 'geo' ? 'border-sky-500 text-sky-400 bg-slate-800/40' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'geo'"
        >
          <span>📍</span>
          <span>Géoréférencement</span>
          <span
            v-if="hasCoordinates"
            class="w-2 h-2 rounded-full bg-emerald-400"
            title="Coordonnées renseignées"
          ></span>
          <span
            v-else
            class="w-2 h-2 rounded-full bg-amber-500"
            title="Non géolocalisé"
          ></span>
        </button>
        <button
          type="button"
          class="px-4 py-2.5 font-medium border-b-2 transition-all flex items-center gap-2"
          :class="activeTab === 'media' ? 'border-sky-500 text-sky-400 bg-slate-800/40' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'media'"
        >
          <span>🖼️</span>
          <span>Image & Numérisation</span>
          <span
            v-if="currentPreviewUrl"
            class="w-2 h-2 rounded-full bg-emerald-400"
            title="Image attachée"
          ></span>
        </button>
      </div>

      <!-- Corps du formulaire scrollable -->
      <form class="flex-1 overflow-y-auto p-6 space-y-6" @submit.prevent="handleSubmit">
        <!-- ONGLET 1 : Notice & Métadonnées documentaires -->
        <div v-show="activeTab === 'document'" class="space-y-5">
          <!-- Titre (obligatoire) -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Titre du cliché <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              required
              placeholder="Ex: Le Quai Cronstadt et les cuirassés en rade"
              class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all text-sm"
            />
          </div>

          <!-- Statut et Licence -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Statut de publication <span class="text-rose-400">*</span>
              </label>
              <select
                v-model="form.status"
                class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all text-sm"
              >
                <option value="draft">Brouillon (draft - masqué au public)</option>
                <option value="published">Publié (published - visible sur la carte)</option>
              </select>
              <p class="text-[11px] text-slate-400 mt-1">
                Le mode brouillon autorise l'enregistrement partiel sans coordonnées GPS.
              </p>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Licence de diffusion <span class="text-rose-400">*</span>
              </label>
              <select
                v-model="form.license"
                class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all text-sm"
              >
                <option
                  v-for="lic in PHOTO_LICENSES"
                  :key="lic.value"
                  :value="lic.value"
                >
                  {{ lic.label }}
                </option>
              </select>
              <p class="text-[11px] text-slate-400 mt-1">
                {{ PHOTO_LICENSES.find(l => l.value === form.license)?.description }}
              </p>
            </div>
          </div>

          <!-- Description historique -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Description & Contexte Historique
            </label>
            <textarea
              v-model="form.description"
              rows="3"
              placeholder="Description documentaire de la vue, des monuments ou navires visibles, de l'événement immortalisé..."
              class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all text-sm resize-y"
            ></textarea>
          </div>

          <!-- Photographe et Datation -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                <span>Photographe / Auteur</span>
                <span v-if="suggestions.photographers.length" class="text-[10px] text-sky-400 font-normal">
                  {{ suggestions.photographers.length }} connu(s)
                </span>
              </label>
              <input
                v-model="form.photographer"
                type="text"
                list="photographers-suggestions"
                placeholder="Ex: Marius Bar, Félix Mesguich"
                class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
              />
              <datalist id="photographers-suggestions">
                <option v-for="p in suggestions.photographers" :key="p" :value="p" />
              </datalist>

              <!-- Tags de suggestions rapides -->
              <div v-if="suggestions.photographers.length" class="flex flex-wrap gap-1 mt-1.5">
                <button
                  v-for="p in suggestions.photographers.slice(0, 3)"
                  :key="p"
                  type="button"
                  class="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  @click="form.photographer = p"
                >
                  {{ p }}
                </button>
              </div>
            </div>

            <!-- Année & Précision -->
            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Année de prise de vue
              </label>
              <div class="flex items-center gap-3">
                <input
                  v-model.number="form.year_taken"
                  type="number"
                  min="1800"
                  max="2030"
                  placeholder="Ex: 1912"
                  class="flex-1 bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
                />
                
                <!-- Toggle Année précise ? -->
                <label class="flex items-center gap-2 cursor-pointer select-none bg-slate-800/80 px-3 py-2 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors">
                  <input
                    v-model="form.is_exact_year"
                    type="checkbox"
                    class="w-4 h-4 rounded text-sky-600 bg-slate-900 border-slate-600 focus:ring-sky-500 focus:ring-offset-slate-900 cursor-pointer"
                  />
                  <span class="text-xs font-medium" :class="form.is_exact_year ? 'text-sky-300 font-semibold' : 'text-slate-400'">
                    {{ form.is_exact_year ? 'Année certifiée' : 'Approximative' }}
                  </span>
                </label>
              </div>
              <p class="text-[11px] text-slate-500 mt-1">
                {{ form.is_exact_year ? 'L\'année est attestée par les archives.' : 'L\'affichage indiquera « Vers ' + (form.year_taken || '...') + ' ».' }}
              </p>
            </div>
          </div>

          <!-- Institution d'archive & Cote d'inventaire -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                <span>Institution d'archives / Fonds</span>
                <span v-if="suggestions.archive_sources.length" class="text-[10px] text-sky-400 font-normal">
                  {{ suggestions.archive_sources.length }} connue(s)
                </span>
              </label>
              <input
                v-model="form.archive_source"
                type="text"
                list="archives-suggestions"
                placeholder="Ex: Archives Municipales de Toulon"
                class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
              />
              <datalist id="archives-suggestions">
                <option v-for="a in suggestions.archive_sources" :key="a" :value="a" />
              </datalist>

              <!-- Tags de suggestions rapides -->
              <div v-if="suggestions.archive_sources.length" class="flex flex-wrap gap-1 mt-1.5">
                <button
                  v-for="a in suggestions.archive_sources.slice(0, 3)"
                  :key="a"
                  type="button"
                  class="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  @click="form.archive_source = a"
                >
                  {{ a }}
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Cote d'inventaire
              </label>
              <input
                v-model="form.archive_ref"
                type="text"
                placeholder="Ex: 21Fi45, 4S128"
                class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
              />
            </div>
          </div>

          <!-- Lien source / notice -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              URL de la notice d'origine
            </label>
            <input
              v-model="form.original_source_url"
              type="url"
              placeholder="https://archives.toulon.fr/fonds/photos/21Fi45"
              class="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
            />
          </div>
        </div>

        <!-- ONGLET 2 : Géoréférencement & Azimut -->
        <div v-show="activeTab === 'geo'" class="space-y-4">
          <PhotoLocationPicker
            ref="locationPickerRef"
            :latitude="form.latitude"
            :longitude="form.longitude"
            :bearing="form.bearing"
            :field-of-view="form.field_of_view"
            :view-distance="form.view_distance"
            @update:latitude="form.latitude = $event"
            @update:longitude="form.longitude = $event"
            @update:bearing="form.bearing = $event"
            @update:field-of-view="form.field_of_view = $event"
            @update:view-distance="form.view_distance = $event"
          />
        </div>

        <!-- ONGLET 3 : Image & Numérisation -->
        <div v-show="activeTab === 'media'" class="space-y-5">
          <!-- Zone Drag & Drop -->
          <div
            class="border-2 border-dashed rounded-2xl p-6 text-center transition-all cursor-pointer flex flex-col items-center justify-center relative overflow-hidden"
            :class="isUploadingImage ? 'border-sky-500 bg-sky-950/20' : 'border-slate-700 hover:border-slate-500 bg-slate-900/40 hover:bg-slate-800/30'"
            @dragover.prevent
            @drop="handleDrop"
            @click="fileInputRef?.click()"
          >
            <input
              ref="fileInputRef"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/tiff"
              class="hidden"
              @change="handleFileSelect"
            />

            <!-- Spinner pendant le téléversement -->
            <div v-if="isUploadingImage" class="py-8 flex flex-col items-center gap-3">
              <div class="w-10 h-10 border-4 border-sky-400 border-t-transparent rounded-full animate-spin"></div>
              <p class="text-sm font-semibold text-sky-300">Traitement de l'image & conversion WebP...</p>
              <p class="text-xs text-slate-400">Génération des déclinaisons (original, display 2048px, thumb 400px)</p>
            </div>

            <!-- Aperçu de l'image -->
            <div v-else-if="currentPreviewUrl" class="space-y-4 w-full">
              <div class="relative max-h-64 mx-auto rounded-lg overflow-hidden border border-slate-700 bg-black flex items-center justify-center">
                <img
                  :src="currentPreviewUrl"
                  alt="Aperçu du cliché"
                  class="max-h-64 object-contain"
                />
                <span class="absolute top-2 right-2 px-2 py-1 bg-slate-900/80 backdrop-blur rounded text-[11px] font-mono text-slate-300 border border-slate-700">
                  WebP Optimisé
                </span>
              </div>

              <div class="text-xs text-slate-400">
                <span class="text-sky-400 font-medium hover:underline">Cliquer ou déposer</span> un nouveau fichier pour remplacer l'image existante (Max 25 Mo).
              </div>
            </div>

            <!-- Placeholder sans image -->
            <div v-else class="py-8 space-y-3">
              <div class="w-12 h-12 mx-auto rounded-full bg-slate-800 flex items-center justify-center text-2xl text-slate-400">
                📷
              </div>
              <div>
                <p class="text-sm font-semibold text-white">
                  Glissez-déposez le fichier numérisé ici, ou <span class="text-sky-400 underline">parcourez vos dossiers</span>
                </p>
                <p class="text-xs text-slate-400 mt-1">
                  Formats acceptés : JPEG, PNG, TIFF, WebP (Jusqu'à 25 Mo).
                </p>
              </div>
            </div>
          </div>

          <!-- Informations sur le pipeline d'ingestion -->
          <div class="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 text-xs text-slate-400 space-y-1.5">
            <div class="font-semibold text-slate-300">ℹ️ Pipeline automatique d'archivage (Pillow WebP) :</div>
            <ul class="list-disc pl-4 space-y-1">
              <li>Le fichier original haute définition est conservé intact pour la conservation patrimoniale.</li>
              <li>Une version WebP affichage (display) max 2048px qualité 85 est générée pour les écrans et la carte.</li>
              <li>Une vignette WebP (thumb) max 400px qualité 80 est générée pour les aperçus rapides.</li>
              <li>Les métadonnées EXIF potentiellement vulnérables sont désinfectées automatiquement.</li>
            </ul>
          </div>
        </div>
      </form>

      <!-- Pied de la modale avec actions -->
      <div class="px-6 py-4 border-t border-slate-800 bg-slate-950/70 flex items-center justify-between">
        <div class="text-xs text-slate-400">
          <span v-if="form.status === 'published'" class="inline-flex items-center gap-1.5 text-emerald-400">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span> Publication immédiate sur la carte
          </span>
          <span v-else class="inline-flex items-center gap-1.5 text-amber-400">
            <span class="w-2 h-2 rounded-full bg-amber-400"></span> Sauvegarde en brouillon (mode draft)
          </span>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            @click="emit('close')"
          >
            Annuler
          </button>

          <button
            type="button"
            class="px-5 py-2 text-sm font-medium text-white rounded-lg transition-all flex items-center gap-2 shadow-lg"
            :class="canSubmit ? 'bg-sky-600 hover:bg-sky-500 shadow-sky-900/30' : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'"
            :disabled="!canSubmit"
            :title="isPublishBlocked ? 'Coordonnées GPS obligatoires pour publier' : ''"
            @click="handleSubmit"
          >
            <span v-if="isSubmitting" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>{{ isSubmitting ? 'Enregistrement...' : (form.status === 'published' ? 'Publier la fiche' : 'Enregistrer le brouillon') }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
