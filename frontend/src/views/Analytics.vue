<template>
  <div class="analytics">
    <h1>Analytics</h1>

    <div v-if="loading" class="loading">Loading analytics...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else>
      <!-- Summary Cards -->
      <div class="summary-grid">
        <div class="stat-card">
          <h3>Total Revenue</h3>
          <p class="stat-value">{{ formatCurrency(summary.total_revenue) }}</p>
        </div>
        <div class="stat-card">
          <h3>Total Profit</h3>
          <p class="stat-value" :class="{ negative: summary.total_profit < 0 }">
            {{ formatCurrency(summary.total_profit) }}
          </p>
        </div>
        <div class="stat-card">
          <h3>Inventory Value</h3>
          <p class="stat-value">{{ formatCurrency(summary.total_inventory_value) }}</p>
        </div>
        <div class="stat-card">
          <h3>Avg Sale Price</h3>
          <p class="stat-value">{{ formatCurrency(summary.avg_sale_price) }}</p>
        </div>
        <div class="stat-card">
          <h3>Active Listings</h3>
          <p class="stat-value">{{ summary.active_listings_count }}</p>
        </div>
        <div class="stat-card">
          <h3>Sold Listings</h3>
          <p class="stat-value">{{ summary.sold_listings_count }}</p>
        </div>
      </div>

      <div v-if="summary.negative_profit_count > 0" class="warning-banner">
        ⚠️ You have {{ summary.negative_profit_count }} listing(s) with negative profit
      </div>

      <!-- Sales Chart -->
      <div class="chart-section">
        <h2>Sales Over Time</h2>
        <div class="chart-filters">
          <button
            v-for="g in (['day', 'week', 'month'] as const)"
            :key="g"
            :class="{ active: granularity === g }"
            @click="granularity = g"
          >
            {{ g.charAt(0).toUpperCase() + g.slice(1) }}
          </button>
        </div>
        <div class="chart-container">
          <div v-if="salesData.length === 0" class="empty">No sales data available</div>
          <div v-else class="simple-chart" role="group" aria-label="Sales over time chart showing revenue by period">
            <div
              v-for="(point, index) in salesData"
              :key="index"
              class="chart-bar"
              :style="{
                height: `${(point.revenue / maxRevenue) * 100}%`,
              }"
              :title="`${point.date}: ${formatCurrency(point.revenue)}`"
              role="img"
              :aria-label="`Revenue for ${formatDate(point.date)} was ${formatCurrency(point.revenue)}`"
            >
              <div class="bar-label" aria-hidden="true">{{ formatDate(point.date) }}</div>
              <div class="bar-value" aria-hidden="true">{{ formatCurrency(point.revenue) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Best Sellers -->
      <div class="best-sellers-section">
        <h2>Best Sellers</h2>

        <div class="best-sellers-grid">
          <!-- Top Categories -->
          <div class="best-seller-card">
            <h3>Top Categories</h3>
            <div v-if="bestSellers.top_categories.length === 0" class="empty">No data</div>
            <div v-else class="list">
              <div
                v-for="cat in bestSellers.top_categories"
                :key="cat.category"
                class="list-item"
              >
                <span class="item-name">{{ cat.category || 'Unknown' }}</span>
                <span class="item-stats">
                  {{ formatCurrency(cat.revenue) }} ({{ cat.count }} sold)
                </span>
              </div>
            </div>
          </div>

          <!-- Top Brands -->
          <div class="best-seller-card">
            <h3>Top Brands</h3>
            <div v-if="bestSellers.top_brands.length === 0" class="empty">No data</div>
            <div v-else class="list">
              <div v-for="brand in bestSellers.top_brands" :key="brand.brand" class="list-item">
                <span class="item-name">{{ brand.brand || 'Unknown' }}</span>
                <span class="item-stats">
                  {{ formatCurrency(brand.revenue) }} ({{ brand.count }} sold)
                </span>
              </div>
            </div>
          </div>

          <!-- Most Profitable -->
          <div class="best-seller-card">
            <h3>Most Profitable</h3>
            <div v-if="bestSellers.most_profitable.length === 0" class="empty">No data</div>
            <div v-else class="list">
              <div v-for="item in bestSellers.most_profitable" :key="item.listing_id" class="list-item">
                <router-link :to="`/listing/${item.listing_id}`" class="item-name">
                  {{ item.title }}
                </router-link>
                <span class="item-stats">{{ formatCurrency(item.profit) }}</span>
              </div>
            </div>
          </div>

          <!-- Fastest Selling -->
          <div class="best-seller-card">
            <h3>Fastest Selling</h3>
            <div v-if="bestSellers.fastest_selling.length === 0" class="empty">No data</div>
            <div v-else class="list">
              <div v-for="item in bestSellers.fastest_selling" :key="item.listing_id" class="list-item">
                <router-link :to="`/listing/${item.listing_id}`" class="item-name">
                  {{ item.title }}
                </router-link>
                <span class="item-stats">{{ item.days_to_sell }} days</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Inventory Breakdown -->
      <div class="inventory-section">
        <h2>Inventory Breakdown</h2>
        <div v-if="inventoryData.length === 0" class="empty">No inventory data</div>
        <div v-else class="inventory-grid">
          <div v-for="item in inventoryData" :key="item.category" class="inventory-card">
            <h4>{{ item.category || 'Unknown' }}</h4>
            <p><strong>Total Value:</strong> {{ formatCurrency(item.total_value) }}</p>
            <p><strong>Count:</strong> {{ item.count }}</p>
            <p><strong>Avg Price:</strong> {{ formatCurrency(item.avg_price) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useToast } from 'vue-toastification'
import { analyticsApi } from '../services/api'
import type {
  AnalyticsSummary,
  SalesDataPoint,
  CategoryStat,
  BrandStat,
  TopItem,
  InventoryBreakdown,
} from '../types'

const toast = useToast()

const loading = ref(true)
const error = ref('')
const granularity = ref<'day' | 'week' | 'month'>('day')

const summary = ref<AnalyticsSummary>({
  total_revenue: 0,
  total_profit: 0,
  total_cost: 0,
  total_inventory_value: 0,
  active_listings_count: 0,
  sold_listings_count: 0,
  avg_sale_price: 0,
  negative_profit_count: 0,
})

const salesData = ref<SalesDataPoint[]>([])

const bestSellers = ref<{
  top_categories: CategoryStat[]
  top_brands: BrandStat[]
  most_profitable: TopItem[]
  fastest_selling: TopItem[]
}>({
  top_categories: [],
  top_brands: [],
  most_profitable: [],
  fastest_selling: [],
})

const inventoryData = ref<InventoryBreakdown[]>([])

const maxRevenue = computed(() => {
  if (salesData.value.length === 0) return 1
  return Math.max(...salesData.value.map((d) => d.revenue))
})

const formatCurrency = (value: number): string => {
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
  }).format(date)
}

const loadAnalytics = async () => {
  loading.value = true
  error.value = ''

  try {
    const [summaryData, salesOverTime, bestSellersData, inventoryValue] = await Promise.all([
      analyticsApi.getSummary(),
      analyticsApi.getSalesOverTime({ granularity: granularity.value }),
      analyticsApi.getBestSellers({ limit: 5 }),
      analyticsApi.getInventoryValue(),
    ])

    summary.value = summaryData
    salesData.value = salesOverTime
    bestSellers.value = bestSellersData
    inventoryData.value = inventoryValue
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load analytics'
  } finally {
    loading.value = false
  }
}

watch(granularity, async () => {
  try {
    salesData.value = await analyticsApi.getSalesOverTime({ granularity: granularity.value })
  } catch (err) {
    toast.error('Failed to load sales data')
  }
})

onMounted(loadAnalytics)
</script>

<style scoped>
.analytics {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
}

h2 {
  margin: 2rem 0 1rem;
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.stat-card h3 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: #666;
  font-weight: 500;
}

.stat-value {
  margin: 0;
  font-size: 1.8rem;
  font-weight: bold;
  color: #42b983;
}

.stat-value.negative {
  color: #e74c3c;
}

.warning-banner {
  background: #fff3cd;
  color: #856404;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 2rem;
  border: 1px solid #ffeaa7;
}

.chart-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #ddd;
  margin-bottom: 2rem;
}

.chart-filters {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.chart-filters button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.chart-filters button:hover {
  background: #f5f5f5;
}

.chart-filters button.active {
  background: #42b983;
  color: white;
  border-color: #42b983;
}

.chart-container {
  min-height: 300px;
}

.simple-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 300px;
  gap: 0.5rem;
  padding: 1rem 0;
}

.chart-bar {
  flex: 1;
  background: linear-gradient(to top, #42b983, #35a372);
  border-radius: 4px 4px 0 0;
  position: relative;
  min-height: 20px;
  transition: all 0.3s;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.chart-bar:hover {
  opacity: 0.8;
}

.bar-label {
  position: absolute;
  bottom: -25px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.7rem;
  color: #666;
}

.bar-value {
  position: absolute;
  top: -25px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.7rem;
  color: #333;
  font-weight: 600;
}

.best-sellers-section {
  margin-bottom: 2rem;
}

.best-sellers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.best-seller-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.best-seller-card h3 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.list-item:last-child {
  border-bottom: none;
}

.item-name {
  font-weight: 500;
  color: #333;
  text-decoration: none;
  flex: 1;
}

a.item-name {
  color: #42b983;
}

a.item-name:hover {
  text-decoration: underline;
}

.item-stats {
  color: #666;
  font-size: 0.9rem;
}

.inventory-section {
  margin-bottom: 2rem;
}

.inventory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.inventory-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.inventory-card h4 {
  margin: 0 0 1rem;
  color: #42b983;
}

.inventory-card p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}
</style>
