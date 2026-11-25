/**
 * Utilitaires purs pour le Studio d'édition et d'ordonnancement des Storymaps
 */

/**
 * Normalise un azimut cartographique dans l'intervalle [0, 360[
 */
export function normalizeBearing(val: number): number {
  if (isNaN(val)) return 0
  let b = val % 360
  if (b < 0) b += 360
  return b === 360 ? 0 : b
}

/**
 * Contraint une valeur numérique entre des bornes min et max
 */
export function clamp(val: number, min: number, max: number): number {
  if (isNaN(val)) return min
  return Math.min(Math.max(val, min), max)
}

/**
 * Borne et normalise l'ensemble des paramètres d'une caméra MapLibre GL
 */
export function clampCameraCoordinates(
  lat: number,
  lng: number,
  zoom: number,
  bearing: number,
  pitch: number
): {
  camera_lat: number
  camera_lng: number
  camera_zoom: number
  camera_bearing: number
  camera_pitch: number
} {
  return {
    camera_lat: clamp(Number(lat.toFixed(6)), -90, 90),
    camera_lng: clamp(Number(lng.toFixed(6)), -180, 180),
    camera_zoom: clamp(Number(zoom.toFixed(2)), 0, 24),
    camera_bearing: Number(normalizeBearing(bearing).toFixed(1)),
    camera_pitch: clamp(Number(pitch.toFixed(1)), 0, 85),
  }
}

/**
 * Réordonne localement les étapes d'un récit et met à jour séquentiellement step_order
 */
export function reorderStepsLocally<T extends { step_order?: number }>(
  steps: T[],
  fromIndex: number,
  toIndex: number
): T[] {
  if (
    fromIndex < 0 ||
    fromIndex >= steps.length ||
    toIndex < 0 ||
    toIndex >= steps.length ||
    fromIndex === toIndex
  ) {
    return [...steps]
  }

  const result = [...steps]
  const [moved] = result.splice(fromIndex, 1)
  result.splice(toIndex, 0, moved)

  return result.map((step, idx) => ({
    ...step,
    step_order: idx,
  }))
}

/**
 * Détache la photo d'archive liée à une étape sans modifier les autres attributs
 */
export function detachPhotoFromStep<T extends { photo_id?: any; photo?: any }>(step: T): T {
  return {
    ...step,
    photo_id: null,
    photo: null,
  }
}

/**
 * Valide un document sonore téléversé (format, extension et taille limite de 50 Mo)
 */
export function validateAudioFile(file: {
  name: string
  size: number
  type?: string
}): { valid: boolean; error?: string } {
  const MAX_SIZE = 50 * 1024 * 1024 // 50 Mo

  if (file.size > MAX_SIZE) {
    return {
      valid: false,
      error: 'Le fichier audio dépasse la taille maximale autorisée de 50 Mo.',
    }
  }

  const ext = (file.name.split('.').pop() || '').toLowerCase()
  const allowedExtensions = ['mp3', 'm4a', 'ogg', 'wav']
  if (!allowedExtensions.includes(ext)) {
    return {
      valid: false,
      error: 'Format audio non supporté. Formats acceptés : .mp3, .m4a, .ogg, .wav.',
    }
  }

  const allowedMimes = [
    'audio/mpeg',
    'audio/mp3',
    'audio/mp4',
    'audio/x-m4a',
    'audio/aac',
    'audio/ogg',
    'audio/wav',
    'audio/x-wav',
    'audio/wave',
    'application/ogg',
  ]

  if (file.type && file.type.trim()) {
    const cleanType = file.type.toLowerCase().split(';')[0].trim()
    if (!allowedMimes.includes(cleanType)) {
      return {
        valid: false,
        error: 'Type MIME audio non valide.',
      }
    }
  }

  return { valid: true }
}

/**
 * Rendu sécurisé d'un aperçu Markdown
 */
export function renderMarkdownPreview(markdown: string | null | undefined): string {
  if (!markdown || !markdown.trim()) {
    return '<p class="text-slate-500 italic">Aucun texte rédigé pour le moment.</p>'
  }

  let text = markdown
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  return text
    .replace(/^### (.*$)/gim, '<h3 class="text-base font-bold text-white mt-3 mb-1">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-lg font-bold text-sky-300 mt-4 mb-2">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-xl font-extrabold text-white mt-4 mb-2">$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong class="text-white font-bold">$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em class="text-slate-300 italic">$1</em>')
    .replace(
      /^(&gt;|>)\s?(.*$)/gim,
      '<blockquote class="border-l-4 border-sky-500 pl-3 py-1 my-2 text-slate-300 italic bg-slate-800/40 rounded-r">$2</blockquote>'
    )
    .replace(/^[-*]\s(.*$)/gim, '<li class="ml-4 list-disc text-slate-200">$1</li>')
    .replace(/\n$/gim, '<br />')
}
