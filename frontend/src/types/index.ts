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
  category: string
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

export interface ExtractFromURLResponse {
  title?: string
  brand?: string
  description?: string
  price?: number
  currency?: string
  category?: string
  condition?: string
  size?: string
  images: string[]
  specifications?: any
}

export type ItemCondition = 'new' | 'like_new' | 'good' | 'fair' | 'poor'

export interface AnalyticsSummary {
  total_revenue: number
  total_profit: number
  total_cost: number
  total_inventory_value: number
  active_listings_count: number
  sold_listings_count: number
  avg_sale_price: number
  negative_profit_count: number
}

export interface SalesDataPoint {
  date: string
  revenue: number
  listings_sold: number
  listings_created: number
}

export interface CategoryStat {
  category: string
  revenue: number
  count: number
}

export interface BrandStat {
  brand: string
  revenue: number
  count: number
}

export interface TopItem {
  listing_id: number
  title: string
  revenue: number
  profit: number
  days_to_sell: number
}

export interface InventoryBreakdown {
  category: string
  total_value: number
  count: number
  avg_price: number
}

export interface CompetitorPrice {
  id: number
  source_platform: string
  competitor_url: string
  competitor_price: number
  currency: string
  similarity_score: number
  title: string
  checked_at: string
}

export interface PriceHistoryPoint {
  date: string
  price: number
}

export interface ScheduledJob {
  id: string
  name: string
  next_run_time: string | null
  trigger: string
}

export interface JobExecution {
  id: number
  job_id: string
  job_name: string
  status: string
  started_at: string
  completed_at: string | null
  error_message: string | null
  result_data: any | null
}
