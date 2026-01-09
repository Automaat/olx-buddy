<template>
  <div class="add-listing">
    <h1>Add Listing</h1>

    <form @submit.prevent="handleSubmit" class="form">
      <div class="form-group">
        <label for="platform">Platform *</label>
        <select id="platform" v-model="form.platform" required>
          <option value="">Select platform</option>
          <option value="vinted">Vinted</option>
          <option value="olx">OLX</option>
        </select>
      </div>

      <div class="form-group">
        <label for="url">Listing URL *</label>
        <input
          id="url"
          v-model="form.url"
          type="url"
          placeholder="https://..."
          required
        />
      </div>

      <div class="form-group">
        <label for="initial_cost">Initial Cost (optional)</label>
        <input
          id="initial_cost"
          v-model.number="form.initial_cost"
          type="number"
          step="0.01"
          min="0"
          placeholder="0.00"
        />
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="success" class="success">Listing added successfully!</div>

      <div class="form-actions">
        <button type="submit" :disabled="loading">
          {{ loading ? 'Adding...' : 'Add Listing' }}
        </button>
        <router-link to="/" class="btn-secondary">Cancel</router-link>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { listingsApi } from '../services/api'

const router = useRouter()

const form = ref({
  platform: '',
  url: '',
  initial_cost: undefined as number | undefined,
})

const loading = ref(false)
const error = ref('')
const success = ref(false)

const handleSubmit = async () => {
  loading.value = true
  error.value = ''
  success.value = false

  try {
    await listingsApi.addByUrl({
      url: form.value.url,
      platform: form.value.platform as 'vinted' | 'olx',
      initial_cost: form.value.initial_cost,
    })

    success.value = true

    setTimeout(() => {
      router.push('/')
    }, 1500)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to add listing'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.add-listing {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
}

.form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #42b983;
}

.error {
  padding: 1rem;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.success {
  padding: 1rem;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
}

.form-actions button,
.form-actions .btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  text-decoration: none;
  display: inline-block;
}

.form-actions button {
  background: #42b983;
  color: white;
  flex: 1;
}

.form-actions button:hover:not(:disabled) {
  background: #35a372;
}

.form-actions button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  text-align: center;
}

.btn-secondary:hover {
  background: #5a6268;
}
</style>
