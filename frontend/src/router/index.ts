import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import AddListing from '../views/AddListing.vue'
import DescriptionGenerator from '../views/DescriptionGenerator.vue'
import Analytics from '../views/Analytics.vue'
import Scheduler from '../views/Scheduler.vue'
import ListingDetail from '../views/ListingDetail.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
  },
  {
    path: '/add-listing',
    name: 'AddListing',
    component: AddListing,
  },
  {
    path: '/generate-description',
    name: 'DescriptionGenerator',
    component: DescriptionGenerator,
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: Analytics,
  },
  {
    path: '/scheduler',
    name: 'Scheduler',
    component: Scheduler,
  },
  {
    path: '/listing/:id',
    name: 'ListingDetail',
    component: ListingDetail,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
