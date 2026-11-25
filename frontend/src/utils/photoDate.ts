/**
 * Formate l'affichage public d'une année de prise de vue
 * selon son degré de certitude archivistique.
 */
export function formatPhotoYear(year: number | null | undefined, isExactYear: boolean = true): string | null {
  if (year === null || year === undefined || isNaN(year)) {
    return null
  }
  return isExactYear ? `${year}` : `Vers ${year}`
}

