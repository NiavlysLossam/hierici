/**
 * Utilitaires de routage d'état URL et de synchronisation des onglets pour HierIci.
 */

export type AppTab = 'accueil' | 'decouverte' | 'recits' | 'studio'

export interface NavigationState {
  tab: AppTab
  photoId: string | null
  storymapSlug: string | null
}

/**
 * Résout l'onglet actif et les entités ciblées à partir d'une URL ou d'une chaîne de requête.
 */
export function resolveNavigationState(urlOrSearch: string | Location | URL): NavigationState {
  let searchParams: URLSearchParams

  if (typeof urlOrSearch === 'string') {
    if (urlOrSearch.includes('?')) {
      const qs = urlOrSearch.split('?')[1].split('#')[0]
      searchParams = new URLSearchParams(qs)
    } else if (urlOrSearch.startsWith('tab=') || urlOrSearch.startsWith('photo=') || urlOrSearch.startsWith('storymap=')) {
      searchParams = new URLSearchParams(urlOrSearch)
    } else {
      searchParams = new URLSearchParams()
    }
  } else if (urlOrSearch instanceof URL || ('search' in urlOrSearch && typeof urlOrSearch.search === 'string')) {
    searchParams = new URLSearchParams(urlOrSearch.search)
  } else {
    searchParams = new URLSearchParams()
  }

  const rawTab = searchParams.get('tab')
  const photoId = searchParams.get('photo') || null
  const storymapSlug = searchParams.get('storymap') || null

  let tab: AppTab = 'accueil'

  if (rawTab === 'decouverte' || rawTab === 'recits' || rawTab === 'studio' || rawTab === 'accueil') {
    tab = rawTab
  } else if (photoId) {
    tab = 'decouverte'
  } else if (storymapSlug) {
    tab = 'recits'
  } else {
    tab = 'accueil'
  }

  // Si une photo est demandée sans onglet explicite contradictoire, on s'assure d'ouvrir la carte
  if (photoId && (!rawTab || rawTab === 'decouverte')) {
    tab = 'decouverte'
  }

  // Si un récit est demandé sans onglet explicite contradictoire, on s'assure d'ouvrir les récits
  if (storymapSlug && (!rawTab || rawTab === 'recits')) {
    tab = 'recits'
  }

  return {
    tab,
    photoId,
    storymapSlug,
  }
}

/**
 * Calcule la nouvelle URL lors d'un changement d'onglet en nettoyant les paramètres obsolètes.
 */
export function computeTabUrl(currentUrl: string, targetTab: AppTab): string {
  const url = new URL(currentUrl, 'http://localhost')

  // Nettoyage des paramètres contextuels d'autres onglets
  if (targetTab !== 'decouverte') {
    url.searchParams.delete('photo')
  }
  if (targetTab !== 'recits') {
    url.searchParams.delete('storymap')
  }

  // Gestion du paramètre tab
  if (targetTab === 'accueil') {
    url.searchParams.delete('tab')
  } else {
    url.searchParams.set('tab', targetTab)
  }

  const qs = url.searchParams.toString()
  return `${url.pathname}${qs ? `?${qs}` : ''}${url.hash}`
}

