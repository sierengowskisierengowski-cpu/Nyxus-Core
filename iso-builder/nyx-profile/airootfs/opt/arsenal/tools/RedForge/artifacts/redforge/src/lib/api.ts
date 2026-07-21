import { customFetch } from '@workspace/api-client-react';

export const directApi = {
  notes: {
    create: (data: any) => customFetch('/api/notes', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: any) => customFetch(`/api/notes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: number) => customFetch(`/api/notes/${id}`, { method: 'DELETE' }),
    pin: (id: number) => customFetch(`/api/notes/${id}/pin`, { method: 'POST' }),
    favorite: (id: number) => customFetch(`/api/notes/${id}/favorite`, { method: 'POST' }),
    archive: (id: number) => customFetch(`/api/notes/${id}/archive`, { method: 'POST' }),
    duplicate: (id: number) => customFetch(`/api/notes/${id}/duplicate`, { method: 'POST' }),
    restore: (id: number, versionId: number) => customFetch(`/api/notes/${id}/restore/${versionId}`, { method: 'POST' }),
  },
  notebooks: {
    create: (data: any) => customFetch('/api/notebooks', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: any) => customFetch(`/api/notebooks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: number) => customFetch(`/api/notebooks/${id}`, { method: 'DELETE' }),
  },
  settings: {
    update: (data: any) => customFetch('/api/settings', { method: 'PATCH', body: JSON.stringify(data) }),
    changePassword: (data: any) => customFetch('/api/settings/change-password', { method: 'POST', body: JSON.stringify(data) }),
  },
  missions: {
    giveup: (id: number) => customFetch(`/api/missions/${id}/giveup`, { method: 'POST' }),
    delete: (id: number) => customFetch(`/api/missions/${id}`, { method: 'DELETE' }),
  }
};
