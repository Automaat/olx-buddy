import axios from 'axios'
import type {
  Listing,
  AddListingRequest,
  GenerateDescriptionResponse,
  ImageUploadResponse,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const listingsApi = {
  async getAll(params?: {
    skip?: number
    limit?: number
    platform?: string
    status?: string
  }): Promise<Listing[]> {
    const response = await api.get('/listings', { params })
    return response.data
  },

  async getById(id: number): Promise<Listing> {
    const response = await api.get(`/listings/${id}`)
    return response.data
  },

  async addByUrl(data: AddListingRequest): Promise<Listing> {
    const response = await api.post('/listings/add-by-url', data)
    return response.data
  },

  async update(id: number, data: Partial<Listing>): Promise<Listing> {
    const response = await api.patch(`/listings/${id}`, data)
    return response.data
  },

  async markSold(
    id: number,
    data: { sale_price: number; sold_at?: string }
  ): Promise<Listing> {
    const response = await api.post(`/listings/${id}/mark-sold`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/listings/${id}`)
  },
}

export const generateApi = {
  async uploadImages(files: File[]): Promise<ImageUploadResponse> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })

    const response = await api.post('/generate/upload-images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async generateDescription(data: {
    category: string
    image_paths: string
    brand?: string
    condition?: string
    size?: string
    additional_details?: string
    include_price_suggestion?: boolean
  }): Promise<GenerateDescriptionResponse> {
    const formData = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value.toString())
      }
    })

    const response = await api.post('/generate/description', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async getCategories(): Promise<string[]> {
    const response = await api.get('/generate/categories')
    return response.data.categories
  },
}

export default api
