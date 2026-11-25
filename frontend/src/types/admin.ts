/**
 * Types pour la console d'administration générale (Story 5.3)
 */

export type BasemapType = 'xyz' | 'wms' | 'wmts' | 'vector'

export interface BasemapConfig {
  id: string
  name: string
  type: BasemapType
  url: string
  attribution?: string | null
  max_zoom?: number | null
  min_zoom?: number | null
  is_default: boolean
  layers?: string | null
  format?: string | null
}

export interface TerritoryAdmin {
  id: string
  slug: string
  name: string
  center_lat: number
  center_lng: number
  default_zoom: number
  basemaps: BasemapConfig[]
  created_at: string
}

export interface TerritoryUpdatePayload {
  name?: string
  center_lat?: number
  center_lng?: number
  default_zoom?: number
  basemaps?: BasemapConfig[]
}

export type UserRole = 'superadmin' | 'contributor'

export interface AdminUser {
  id: string
  email: string
  full_name: string
  role: UserRole
  territory_id: string | null
  is_active: boolean
  created_at: string
}

export interface AdminUserCreatePayload {
  email: string
  password: string
  full_name: string
  role?: UserRole
}

export interface AdminUserUpdatePayload {
  full_name?: string
  role?: UserRole
  is_active?: boolean
  password?: string
}

