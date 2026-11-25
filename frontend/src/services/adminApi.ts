import { request } from './api'
import type {
  TerritoryAdmin,
  TerritoryUpdatePayload,
  AdminUser,
  AdminUserCreatePayload,
  AdminUserUpdatePayload,
} from '@/types/admin'

export const adminApi = {
  /**
   * Configuration du territoire (cadrage, nom, fonds de carte)
   */
  async getTerritory(): Promise<TerritoryAdmin> {
    return request<TerritoryAdmin>('/api/v1/admin/territory')
  },

  async updateTerritory(payload: TerritoryUpdatePayload): Promise<TerritoryAdmin> {
    return request<TerritoryAdmin>('/api/v1/admin/territory', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Gestion des utilisateurs contributeurs
   */
  async listUsers(): Promise<AdminUser[]> {
    return request<AdminUser[]>('/api/v1/admin/users')
  },

  async createUser(payload: AdminUserCreatePayload): Promise<AdminUser> {
    return request<AdminUser>('/api/v1/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async updateUser(userId: string, payload: AdminUserUpdatePayload): Promise<AdminUser> {
    return request<AdminUser>(`/api/v1/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async deleteUser(userId: string): Promise<void> {
    await request<void>(`/api/v1/admin/users/${userId}`, {
      method: 'DELETE',
    })
  },
}

