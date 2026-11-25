<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { photoApi, setAuthToken, hasAuthToken } from './services/api'
import PhotoAdminCatalog from './components/admin/PhotoAdminCatalog.vue'
import StorymapAdminCatalog from './components/admin/StorymapAdminCatalog.vue'
import GeneralAdminView from './components/admin/GeneralAdminView.vue'
import HomePresentationView from './components/public/HomePresentationView.vue'
import PublicMapViewer from './components/public/PublicMapViewer.vue'
import StorymapReader from './components/public/StorymapReader.vue'
import StorymapPublicCatalog from './components/public/StorymapPublicCatalog.vue'
import { extractStorymapSlug, cleanStorymapUrl } from './utils/storymapReader'
import { resolveNavigationState, computeTabUrl } from './utils/navigationState'

const currentTab = ref<'accueil' | 'decouverte' | 'recits' | 'studio'>('accueil')
const studioSubTab = ref<'photos' | 'storymaps' | 'admin'>('photos')
const activeStorymapSlug = ref<string | null>(null)

const apiHealth = ref<{ status: string; database: string } | null>(null)
const territory = ref<{ slug: string; name: string; center_lat: number; center_lng: number; default_zoom: number } | null>(null)
const currentUser = ref<{ email: string; full_name?: string; role: string; territory_id?: string } | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Modal de connexion
const isLoginModalOpen = ref(false)
const loginEmail = ref('admin@hierici.local')
const loginPassword = ref('admin_hierici_2026')
const loginError = ref<string | null>(null)
const isLoggingIn = ref(false)

async function authenticate() {
  try {
    if (hasAuthToken()) {
      try {
        currentUser.value = await photoApi.getMe()
        return
      } catch {
        setAuthToken(null)
      }
    }

    // Tentative d'auto-authentification avec le compte de développement local
    const loginRes = await photoApi.login(loginEmail.value, loginPassword.value)
    currentUser.value = loginRes.user
  } catch (err: any) {
    console.warn('Authentification requise pour le Studio:', err.message)
  }
}

async function handleManualLogin() {
  loginError.value = null
  isLoggingIn.value = true

  try {
    const res = await photoApi.login(loginEmail.value, loginPassword.value)
    currentUser.value = res.user
    isLoginModalOpen.value = false
  } catch (err: any) {
    loginError.value = err.message || 'Identifiants invalides'
  } finally {
    isLoggingIn.value = false
  }
}

function handleLogout() {
  setAuthToken(null)
  currentUser.value = null
}

function syncUrlState() {
  const navState = resolveNavigationState(window.location)
  currentTab.value = navState.tab

  // Synchronisation de la storymap active (et réinitialisation propre si absente lors du popstate)
  const slug = navState.storymapSlug || extractStorymapSlug(window.location)
  activeStorymapSlug.value = slug || null
}

function switchTab(tab: 'accueil' | 'decouverte' | 'recits' | 'studio') {
  currentTab.value = tab

  // Si on quitte les récits, réinitialisation de la storymap active
  if (tab !== 'recits') {
    activeStorymapSlug.value = null
  }

  const newUrl = computeTabUrl(window.location.href, tab)
  window.history.pushState({}, '', newUrl)
}

function handleOpenStorymap(slug: string) {
  activeStorymapSlug.value = slug
  const url = new URL(window.location.href)
  url.searchParams.set('storymap', slug)
  window.history.pushState({}, '', url.toString())
}

function handleCloseStorymap() {
  activeStorymapSlug.value = null
  const newUrl = cleanStorymapUrl(window.location.href)
  window.history.replaceState({}, '', newUrl)
}

onMounted(async () => {
  syncUrlState()
  window.addEventListener('popstate', syncUrlState)

  try {
    const [healthRes, territoryRes] = await Promise.all([
      photoApi.getHealth().catch(() => null),
      photoApi.getCurrentTerritory().catch(() => null),
    ])

    if (healthRes) apiHealth.value = healthRes
    if (territoryRes) territory.value = territoryRes

    // Connexion automatique initiale pour le studio
    await authenticate()
  } catch (e: any) {
    error.value = "Impossible de contacter l'API backend"
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('popstate', syncUrlState)
})
</script>

<template>
  <main class="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-sky-500 selection:text-white">
    <!-- En-tête Global -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between shadow-lg">
      <div class="flex items-center space-x-6">
        <button
          type="button"
          class="flex items-center space-x-3 text-left hover:opacity-90 transition-opacity focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none rounded-lg p-0.5"
          title="Retour à l'accueil"
          @click="switchTab('accueil')"
        >
          <span class="text-2xl drop-shadow">🧭</span>
          <div>
            <h1 class="text-lg font-black tracking-tight text-white flex items-center gap-2">
              <span>HierIci</span>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
                Studio 2.0
              </span>
            </h1>
            <p class="text-[11px] text-slate-400">Patrimoine géohistorique & archives territoriales</p>
          </div>
        </button>

        <!-- Onglets de Navigation Principale -->
        <nav class="hidden md:flex items-center space-x-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800 text-xs">
          <button
            type="button"
            class="px-4 py-1.5 rounded-lg font-medium transition-all flex items-center gap-2"
            :class="currentTab === 'accueil' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="switchTab('accueil')"
          >
            <span>🏠</span>
            <span>Accueil</span>
          </button>
          <button
            type="button"
            class="px-4 py-1.5 rounded-lg font-medium transition-all flex items-center gap-2"
            :class="currentTab === 'decouverte' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="switchTab('decouverte')"
          >
            <span>🗺️</span>
            <span>Carte Découverte</span>
          </button>
          <button
            type="button"
            class="px-4 py-1.5 rounded-lg font-medium transition-all flex items-center gap-2"
            :class="currentTab === 'recits' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="switchTab('recits')"
          >
            <span>📖</span>
            <span>Récits & Parcours</span>
          </button>
          <button
            type="button"
            class="px-4 py-1.5 rounded-lg font-medium transition-all flex items-center gap-2"
            :class="currentTab === 'studio' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="switchTab('studio')"
          >
            <span>🗂️</span>
            <span>Studio Admin</span>
          </button>
        </nav>
      </div>

      <!-- Informations de session & statut -->
      <div class="flex items-center space-x-3 text-xs">
        <!-- Badge Territoire -->
        <span
          v-if="territory"
          class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-medium bg-slate-800/80 text-slate-300 border border-slate-700"
          :title="`Centre : ${territory.center_lat.toFixed(4)}, ${territory.center_lng.toFixed(4)}`"
        >
          📍 {{ territory.name }}
        </span>

        <!-- Badge Santé API -->
        <span
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium"
          :class="apiHealth?.database === 'connected' ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800' : 'bg-amber-950/80 text-amber-400 border border-amber-800'"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="apiHealth?.database === 'connected' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'"></span>
          {{ apiHealth?.database === 'connected' ? 'API Connectée' : 'Connexion...' }}
        </span>

        <!-- Utilisateur connecté -->
        <div v-if="currentUser" class="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div class="hidden lg:block text-right">
            <div class="text-[11px] font-semibold text-white leading-tight">
              {{ currentUser.full_name || currentUser.email }}
            </div>
            <div class="text-[10px] text-slate-400 capitalize">
              {{ currentUser.role }}
            </div>
          </div>
          <button
            type="button"
            class="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            title="Se déconnecter"
            @click="handleLogout"
          >
            🚪
          </button>
        </div>
        <button
          v-else
          type="button"
          class="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-lg font-medium transition-colors"
          @click="isLoginModalOpen = true"
        >
          Connexion
        </button>
      </div>
    </header>

    <!-- Navigation mobile sous l'en-tête -->
    <div class="md:hidden border-b border-slate-800 bg-slate-900 px-4 py-2 flex items-center justify-center space-x-1.5 text-xs">
      <button
        type="button"
        class="flex-1 py-1.5 text-center rounded-lg font-medium transition-colors"
        :class="currentTab === 'accueil' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'"
        @click="switchTab('accueil')"
      >
        🏠 Accueil
      </button>
      <button
        type="button"
        class="flex-1 py-1.5 text-center rounded-lg font-medium transition-colors"
        :class="currentTab === 'decouverte' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'"
        @click="switchTab('decouverte')"
      >
        🗺️ Carte
      </button>
      <button
        type="button"
        class="flex-1 py-1.5 text-center rounded-lg font-medium transition-colors"
        :class="currentTab === 'recits' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'"
        @click="switchTab('recits')"
      >
        📖 Récits
      </button>
      <button
        type="button"
        class="flex-1 py-1.5 text-center rounded-lg font-medium transition-colors"
        :class="currentTab === 'studio' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'"
        @click="switchTab('studio')"
      >
        🗂️ Studio
      </button>
    </div>

    <!-- Contenu Principal -->
    <div :class="currentTab === 'decouverte' ? 'flex-1 w-full px-4 sm:px-6 py-4' : 'flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8'">
      <!-- VUE ACCUEIL VITRINE PATRIMONIALE (Story 5.4) -->
      <section v-if="currentTab === 'accueil'" class="w-full">
        <HomePresentationView @navigate="switchTab" />
      </section>

      <!-- VUE STUDIO ADMIN (Story 2.3 & Story 4.2) -->
      <section v-else-if="currentTab === 'studio'" class="space-y-6">
        <!-- Sous-navigation Studio : Photothèque vs Storymaps -->
        <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
          <button
            type="button"
            class="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
            :class="studioSubTab === 'photos' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="studioSubTab = 'photos'"
          >
            <span>📸</span>
            <span>Photothèque</span>
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
            :class="studioSubTab === 'storymaps' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="studioSubTab = 'storymaps'"
          >
            <span>📖</span>
            <span>Storymaps & Récits</span>
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
            :class="studioSubTab === 'admin' ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            @click="studioSubTab = 'admin'"
          >
            <span>⚙️</span>
            <span>Administration Générale</span>
          </button>
        </div>

        <PhotoAdminCatalog v-if="studioSubTab === 'photos'" />
        <StorymapAdminCatalog
          v-else-if="studioSubTab === 'storymaps'"
          :territory-center="territory ? { lat: territory.center_lat, lng: territory.center_lng, zoom: territory.default_zoom } : null"
          :territory-id="currentUser?.territory_id"
          @view-public="handleOpenStorymap"
        />
        <GeneralAdminView
          v-else-if="studioSubTab === 'admin'"
          :current-user-email="currentUser?.email"
        />
      </section>

      <!-- VUE CATALOGUE PUBLIC DES RÉCITS (Story 4.4) -->
      <section v-else-if="currentTab === 'recits'" class="w-full">
        <StorymapPublicCatalog
          :territory-name="territory?.name"
          :territory-slug="territory?.slug"
          @select-storymap="handleOpenStorymap"
          @explore-map="switchTab('decouverte')"
        />
      </section>

      <!-- VUE DÉCOUVERTE PUBLIQUE CARTE (Story 3.1) -->
      <section v-else-if="currentTab === 'decouverte'" class="w-full">
        <PublicMapViewer
          :territory-center="territory ? [territory.center_lng, territory.center_lat] : [5.93, 43.12]"
          :default-zoom="territory?.default_zoom ?? 13"
          :territory-name="territory?.name ?? 'Territoire'"
          @select-photo="(id) => console.log('Photo sélectionnée:', id)"
        />
      </section>
    </div>

    <!-- Modale de connexion manuelle -->
    <div
      v-if="isLoginModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
      @click.self="isLoginModalOpen = false"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-sm p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-base font-bold text-white">Connexion au Studio</h3>
          <button
            type="button"
            class="text-slate-400 hover:text-white"
            @click="isLoginModalOpen = false"
          >
            ✕
          </button>
        </div>

        <div v-if="loginError" class="p-2.5 rounded-lg bg-rose-950/80 border border-rose-800 text-xs text-rose-300">
          {{ loginError }}
        </div>

        <form class="space-y-4" @submit.prevent="handleManualLogin">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Email</label>
            <input
              v-model="loginEmail"
              type="email"
              required
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Mot de passe</label>
            <input
              v-model="loginPassword"
              type="password"
              required
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div class="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              class="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              @click="isLoginModalOpen = false"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold shadow-md flex items-center gap-1.5"
              :disabled="isLoggingIn"
            >
              <span v-if="isLoggingIn" class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>Connexion</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Lecteur Public de Storymap en Scrollytelling (Story 4.3) -->
    <StorymapReader
      v-if="activeStorymapSlug"
      :slug="activeStorymapSlug"
      :default-center="territory ? { lat: territory.center_lat, lng: territory.center_lng, zoom: territory.default_zoom } : null"
      @close="handleCloseStorymap"
    />

    <!-- Pied de page -->
    <footer class="border-t border-slate-800/80 bg-slate-950 px-6 py-4 text-center text-xs text-slate-500">
      HierIci — Studio d'Administration & Métadonnées d'Archives (Story 2.3)
    </footer>
  </main>
</template>
