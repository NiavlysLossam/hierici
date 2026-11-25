/**
 * Utilitaires géographiques et trigonométriques pour le calcul du cône de vue orienté
 * dans le référentiel WGS84 (EPSG:4326).
 */

export interface ViewConeProperties {
  bearing: number
  field_of_view: number
  distance: number
  center_lat: number
  center_lng: number
}

export type ViewConeFeature = GeoJSON.Feature<GeoJSON.Polygon, ViewConeProperties>

/**
 * Arrondit un nombre à un nombre donné de décimales (défaut : 6 décimales ~10 cm).
 */
export function roundCoordinate(val: number, decimals: number = 6): number {
  const factor = Math.pow(10, decimals)
  return Math.round(val * factor) / factor
}

/**
 * Normalise un azimut pour garantir un entier strict entre 0 et 359 degrés.
 * 0° = Nord, 90° = Est, 180° = Sud, 270° = Ouest.
 */
export function normalizeBearing(bearing: number): number {
  if (!Number.isFinite(bearing)) return 0
  const normalized = Math.round(((bearing % 360) + 360) % 360)
  return normalized === 360 ? 0 : normalized
}

/**
 * Borne l'ouverture angulaire (FOV) entre 10° et 120° (défaut : 60°).
 */
export function clampFov(fov: number): number {
  if (!Number.isFinite(fov)) return 60
  return Math.max(10, Math.min(120, Math.round(fov)))
}

/**
 * Calcule le point de destination géographique [longitude, latitude] à partir
 * d'un point d'origine, d'une distance en mètres et d'un cap en degrés.
 * Formule directe d'orthodromie (Haversine direct problem) sur sphère terrestre (R = 6 371 000 m).
 */
export function destinationPoint(
  lat: number,
  lng: number,
  distanceMeters: number,
  bearingDegrees: number
): [number, number] {
  const R = 6371000 // Rayon moyen de la Terre en mètres
  const dByR = distanceMeters / R
  const latRad = (lat * Math.PI) / 180
  const lngRad = (lng * Math.PI) / 180
  const bearingRad = (bearingDegrees * Math.PI) / 180

  const sinLat = Math.sin(latRad) * Math.cos(dByR) +
    Math.cos(latRad) * Math.sin(dByR) * Math.cos(bearingRad)
  const destLatRad = Math.asin(Math.max(-1, Math.min(1, sinLat)))

  const destLngRad =
    lngRad +
    Math.atan2(
      Math.sin(bearingRad) * Math.sin(dByR) * Math.cos(latRad),
      Math.cos(dByR) - Math.sin(latRad) * Math.sin(destLatRad)
    )

  const destLat = (destLatRad * 180) / Math.PI
  const destLng = (((destLngRad * 180) / Math.PI + 540) % 360) - 180

  return [roundCoordinate(destLng, 6), roundCoordinate(destLat, 6)]
}

/**
 * Génère le polygone GeoJSON (Feature<Polygon>) représentant le cône de vue projeté.
 * 
 * Le polygone commence au point de prise de vue [originLng, originLat],
 * trace un arc de cercle discrétisé entre (bearing - fov/2) et (bearing + fov/2)
 * à une distance métrique donnée, puis se referme sur le point d'origine.
 * 
 * Les coordonnées retournées suivent strictement la convention GeoJSON [longitude, latitude].
 */
export function createViewConePolygon(
  lng: number,
  lat: number,
  bearing: number = 0,
  fov: number = 60,
  distanceMeters: number = 160,
  stepDegrees: number = 2
): ViewConeFeature {
  const normBearing = normalizeBearing(bearing)
  const normFov = clampFov(fov)
  const safeDistance = Math.max(20, Math.min(2000, typeof distanceMeters === 'number' && !isNaN(distanceMeters) ? distanceMeters : 160))
  const origin: [number, number] = [roundCoordinate(lng, 6), roundCoordinate(lat, 6)]

  const halfFov = normFov / 2
  const startAngle = normBearing - halfFov
  const endAngle = normBearing + halfFov

  const step = stepDegrees > 0 ? stepDegrees : 2
  const arcPoints: [number, number][] = []

  // Échantillonnage régulier de l'arc
  for (let angle = startAngle; angle < endAngle; angle += step) {
    arcPoints.push(destinationPoint(origin[1], origin[0], safeDistance, angle))
  }
  // Point final précis de l'arc
  arcPoints.push(destinationPoint(origin[1], origin[0], safeDistance, endAngle))

  // Construction de l'anneau linéaire fermé
  const coordinates: [number, number][] = [origin, ...arcPoints, origin]

  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [coordinates],
    },
    properties: {
      bearing: normBearing,
      field_of_view: normFov,
      distance: safeDistance,
      center_lat: origin[1],
      center_lng: origin[0],
    },
  }
}

/**
 * Retourne une FeatureCollection GeoJSON vide.
 */
export function createEmptyFeatureCollection(): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: [],
  }
}
