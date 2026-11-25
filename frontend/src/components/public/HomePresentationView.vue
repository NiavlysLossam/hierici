<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'navigate', tab: 'decouverte' | 'recits' | 'studio'): void
}>()

const failedImages = ref<Set<string>>(new Set())

function handleImageError(id: string) {
  failedImages.value.add(id)
}

const featuredPhotos = [
  {
    id: 'viaduc',
    title: 'Le Viaduc et les Pêcheurs',
    subtitle: 'Perspective fluviale sur les grandes infrastructures du XIXe siècle',
    image: '/images/landing/viaduc-pecheur.jpg',
    tag: '📷 Cône métrique 350m',
    source: 'Gallica BnF / Association des Toulousains de Toulouse',
    description: "Une composition remarquable capturant l'arche monumentale du viaduc ferroviaire se reflétant dans les eaux calmes, tandis qu'un pêcheur à l'ombrelle contemple la rive.",
  },
  {
    id: 'place-marche',
    title: 'La Place du Marché et ses Attelages',
    subtitle: "Animation populaire, charrettes à bœufs et commerces d'antan",
    image: '/images/landing/place-marche-boeufs.jpg',
    tag: '🐂 Scène de vie populaire',
    source: 'Gallica BnF / Bibliothèque nationale de France',
    description: "Au cœur de la cité, badauds, négociants et attelages bovins se croisent devant les enseignes historiques de marchands de boissons et d'artisans locaux.",
  },
  {
    id: 'theatre',
    title: 'Le Théâtre Municipal et le Convoi',
    subtitle: 'Contraste saisissant entre majesté architecturale et labeur quotidien',
    image: '/images/landing/theatre-boeufs.jpg',
    tag: '🏛️ Patrimoine architectural',
    source: 'Gallica BnF / Bibliothèque nationale de France',
    description: "La solennité des arcades néo-classiques du théâtre municipal côtoie la rudesse du travail de la terre alors qu'une paire de bœufs traverse la chaussée.",
  },
]

const pillars = [
  {
    icon: '📐',
    title: 'Géoréférencement Orienté',
    description:
      "Chaque photographie d'archive est précisément localisée avec sa position d'appareil, son azimut de prise de vue (0 à 359°) et son cône de vision métrique calculé en temps réel en WebGL.",
  },
  {
    icon: '🗺️',
    title: 'Fonds Cartographiques Multiples',
    description:
      'Superposez et comparez les clichés centenaires avec la carte contemporaine, les orthophotos aériennes haute définition (IGN / Esri) ou les plans cadastraux historiques.',
  },
  {
    icon: '🎧',
    title: 'Scrollytelling & Archives Sonores',
    description:
      "Laissez-vous guider par des parcours narratifs immersifs où la caméra 3D voyage de quartier en quartier au fil de récits historiques accompagnés de documents audio d'époque.",
  },
]
</script>

<template>
  <div class="space-y-16 pb-12 animate-fade-in text-slate-100">
    <!-- Section Hero -->
    <section class="relative rounded-3xl overflow-hidden border border-slate-800 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-950 p-8 sm:p-12 lg:p-16 shadow-2xl">
      <!-- Halo lumineux d'ambiance -->
      <div class="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 bg-sky-500/15 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 max-w-3xl mx-auto text-center space-y-6">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-950/80 border border-sky-800/80 text-sky-300 text-xs font-semibold tracking-wide uppercase">
          <span>🏛️</span>
          <span>Patrimoine Photographique & Cartographie Interactive</span>
        </div>

        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-tight">
          Redécouvrez l'histoire à l'endroit exact où elle a eu lieu.
        </h1>

        <p class="text-base sm:text-lg text-slate-300 leading-relaxed font-normal">
          <strong>HierIci</strong> relie la mémoire visuelle des territoires aux cartes contemporaines. 
          Explorez des clichés d'archives géoréférencés avec leur cône de vision réel et plongez dans des récits immersifs en scrollytelling.
        </p>

        <!-- Boutons d'Action Principaux -->
        <div class="pt-4 flex flex-wrap items-center justify-center gap-4">
          <button
            type="button"
            class="px-6 py-3.5 bg-sky-600 hover:bg-sky-500 text-white font-bold rounded-2xl shadow-xl shadow-sky-950/60 transition-all transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none flex items-center gap-2.5 text-sm motion-reduce:transform-none"
            @click="emit('navigate', 'decouverte')"
          >
            <span>🗺️</span>
            <span>Explorer la Carte Interactive</span>
          </button>

          <button
            type="button"
            class="px-6 py-3.5 bg-slate-800/90 hover:bg-slate-700/90 text-slate-200 hover:text-white font-bold rounded-2xl border border-slate-700 transition-all transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none flex items-center gap-2.5 text-sm motion-reduce:transform-none"
            @click="emit('navigate', 'recits')"
          >
            <span>📖</span>
            <span>Découvrir les Récits Narratifs</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Galerie des Photographies Historiques d'Illustration -->
    <section class="space-y-6">
      <div class="text-center max-w-2xl mx-auto space-y-2">
        <h2 class="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Fenêtres ouvertes sur le passé
        </h2>
        <p class="text-sm text-slate-400">
          Trois regards issus des collections patrimoniales nationales (Gallica BnF), témoins de l'évolution de nos paysages et de la vie quotidienne.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <article
          v-for="photo in featuredPhotos"
          :key="photo.id"
          role="button"
          tabindex="0"
          class="group bg-slate-900 border border-slate-800 hover:border-sky-500/60 rounded-3xl overflow-hidden shadow-xl flex flex-col transition-all duration-300 transform hover:-translate-y-1.5 cursor-pointer focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none motion-reduce:transform-none"
          @click="emit('navigate', 'decouverte')"
          @keydown.enter="emit('navigate', 'decouverte')"
        >
          <!-- Image historique avec gestion d'erreur -->
          <div class="relative aspect-[4/3] overflow-hidden bg-slate-950">
            <img
              v-if="!failedImages.has(photo.id)"
              :src="photo.image"
              :alt="photo.title"
              class="w-full h-full object-cover grayscale contrast-115 group-hover:scale-105 group-hover:grayscale-0 transition-all duration-500 motion-reduce:transform-none"
              loading="lazy"
              @error="handleImageError(photo.id)"
            />
            <div
              v-else
              class="w-full h-full flex flex-col items-center justify-center bg-slate-950 text-slate-500 space-y-2 p-4 text-center"
            >
              <span class="text-3xl">🖼️</span>
              <span class="text-xs">Archive patrimoniale</span>
            </div>

            <div class="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-slate-950/80 backdrop-blur-md text-[11px] font-semibold text-sky-300 border border-slate-700">
              {{ photo.tag }}
            </div>
          </div>

          <!-- Contenu éditorial -->
          <div class="p-6 flex-1 flex flex-col justify-between space-y-4">
            <div class="space-y-2">
              <h3 class="text-base font-bold text-white group-hover:text-sky-400 transition-colors">
                {{ photo.title }}
              </h3>
              <p class="text-xs text-sky-200/80 font-medium">
                {{ photo.subtitle }}
              </p>
              <p class="text-xs text-slate-400 leading-relaxed pt-1">
                {{ photo.description }}
              </p>
            </div>

            <div class="pt-3 border-t border-slate-800 space-y-2">
              <div class="text-[11px] text-slate-400 flex items-center justify-between">
                <span>Source : {{ photo.source }}</span>
              </div>
              <div class="text-[11px] text-sky-400 font-semibold flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                <span>Localiser sur la carte</span>
                <span>→</span>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- Piliers d'Innovation -->
    <section class="bg-slate-900/60 border border-slate-800/80 rounded-3xl p-8 sm:p-12 space-y-8">
      <div class="text-center max-w-2xl mx-auto space-y-2">
        <h2 class="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Une approche cartographique inédite
        </h2>
        <p class="text-sm text-slate-400">
          HierIci combine rigueur archivistique et technologies géospatiales modernes pour offrir une expérience immersive.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div
          v-for="pillar in pillars"
          :key="pillar.title"
          class="bg-slate-950/70 border border-slate-800 rounded-2xl p-6 space-y-3 shadow-lg"
        >
          <div class="w-12 h-12 rounded-xl bg-sky-950 border border-sky-800 text-2xl flex items-center justify-center">
            {{ pillar.icon }}
          </div>
          <h3 class="text-base font-bold text-white">{{ pillar.title }}</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            {{ pillar.description }}
          </p>
        </div>
      </div>
    </section>

    <!-- Appel à l'action final -->
    <section class="border border-sky-900/60 bg-gradient-to-r from-sky-950/50 via-slate-900 to-indigo-950/50 rounded-3xl p-8 sm:p-10 text-center space-y-6 shadow-2xl">
      <h2 class="text-2xl sm:text-3xl font-extrabold text-white">
        Explorez le territoire d'hier à aujourd'hui
      </h2>
      <p class="text-sm text-slate-300 max-w-xl mx-auto leading-relaxed">
        Naviguez librement parmi les photographies publiées ou parcourez les récits interactifs composés par les historiens et archivistes.
      </p>

      <div class="flex flex-wrap items-center justify-center gap-4 pt-2">
        <button
          type="button"
          class="px-6 py-3 bg-sky-600 hover:bg-sky-500 text-white font-bold rounded-xl text-xs shadow-lg transition-colors focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none flex items-center gap-2"
          @click="emit('navigate', 'decouverte')"
        >
          <span>🎯</span> Lancer l'exploration cartographique
        </button>
        <button
          type="button"
          class="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white font-bold rounded-xl text-xs border border-slate-700 transition-colors focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none flex items-center gap-2"
          @click="emit('navigate', 'studio')"
        >
          <span>🗂️</span> Espace Contribution & Studio
        </button>
      </div>
    </section>
  </div>
</template>
