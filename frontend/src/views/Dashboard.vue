<template>
  <div class="dashboard">
    <h1>Dashboard</h1>

    <div class="filters">
      <select v-model="filters.platform">
        <option value="">All Platforms</option>
        <option value="vinted">Vinted</option>
        <option value="olx">OLX</option>
      </select>

      <select v-model="filters.status">
        <option value="">All Status</option>
        <option value="active">Active</option>
        <option value="sold">Sold</option>
        <option value="removed">Removed</option>
      </select>

      <button @click="loadListings">Refresh</button>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="listings.length === 0" class="empty">No listings found</div>

    <div v-else class="listings-grid">
      <div v-for="listing in listings" :key="listing.id" class="listing-card">
        <div class="listing-header">
          <h3>{{ listing.title || 'No title' }}</h3>
          <span class="badge" :class="listing.status">{{ listing.status }}</span>
        </div>

        <div class="listing-details">
          <p><strong>Platform:</strong> {{ listing.platform }}</p>
          <p v-if="listing.price">
            <strong>Price:</strong> {{ listing.price }} {{ listing.currency }}
          </p>
          <p v-if="listing.initial_cost">
            <strong>Cost:</strong> {{ listing.initial_cost }} {{ listing.currency }}
          </p>
          <p v-if="listing.sale_price">
            <strong>Sold for:</strong> {{ listing.sale_price }} {{ listing.currency }}
          </p>
          <p><strong>Views:</strong> {{ listing.views }}</p>
          <p v-if="listing.category"><strong>Category:</strong> {{ listing.category }}</p>
          <p v-if="listing.brand"><strong>Brand:</strong> {{ listing.brand }}</p>
        </div>

        <div class="listing-actions">
          <a :href="listing.url" target="_blank" class="btn-link">View</a>
          <button v-if="listing.status === 'active'" @click="markAsSold(listing.id)">
            Mark Sold
          </button>
          <button @click="deleteListing(listing.id)" class="btn-danger">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { listingsApi } from '../services/api'
import type { Listing } from '../types'

const listings = ref<Listing[]>([])
const loading = ref(false)
const error = ref('')

const filters = ref({
  platform: '',
  status: 'active',
})

const loadListings = async () => {
  loading.value = true
  error.value = ''

  try {
    listings.value = await listingsApi.getAll({
      platform: filters.value.platform || undefined,
      status: filters.value.status || undefined,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load listings'
  } finally {
    loading.value = false
  }
}

const markAsSold = async (id: number) => {
  const salePrice = prompt('Enter sale price:')
  if (!salePrice) return

  try {
    await listingsApi.markSold(id, {
      sale_price: parseFloat(salePrice),
    })
    await loadListings()
  } catch (err) {
    alert('Failed to mark as sold')
  }
}

const deleteListing = async (id: number) => {
  if (!confirm('Are you sure you want to delete this listing?')) return

  try {
    await listingsApi.delete(id)
    await loadListings()
  } catch (err) {
    alert('Failed to delete listing')
  }
}

watch(filters, loadListings, { deep: true })
onMounted(loadListings)
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
}

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.filters select,
.filters button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.filters button {
  background: #42b983;
  color: white;
  border: none;
  cursor: pointer;
}

.filters button:hover {
  background: #35a372;
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.error {
  color: #e74c3c;
}

.listings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.listing-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  background: white;
}

.listing-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.listing-header h3 {
  margin: 0;
  font-size: 1.1rem;
  flex: 1;
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

.listing-details {
  margin-bottom: 1rem;
}

.listing-details p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.listing-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.listing-actions button,
.listing-actions .btn-link {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  text-decoration: none;
  display: inline-block;
}

.listing-actions button {
  background: #42b983;
  color: white;
}

.listing-actions button:hover {
  background: #35a372;
}

.btn-link {
  background: #3498db;
  color: white;
}

.btn-link:hover {
  background: #2980b9;
}

.btn-danger {
  background: #e74c3c !important;
}

.btn-danger:hover {
  background: #c0392b !important;
}
</style>
