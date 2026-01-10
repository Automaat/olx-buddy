import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import AddListing from '../views/AddListing.vue'
import DescriptionGenerator from '../views/DescriptionGenerator.vue'

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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
