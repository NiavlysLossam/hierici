import type {
  Photo,
  PhotoCreatePayload,
  PhotoUpdatePayload,
  PhotoListResponse,
  PhotoUploadResponse,
  PhotoStatus,
  PhotoGeoJsonFeatureCollection,
  MetadataSuggestionsResponse,
} from '@/types/photo'
import type {
  Storymap,
  StorymapStep,
  StorymapStatus,
  StorymapCreatePayload,
  StorymapUpdatePayload,
  StorymapStepCreatePayload,
  StorymapStepUpdatePayload,
  StorymapListResponse,
} from '@/types/storymap'
import type {
  TerritoryAdmin,
  TerritoryUpdatePayload,
  AdminUser,
  AdminUserCreatePayload,
  AdminUserUpdatePayload,
} from '@/types/admin'

const TOKEN_STORAGE_KEY = 'hierici_access_token'

export class ApiError extends Error {
  code: string
  status: number
  details?: any

  constructor(message: string, code = 'API_ERROR', status = 500, details?: any) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setAuthToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }
}

export function hasAuthToken(): boolean {
  return !!getAuthToken()
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }

  const token = getAuthToken()
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Si le body n'est pas un FormData, on ajoute Content-Type: application/json si non défini
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  })

  if (response.status === 204) {
    return {} as T
  }

  let data: any = null
  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    let message = `Erreur HTTP ${response.status}`
    let code = 'HTTP_ERROR'
    let details = undefined

    if (data?.error) {
      code = data.error.code || code
      message = data.error.message || message
      details = data.error.details
    } else if (data?.detail) {
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (data.detail?.error) {
        code = data.detail.error.code || code
        message = data.detail.error.message || message
        details = data.detail.error.details
      } else if (Array.isArray(data.detail)) {
        // FastAPI validation errors
        message = data.detail.map((err: any) => `${err.loc?.join('.') || 'champ'}: ${err.msg}`).join(', ')
      }
    }

    throw new ApiError(message, code, response.status, details)
  }

  return data as T
}

export const photoApi = {
  /**
   * Connexion avec email et mot de passe
   */
  async login(email: string, password: string): Promise<{ access_token: string; user: any }> {
    const res = await request<{ access_token: string; token_type: string; user: any }>(
      '/api/v1/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    )
    setAuthToken(res.access_token)
    return res
  },

  /**
   * Récupère le profil de l'utilisateur connecté
   */
  async getMe(): Promise<any> {
    return request<any>('/api/v1/auth/me')
  },

  /**
   * Liste paginée des photographies
   */
  async listPhotos(params?: {
    page?: number
    page_size?: number
    status?: PhotoStatus
    search?: string
    territory_id?: string
  }): Promise<PhotoListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set('page', params.page.toString())
    if (params?.page_size) query.set('page_size', params.page_size.toString())
    if (params?.status) query.set('status', params.status)
    if (params?.search && params.search.trim()) query.set('search', params.search.trim())
    if (params?.territory_id) query.set('territory_id', params.territory_id)

    const qs = query.toString()
    return request<PhotoListResponse>(`/api/v1/admin/photos${qs ? `?${qs}` : ''}`)
  },

  /**
   * Consultation du détail d'une photographie
   */
  async getPhoto(id: string): Promise<Photo> {
    return request<Photo>(`/api/v1/admin/photos/${id}`)
  },

  /**
   * Récupération des suggestions d'archives et photographes du territoire
   */
  async getMetadataSuggestions(): Promise<MetadataSuggestionsResponse> {
    return request<MetadataSuggestionsResponse>('/api/v1/admin/photos/metadata-suggestions')
  },

  /**
   * Création d'une nouvelle fiche photo
   */
  async createPhoto(payload: PhotoCreatePayload): Promise<Photo> {
    return request<Photo>('/api/v1/admin/photos', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Mise à jour d'une fiche photo existante
   */
  async updatePhoto(id: string, payload: PhotoUpdatePayload): Promise<Photo> {
    return request<Photo>(`/api/v1/admin/photos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Suppression d'une fiche photo et de ses médias
   */
  async deletePhoto(id: string): Promise<void> {
    await request<void>(`/api/v1/admin/photos/${id}`, {
      method: 'DELETE',
    })
  },

  /**
   * Téléversement d'image pour une photo existante
   */
  async uploadPhotoImage(photoId: string, file: File): Promise<PhotoUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    return request<PhotoUploadResponse>(`/api/v1/admin/photos/${photoId}/upload`, {
      method: 'POST',
      body: formData,
    })
  },

  /**
   * Téléversement direct créant une nouvelle photo avec image
   */
  async uploadPhotoDirect(file: File, title?: string): Promise<PhotoUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    if (title && title.trim()) {
      formData.append('title', title.trim())
    }

    return request<PhotoUploadResponse>('/api/v1/admin/photos/upload', {
      method: 'POST',
      body: formData,
    })
  },

  /**
   * Récupération du territoire actif
   */
  async getCurrentTerritory(): Promise<{
    id: string
    slug: string
    name: string
    center_lat: number
    center_lng: number
    default_zoom: number
  }> {
    return request('/api/v1/territory/current')
  },

  /**
   * Health check de l'API
   */
  async getHealth(): Promise<{ status: string; database: string }> {
    return request('/api/health')
  },

  /**
   * Récupère la collection GeoJSON des photos publiées du territoire actif
   */
  async getPublicPhotos(
    params?: {
      search?: string
      year_min?: number
      year_max?: number
    },
    signal?: AbortSignal
  ): Promise<PhotoGeoJsonFeatureCollection> {
    const query = new URLSearchParams()
    if (params?.search && params.search.trim()) query.set('search', params.search.trim())
    if (params?.year_min !== undefined && params.year_min !== null) {
      query.set('year_min', params.year_min.toString())
    }
    if (params?.year_max !== undefined && params.year_max !== null) {
      query.set('year_max', params.year_max.toString())
    }

    const qs = query.toString()
    return request<PhotoGeoJsonFeatureCollection>(`/api/v1/photos${qs ? `?${qs}` : ''}`, { signal })
  },

  /**
   * Récupère la fiche détaillée d'une photo publique
   */
  async getPublicPhoto(id: string): Promise<Photo> {
    return request<Photo>(`/api/v1/photos/${id}`)
  },
}

export const storymapApi = {
  /**
   * Liste paginée des storymaps du territoire
   */
  async listStorymaps(params?: {
    page?: number
    page_size?: number
    status?: StorymapStatus
    search?: string
    territory_id?: string
  }): Promise<StorymapListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set('page', params.page.toString())
    if (params?.page_size) query.set('page_size', params.page_size.toString())
    if (params?.status) query.set('status', params.status)
    if (params?.search && params.search.trim()) query.set('search', params.search.trim())
    if (params?.territory_id) query.set('territory_id', params.territory_id)

    const qs = query.toString()
    return request<StorymapListResponse>(`/api/v1/admin/storymaps${qs ? `?${qs}` : ''}`)
  },

  /**
   * Consultation du détail d'une storymap avec ses étapes ordonnées
   */
  async getStorymap(id: string): Promise<Storymap> {
    return request<Storymap>(`/api/v1/admin/storymaps/${id}`)
  },

  /**
   * Création d'une nouvelle storymap
   */
  async createStorymap(payload: StorymapCreatePayload): Promise<Storymap> {
    return request<Storymap>('/api/v1/admin/storymaps', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Mise à jour des métadonnées d'une storymap
   */
  async updateStorymap(id: string, payload: StorymapUpdatePayload): Promise<Storymap> {
    return request<Storymap>(`/api/v1/admin/storymaps/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Suppression définitive d'une storymap et cascade sur ses étapes
   */
  async deleteStorymap(id: string): Promise<void> {
    await request<void>(`/api/v1/admin/storymaps/${id}`, {
      method: 'DELETE',
    })
  },

  /**
   * Téléversement et association d'une image de couverture
   */
  async uploadCover(id: string, file: File): Promise<Storymap> {
    const formData = new FormData()
    formData.append('file', file)
    return request<Storymap>(`/api/v1/admin/storymaps/${id}/cover`, {
      method: 'POST',
      body: formData,
    })
  },

  /**
   * Suppression de l'image de couverture
   */
  async deleteCover(id: string): Promise<Storymap> {
    return request<Storymap>(`/api/v1/admin/storymaps/${id}/cover`, {
      method: 'DELETE',
    })
  },

  /**
   * Ajout d'une étape / chapitre à une storymap
   */
  async addStep(id: string, payload: StorymapStepCreatePayload): Promise<StorymapStep> {
    return request<StorymapStep>(`/api/v1/admin/storymaps/${id}/steps`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Mise à jour d'un chapitre / étape
   */
  async updateStep(id: string, stepId: string, payload: StorymapStepUpdatePayload): Promise<StorymapStep> {
    return request<StorymapStep>(`/api/v1/admin/storymaps/${id}/steps/${stepId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Suppression d'une étape d'une storymap
   */
  async deleteStep(id: string, stepId: string): Promise<void> {
    await request<void>(`/api/v1/admin/storymaps/${id}/steps/${stepId}`, {
      method: 'DELETE',
    })
  },

  /**
   * Réordonnancement atomique de l'ensemble des étapes
   */
  async reorderSteps(id: string, stepIds: string[]): Promise<Storymap> {
    return request<Storymap>(`/api/v1/admin/storymaps/${id}/steps/reorder`, {
      method: 'PUT',
      body: JSON.stringify({ step_ids: stepIds }),
    })
  },

  /**
   * Téléversement d'un document sonore (MP3, etc.) pour une étape
   */
  async uploadStepAudio(id: string, stepId: string, file: File): Promise<StorymapStep> {
    const formData = new FormData()
    formData.append('file', file)
    return request<StorymapStep>(`/api/v1/admin/storymaps/${id}/steps/${stepId}/audio`, {
      method: 'POST',
      body: formData,
    })
  },

  /**
   * Suppression du fichier audio d'une étape
   */
  async deleteStepAudio(id: string, stepId: string): Promise<StorymapStep> {
    return request<StorymapStep>(`/api/v1/admin/storymaps/${id}/steps/${stepId}/audio`, {
      method: 'DELETE',
    })
  },

  /**
   * Consultation publique du catalogue des récits publiés du territoire actif
   */
  async listPublicStorymaps(
    params?: {
      page?: number
      page_size?: number
      search?: string
    },
    signal?: AbortSignal
  ): Promise<StorymapListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set('page', params.page.toString())
    if (params?.page_size) query.set('page_size', params.page_size.toString())
    if (params?.search && params.search.trim()) query.set('search', params.search.trim())

    const qs = query.toString()
    return request<StorymapListResponse>(`/api/v1/storymaps${qs ? `?${qs}` : ''}`, { signal })
  },

  /**
   * Consultation publique d'un récit publié par son slug
   */
  async getPublicStorymap(slug: string, signal?: AbortSignal): Promise<Storymap> {
    return request<Storymap>(`/api/v1/storymaps/${encodeURIComponent(slug.trim())}`, { signal })
  },

  /**
   * Administration Générale : Configuration du territoire (Story 5.3)
   */
  async getAdminTerritory(): Promise<TerritoryAdmin> {
    return request<TerritoryAdmin>('/api/v1/admin/territory')
  },

  async updateAdminTerritory(payload: TerritoryUpdatePayload): Promise<TerritoryAdmin> {
    return request<TerritoryAdmin>('/api/v1/admin/territory', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Administration Générale : Gestion des contributeurs (Story 5.3)
   */
  async listAdminUsers(): Promise<AdminUser[]> {
    return request<AdminUser[]>('/api/v1/admin/users')
  },

  async createAdminUser(payload: AdminUserCreatePayload): Promise<AdminUser> {
    return request<AdminUser>('/api/v1/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async updateAdminUser(userId: string, payload: AdminUserUpdatePayload): Promise<AdminUser> {
    return request<AdminUser>(`/api/v1/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async deleteAdminUser(userId: string): Promise<void> {
    await request<void>(`/api/v1/admin/users/${userId}`, {
      method: 'DELETE',
    })
  },
}

