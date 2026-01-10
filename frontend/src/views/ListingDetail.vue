<template>
  <div class="listing-detail">
    <div v-if="loading" class="loading">Loading listing...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="listing">
      <div class="header">
        <div>
          <h1>{{ listing.title || 'Untitled Listing' }}</h1>
          <span class="badge" :class="listing.status">{{ listing.status }}</span>
        </div>
        <div class="actions">
          <button @click="showEditModal = true" class="btn-edit">Edit</button>
          <a :href="listing.url" target="_blank" class="btn-link">View on {{ listing.platform }}</a>
        </div>
      </div>

      <div class="content-grid">
        <!-- Details Section -->
        <div class="details-section">
          <h2>Details</h2>
          <div class="detail-item">
            <strong>Platform:</strong>
            <span>{{ listing.platform }}</span>
          </div>
          <div class="detail-item">
            <strong>Price:</strong>
            <span>{{ formatCurrency(listing.price) }}</span>
          </div>
          <div class="detail-item">
            <strong>Initial Cost:</strong>
            <span>{{ formatCurrency(listing.initial_cost) }}</span>
          </div>
          <div v-if="listing.sale_price" class="detail-item">
            <strong>Sale Price:</strong>
            <span>{{ formatCurrency(listing.sale_price) }}</span>
          </div>
          <div v-if="listing.sale_price && listing.initial_cost && profit !== undefined" class="detail-item">
            <strong>Profit:</strong>
            <span :class="{ negative: profit < 0 }">{{ formatCurrency(profit) }}</span>
          </div>
          <div class="detail-item">
            <strong>Views:</strong>
            <span>{{ listing.views }}</span>
          </div>
          <div v-if="listing.category" class="detail-item">
            <strong>Category:</strong>
            <span>{{ listing.category }}</span>
          </div>
          <div v-if="listing.brand" class="detail-item">
            <strong>Brand:</strong>
            <span>{{ listing.brand }}</span>
          </div>
          <div v-if="listing.condition" class="detail-item">
            <strong>Condition:</strong>
            <span>{{ listing.condition }}</span>
          </div>
          <div v-if="listing.size" class="detail-item">
            <strong>Size:</strong>
            <span>{{ listing.size }}</span>
          </div>
          <div v-if="listing.posted_at" class="detail-item">
            <strong>Posted:</strong>
            <span>{{ formatDate(listing.posted_at) }}</span>
          </div>
          <div v-if="listing.sold_at" class="detail-item">
            <strong>Sold:</strong>
            <span>{{ formatDate(listing.sold_at) }}</span>
          </div>
        </div>

        <!-- Description -->
        <div v-if="listing.description" class="description-section">
          <h2>Description</h2>
          <p>{{ listing.description }}</p>
        </div>
      </div>

      <!-- Price History Chart -->
      <div v-if="priceHistory.length > 0" class="price-history-section">
        <h2>Price History</h2>
        <div class="price-chart" role="group" aria-label="Price history chart showing price changes over time">
          <div
            v-for="(point, index) in priceHistory"
            :key="index"
            class="price-point"
            :style="{ height: `${(point.price / maxPrice) * 100}%` }"
            :title="`${point.date}: ${formatCurrency(point.price)}`"
            role="img"
            :aria-label="`Price on ${formatDate(point.date)} was ${formatCurrency(point.price)}`"
          >
            <div class="point-label" aria-hidden="true">{{ formatShortDate(point.date) }}</div>
            <div class="point-value" aria-hidden="true">{{ formatCurrency(point.price) }}</div>
          </div>
        </div>
      </div>

      <!-- Competitor Prices -->
      <div v-if="competitorPrices.length > 0" class="competitor-section">
        <h2>Competitor Prices</h2>
        <div class="competitor-grid">
          <div
            v-for="comp in competitorPrices"
            :key="comp.id"
            class="competitor-card"
          >
            <div class="competitor-header">
              <h3>{{ comp.title }}</h3>
              <span class="similarity">{{ Math.round(comp.similarity_score * 100) }}% similar</span>
            </div>
            <div class="competitor-details">
              <p>
                <strong>Price:</strong> {{ formatCurrency(comp.competitor_price) }}
              </p>
              <p>
                <strong>Platform:</strong> {{ comp.source_platform }}
              </p>
              <p>
                <strong>Checked:</strong> {{ formatDate(comp.checked_at) }}
              </p>
            </div>
            <a :href="comp.competitor_url" target="_blank" class="btn-link">View Listing</a>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="edit-modal-title">
        <h3 id="edit-modal-title">Edit Listing</h3>
        <form @submit.prevent="saveListing">
          <div class="form-group">
            <label for="title">Title</label>
            <input id="title" v-model="editForm.title" type="text" />
          </div>
          <div class="form-group">
            <label for="description">Description</label>
            <textarea id="description" v-model="editForm.description" rows="5"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="price">Price</label>
              <input id="price" v-model.number="editForm.price" type="number" step="0.01" />
            </div>
            <div class="form-group">
              <label for="initial_cost">Initial Cost</label>
              <input
                id="initial_cost"
                v-model.number="editForm.initial_cost"
                type="number"
                step="0.01"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="category">Category</label>
              <input id="category" v-model="editForm.category" type="text" />
            </div>
            <div class="form-group">
              <label for="brand">Brand</label>
              <input id="brand" v-model="editForm.brand" type="text" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="condition">Condition</label>
              <select id="condition" v-model="editForm.condition">
                <option value="">Select condition</option>
                <option value="new">New</option>
                <option value="like_new">Like New</option>
                <option value="good">Good</option>
                <option value="fair">Fair</option>
                <option value="poor">Poor</option>
              </select>
            </div>
            <div class="form-group">
              <label for="size">Size</label>
              <input id="size" v-model="editForm.size" type="text" />
            </div>
          </div>
          <div class="form-group">
            <label for="status">Status</label>
            <select id="status" v-model="editForm.status">
              <option value="active">Active</option>
              <option value="sold">Sold</option>
              <option value="removed">Removed</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
            <button type="button" @click="closeModal" class="btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { listingsApi, analyticsApi } from '../services/api'
import type { Listing, CompetitorPrice, PriceHistoryPoint } from '../types'

const route = useRoute()
const toast = useToast()

const loading = ref(true)
const error = ref('')
const saving = ref(false)
const listing = ref<Listing | null>(null)
const competitorPrices = ref<CompetitorPrice[]>([])
const priceHistory = ref<PriceHistoryPoint[]>([])
const showEditModal = ref(false)

const editForm = ref({
  title: '',
  description: '',
  price: 0,
  initial_cost: 0,
  category: '',
  brand: '',
  condition: '',
  size: '',
  status: 'active',
})

const profit = computed<number | undefined>(() => {
  if (listing.value?.sale_price == null || listing.value?.initial_cost == null) {
    return undefined
  }
  return listing.value.sale_price - listing.value.initial_cost
})

const hasUnsavedChanges = computed(() => {
  if (!listing.value) return false
  return (
    editForm.value.title !== (listing.value.title || '') ||
    editForm.value.description !== (listing.value.description || '') ||
    editForm.value.price !== (listing.value.price || 0) ||
    editForm.value.initial_cost !== (listing.value.initial_cost || 0) ||
    editForm.value.category !== (listing.value.category || '') ||
    editForm.value.brand !== (listing.value.brand || '') ||
    editForm.value.condition !== (listing.value.condition || '') ||
    editForm.value.size !== (listing.value.size || '') ||
    editForm.value.status !== listing.value.status
  )
})

const closeModal = () => {
  if (hasUnsavedChanges.value) {
    if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
      return
    }
  }
  showEditModal.value = false
}

const maxPrice = computed(() => {
  if (priceHistory.value.length === 0) return 1
  return Math.max(...priceHistory.value.map((p) => p.price))
})

const formatCurrency = (value: number | undefined): string => {
  if (value === undefined || value === null) return 'N/A'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'EUR',
  }).format(value)
}

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const formatShortDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(date)
}

const loadListing = async () => {
  const listingId = parseInt(route.params.id as string)
  if (isNaN(listingId)) {
    error.value = 'Invalid listing ID'
    loading.value = false
    return
  }

  loading.value = true
  error.value = ''

  try {
    const [listingData, competitors, history] = await Promise.all([
      listingsApi.getById(listingId),
      analyticsApi.getPriceMonitoring(listingId).catch(() => {
        toast.error('Failed to load competitor prices')
        return []
      }),
      analyticsApi.getPriceHistory(listingId).catch(() => {
        toast.error('Failed to load price history')
        return []
      }),
    ])

    listing.value = listingData
    competitorPrices.value = competitors
    priceHistory.value = history

    editForm.value = {
      title: listingData.title || '',
      description: listingData.description || '',
      price: listingData.price || 0,
      initial_cost: listingData.initial_cost || 0,
      category: listingData.category || '',
      brand: listingData.brand || '',
      condition: listingData.condition || '',
      size: listingData.size || '',
      status: listingData.status,
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load listing'
  } finally {
    loading.value = false
  }
}

const saveListing = async () => {
  if (!listing.value) return

  if (!editForm.value.title || editForm.value.title.trim().length === 0) {
    toast.error('Title is required')
    return
  }

  if (editForm.value.title.length > 200) {
    toast.error('Title must be 200 characters or less')
    return
  }

  if (editForm.value.price != null && editForm.value.price < 0) {
    toast.error('Price must be a positive number')
    return
  }

  if (editForm.value.initial_cost != null && editForm.value.initial_cost < 0) {
    toast.error('Initial cost must be a positive number')
    return
  }

  saving.value = true
  try {
    await listingsApi.update(listing.value.id, editForm.value)
    toast.success('Listing updated successfully')
    showEditModal.value = false
    await loadListing()
  } catch (err) {
    toast.error('Failed to update listing')
  } finally {
    saving.value = false
  }
}

onMounted(loadListing)
</script>

<style scoped>
.listing-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading,
.error {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.error {
  color: #e74c3c;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  gap: 2rem;
}

.header h1 {
  margin: 0 0 0.5rem;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.badge.active {
  background: #d4edda;
  color: #155724;
}

.badge.sold {
  background: #cce5ff;
  color: #004085;
}

.badge.removed {
  background: #f8d7da;
  color: #721c24;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit,
.btn-link {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  text-decoration: none;
  display: inline-block;
}

.btn-edit {
  background: #42b983;
  color: white;
}

.btn-edit:hover {
  background: #35a372;
}

.btn-link {
  background: #3498db;
  color: white;
}

.btn-link:hover {
  background: #2980b9;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.details-section,
.description-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.details-section h2,
.description-section h2 {
  margin: 0 0 1rem;
  font-size: 1.2rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item strong {
  color: #666;
}

.negative {
  color: #e74c3c;
}

.description-section p {
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

.price-history-section,
.competitor-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #ddd;
  margin-bottom: 2rem;
}

.price-history-section h2,
.competitor-section h2 {
  margin: 0 0 1.5rem;
  font-size: 1.2rem;
}

.price-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 200px;
  gap: 0.5rem;
}

.price-point {
  flex: 1;
  background: linear-gradient(to top, #3498db, #2980b9);
  border-radius: 4px 4px 0 0;
  position: relative;
  min-height: 20px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.price-point:hover {
  opacity: 0.8;
}

.point-label {
  position: absolute;
  bottom: -25px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.7rem;
  color: #666;
}

.point-value {
  position: absolute;
  top: -25px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.7rem;
  color: #333;
  font-weight: 600;
}

.competitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.competitor-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  background: #fafafa;
}

.competitor-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.competitor-header h3 {
  margin: 0;
  font-size: 1rem;
  flex: 1;
}

.similarity {
  background: #42b983;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  white-space: nowrap;
}

.competitor-details p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h3 {
  margin: 0 0 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  font-family: inherit;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #42b983;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.modal-actions button {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-primary {
  background: #42b983;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #35a372;
}

.btn-primary:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}
</style>
