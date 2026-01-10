import axios from 'axios'
import type {
  Listing,
  AddListingRequest,
  GenerateDescriptionResponse,
  ImageUploadResponse,
  AnalyticsSummary,
  SalesDataPoint,
  CategoryStat,
  BrandStat,
  TopItem,
  InventoryBreakdown,
  CompetitorPrice,
  PriceHistoryPoint,
  ScheduledJob,
  JobExecution,
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

export const analyticsApi = {
  async getSummary(): Promise<AnalyticsSummary> {
    const response = await api.get('/analytics/summary')
    return response.data
  },

  async getSalesOverTime(params?: {
    start_date?: string
    end_date?: string
    granularity?: 'day' | 'week' | 'month'
  }): Promise<SalesDataPoint[]> {
    const response = await api.get('/analytics/sales-over-time', { params })
    return response.data
  },

  async getBestSellers(params?: {
    start_date?: string
    end_date?: string
    limit?: number
  }): Promise<{
    top_categories: CategoryStat[]
    top_brands: BrandStat[]
    most_profitable: TopItem[]
    fastest_selling: TopItem[]
  }> {
    const response = await api.get('/analytics/best-sellers', { params })
    return response.data
  },

  async getInventoryValue(): Promise<InventoryBreakdown[]> {
    const response = await api.get('/analytics/inventory-value')
    return response.data
  },

  async getPriceMonitoring(listingId: number): Promise<CompetitorPrice[]> {
    const response = await api.get(`/analytics/price-monitoring/${listingId}`)
    return response.data
  },

  async getPriceHistory(listingId: number): Promise<PriceHistoryPoint[]> {
    const response = await api.get(`/analytics/price-monitoring/${listingId}/history`)
    return response.data
  },
}

export const schedulerApi = {
  async getJobs(): Promise<ScheduledJob[]> {
    const response = await api.get('/scheduler/jobs')
    return response.data
  },

  async getJobHistory(jobId: string): Promise<JobExecution[]> {
    const response = await api.get(`/scheduler/jobs/${jobId}/history`)
    return response.data
  },

  async getAllHistory(params?: {
    limit?: number
    success_only?: boolean
  }): Promise<JobExecution[]> {
    const response = await api.get('/scheduler/history', { params })
    return response.data
  },

  async runJob(jobId: string): Promise<{ message: string }> {
    const response = await api.post(`/scheduler/jobs/${jobId}/run`)
    return response.data
  },
}

export default api
