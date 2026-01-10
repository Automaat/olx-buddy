import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ListingDetail from './ListingDetail.vue'
import { listingsApi, analyticsApi } from '../services/api'
import type { Listing, CompetitorPrice, PriceHistoryPoint } from '../types'

vi.mock('../services/api', () => ({
  listingsApi: {
    getById: vi.fn(),
    update: vi.fn(),
  },
  analyticsApi: {
    getPriceMonitoring: vi.fn(),
    getPriceHistory: vi.fn(),
  },
}))

vi.mock('vue-toastification', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}))

describe('ListingDetail', () => {
  const mockListing: Listing = {
    id: 1,
    platform: 'vinted',
    external_id: 'ext123',
    url: 'https://vinted.com/item/123',
    title: 'Test Listing',
    description: 'Test description',
    price: 100,
    currency: 'EUR',
    category: 'Electronics',
    brand: 'Apple',
    condition: 'good',
    size: 'M',
    views: 50,
    status: 'active',
    initial_cost: 50,
    sale_price: undefined,
    sold_at: undefined,
    posted_at: '2024-01-01T00:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockCompetitorPrices: CompetitorPrice[] = [
    {
      id: 1,
      source_platform: 'vinted',
      competitor_url: 'https://vinted.com/item/456',
      competitor_price: 95,
      currency: 'EUR',
      similarity_score: 0.85,
      title: 'Similar Item',
      checked_at: '2024-01-10T00:00:00Z',
    },
  ]

  const mockPriceHistory: PriceHistoryPoint[] = [
    { date: '2024-01-01', price: 100 },
    { date: '2024-01-02', price: 95 },
    { date: '2024-01-03', price: 90 },
  ]

  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/listing/:id',
        name: 'ListingDetail',
        component: ListingDetail,
      },
    ],
  })

  beforeEach(async () => {
    await router.push('/listing/1')
    await router.isReady()

    vi.mocked(listingsApi.getById).mockResolvedValue(mockListing)
    vi.mocked(listingsApi.update).mockResolvedValue(mockListing)
    vi.mocked(analyticsApi.getPriceMonitoring).mockResolvedValue(mockCompetitorPrices)
    vi.mocked(analyticsApi.getPriceHistory).mockResolvedValue(mockPriceHistory)
  })

  it('renders properly', () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays loading state initially', () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    expect(wrapper.find('.loading').exists()).toBe(true)
  })

  it('loads and displays listing data', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(listingsApi.getById).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('Test Listing')
  })

  it('displays listing title and status badge', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('h1').text()).toContain('Test Listing')
    expect(wrapper.find('.badge').text()).toBe('active')
  })

  it('displays all listing details', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('vinted')
    expect(wrapper.text()).toContain('Electronics')
    expect(wrapper.text()).toContain('Apple')
    expect(wrapper.text()).toContain('good')
  })

  it('displays Edit button', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    const editButton = wrapper.find('.btn-edit')
    expect(editButton.exists()).toBe(true)
    expect(editButton.text()).toBe('Edit')
  })

  it('displays external link to platform', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    const link = wrapper.find('.btn-link')
    expect(link.attributes('href')).toBe('https://vinted.com/item/123')
    expect(link.text()).toContain('vinted')
  })

  it('displays description section', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('.description-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('Test description')
  })

  it('calculates and displays profit for sold items', async () => {
    const soldListing = {
      ...mockListing,
      status: 'sold',
      sale_price: 120,
    }
    vi.mocked(listingsApi.getById).mockResolvedValue(soldListing)

    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Profit')
  })

  it('displays negative profit in red', async () => {
    const soldListing = {
      ...mockListing,
      status: 'sold',
      sale_price: 30,
      initial_cost: 50,
    }
    vi.mocked(listingsApi.getById).mockResolvedValue(soldListing)

    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    const profitElement = wrapper.find('.negative')
    expect(profitElement.exists()).toBe(true)
  })

  it('displays price history chart when available', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('.price-history-section').exists()).toBe(true)
    expect(wrapper.findAll('.price-point')).toHaveLength(mockPriceHistory.length)
  })

  it('displays competitor prices when available', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('.competitor-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('Similar Item')
    expect(wrapper.text()).toContain('85% similar')
  })

  it('opens edit modal when Edit button is clicked', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('.modal').exists()).toBe(false)

    await wrapper.find('.btn-edit').trigger('click')
    expect(wrapper.find('.modal').exists()).toBe(true)
  })

  it('closes edit modal when Cancel is clicked', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    await wrapper.find('.btn-edit').trigger('click')
    expect(wrapper.find('.modal').exists()).toBe(true)

    await wrapper.find('.btn-secondary').trigger('click')
    expect(wrapper.find('.modal').exists()).toBe(false)
  })

  it('populates edit form with current listing data', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    await wrapper.find('.btn-edit').trigger('click')

    const titleInput = wrapper.find('#title')
    expect((titleInput.element as HTMLInputElement).value).toBe('Test Listing')

    const descriptionInput = wrapper.find('#description')
    expect((descriptionInput.element as HTMLTextAreaElement).value).toBe('Test description')
  })

  it('updates listing when save is clicked', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    await wrapper.find('.btn-edit').trigger('click')

    const titleInput = wrapper.find('#title')
    await titleInput.setValue('Updated Title')

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')

    expect(listingsApi.update).toHaveBeenCalledWith(1, expect.objectContaining({
      title: 'Updated Title',
    }))
  })

  it('closes modal after successful save', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    await wrapper.find('.btn-edit').trigger('click')
    expect(wrapper.find('.modal').exists()).toBe(true)

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.find('.modal').exists()).toBe(false)
  })

  it('displays error message when listing load fails', async () => {
    vi.mocked(listingsApi.getById).mockRejectedValue(new Error('API Error'))

    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('.error').exists()).toBe(true)
  })

  it('handles invalid listing ID', async () => {
    await router.push('/listing/invalid')

    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('.error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Invalid listing ID')
  })

  it('formats currency correctly', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toMatch(/€\d+/)
  })

  it('formats dates correctly', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toMatch(/\w{3}\s+\d{1,2}/)
  })

  it('disables save button while saving', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    await wrapper.find('.btn-edit').trigger('click')

    const saveButton = wrapper.find('.btn-primary')
    expect(saveButton.text()).toBe('Save')

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')

    expect(saveButton.attributes('disabled')).toBeDefined()
  })

  it('displays all form fields in edit modal', async () => {
    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    await wrapper.find('.btn-edit').trigger('click')

    expect(wrapper.find('#title').exists()).toBe(true)
    expect(wrapper.find('#description').exists()).toBe(true)
    expect(wrapper.find('#price').exists()).toBe(true)
    expect(wrapper.find('#initial_cost').exists()).toBe(true)
    expect(wrapper.find('#category').exists()).toBe(true)
    expect(wrapper.find('#brand').exists()).toBe(true)
    expect(wrapper.find('#condition').exists()).toBe(true)
    expect(wrapper.find('#size').exists()).toBe(true)
    expect(wrapper.find('#status').exists()).toBe(true)
  })

  it('handles missing optional data gracefully', async () => {
    const minimalListing: Listing = {
      ...mockListing,
      title: undefined,
      description: undefined,
      category: undefined,
      brand: undefined,
      condition: undefined,
      size: undefined,
      price: undefined,
      initial_cost: undefined,
    }
    vi.mocked(listingsApi.getById).mockResolvedValue(minimalListing)

    const wrapper = mount(ListingDetail, {
      global: {
        plugins: [router],
      },
    })
    await flushPromises()

    expect(wrapper.find('h1').text()).toContain('Untitled Listing')
    expect(wrapper.text()).toContain('N/A')
  })
})
