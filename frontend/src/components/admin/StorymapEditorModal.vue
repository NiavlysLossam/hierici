<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { storymapApi, photoApi } from '@/services/api'
import type { Storymap, StorymapStep, StorymapStatus } from '@/types/storymap'
import type { Photo } from '@/types/photo'
import {
  reorderStepsLocally,
  detachPhotoFromStep as detachPhotoUtil,
  validateAudioFile,
  renderMarkdownPreview,
} from '@/utils/storymapStudio'
import StorymapCameraPicker from './StorymapCameraPicker.vue'

const props = withDefaults(
  defineProps<{
    isOpen: boolean
    storymapId?: string | null
    territoryCenter?: { lat: number; lng: number; zoom?: number } | null
    territoryId?: string | null
  }>(),
  {
    storymapId: null,
    territoryCenter: () => ({ lat: 43.1242, lng: 5.9328, zoom: 13 }),
    territoryId: null,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', storymap: Storymap): void
  (e: 'deleted', id: string): void
}>()

// État général du formulaire
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Métadonnées globales du récit
const currentStorymap = ref<Storymap | null>(null)
const title = ref('')
const summary = ref('')
const slug = ref('')
const status = ref<StorymapStatus>('draft')
const coverImageUrl = ref<string | null>(null)
const isUploadingCover = ref(false)

// Étapes du récit
const steps = ref<StorymapStep[]>([])
const activeStepIndex = ref(0)
const activeStep = computed(() => steps.value[activeStepIndex.value] || null)

// Markdown : bascule vue code / aperçu
const showMarkdownPreview = ref(false)

// Drag and drop state
const draggedStepIndex = ref<number | null>(null)
const dragOverStepIndex = ref<number | null>(null)

// Sélecteur modal de photos
const isPhotoSelectorOpen = ref(false)
const territoryPhotos = ref<Photo[]>([])
const photoSearchQuery = ref('')
const isLoadingPhotos = ref(false)

// Téléversement audio
const isUploadingAudio = ref(false)
const audioInputRef = ref<HTMLInputElement | null>(null)
const coverInputRef = ref<HTMLInputElement | null>(null)

function defaultCoordinates() {
  return {
    camera_lat: props.territoryCenter?.lat ?? 43.1242,
    camera_lng: props.territoryCenter?.lng ?? 5.9328,
    camera_zoom: props.territoryCenter?.zoom ?? 13,
    camera_bearing: 0,
    camera_pitch: 0,
  }
}

/**
 * Initialise le formulaire (mode création ou édition)
 */
async function loadStorymapData() {
  errorMessage.value = null
  successMessage.value = null

  if (props.storymapId) {
    loading.value = true
    try {
      const data = await storymapApi.getStorymap(props.storymapId)
      currentStorymap.value = data
      title.value = data.title
      summary.value = data.summary || ''
      slug.value = data.slug
      status.value = data.status
      coverImageUrl.value = data.cover_image_url || null
      steps.value = (data.steps || []).map((s, idx) => ({
        ...s,
        step_order: s.step_order ?? idx,
      }))
      activeStepIndex.value = 0
    } catch (err: any) {
      errorMessage.value = err.message || 'Impossible de charger le récit.'
    } finally {
      loading.value = false
    }
  } else {
    // Mode création vierge
    currentStorymap.value = null
    title.value = ''
    summary.value = ''
    slug.value = ''
    status.value = 'draft'
    coverImageUrl.value = null

    // Initialiser avec une première étape par défaut
    const def = defaultCoordinates()
    steps.value = [
      {
        id: `temp-${Date.now()}-0`,
        storymap_id: '',
        step_order: 0,
        title: 'Prologue',
        content_markdown: 'Rédigez ici le récit narratif de ce premier chapitre...',
        photo_id: null,
        audio_file_path: null,
        audio_url: null,
        camera_lat: def.camera_lat,
        camera_lng: def.camera_lng,
        camera_zoom: def.camera_zoom,
        camera_bearing: def.camera_bearing,
        camera_pitch: def.camera_pitch,
        created_at: new Date().toISOString(),
      },
    ]
    activeStepIndex.value = 0
  }
}

watch(
  () => [props.isOpen, props.storymapId],
  ([isOpen]) => {
    if (isOpen) {
      loadStorymapData()
    }
  },
  { immediate: true }
)

/**
 * Sauvegarde globale de la storymap (création ou mise à jour)
 */
async function handleSaveStorymap() {
  if (!title.value.trim()) {
    errorMessage.value = 'Le titre du récit est obligatoire.'
    return
  }

  saving.value = true
  errorMessage.value = null
  successMessage.value = null

  try {
    let savedStorymap: Storymap

    if (currentStorymap.value?.id) {
      // 1. Mise à jour des métadonnées du récit
      savedStorymap = await storymapApi.updateStorymap(currentStorymap.value.id, {
        title: title.value.trim(),
        summary: summary.value.trim() || null,
        slug: slug.value.trim() || undefined,
        status: status.value,
      })

      // 2. Synchroniser les étapes modifiées
      for (let i = 0; i < steps.value.length; i++) {
        const step = steps.value[i]
        const stepPayload = {
          title: step.title.trim() || `Chapitre ${i + 1}`,
          content_markdown: step.content_markdown || null,
          photo_id: step.photo_id ?? null,
          step_order: i,
          camera_lat: step.camera_lat,
          camera_lng: step.camera_lng,
          camera_zoom: step.camera_zoom,
          camera_bearing: step.camera_bearing,
          camera_pitch: step.camera_pitch,
        }

        if (step.id.startsWith('temp-')) {
          // Nouvelle étape ajoutée en cours d'édition
          const createdStep = await storymapApi.addStep(savedStorymap.id, stepPayload)
          steps.value[i] = createdStep
        } else {
          // Étape existante mise à jour
          const updatedStep = await storymapApi.updateStep(savedStorymap.id, step.id, stepPayload)
          steps.value[i] = updatedStep
        }
      }

      // Recharger la version finale consolidée
      savedStorymap = await storymapApi.getStorymap(savedStorymap.id)
      currentStorymap.value = savedStorymap
      steps.value = savedStorymap.steps
    } else {
      // Mode création complet
      const def = defaultCoordinates()
      const initialSteps = steps.value.map((s, idx) => ({
        title: s.title.trim() || `Chapitre ${idx + 1}`,
        content_markdown: s.content_markdown || null,
        photo_id: s.photo_id ?? null,
        step_order: idx,
        camera_lat: s.camera_lat ?? def.camera_lat,
        camera_lng: s.camera_lng ?? def.camera_lng,
        camera_zoom: s.camera_zoom ?? def.camera_zoom,
        camera_bearing: s.camera_bearing ?? def.camera_bearing,
        camera_pitch: s.camera_pitch ?? def.camera_pitch,
      }))

      savedStorymap = await storymapApi.createStorymap({
        title: title.value.trim(),
        summary: summary.value.trim() || null,
        slug: slug.value.trim() || undefined,
        status: status.value,
        steps: initialSteps,
      })

      currentStorymap.value = savedStorymap
      steps.value = savedStorymap.steps
    }

    successMessage.value = 'Récit enregistré avec succès !'
    emit('saved', savedStorymap)
    setTimeout(() => {
      successMessage.value = null
    }, 2500)
  } catch (err: any) {
    errorMessage.value = err.message || "Erreur lors de l'enregistrement du récit."
  } finally {
    saving.value = false
  }
}

/**
 * Ajout d'une nouvelle étape
 */
function handleAddStep() {
  const def = defaultCoordinates()
  const newIndex = steps.value.length
  const newStep: StorymapStep = {
    id: `temp-${Date.now()}-${newIndex}`,
    storymap_id: currentStorymap.value?.id || '',
    step_order: newIndex,
    title: `Chapitre ${newIndex + 1}`,
    content_markdown: '',
    photo_id: null,
    audio_file_path: null,
    audio_url: null,
    camera_lat: def.camera_lat,
    camera_lng: def.camera_lng,
    camera_zoom: def.camera_zoom,
    camera_bearing: def.camera_bearing,
    camera_pitch: def.camera_pitch,
    created_at: new Date().toISOString(),
  }

  steps.value.push(newStep)
  activeStepIndex.value = newIndex
}

/**
 * Suppression d'une étape
 */
async function handleDeleteStep(index: number) {
  if (steps.value.length <= 1) {
    errorMessage.value = 'Une storymap doit comporter au moins une étape.'
    return
  }

  const stepToDelete = steps.value[index]
  if (!confirm(`Supprimer l'étape "${stepToDelete.title}" ?`)) return

  try {
    if (currentStorymap.value?.id && !stepToDelete.id.startsWith('temp-')) {
      await storymapApi.deleteStep(currentStorymap.value.id, stepToDelete.id)
    }

    steps.value.splice(index, 1)
    // Réordonner les index locaux
    steps.value.forEach((s, idx) => {
      s.step_order = idx
    })

    if (activeStepIndex.value >= steps.value.length) {
      activeStepIndex.value = Math.max(0, steps.value.length - 1)
    }

    // Persister le réordonnancement si enregistré
    if (currentStorymap.value?.id) {
      const persistedIds = steps.value.filter((s) => !s.id.startsWith('temp-')).map((s) => s.id)
      if (persistedIds.length === steps.value.length) {
        await storymapApi.reorderSteps(currentStorymap.value.id, persistedIds)
      }
    }
  } catch (err: any) {
    errorMessage.value = err.message || "Impossible de supprimer l'étape."
  }
}

/**
 * Réordonnancement par boutons haut / bas
 */
async function moveStep(fromIdx: number, toIdx: number) {
  if (toIdx < 0 || toIdx >= steps.value.length || fromIdx === toIdx) return

  const originalOrder = [...steps.value]
  const previousActiveIndex = activeStepIndex.value

  steps.value = reorderStepsLocally(steps.value, fromIdx, toIdx)
  activeStepIndex.value = toIdx

  // Si storymap déjà persistée et que toutes les étapes ont un ID réel, synchroniser l'API
  if (currentStorymap.value?.id) {
    const hasTemp = steps.value.some((s) => s.id.startsWith('temp-'))
    if (!hasTemp) {
      try {
        await storymapApi.reorderSteps(
          currentStorymap.value.id,
          steps.value.map((s) => s.id)
        )
      } catch (err: any) {
        // Rollback de l'ordre ET de l'index de chapitre actif en cas d'échec
        steps.value = originalOrder
        activeStepIndex.value = previousActiveIndex
        errorMessage.value = 'Échec de synchronisation du réordonnancement.'
      }
    }
  }
}

/**
 * Drag and Drop HTML5 natif
 */
function onDragStart(idx: number, e: DragEvent) {
  draggedStepIndex.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', idx.toString())
  }
}

function onDragOver(idx: number, e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  dragOverStepIndex.value = idx
}

async function onDrop(targetIdx: number, e: DragEvent) {
  e.preventDefault()
  const fromIdx = draggedStepIndex.value
  draggedStepIndex.value = null
  dragOverStepIndex.value = null

  if (fromIdx !== null && fromIdx !== targetIdx) {
    await moveStep(fromIdx, targetIdx)
  }
}

function onDragEnd() {
  draggedStepIndex.value = null
  dragOverStepIndex.value = null
}

/**
 * Gestion de l'image de couverture
 */
async function handleCoverFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  if (!currentStorymap.value?.id) {
    // Si la storymap n'est pas encore enregistrée, inviter à sauvegarder d'abord
    errorMessage.value = "Veuillez d'abord enregistrer le récit avant d'ajouter une couverture."
    return
  }

  isUploadingCover.value = true
  errorMessage.value = null
  try {
    const updated = await storymapApi.uploadCover(currentStorymap.value.id, file)
    currentStorymap.value = updated
    coverImageUrl.value = updated.cover_image_url || null
    successMessage.value = 'Couverture téléversée avec succès.'
  } catch (err: any) {
    errorMessage.value = err.message || 'Erreur lors du téléversement de la couverture.'
  } finally {
    isUploadingCover.value = false
    if (coverInputRef.value) coverInputRef.value.value = ''
  }
}

async function handleRemoveCover() {
  if (!currentStorymap.value?.id) {
    coverImageUrl.value = null
    return
  }

  isUploadingCover.value = true
  try {
    const updated = await storymapApi.deleteCover(currentStorymap.value.id)
    currentStorymap.value = updated
    coverImageUrl.value = null
  } catch (err: any) {
    errorMessage.value = err.message || 'Impossible de supprimer la couverture.'
  } finally {
    isUploadingCover.value = false
  }
}

/**
 * Gestion du document sonore de l'étape active
 */
async function handleAudioFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !activeStep.value) return

  // Validation du fichier audio via l'utilitaire partagé
  const validation = validateAudioFile({
    name: file.name,
    size: file.size,
    type: file.type,
  })
  if (!validation.valid) {
    errorMessage.value = validation.error || 'Fichier audio non valide.'
    return
  }

  if (!currentStorymap.value?.id || activeStep.value.id.startsWith('temp-')) {
    errorMessage.value = "Veuillez enregistrer le récit avant de téléverser un fichier audio sur cette étape."
    return
  }

  isUploadingAudio.value = true
  errorMessage.value = null
  try {
    const updatedStep = await storymapApi.uploadStepAudio(
      currentStorymap.value.id,
      activeStep.value.id,
      file
    )
    const idx = steps.value.findIndex((s) => s.id === updatedStep.id)
    if (idx !== -1) {
      steps.value[idx] = updatedStep
    }
    successMessage.value = 'Document sonore associé avec succès.'
  } catch (err: any) {
    errorMessage.value = err.message || "Erreur lors de l'upload audio."
  } finally {
    isUploadingAudio.value = false
    if (audioInputRef.value) audioInputRef.value.value = ''
  }
}

async function handleRemoveAudio() {
  if (!activeStep.value) return
  if (!currentStorymap.value?.id || activeStep.value.id.startsWith('temp-')) {
    activeStep.value.audio_file_path = null
    activeStep.value.audio_url = null
    return
  }

  isUploadingAudio.value = true
  try {
    const updatedStep = await storymapApi.deleteStepAudio(
      currentStorymap.value.id,
      activeStep.value.id
    )
    const idx = steps.value.findIndex((s) => s.id === updatedStep.id)
    if (idx !== -1) {
      steps.value[idx] = updatedStep
    }
  } catch (err: any) {
    errorMessage.value = err.message || "Impossible de supprimer l'audio."
  } finally {
    isUploadingAudio.value = false
  }
}

/**
 * Sélecteur de photo d'archive du territoire
 */
async function openPhotoSelector() {
  isPhotoSelectorOpen.value = true
  isLoadingPhotos.value = true
  try {
    const res = await photoApi.listPhotos({
      status: 'published',
      page_size: 100,
      territory_id: props.territoryId || undefined,
    })
    territoryPhotos.value = res.items || []
  } catch (err: any) {
    errorMessage.value = "Impossible de charger la photothèque du territoire."
  } finally {
    isLoadingPhotos.value = false
  }
}

const filteredTerritoryPhotos = computed(() => {
  if (!photoSearchQuery.value.trim()) return territoryPhotos.value
  const q = photoSearchQuery.value.toLowerCase().trim()
  return territoryPhotos.value.filter(
    (p) =>
      p.title.toLowerCase().includes(q) ||
      (p.archive_ref && p.archive_ref.toLowerCase().includes(q)) ||
      (p.photographer && p.photographer.toLowerCase().includes(q))
  )
})

function selectPhotoForStep(photo: Photo) {
  if (!activeStep.value) return
  activeStep.value.photo_id = photo.id
  activeStep.value.photo = photo
  isPhotoSelectorOpen.value = false
}

function detachPhotoFromStep() {
  if (!activeStep.value) return
  const updated = detachPhotoUtil(activeStep.value)
  activeStep.value.photo_id = updated.photo_id
  activeStep.value.photo = updated.photo
}

/**
 * Mise à jour des coordonnées caméra capturées
 */
function onCameraCapture(coords: {
  camera_lat: number
  camera_lng: number
  camera_zoom: number
  camera_bearing: number
  camera_pitch: number
}) {
  if (!activeStep.value) return
  activeStep.value.camera_lat = coords.camera_lat
  activeStep.value.camera_lng = coords.camera_lng
  activeStep.value.camera_zoom = coords.camera_zoom
  activeStep.value.camera_bearing = coords.camera_bearing
  activeStep.value.camera_pitch = coords.camera_pitch
}
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-slate-950/85 backdrop-blur-md overflow-y-auto"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-7xl max-h-[96vh] flex flex-col shadow-2xl overflow-hidden font-sans"
    >
      <!-- En-tête supérieur du Studio -->
      <header class="px-6 py-4 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between gap-4 sticky top-0 z-20">
        <div class="flex items-center gap-3">
          <span class="text-2xl">📖</span>
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>{{ currentStorymap ? 'Éditer le récit' : 'Nouveau récit territorial' }}</span>
              <span
                class="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full"
                :class="status === 'published' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'"
              >
                {{ status === 'published' ? 'Publié' : 'Brouillon' }}
              </span>
            </h2>
            <p class="text-xs text-slate-400">
              {{ steps.length }} chapitre{{ steps.length > 1 ? 's' : '' }} ordonné{{ steps.length > 1 ? 's' : '' }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <!-- Bascule statut de publication -->
          <div class="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              type="button"
              class="px-3 py-1 rounded-lg font-medium transition-colors"
              :class="status === 'draft' ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-white'"
              @click="status = 'draft'"
            >
              Brouillon
            </button>
            <button
              type="button"
              class="px-3 py-1 rounded-lg font-medium transition-colors"
              :class="status === 'published' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'"
              @click="status = 'published'"
            >
              Publier
            </button>
          </div>

          <!-- Bouton Enregistrer -->
          <button
            type="button"
            class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold shadow-md flex items-center gap-2 transition-all disabled:opacity-50"
            :disabled="saving"
            @click="handleSaveStorymap"
          >
            <span v-if="saving" class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>{{ saving ? 'Enregistrement...' : 'Enregistrer le récit' }}</span>
          </button>

          <!-- Bouton Fermer -->
          <button
            type="button"
            class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>
      </header>

      <!-- Alertes d'état -->
      <div v-if="errorMessage" class="mx-6 mt-3 p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-xs text-rose-300 flex items-center justify-between">
        <span>⚠️ {{ errorMessage }}</span>
        <button type="button" class="text-rose-400 hover:text-white" @click="errorMessage = null">✕</button>
      </div>

      <div v-if="successMessage" class="mx-6 mt-3 p-3 rounded-xl bg-emerald-950/80 border border-emerald-800 text-xs text-emerald-300 flex items-center justify-between">
        <span>✓ {{ successMessage }}</span>
        <button type="button" class="text-emerald-400 hover:text-white" @click="successMessage = null">✕</button>
      </div>

      <!-- Corps du Studio scindé en deux volets -->
      <div class="flex-1 flex flex-col lg:flex-row overflow-hidden">
        <!-- VOLET GAUCHE : Stepper & Métadonnées globales -->
        <aside class="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-slate-800 bg-slate-950/60 p-4 flex flex-col overflow-y-auto space-y-5">
          <!-- Métadonnées globales pliables -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-3">
            <h3 class="text-xs font-bold text-slate-300 flex items-center gap-2">
              <span>📋</span>
              <span>Informations Générales</span>
            </h3>

            <div>
              <label class="block text-[11px] font-medium text-slate-400 mb-1">Titre du récit *</label>
              <input
                v-model="title"
                type="text"
                placeholder="ex: Le Tramway et les mutations du port"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>

            <div>
              <label class="block text-[11px] font-medium text-slate-400 mb-1">Résumé introductif</label>
              <textarea
                v-model="summary"
                rows="2"
                placeholder="Courte présentation de l'itinéraire patrimonial..."
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 resize-none"
              ></textarea>
            </div>

            <div>
              <label class="block text-[11px] font-medium text-slate-400 mb-1">Slug URL</label>
              <input
                v-model="slug"
                type="text"
                placeholder="laisser vide pour auto-génération"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono text-[11px]"
              />
            </div>

            <!-- Image de couverture du récit -->
            <div class="pt-2 border-t border-slate-800">
              <label class="block text-[11px] font-medium text-slate-400 mb-2">Image de couverture</label>
              <div v-if="coverImageUrl" class="relative group rounded-lg overflow-hidden border border-slate-700">
                <img :src="coverImageUrl" alt="Couverture" class="w-full h-24 object-cover" />
                <button
                  type="button"
                  class="absolute top-1 right-1 p-1 bg-rose-900/90 hover:bg-rose-800 text-white rounded text-xs opacity-90 transition-opacity"
                  title="Supprimer la couverture"
                  @click="handleRemoveCover"
                >
                  ✕
                </button>
              </div>
              <div v-else class="flex items-center gap-2">
                <input
                  ref="coverInputRef"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  class="hidden"
                  @change="handleCoverFileChange"
                />
                <button
                  type="button"
                  class="w-full py-2 px-3 border border-dashed border-slate-700 hover:border-sky-500 rounded-lg text-slate-400 hover:text-white text-xs flex items-center justify-center gap-2 transition-colors"
                  :disabled="isUploadingCover"
                  @click="coverInputRef?.click()"
                >
                  <span v-if="isUploadingCover" class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span v-else>🖼️</span>
                  <span>{{ isUploadingCover ? 'Téléversement...' : 'Téléverser une couverture' }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Stepper ordonné des chapitres avec Drag & Drop -->
          <div class="flex-1 flex flex-col space-y-2">
            <div class="flex items-center justify-between pb-1">
              <h3 class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                <span>📑</span>
                <span>Séquence des Chapitres</span>
              </h3>
              <button
                type="button"
                class="px-2 py-1 rounded-md bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 text-[11px] font-medium flex items-center gap-1 transition-colors"
                @click="handleAddStep"
              >
                <span>+</span>
                <span>Ajouter</span>
              </button>
            </div>

            <!-- Liste des cartes de chapitres -->
            <div class="space-y-1.5 overflow-y-auto pr-1">
              <div
                v-for="(step, idx) in steps"
                :key="step.id"
                draggable="true"
                class="group relative rounded-xl border p-2.5 transition-all flex items-center gap-2.5 cursor-pointer select-none"
                :class="[
                  activeStepIndex === idx
                    ? 'bg-slate-800 border-sky-500 shadow-md ring-1 ring-sky-500/50'
                    : 'bg-slate-900/80 border-slate-800 hover:bg-slate-850 hover:border-slate-700',
                  draggedStepIndex === idx ? 'opacity-40' : '',
                  dragOverStepIndex === idx ? 'border-t-2 border-t-amber-400' : '',
                ]"
                @click="activeStepIndex = idx"
                @dragstart="onDragStart(idx, $event)"
                @dragover="onDragOver(idx, $event)"
                @drop="onDrop(idx, $event)"
                @dragend="onDragEnd"
              >
                <!-- Poignée de glissement -->
                <span class="text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing text-sm font-mono px-0.5">
                  ⠿
                </span>

                <!-- Numéro d'ordre -->
                <span class="w-5 h-5 rounded-full bg-slate-950 border border-slate-700 text-[10px] font-bold flex items-center justify-center text-slate-300 flex-shrink-0">
                  {{ idx + 1 }}
                </span>

                <!-- Miniature photo liée si présente -->
                <div v-if="step.photo?.thumb_url || step.photo?.image_thumb_url" class="w-8 h-8 rounded bg-slate-950 overflow-hidden flex-shrink-0 border border-slate-700">
                  <img
                    :src="step.photo.thumb_url || step.photo.image_thumb_url || ''"
                    alt=""
                    class="w-full h-full object-cover"
                  />
                </div>
                <div v-else class="w-8 h-8 rounded bg-slate-950 border border-slate-800 flex items-center justify-center text-xs text-slate-600 flex-shrink-0">
                  📷
                </div>

                <!-- Titre & Badges média -->
                <div class="flex-1 min-w-0">
                  <h4 class="text-xs font-semibold text-white truncate">
                    {{ step.title || `Chapitre ${idx + 1}` }}
                  </h4>
                  <div class="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                    <span v-if="step.audio_file_path" title="Piste sonore associée">🎵</span>
                    <span title="Cadrage caméra">🎥 {{ step.camera_zoom?.toFixed(0) || '13' }}x</span>
                  </div>
                </div>

                <!-- Contrôles Haut/Bas & Suppression -->
                <div class="flex items-center gap-1 opacity-80 group-hover:opacity-100">
                  <button
                    type="button"
                    class="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700 text-[10px] disabled:opacity-20"
                    :disabled="idx === 0"
                    title="Monter"
                    @click.stop="moveStep(idx, idx - 1)"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    class="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700 text-[10px] disabled:opacity-20"
                    :disabled="idx === steps.length - 1"
                    title="Descendre"
                    @click.stop="moveStep(idx, idx + 1)"
                  >
                    ▼
                  </button>
                  <button
                    type="button"
                    class="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/60 text-[10px]"
                    title="Supprimer cette étape"
                    @click.stop="handleDeleteStep(idx)"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- VOLET DROIT : Éditeur du chapitre actif -->
        <main v-if="activeStep" class="flex-1 p-6 overflow-y-auto space-y-6">
          <!-- Titre du chapitre actif -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div class="flex-1">
              <label class="block text-xs font-medium text-slate-400 mb-1">
                Titre de l'étape {{ activeStepIndex + 1 }}
              </label>
              <input
                v-model="activeStep.title"
                type="text"
                placeholder="Titre accrocheur du chapitre..."
                class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white font-semibold placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
          </div>

          <!-- Section Scindée : Texte Narratif Markdown & Photo liée -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 1. Éditeur de texte narratif Markdown -->
            <div class="space-y-2 flex flex-col">
              <div class="flex items-center justify-between">
                <label class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <span>✍️</span>
                  <span>Texte narratif (Markdown)</span>
                </label>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="text-[11px] px-2 py-0.5 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    :class="showMarkdownPreview ? 'bg-slate-800 text-sky-400 font-semibold' : ''"
                    @click="showMarkdownPreview = !showMarkdownPreview"
                  >
                    {{ showMarkdownPreview ? 'Mode Éditeur' : 'Aperçu Rendu' }}
                  </button>
                </div>
              </div>

              <!-- Zone de saisie Markdown -->
              <div v-if="!showMarkdownPreview" class="flex-1">
                <textarea
                  v-model="activeStep.content_markdown"
                  rows="8"
                  placeholder="Racontez l'histoire de ce lieu, le contexte historique, les anecdotes..."
                  class="w-full h-56 bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono leading-relaxed resize-none"
                ></textarea>
              </div>

              <!-- Zone d'aperçu Markdown -->
              <div
                v-else
                class="w-full h-56 bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 overflow-y-auto prose prose-invert max-w-none"
                v-html="renderMarkdownPreview(activeStep.content_markdown)"
              ></div>
            </div>

            <!-- 2. Cliché d'archive associé & Bande sonore -->
            <div class="space-y-4">
              <!-- Cliché photographique territorial -->
              <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div class="flex items-center justify-between">
                  <label class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <span>📸</span>
                    <span>Cliché photographique d'archive</span>
                  </label>
                  <button
                    v-if="!activeStep.photo_id"
                    type="button"
                    class="px-2.5 py-1 bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                    @click="openPhotoSelector"
                  >
                    <span>Choisir une photo</span>
                  </button>
                  <button
                    v-else
                    type="button"
                    class="text-xs text-rose-400 hover:text-rose-300 hover:underline"
                    @click="detachPhotoFromStep"
                  >
                    Retirer la photo
                  </button>
                </div>

                <!-- Aperçu de la photo attachée -->
                <div v-if="activeStep.photo || activeStep.photo_id" class="flex items-start gap-3 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <img
                    :src="activeStep.photo?.thumb_url || activeStep.photo?.display_url || activeStep.photo?.image_thumb_url || '/placeholder.png'"
                    alt=""
                    class="w-20 h-20 object-cover rounded-lg border border-slate-700 flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0 text-xs">
                    <h5 class="font-bold text-white truncate">
                      {{ activeStep.photo?.title || 'Photo associée' }}
                    </h5>
                    <p class="text-[11px] text-slate-400 mt-0.5">
                      {{ activeStep.photo?.archive_source || 'Archives' }}
                      <span v-if="activeStep.photo?.archive_ref">({{ activeStep.photo.archive_ref }})</span>
                    </p>
                    <p v-if="activeStep.photo?.year_taken" class="text-[10px] text-sky-400 mt-0.5 font-mono">
                      Année : {{ activeStep.photo.year_taken }}
                    </p>
                  </div>
                </div>

                <div v-else class="text-center py-4 border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
                  Aucun cliché associé à ce chapitre (optionnel)
                </div>
              </div>

              <!-- Document sonore narratif MP3 -->
              <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div class="flex items-center justify-between">
                  <label class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <span>🎙️</span>
                    <span>Document sonore (MP3, M4A, OGG, WAV)</span>
                  </label>
                  <button
                    v-if="activeStep.audio_file_path"
                    type="button"
                    class="text-xs text-rose-400 hover:text-rose-300 hover:underline"
                    @click="handleRemoveAudio"
                  >
                    Supprimer l'audio
                  </button>
                </div>

                <!-- Lecteur de pré-écoute si audio présent -->
                <div v-if="activeStep.audio_url || activeStep.audio_file_path" class="space-y-2">
                  <audio :src="activeStep.audio_url || undefined" controls class="w-full h-9 rounded-lg bg-slate-900"></audio>
                </div>

                <div v-else class="flex items-center gap-2">
                  <input
                    ref="audioInputRef"
                    type="file"
                    accept=".mp3,.m4a,.ogg,.wav,audio/*"
                    class="hidden"
                    @change="handleAudioFileChange"
                  />
                  <button
                    type="button"
                    class="w-full py-2 px-3 border border-dashed border-slate-800 hover:border-sky-500 rounded-lg text-slate-400 hover:text-white text-xs flex items-center justify-center gap-2 transition-colors"
                    :disabled="isUploadingAudio"
                    @click="audioInputRef?.click()"
                  >
                    <span v-if="isUploadingAudio" class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span v-else>🎵</span>
                    <span>{{ isUploadingAudio ? 'Téléversement...' : 'Téléverser un document sonore (max 50Mo)' }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Section Caméra Cartographique Interactive MapLibre GL -->
          <div class="space-y-2">
            <StorymapCameraPicker
              v-model:camera-lat="activeStep.camera_lat"
              v-model:camera-lng="activeStep.camera_lng"
              v-model:camera-zoom="activeStep.camera_zoom"
              v-model:camera-bearing="activeStep.camera_bearing"
              v-model:camera-pitch="activeStep.camera_pitch"
              :default-center="territoryCenter"
              @capture="onCameraCapture"
            />
          </div>
        </main>
      </div>
    </div>

    <!-- Modale de sélection de photo territoriale -->
    <div
      v-if="isPhotoSelectorOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
      @click.self="isPhotoSelectorOpen = false"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        <div class="p-4 border-b border-slate-800 flex items-center justify-between gap-4">
          <h3 class="text-sm font-bold text-white flex items-center gap-2">
            <span>📷</span>
            <span>Sélectionner une photo d'archive du territoire</span>
          </h3>
          <button type="button" class="text-slate-400 hover:text-white" @click="isPhotoSelectorOpen = false">✕</button>
        </div>

        <div class="p-4 border-b border-slate-800">
          <input
            v-model="photoSearchQuery"
            type="text"
            placeholder="Rechercher par titre, photographe, référence..."
            class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <div class="flex-1 p-4 overflow-y-auto">
          <div v-if="isLoadingPhotos" class="text-center py-8 text-xs text-slate-400">
            Chargement des clichés...
          </div>
          <div v-else-if="filteredTerritoryPhotos.length === 0" class="text-center py-8 text-xs text-slate-500">
            Aucun cliché trouvé dans ce territoire.
          </div>
          <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            <div
              v-for="photo in filteredTerritoryPhotos"
              :key="photo.id"
              class="group relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950 hover:border-sky-500 cursor-pointer transition-all shadow-sm flex flex-col"
              @click="selectPhotoForStep(photo)"
            >
              <img
                :src="photo.thumb_url || photo.display_url || photo.image_thumb_url || ''"
                alt=""
                class="w-full h-28 object-cover group-hover:scale-105 transition-transform"
              />
              <div class="p-2 text-[11px] flex-1 flex flex-col justify-between">
                <span class="font-semibold text-white line-clamp-2 leading-tight">{{ photo.title }}</span>
                <span v-if="photo.year_taken" class="text-[10px] text-sky-400 font-mono mt-1">
                  {{ photo.year_taken }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
