/**
 * Utilitaires partagés pour la fiche détaillée et la visionneuse plein écran (Story 3.3)
 */

/**
 * Extrait l'identifiant photo d'un query string d'URL (ou de window.location.search par défaut)
 */
export function getUrlPhotoId(searchString?: string): string | null {
  const query =
    searchString !== undefined
      ? searchString
      : typeof window !== 'undefined'
        ? window.location.search
        : ''
  const params = new URLSearchParams(query)
  return params.get('photo')
}

/**
 * Calcule la nouvelle URL avec ou sans le paramètre photo
 */
export function computePhotoUrl(currentUrlStr: string, photoId: string | null): string {
  const url = new URL(currentUrlStr)
  if (photoId) {
    url.searchParams.set('photo', photoId)
  } else {
    url.searchParams.delete('photo')
  }
  return url.pathname + (url.search ? url.search : '') + url.hash
}

/**
 * Contraint une valeur de zoom entre les bornes autorisées
 */
export function clampZoom(val: number, min = 0.5, max = 6.0): number {
  return Math.min(Math.max(val, min), max)
}

/**
 * Calcule le nouveau zoom et les translations de pan pour centrer le zoom sur le curseur
 */
export function calculateZoomToCursor(
  currentZoom: number,
  factor: number,
  mouseX: number,
  mouseY: number,
  currentPanX: number,
  currentPanY: number,
  min = 0.5,
  max = 6.0
): { zoom: number; panX: number; panY: number } {
  const newZoom = clampZoom(currentZoom * factor, min, max)
  if (newZoom === currentZoom) {
    return { zoom: currentZoom, panX: currentPanX, panY: currentPanY }
  }
  const ratio = newZoom / currentZoom
  const newPanX = mouseX - (mouseX - currentPanX) * ratio
  const newPanY = mouseY - (mouseY - currentPanY) * ratio
  return {
    zoom: Number(newZoom.toFixed(3)),
    panX: Number(newPanX.toFixed(2)),
    panY: Number(newPanY.toFixed(2)),
  }
}

/**
 * Résout l'URL de l'image optimisée pour le volet (display en priorité, fallback sur thumb)
 */
export function resolveDisplayImageUrl(photo: any): string | null {
  if (!photo) return null
  return (
    photo.image_display_url ||
    photo.display_url ||
    photo.image_thumb_url ||
    photo.thumb_url ||
    photo.image_original_url ||
    photo.original_url ||
    null
  )
}

/**
 * Résout l'URL de l'image haute définition pour la visionneuse plein écran
 * (original en priorité, fallback sur display puis thumb)
 */
export function resolveLightboxImageUrl(photo: any): string {
  if (!photo) return ''
  return (
    photo.image_original_url ||
    photo.original_url ||
    photo.image_display_url ||
    photo.display_url ||
    photo.image_thumb_url ||
    photo.thumb_url ||
    ''
  )
}
