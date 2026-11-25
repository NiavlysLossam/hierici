import type { Photo } from './photo'

export type StorymapStatus = 'draft' | 'published'

export interface StorymapStep {
  id: string
  storymap_id?: string | null
  photo_id?: string | null
  step_order: number
  title: string
  content_markdown?: string | null
  audio_file_path?: string | null
  audio_url?: string | null
  camera_lat: number
  camera_lng: number
  camera_zoom: number
  camera_bearing: number
  camera_pitch: number
  lat?: number
  lng?: number
  zoom?: number
  bearing?: number
  pitch?: number
  created_at?: string
  updated_at?: string
  photo?: Photo | null
}

export interface StorymapStepCreatePayload {
  photo_id?: string | null
  step_order?: number
  title: string
  content_markdown?: string | null
  audio_file_path?: string | null
  camera_lat: number
  camera_lng: number
  camera_zoom?: number
  camera_bearing?: number
  camera_pitch?: number
  lat?: number
  lng?: number
  zoom?: number
  bearing?: number
  pitch?: number
}

export interface StorymapStepUpdatePayload {
  photo_id?: string | null
  step_order?: number
  title?: string
  content_markdown?: string | null
  audio_file_path?: string | null
  camera_lat?: number
  camera_lng?: number
  camera_zoom?: number
  camera_bearing?: number
  camera_pitch?: number
  lat?: number
  lng?: number
  zoom?: number
  bearing?: number
  pitch?: number
}

export interface Storymap {
  id: string
  territory_id: string
  author_user_id?: string | null
  slug: string
  title: string
  summary?: string | null
  cover_image_path?: string | null
  cover_image_url?: string | null
  status: StorymapStatus
  created_at: string
  updated_at: string
  steps: StorymapStep[]
  steps_count?: number
}

export interface StorymapCreatePayload {
  title: string
  summary?: string | null
  slug?: string | null
  cover_image_path?: string | null
  status?: StorymapStatus
  territory_id?: string | null
  steps?: StorymapStepCreatePayload[]
}

export interface StorymapUpdatePayload {
  title?: string
  summary?: string | null
  slug?: string | null
  cover_image_path?: string | null
  status?: StorymapStatus
  territory_id?: string | null
}

export interface StorymapReorderPayload {
  step_ids: string[]
}

export interface StorymapListResponse {
  items: Storymap[]
  total: number
  page: number
  page_size: number
  pages: number
}
