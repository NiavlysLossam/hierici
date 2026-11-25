/**
 * Utilitaires purs pour le Catalogue Public des Récits et la Navigation Territoriale (Story 4.4)
 */

import type { Storymap } from '../types/storymap'

export type StorymapSortOption = 'recent' | 'steps' | 'title'

export interface StorymapFilterOptions {
  search?: string
  hasAudioOnly?: boolean
  sortBy?: StorymapSortOption
}

/**
 * Normalise une chaîne en supprimant les accents (diacritiques) et en minuscules
 */
export function normalizeSearchString(val: string | null | undefined): string {
  if (!val) return ''
  return val
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
}

/**
 * Estime le temps de lecture / visite d'une storymap selon son nombre d'étapes
 * (environ 2.5 minutes par étape : lecture, observation des clichés et transition de carte)
 */
export function estimateReadingTime(stepsCount: number, minutesPerStep = 2.5): number {
  if (isNaN(stepsCount) || stepsCount <= 0) return 2
  const estimated = Math.ceil(stepsCount * minutesPerStep)
  return Math.max(2, estimated)
}

/**
 * Formate le temps de visite estimé en libellé convivial
 */
export function formatReadingDuration(minutes: number): string {
  if (isNaN(minutes) || minutes <= 0) return '~2 min de visite'
  return `~${minutes} min de visite`
}

/**
 * Détermine si une storymap contient au moins une capsule sonore
 */
export function hasAudioContent(storymap: Storymap | null | undefined): boolean {
  if (!storymap || !storymap.steps || !Array.isArray(storymap.steps)) return false
  return storymap.steps.some((step) => step && Boolean(step.audio_url || step.audio_file_path))
}

/**
 * Filtre et ordonne la liste des storymaps côté client
 */
export function filterAndSortStorymaps(
  items: Storymap[],
  options: StorymapFilterOptions = {}
): Storymap[] {
  if (!Array.isArray(items)) return []

  let filtered = [...items]

  // 1. Filtrage par recherche textuelle multi-termes et insensible aux diacritiques (accents)
  if (options.search && options.search.trim()) {
    const rawSearch = normalizeSearchString(options.search)
    const tokens = rawSearch.split(/\s+/).filter(Boolean)

    if (tokens.length > 0) {
      filtered = filtered.filter((story) => {
        const titleNormalized = normalizeSearchString(story.title)
        const summaryNormalized = normalizeSearchString(story.summary)

        // Chaque mot-clé recherché doit apparaître soit dans le titre soit dans le résumé
        return tokens.every(
          (token) => titleNormalized.includes(token) || summaryNormalized.includes(token)
        )
      })
    }
  }

  // 2. Filtrage par présence audio
  if (options.hasAudioOnly) {
    filtered = filtered.filter(hasAudioContent)
  }

  // 3. Tri
  const sortBy = options.sortBy || 'recent'
  filtered.sort((a, b) => {
    const titleA = a?.title ?? ''
    const titleB = b?.title ?? ''

    if (sortBy === 'steps') {
      const countA = a.steps_count ?? a.steps?.length ?? 0
      const countB = b.steps_count ?? b.steps?.length ?? 0
      if (countB !== countA) return countB - countA
      return titleA.localeCompare(titleB, 'fr')
    }

    if (sortBy === 'title') {
      return titleA.localeCompare(titleB, 'fr')
    }

    // Défaut : recent (plus récents en premier)
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
    return timeB - timeA
  })

  return filtered
}
