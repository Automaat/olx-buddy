import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import Analytics from './Analytics.vue'
import { analyticsApi } from '../services/api'
import type {
  AnalyticsSummary,
  SalesDataPoint,
  CategoryStat,
  BrandStat,
  TopItem,
  InventoryBreakdown,
} from '../types'

vi.mock('../services/api', () => ({
  analyticsApi: {
    getSummary: vi.fn(),
    getSalesOverTime: vi.fn(),
    getBestSellers: vi.fn(),
    getInventoryValue: vi.fn(),
  },
}))

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/analytics',
      name: 'Analytics',
      component: Analytics,
    },
    {
      path: '/listing/:id',
      name: 'ListingDetail',
      component: { template: '<div>Listing Detail</div>' },
    },
  ],
})

describe('Analytics', () => {
  const mockSummary: AnalyticsSummary = {
    total_revenue: 1000,
    total_profit: 500,
    total_cost: 500,
    total_inventory_value: 2000,
    active_listings_count: 10,
    sold_listings_count: 5,
    avg_sale_price: 200,
    negative_profit_count: 2,
  }

  const mockSalesData: SalesDataPoint[] = [
    { date: '2024-01-01', revenue: 100, listings_sold: 1, listings_created: 2 },
    { date: '2024-01-02', revenue: 200, listings_sold: 2, listings_created: 1 },
  ]

  const mockBestSellers = {
    top_categories: [
      { category: 'Electronics', revenue: 500, count: 3 },
      { category: 'Clothing', revenue: 300, count: 2 },
    ] as CategoryStat[],
    top_brands: [
      { brand: 'Apple', revenue: 400, count: 2 },
      { brand: 'Nike', revenue: 200, count: 1 },
    ] as BrandStat[],
    most_profitable: [
      {
        listing_id: 1,
        title: 'iPhone',
        revenue: 500,
        profit: 200,
        days_to_sell: 5,
      },
    ] as TopItem[],
    fastest_selling: [
      {
        listing_id: 2,
        title: 'Shoes',
        revenue: 100,
        profit: 50,
        days_to_sell: 1,
      },
    ] as TopItem[],
  }

  const mockInventoryData: InventoryBreakdown[] = [
    { category: 'Electronics', total_value: 1000, count: 5, avg_price: 200 },
    { category: 'Clothing', total_value: 500, count: 10, avg_price: 50 },
  ]

  beforeEach(() => {
    vi.mocked(analyticsApi.getSummary).mockResolvedValue(mockSummary)
    vi.mocked(analyticsApi.getSalesOverTime).mockResolvedValue(mockSalesData)
    vi.mocked(analyticsApi.getBestSellers).mockResolvedValue(mockBestSellers)
    vi.mocked(analyticsApi.getInventoryValue).mockResolvedValue(mockInventoryData)
  })

  it('renders properly', () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays loading state initially', () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    expect(wrapper.find('.loading').exists()).toBe(true)
  })

  it('loads and displays analytics data', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(analyticsApi.getSummary).toHaveBeenCalled()
    expect(analyticsApi.getSalesOverTime).toHaveBeenCalled()
    expect(analyticsApi.getBestSellers).toHaveBeenCalled()
    expect(analyticsApi.getInventoryValue).toHaveBeenCalled()
  })

  it('displays summary statistics', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Total Revenue')
    expect(wrapper.text()).toContain('Total Profit')
    expect(wrapper.text()).toContain('Inventory Value')
  })

  it('displays warning banner for negative profit listings', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.warning-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('2 listing(s) with negative profit')
  })

  it('does not display warning banner when no negative profit', async () => {
    vi.mocked(analyticsApi.getSummary).mockResolvedValue({
      ...mockSummary,
      negative_profit_count: 0,
    })

    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.warning-banner').exists()).toBe(false)
  })

  it('displays sales chart', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.chart-section').exists()).toBe(true)
    expect(wrapper.findAll('.chart-bar')).toHaveLength(mockSalesData.length)
  })

  it('changes granularity when filter buttons are clicked', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const buttons = wrapper.findAll('.chart-filters button')
    expect(buttons).toHaveLength(3)

    await buttons[1].trigger('click')
    expect(analyticsApi.getSalesOverTime).toHaveBeenCalledWith({ granularity: 'week' })
  })

  it('displays best sellers sections', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Top Categories')
    expect(wrapper.text()).toContain('Top Brands')
    expect(wrapper.text()).toContain('Most Profitable')
    expect(wrapper.text()).toContain('Fastest Selling')
  })

  it('displays top categories with data', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Electronics')
    expect(wrapper.text()).toContain('Clothing')
  })

  it('displays inventory breakdown', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.inventory-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('Inventory Breakdown')
  })

  it('displays error message on API failure', async () => {
    vi.mocked(analyticsApi.getSummary).mockRejectedValue(new Error('API Error'))

    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.error').exists()).toBe(true)
  })

  it('displays empty state when no sales data', async () => {
    vi.mocked(analyticsApi.getSalesOverTime).mockResolvedValue([])

    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('No sales data available')
  })

  it('formats currency correctly', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const text = wrapper.text()
    expect(text).toMatch(/€[\d,]+\.?\d*/)
  })

  it('displays router links to listing details in best sellers', async () => {
    const wrapper = mount(Analytics, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const links = wrapper.findAll('a[href^="/listing/"]')
    expect(links.length).toBeGreaterThan(0)
  })
})
