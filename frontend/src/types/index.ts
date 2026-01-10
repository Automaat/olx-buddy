export interface Listing {
  id: number
  platform: string
  external_id: string
  url: string
  title?: string
  description?: string
  price?: number
  currency: string
  category?: string
  brand?: string
  condition?: string
  size?: string
  views: number
  status: string
  initial_cost?: number
  sale_price?: number
  sold_at?: string
  posted_at?: string
  created_at: string
  updated_at: string
}

export interface AddListingRequest {
  url: string
  platform: 'vinted' | 'olx'
  initial_cost?: number
}

export interface GenerateDescriptionResponse {
  description: string
  suggested_price?: number
  min_price?: number
  max_price?: number
  median_price?: number
  sample_size: number
  similar_items: Array<{
    title?: string
    price?: number
    url?: string
  }>
}

export interface ImageUploadResponse {
  image_paths: string[]
  count: number
}

export type ItemCondition = 'new' | 'like_new' | 'good' | 'fair' | 'poor'
