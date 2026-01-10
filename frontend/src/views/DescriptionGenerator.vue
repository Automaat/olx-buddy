<template>
  <div class="generator">
    <h1>Description Generator</h1>

    <form @submit.prevent="handleSubmit" class="form">
      <div class="form-group">
        <label for="product-url">Product URL (optional)</label>
        <input
          id="product-url"
          v-model="form.product_url"
          type="url"
          placeholder="https://example.com/product"
        />
        <small class="help-text">AI will extract technical details from this URL to enhance the description</small>
      </div>

      <div class="form-group">
        <label for="photo-upload">Upload Photos (max 10) *</label>
        <input
          id="photo-upload"
          ref="fileInput"
          type="file"
          accept="image/*"
          multiple
          @change="handleFileChange"
          :disabled="uploadingImages"
        />
        <div v-if="selectedFiles.length > 0" class="file-list">
          <p>{{ selectedFiles.length }} file(s) selected</p>
        </div>
        <div v-if="uploadedPaths.length > 0" class="success-small">
          Images uploaded successfully!
        </div>
      </div>

      <div class="form-group">
        <label for="language">Language *</label>
        <select id="language" v-model="form.language" required>
          <option value="pl">Polish</option>
          <option value="en">English</option>
        </select>
      </div>

      <div class="form-group">
        <label for="brand">Brand</label>
        <input id="brand" v-model="form.brand" type="text" placeholder="e.g. Nike, Adidas" />
      </div>

      <div class="form-group">
        <label for="condition">Condition</label>
        <select id="condition" v-model="form.condition">
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
        <input id="size" v-model="form.size" type="text" placeholder="e.g. M, 42, 10" />
      </div>

      <div class="form-group">
        <label for="details">Additional Details</label>
        <textarea
          id="details"
          v-model="form.additional_details"
          rows="3"
          placeholder="Any other relevant information..."
        ></textarea>
      </div>

      <div class="form-group">
        <label>
          <input type="checkbox" v-model="form.include_price_suggestion" />
          Include price suggestion
        </label>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div class="form-actions">
        <button type="submit" :disabled="loading || uploadingImages">
          {{ loading ? 'Generating...' : 'Generate Description' }}
        </button>
        <router-link to="/" class="btn-secondary">Cancel</router-link>
      </div>
    </form>

    <div v-if="result" class="result">
      <h2>Generated Description</h2>

      <div class="result-section">
        <h3>Category</h3>
        <div class="category-box">
          {{ result.category
            .replace(/_/g, ' ')
            .replace(/\bwomens\b/i, "Women's")
            .replace(/\bmens\b/i, "Men's")
            .replace(/\b\w/g, (c: string) => c.toUpperCase())
          }}
        </div>
      </div>

      <div class="result-section">
        <h3>Description</h3>
        <div class="description-box">
          {{ result.description }}
        </div>
        <button @click="copyToClipboard(result.description)" class="btn-copy">
          Copy Description
        </button>
      </div>

      <div v-if="result.suggested_price" class="result-section">
        <h3>Price Suggestion</h3>
        <div class="price-info">
          <p><strong>Suggested:</strong> {{ result.suggested_price }} PLN</p>
          <p v-if="result.min_price">
            <strong>Min:</strong> {{ result.min_price }} PLN
          </p>
          <p v-if="result.max_price">
            <strong>Max:</strong> {{ result.max_price }} PLN
          </p>
          <p v-if="result.median_price">
            <strong>Median:</strong> {{ result.median_price }} PLN
          </p>
          <p><strong>Sample size:</strong> {{ result.sample_size }}</p>
        </div>
      </div>

      <div v-if="result.similar_items?.length > 0" class="result-section">
        <h3>Similar Items</h3>
        <div class="similar-items">
          <div v-for="(item, index) in result.similar_items" :key="index" class="similar-item">
            <p v-if="item.title">{{ item.title }}</p>
            <p v-if="item.price"><strong>{{ item.price }} PLN</strong></p>
            <a v-if="item.url" :href="item.url" target="_blank">View</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'vue-toastification'
import { generateApi } from '../services/api'
import type { GenerateDescriptionResponse } from '../types'

const toast = useToast()
const fileInput = ref<HTMLInputElement | null>(null)

const form = ref({
  product_url: '',
  brand: '',
  condition: '',
  size: '',
  additional_details: '',
  include_price_suggestion: true,
  language: 'pl',
})

const selectedFiles = ref<File[]>([])
const uploadedPaths = ref<string[]>([])
const loading = ref(false)
const uploadingImages = ref(false)
const error = ref('')
const result = ref<GenerateDescriptionResponse | null>(null)

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files) return

  const files = Array.from(target.files)
  if (files.length > 10) {
    error.value = 'Maximum 10 images allowed'
    return
  }

  selectedFiles.value = files
  error.value = ''

  uploadingImages.value = true
  try {
    const response = await generateApi.uploadImages(files)
    uploadedPaths.value = response.image_paths
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to upload images'
    selectedFiles.value = []
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } finally {
    uploadingImages.value = false
  }
}

const handleSubmit = async () => {
  if (uploadedPaths.value.length === 0) {
    error.value = 'Please upload at least one image'
    return
  }

  loading.value = true
  error.value = ''
  result.value = null

  try {
    result.value = await generateApi.generateDescription({
      image_paths: uploadedPaths.value.join(','),
      language: form.value.language,
      product_url: form.value.product_url || undefined,
      brand: form.value.brand || undefined,
      condition: form.value.condition || undefined,
      size: form.value.size || undefined,
      additional_details: form.value.additional_details || undefined,
      include_price_suggestion: form.value.include_price_suggestion,
    })

    // Clear uploaded paths and files after successful generation
    uploadedPaths.value = []
    selectedFiles.value = []
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to generate description'
  } finally {
    loading.value = false
  }
}

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard!')
  } catch (err) {
    toast.error('Failed to copy to clipboard')
  }
}
</script>

<style scoped>
.generator {
  max-width: 800px;
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
  margin-bottom: 2rem;
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

.form-group input[type='text'],
.form-group input[type='url'],
.form-group input[type='file'],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.help-text {
  display: block;
  color: #6c757d;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.form-group input[type='checkbox'] {
  width: auto;
  margin-right: 0.5rem;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #42b983;
}

.file-list {
  margin-top: 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.success-small {
  margin-top: 0.5rem;
  color: #155724;
  font-size: 0.9rem;
}

.error {
  padding: 1rem;
  background: #f8d7da;
  color: #721c24;
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

.result {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.result h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
}

.result-section {
  margin-bottom: 2rem;
}

.result-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.category-box {
  padding: 0.5rem 1rem;
  background: #e3f2fd;
  border-radius: 4px;
  font-weight: 600;
  color: #1976d2;
  text-transform: capitalize;
}

.description-box {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  white-space: pre-wrap;
  margin-bottom: 1rem;
}

.btn-copy {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-copy:hover {
  background: #2980b9;
}

.price-info {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
}

.price-info p {
  margin: 0.5rem 0;
}

.similar-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.similar-item {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.similar-item p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.similar-item a {
  color: #3498db;
  text-decoration: none;
  font-size: 0.9rem;
}

.similar-item a:hover {
  text-decoration: underline;
}
</style>
