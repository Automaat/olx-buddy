<template>
  <div class="scheduler">
    <h1>Scheduler Monitor</h1>

    <div v-if="loading" class="loading">Loading scheduler data...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else>
      <!-- Jobs List -->
      <div class="jobs-section">
        <h2>Scheduled Jobs</h2>
        <div v-if="jobs.length === 0" class="empty">No scheduled jobs</div>
        <div v-else class="jobs-grid">
          <div v-for="job in jobs" :key="job.id" class="job-card">
            <div class="job-header">
              <h3>{{ job.name }}</h3>
              <button @click="runJob(job.id)" class="btn-run" :disabled="runningJobs.has(job.id)">
                {{ runningJobs.has(job.id) ? 'Running...' : 'Run Now' }}
              </button>
            </div>
            <div class="job-details">
              <p>
                <strong>Job ID:</strong>
                <code>{{ job.id }}</code>
              </p>
              <p>
                <strong>Next Run:</strong>
                {{
                  job.next_run_time
                    ? formatDateTime(job.next_run_time)
                    : 'Not scheduled'
                }}
              </p>
              <p>
                <strong>Trigger:</strong>
                {{ job.trigger }}
              </p>
            </div>
            <button @click="toggleJobHistory(job.id)" class="btn-history">
              {{ expandedJobs.has(job.id) ? 'Hide History' : 'Show History' }}
            </button>

            <!-- Job History -->
            <div v-if="expandedJobs.has(job.id)" class="job-history">
              <div v-if="loadingHistory.has(job.id)" class="loading-history">
                Loading history...
              </div>
              <div v-else-if="jobHistories[job.id]?.length === 0" class="empty-history">
                No execution history
              </div>
              <div v-else class="history-list">
                <div
                  v-for="(execution, index) in jobHistories[job.id]"
                  :key="index"
                  class="history-item"
                  :class="{ success: execution.status === 'success', failure: execution.status !== 'success' }"
                >
                  <div class="history-header">
                    <span class="status-badge">
                      {{ execution.status === 'success' ? '✓ Success' : '✗ Failed' }}
                    </span>
                    <span class="timestamp">{{ formatDateTime(execution.started_at) }}</span>
                  </div>
                  <div v-if="execution.error_message" class="error-message">
                    <strong>Error:</strong> {{ execution.error_message }}
                  </div>
                  <div v-if="execution.result_data" class="result-data">
                    <strong>Result:</strong>
                    <pre>{{ JSON.stringify(execution.result_data, null, 2) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- All History -->
      <div class="all-history-section">
        <div class="section-header">
          <h2>Recent Executions</h2>
          <div class="history-filters">
            <label>
              <input v-model="showSuccessOnly" type="checkbox" />
              Success only
            </label>
            <button @click="loadAllHistory">Refresh</button>
          </div>
        </div>

        <div v-if="allHistory.length === 0" class="empty">No execution history</div>
        <div v-else class="all-history-list">
          <div
            v-for="(execution, index) in allHistory"
            :key="index"
            class="history-item"
            :class="{ success: execution.status === 'success', failure: execution.status !== 'success' }"
          >
            <div class="history-header">
              <span class="job-id">{{ execution.job_id }}</span>
              <span class="status-badge">
                {{ execution.status === 'success' ? '✓ Success' : '✗ Failed' }}
              </span>
              <span class="timestamp">{{ formatDateTime(execution.started_at) }}</span>
            </div>
            <div v-if="execution.error_message" class="error-message">
              <strong>Error:</strong> {{ execution.error_message }}
            </div>
            <div v-if="execution.result_data" class="result-data">
              <strong>Result:</strong>
              <pre>{{ JSON.stringify(execution.result_data, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { schedulerApi } from '../services/api'
import type { ScheduledJob, JobExecution } from '../types'

const toast = useToast()
const loading = ref(true)
const error = ref('')
const jobs = ref<ScheduledJob[]>([])
const allHistory = ref<JobExecution[]>([])
const jobHistories = ref<Record<string, JobExecution[]>>({})
const expandedJobs = ref<Set<string>>(new Set())
const loadingHistory = ref<Set<string>>(new Set())
const runningJobs = ref<Set<string>>(new Set())
const showSuccessOnly = ref(false)

const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const loadJobs = async () => {
  loading.value = true
  error.value = ''

  try {
    jobs.value = await schedulerApi.getJobs()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load jobs'
  } finally {
    loading.value = false
  }
}

const loadAllHistory = async () => {
  try {
    allHistory.value = await schedulerApi.getAllHistory({
      limit: 20,
      success_only: showSuccessOnly.value || undefined,
    })
  } catch (err) {
    toast.error('Failed to load execution history')
  }
}

const toggleJobHistory = async (jobId: string) => {
  if (expandedJobs.value.has(jobId)) {
    expandedJobs.value.delete(jobId)
    return
  }

  expandedJobs.value.add(jobId)

  if (jobHistories.value[jobId]) {
    return
  }

  loadingHistory.value.add(jobId)
  try {
    const history = await schedulerApi.getJobHistory(jobId)
    jobHistories.value[jobId] = history
  } catch (err) {
    toast.error('Failed to load job history')
  } finally {
    loadingHistory.value.delete(jobId)
  }
}

const runJob = async (jobId: string) => {
  runningJobs.value.add(jobId)
  try {
    await schedulerApi.runJob(jobId)
    toast.success('Job triggered successfully')
    setTimeout(async () => {
      if (expandedJobs.value.has(jobId)) {
        const history = await schedulerApi.getJobHistory(jobId)
        jobHistories.value[jobId] = history
      }
      await loadAllHistory()
    }, 1000)
  } catch (err) {
    toast.error('Failed to run job')
  } finally {
    runningJobs.value.delete(jobId)
  }
}

watch(showSuccessOnly, loadAllHistory)

onMounted(async () => {
  await loadJobs()
  await loadAllHistory()
})
</script>

<style scoped>
.scheduler {
  max-width: 1200px;
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

.jobs-section {
  margin-bottom: 3rem;
}

.jobs-grid {
  display: grid;
  gap: 1.5rem;
}

.job-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.job-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.job-details {
  margin-bottom: 1rem;
}

.job-details p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.job-details code {
  background: #f5f5f5;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-size: 0.85rem;
}

.btn-run,
.btn-history {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-run {
  background: #42b983;
  color: white;
}

.btn-run:hover:not(:disabled) {
  background: #35a372;
}

.btn-run:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-history {
  background: #3498db;
  color: white;
  width: 100%;
}

.btn-history:hover {
  background: #2980b9;
}

.job-history {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.loading-history,
.empty-history {
  text-align: center;
  padding: 1rem;
  color: #666;
  font-size: 0.9rem;
}

.history-list,
.all-history-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.history-item {
  padding: 1rem;
  border-radius: 4px;
  border-left: 4px solid #95a5a6;
}

.history-item.success {
  background: #d4edda;
  border-left-color: #28a745;
}

.history-item.failure {
  background: #f8d7da;
  border-left-color: #dc3545;
}

.history-header {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

.status-badge {
  font-weight: 600;
  font-size: 0.85rem;
}

.job-id {
  font-family: monospace;
  background: #f5f5f5;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-size: 0.85rem;
}

.timestamp {
  margin-left: auto;
  font-size: 0.85rem;
  color: #666;
}

.error-message {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #721c24;
}

.result-data {
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.result-data pre {
  background: #f5f5f5;
  padding: 0.5rem;
  border-radius: 3px;
  overflow-x: auto;
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
}

.all-history-section {
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
}

.history-filters {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.history-filters label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.history-filters button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.history-filters button:hover {
  background: #f5f5f5;
}
</style>
