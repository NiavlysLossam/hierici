export type PhotoStatus = 'draft' | 'published'

export type PhotoLicense =
  | 'Domaine Public'
  | 'Licence Ouverte (Etalab)'
  | 'Creative Commons (BY)'
  | 'Creative Commons (BY-SA)'
  | 'Tous droits réservés'

export const PHOTO_LICENSES: { value: PhotoLicense; label: string; description: string }[] = [
  {
    value: 'Domaine Public',
    label: 'Domaine Public',
    description: 'Œuvre libre de droits patrimoniaux, réutilisation sans restriction.',
  },
  {
    value: 'Licence Ouverte (Etalab)',
    label: 'Licence Ouverte (Etalab)',
    description: 'Réutilisation libre sous réserve de mentionner la source et la date.',
  },
  {
    value: 'Creative Commons (BY)',
    label: 'Creative Commons (BY)',
    description: 'Attribution obligatoire, modifications et usages commerciaux autorisés.',
  },
  {
    value: 'Creative Commons (BY-SA)',
    label: 'Creative Commons (BY-SA)',
    description: 'Attribution et partage dans les mêmes conditions.',
  },
  {
    value: 'Tous droits réservés',
    label: 'Tous droits réservés',
    description: 'Diffusion sous autorisation exclusive du titulaire des droits.',
  },
]

export interface Photo {
  id: string
  territory_id: string
  author_user_id?: string | null
  title: string
  description?: string | null
  photographer?: string | null
  year_taken?: number | null
  year?: number | null
  is_exact_year?: boolean
  date_exact?: string | null
  period_label?: string | null
  archive_source?: string | null
  archive_ref?: string | null
  archive_reference?: string | null
  original_source_url?: string | null
  source_url?: string | null
  license?: PhotoLicense | string | null
  latitude?: number | null
  longitude?: number | null
  bearing?: number | null
  field_of_view?: number
  view_distance?: number
  file_original_path?: string | null
  file_display_path?: string | null
  file_thumb_path?: string | null
  original_url?: string | null
  display_url?: string | null
  thumb_url?: string | null
  image_original_url?: string | null
  image_display_url?: string | null
  image_thumb_url?: string | null
  status: PhotoStatus
  created_at: string
  updated_at: string
  location?: {
    type: 'Point'
    coordinates: [number, number]
  } | null
}

export interface PhotoCreatePayload {
  title: string
  description?: string | null
  photographer?: string | null
  year_taken?: number | null
  is_exact_year?: boolean
  date_exact?: string | null
  period_label?: string | null
  archive_source?: string | null
  archive_ref?: string | null
  original_source_url?: string | null
  license?: string | null
  latitude?: number | null
  longitude?: number | null
  bearing?: number | null
  field_of_view?: number
  view_distance?: number
  status?: PhotoStatus
  territory_id?: string | null
  file_original_path?: string | null
  file_display_path?: string | null
  file_thumb_path?: string | null
}

export interface PhotoUpdatePayload {
  title?: string
  description?: string | null
  photographer?: string | null
  year_taken?: number | null
  is_exact_year?: boolean
  date_exact?: string | null
  period_label?: string | null
  archive_source?: string | null
  archive_ref?: string | null
  original_source_url?: string | null
  license?: string | null
  latitude?: number | null
  longitude?: number | null
  bearing?: number | null
  field_of_view?: number
  view_distance?: number
  status?: PhotoStatus
  territory_id?: string | null
}

export interface PhotoListResponse {
  items: Photo[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface PhotoUploadResponse {
  photo_id: string
  file_original_path: string
  file_display_path: string
  file_thumb_path: string
  original_url: string
  display_url: string
  thumb_url: string
  width: number
  height: number
  photo?: Photo | null
}

export interface ApiProblemDetails {
  error: {
    code: string
    message: string
    details?: Record<string, any>
  }
}

export interface PhotoGeoJsonProperties {
  id: string
  title: string
  description?: string | null
  photographer?: string | null
  year_taken?: number | null
  is_exact_year?: boolean
  date_exact?: string | null
  period_label?: string | null
  archive_source?: string | null
  archive_ref?: string | null
  original_source_url?: string | null
  license?: string | null
  bearing?: number | null
  field_of_view: number
  view_distance?: number
  image_thumb_url?: string | null
  image_display_url?: string | null
  image_original_url?: string | null
  created_at: string
  updated_at: string
}

export interface MetadataSuggestionsResponse {
  photographers: string[]
  archive_sources: string[]
}

export interface PhotoGeoJsonFeature {
  type: 'Feature'
  id: string
  geometry: {
    type: 'Point'
    coordinates: [number, number]
  }
  properties: PhotoGeoJsonProperties
}

export interface PhotoGeoJsonFeatureCollection {
  type: 'FeatureCollection'
  features: PhotoGeoJsonFeature[]
}
