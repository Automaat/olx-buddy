import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import Scheduler from './Scheduler.vue'
import { schedulerApi } from '../services/api'
import type { ScheduledJob, JobExecution } from '../types'

vi.mock('../services/api', () => ({
  schedulerApi: {
    getJobs: vi.fn(),
    getJobHistory: vi.fn(),
    getAllHistory: vi.fn(),
    runJob: vi.fn(),
  },
}))

vi.mock('vue-toastification', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}))

describe('Scheduler', () => {
  const mockJobs: ScheduledJob[] = [
    {
      id: 'job1',
      name: 'Update Listings',
      next_run_time: '2024-01-10T10:00:00Z',
      trigger: 'interval[0:01:00]',
    },
    {
      id: 'job2',
      name: 'Check Prices',
      next_run_time: null,
      trigger: 'cron[0 */6 * * *]',
    },
  ]

  const mockJobHistory: JobExecution[] = [
    {
      job_id: 'job1',
      run_time: '2024-01-10T09:00:00Z',
      success: true,
      result: { updated: 5 },
    },
    {
      job_id: 'job1',
      run_time: '2024-01-10T08:00:00Z',
      success: false,
      error: 'Connection timeout',
    },
  ]

  const mockAllHistory: JobExecution[] = [
    {
      job_id: 'job1',
      run_time: '2024-01-10T09:00:00Z',
      success: true,
    },
    {
      job_id: 'job2',
      run_time: '2024-01-10T08:30:00Z',
      success: true,
    },
  ]

  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/scheduler',
        name: 'Scheduler',
        component: Scheduler,
      },
    ],
  })

  beforeEach(() => {
    vi.mocked(schedulerApi.getJobs).mockResolvedValue(mockJobs)
    vi.mocked(schedulerApi.getJobHistory).mockResolvedValue(mockJobHistory)
    vi.mocked(schedulerApi.getAllHistory).mockResolvedValue(mockAllHistory)
    vi.mocked(schedulerApi.runJob).mockResolvedValue({ message: 'Job triggered' })
  })

  it('renders properly', () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays loading state initially', () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    expect(wrapper.find('.loading').exists()).toBe(true)
  })

  it('loads and displays jobs', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(schedulerApi.getJobs).toHaveBeenCalled()
    expect(schedulerApi.getAllHistory).toHaveBeenCalled()
  })

  it('displays job cards with details', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Update Listings')
    expect(wrapper.text()).toContain('Check Prices')
  })

  it('displays job next run time', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Next Run:')
  })

  it('displays "Not scheduled" when next_run_time is null', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Not scheduled')
  })

  it('has run now button for each job', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const runButtons = wrapper.findAll('.btn-run')
    expect(runButtons).toHaveLength(mockJobs.length)
  })

  it('triggers job when run button is clicked', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const runButton = wrapper.find('.btn-run')
    await runButton.trigger('click')

    expect(schedulerApi.runJob).toHaveBeenCalledWith('job1')
  })

  it('disables run button while job is running', async () => {
    let resolveRunJob: () => void
    const runJobPromise = new Promise<{ message: string }>((resolve) => {
      resolveRunJob = () => resolve({ message: 'Job triggered' })
    })
    vi.mocked(schedulerApi.runJob).mockReturnValue(runJobPromise)

    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const runButton = wrapper.find('.btn-run')
    runButton.trigger('click')
    await wrapper.vm.$nextTick()

    expect(runButton.attributes('disabled')).toBeDefined()

    resolveRunJob!()
  })

  it('toggles job history visibility', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.job-history').exists()).toBe(false)

    const historyButton = wrapper.find('.btn-history')
    await historyButton.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.job-history').exists()).toBe(true)
  })

  it('loads job history when expanded', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const historyButton = wrapper.find('.btn-history')
    await historyButton.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(schedulerApi.getJobHistory).toHaveBeenCalledWith('job1')
  })

  it('displays job execution history', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const historyButton = wrapper.find('.btn-history')
    await historyButton.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Success')
    expect(wrapper.text()).toContain('Failed')
  })

  it('displays error messages for failed jobs', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const historyButton = wrapper.find('.btn-history')
    await historyButton.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('Connection timeout')
  })

  it('displays recent executions section', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.all-history-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('Recent Executions')
  })

  it('has success only filter checkbox', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
  })

  it('filters history by success when checkbox is checked', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const checkbox = wrapper.find('input[type="checkbox"]')
    await checkbox.setValue(true)
    await wrapper.vm.$nextTick()

    expect(schedulerApi.getAllHistory).toHaveBeenCalledWith({
      limit: 20,
      success_only: true,
    })
  })

  it('refreshes all history when refresh button is clicked', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    vi.mocked(schedulerApi.getAllHistory).mockClear()

    const refreshButton = wrapper.findAll('.history-filters button')[0]
    await refreshButton.trigger('click')

    expect(schedulerApi.getAllHistory).toHaveBeenCalled()
  })

  it('displays error message on API failure', async () => {
    vi.mocked(schedulerApi.getJobs).mockRejectedValue(new Error('API Error'))

    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.error').exists()).toBe(true)
  })

  it('displays empty state when no jobs', async () => {
    vi.mocked(schedulerApi.getJobs).mockResolvedValue([])

    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.text()).toContain('No scheduled jobs')
  })

  it('formats timestamps correctly', async () => {
    const wrapper = mount(Scheduler, {
      global: {
        plugins: [router],
      },
    })
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    const text = wrapper.text()
    expect(text).toMatch(/\w{3}\s+\d{1,2}/)
  })
})
