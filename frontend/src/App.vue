<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-container">
        <router-link to="/" class="nav-brand">OLX Buddy</router-link>
        <div class="nav-links">
          <router-link to="/">Dashboard</router-link>
          <router-link to="/add-listing">Add Listing</router-link>
          <router-link to="/generate-description">Generate Description</router-link>
        </div>
      </div>
    </nav>

    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    sans-serif;
  background: #f5f5f5;
  color: #333;
}

#app {
  min-height: 100vh;
}

.navbar {
  background: white;
  border-bottom: 1px solid #e0e0e0;
  padding: 1rem 0;
  margin-bottom: 2rem;
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand {
  font-size: 1.5rem;
  font-weight: bold;
  color: #42b983;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 2rem;
}

.nav-links a {
  color: #666;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: #42b983;
}

main {
  min-height: calc(100vh - 100px);
}
</style>
