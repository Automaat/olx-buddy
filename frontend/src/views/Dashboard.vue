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
          <router-link :to="`/listing/${listing.id}`" class="listing-title">
            <h3>{{ listing.title || 'No title' }}</h3>
          </router-link>
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
          <button v-if="listing.status === 'active'" @click="showSoldModal(listing.id)">
            Mark Sold
          </button>
          <button @click="showDeleteModal(listing.id)" class="btn-danger">Delete</button>
        </div>
      </div>
    </div>

    <!-- Mark as Sold Modal -->
    <div v-if="soldModal.show" class="modal-overlay" @click.self="soldModal.show = false">
      <div class="modal">
        <h3>Mark as Sold</h3>
        <div class="form-group">
          <label for="sale-price">Enter sale price:</label>
          <input
            id="sale-price"
            v-model="soldModal.salePrice"
            type="number"
            step="0.01"
            min="0"
            placeholder="0.00"
            @keyup.enter="markAsSold"
            autofocus
          />
        </div>
        <div class="modal-actions">
          <button @click="markAsSold" class="btn-primary">Confirm</button>
          <button @click="soldModal.show = false" class="btn-secondary">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteModal.show" class="modal-overlay" @click.self="deleteModal.show = false">
      <div class="modal">
        <h3>Delete Listing</h3>
        <p>Are you sure you want to delete this listing?</p>
        <div class="modal-actions">
          <button @click="deleteListing" class="btn-danger">Delete</button>
          <button @click="deleteModal.show = false" class="btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { listingsApi } from '../services/api'
import type { Listing } from '../types'

const toast = useToast()
const listings = ref<Listing[]>([])
const loading = ref(false)
const error = ref('')

const filters = ref({
  platform: '',
  status: 'active',
})

const soldModal = ref({
  show: false,
  listingId: null as number | null,
  salePrice: '',
})

const deleteModal = ref({
  show: false,
  listingId: null as number | null,
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

const showSoldModal = (id: number) => {
  soldModal.value = {
    show: true,
    listingId: id,
    salePrice: '',
  }
}

const markAsSold = async () => {
  const salePriceInput = soldModal.value.salePrice
  if (!salePriceInput) {
    soldModal.value.show = false
    return
  }

  const salePrice = parseFloat(salePriceInput)
  if (!Number.isFinite(salePrice) || salePrice <= 0) {
    toast.error('Please enter a valid positive number for the sale price')
    return
  }

  try {
    await listingsApi.markSold(soldModal.value.listingId!, {
      sale_price: salePrice,
    })
    soldModal.value.show = false
    await loadListings()
    toast.success('Listing marked as sold')
  } catch (err) {
    toast.error('Failed to mark as sold')
  }
}

const showDeleteModal = (id: number) => {
  deleteModal.value = {
    show: true,
    listingId: id,
  }
}

const deleteListing = async () => {
  try {
    await listingsApi.delete(deleteModal.value.listingId!)
    deleteModal.value.show = false
    await loadListings()
    toast.success('Listing deleted')
  } catch (err) {
    toast.error('Failed to delete listing')
  }
}

watch(() => filters.value.platform, loadListings)
watch(() => filters.value.status, loadListings)
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

.listing-title {
  flex: 1;
  text-decoration: none;
  color: inherit;
}

.listing-title:hover h3 {
  color: #42b983;
}

.listing-header h3 {
  margin: 0;
  font-size: 1.1rem;
  transition: color 0.2s;
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
  min-width: 400px;
  max-width: 90%;
}

.modal h3 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.modal p {
  margin-bottom: 1.5rem;
}

.modal .form-group {
  margin-bottom: 1.5rem;
}

.modal .form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.modal .form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.modal .form-group input:focus {
  outline: none;
  border-color: #42b983;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-primary {
  background: #42b983;
  color: white;
}

.btn-primary:hover {
  background: #35a372;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}
</style>
