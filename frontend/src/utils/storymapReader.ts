/**
 * Utilitaires purs pour le Lecteur Public de Storymaps (Scrollytelling & Audio)
 */

import { clamp, normalizeBearing } from './storymapStudio'

export interface CameraTarget {
  lat: number
  lng: number
  zoom: number
  bearing: number
  pitch: number
}

const DEFAULT_CAMERA_FALLBACK: CameraTarget = {
  lat: 43.1242,
  lng: 5.9328,
  zoom: 13,
  bearing: 0,
  pitch: 0,
}

/**
 * Extrait le slug d'une storymap depuis une chaîne (query param ?storymap=, path /storymaps/slug ou slug brut)
 */
export function extractStorymapSlug(
  input: string | URLSearchParams | Location | { search?: string; pathname?: string } | null | undefined
): string | null {
  if (!input) return null

  // 1. Cas objet Location ou objet avec propriétés d'URL
  if (typeof input === 'object' && !(input instanceof URLSearchParams)) {
    if ('search' in input && input.search) {
      const cleanSearch = input.search.split('#')[0]
      const params = new URLSearchParams(cleanSearch)
      const val = params.get('storymap')
      if (val && val.trim()) return val.trim().toLowerCase()
    }

    if ('pathname' in input && typeof input.pathname === 'string') {
      const cleanPath = input.pathname.split('#')[0]
      const pathMatch = cleanPath.match(/\/storymaps\/([a-zA-Z0-9_-]+)/)
      if (pathMatch && pathMatch[1]) return pathMatch[1].toLowerCase()
    }

    return null
  }

  // 2. Cas URLSearchParams
  if (input instanceof URLSearchParams) {
    const val = input.get('storymap')
    return val && val.trim() ? val.trim().toLowerCase() : null
  }

  // 3. Cas chaîne brute
  let str = String(input).trim()
  if (!str) return null

  // Retirer l'éventuelle ancre d'URL (#ancre)
  str = str.split('#')[0].trim()
  if (!str) return null

  // Si c'est une chaîne de query string (?storymap=slug ou photo=1&storymap=slug)
  if (str.includes('storymap=')) {
    const queryPart = str.includes('?') ? str.split('?')[1] : str
    const params = new URLSearchParams(queryPart)
    const val = params.get('storymap')
    return val && val.trim() ? val.trim().toLowerCase() : null
  }

  // Si c'est un chemin (/storymaps/slug ou /storymaps/slug/)
  const pathMatch = str.match(/\/storymaps\/([a-zA-Z0-9_-]+)/)
  if (pathMatch && pathMatch[1]) {
    return pathMatch[1].toLowerCase()
  }

  // Si c'est directement un slug valide sans slash ni query
  if (/^[a-zA-Z0-9_-]+$/.test(str)) {
    return str.toLowerCase()
  }

  return null
}

/**
 * Nettoie une URL en retirant le paramètre storymap tout en préservant les autres paramètres et le fragment
 */
export function cleanStorymapUrl(currentUrlStr: string): string {
  try {
    const isAbsolute = /^https?:\/\//i.test(currentUrlStr)
    const url = new URL(currentUrlStr, isAbsolute ? undefined : 'http://hierici.local')
    url.searchParams.delete('storymap')
    const qs = url.searchParams.toString()
    const pathAndQuery = `${url.pathname}${qs ? `?${qs}` : ''}${url.hash}`
    return isAbsolute ? `${url.origin}${pathAndQuery}` : pathAndQuery
  } catch {
    return currentUrlStr
  }
}

/**
 * Extrait et valide les coordonnées de caméra d'une étape de storymap
 */
export function getValidCameraTarget(
  step:
    | {
        camera_lat?: number | null
        camera_lng?: number | null
        lat?: number | null
        lng?: number | null
        camera_zoom?: number | null
        zoom?: number | null
        camera_bearing?: number | null
        bearing?: number | null
        camera_pitch?: number | null
        pitch?: number | null
      }
    | null
    | undefined,
  fallback: Partial<CameraTarget> = DEFAULT_CAMERA_FALLBACK
): CameraTarget {
  const fb: CameraTarget = {
    ...DEFAULT_CAMERA_FALLBACK,
    ...fallback,
  }

  if (!step) {
    return fb
  }

  const rawLat = step.camera_lat ?? step.lat
  const rawLng = step.camera_lng ?? step.lng
  const rawZoom = step.camera_zoom ?? step.zoom
  const rawBearing = step.camera_bearing ?? step.bearing
  const rawPitch = step.camera_pitch ?? step.pitch

  const lat =
    typeof rawLat === 'number' && !isNaN(rawLat)
      ? clamp(Number(rawLat.toFixed(6)), -90, 90)
      : fb.lat

  const lng =
    typeof rawLng === 'number' && !isNaN(rawLng)
      ? clamp(Number(rawLng.toFixed(6)), -180, 180)
      : fb.lng

  const zoom =
    typeof rawZoom === 'number' && !isNaN(rawZoom)
      ? clamp(Number(rawZoom.toFixed(2)), 0, 24)
      : fb.zoom

  const bearing =
    typeof rawBearing === 'number' && !isNaN(rawBearing)
      ? Number(normalizeBearing(rawBearing).toFixed(1))
      : fb.bearing

  const pitch =
    typeof rawPitch === 'number' && !isNaN(rawPitch)
      ? clamp(Number(rawPitch.toFixed(1)), 0, 85)
      : fb.pitch

  return {
    lat,
    lng,
    zoom,
    bearing: bearing === 360 ? 0 : bearing,
    pitch,
  }
}

/**
 * Calcule le pourcentage de progression de lecture (0 à 100)
 */
export function calculateStepProgress(currentIndex: number, totalSteps: number): number {
  if (totalSteps <= 0 || currentIndex < 0) return 0
  if (totalSteps === 1 || currentIndex >= totalSteps - 1) return 100
  const ratio = currentIndex / (totalSteps - 1)
  return Math.round(clamp(ratio * 100, 0, 100))
}

/**
 * Libellé du badge d'étape
 */
export function formatStepBadge(currentIndex: number, totalSteps: number): string {
  if (currentIndex < 0) return 'Introduction'
  if (totalSteps <= 0) return 'Étape 1'
  if (currentIndex >= totalSteps) return 'Conclusion'
  return `Chapitre ${currentIndex + 1} sur ${totalSteps}`
}

/**
 * Détermine si la lecture audio active doit être interrompue lors du changement d'étape
 */
export function shouldStopAudioOnStepChange(
  currentStepIndex: number,
  newStepIndex: number,
  hasActiveAudio: boolean
): boolean {
  return hasActiveAudio && currentStepIndex !== newStepIndex
}

/**
 * Formate une durée en secondes sous forme mm:ss
 */
export function formatAudioDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || isNaN(seconds) || seconds < 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`
}
