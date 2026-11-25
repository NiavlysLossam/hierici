import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { resolveNavigationState, computeTabUrl } from '../src/utils/navigationState.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Story 5.4 - Page de Présentation Vitrine Patrimoniale (Landing Page)', async (t) => {
  const homeViewPath = path.resolve(__dirname, '../src/components/public/HomePresentationView.vue')
  const appVuePath = path.resolve(__dirname, '../src/App.vue')
  const landingDir = path.resolve(__dirname, '../public/images/landing')

  const homeViewSource = fs.readFileSync(homeViewPath, 'utf-8')
  const appVueSource = fs.readFileSync(appVuePath, 'utf-8')

  await t.test('AC-5.4-1 : Présence physique et intégrité des 3 photographies d archives historiques', () => {
    const images = ['viaduc-pecheur.jpg', 'place-marche-boeufs.jpg', 'theatre-boeufs.jpg']
    for (const img of images) {
      const imgPath = path.join(landingDir, img)
      assert.ok(fs.existsSync(imgPath), `L image ${img} doit exister dans ${landingDir}`)
      const stat = fs.statSync(imgPath)
      assert.ok(stat.size > 10000, `L image ${img} doit avoir une taille valide (> 10Ko), reçu: ${stat.size}`)
    }
  })

  await t.test('AC-5.4-2 : Références, citations Gallica BnF et accessibilité (alt, lazy-loading, AA contrast)', () => {
    assert.match(homeViewSource, /\/images\/landing\/viaduc-pecheur\.jpg/, 'Le viaduc doit être référencé')
    assert.match(homeViewSource, /\/images\/landing\/place-marche-boeufs\.jpg/, 'La place du marché doit être référencée')
    assert.match(homeViewSource, /\/images\/landing\/theatre-boeufs\.jpg/, 'Le théâtre municipal doit être référencé')
    assert.match(homeViewSource, /Gallica BnF \/ Bibliothèque nationale de France/, 'Les crédits BnF doivent être mentionnés')
    assert.match(homeViewSource, /Gallica BnF \/ Association des Toulousains de Toulouse/, 'Le fonds d archive local doit être mentionné')
    assert.match(homeViewSource, /:alt="photo\.title"/, 'Les balises img doivent avoir un alt accessible')
    assert.match(homeViewSource, /loading="lazy"/, 'Les images doivent disposer du lazy-loading natif')
    assert.match(homeViewSource, /text-slate-400/, 'Les crédits doivent utiliser text-slate-400 pour garantir WCAG 2.1 AA')
  })

  await t.test('AC-5.4-3 : Piliers d innovation cartographique et affordance de la galerie', () => {
    assert.match(homeViewSource, /Géoréférencement Orienté/, 'Le pilier géoréférencement doit être décrit')
    assert.match(homeViewSource, /Fonds Cartographiques Multiples/, 'Le pilier multi-fonds doit être décrit')
    assert.match(homeViewSource, /Scrollytelling & Archives Sonores/, 'Le pilier scrollytelling sonore doit être décrit')
    assert.match(homeViewSource, /cursor-pointer/, 'Les fiches de photos doivent avoir l affordance cliquable cursor-pointer')
    assert.match(homeViewSource, /Localiser sur la carte/, 'Un appel d exploration cartographique doit être présent sur les cartes')
  })

  await t.test('AC-5.4-4 : Boutons CTA et émission d événements de navigation', () => {
    assert.match(homeViewSource, /emit\('navigate', 'decouverte'\)/, 'Le bouton découverte doit émettre navigate decouverte')
    assert.match(homeViewSource, /emit\('navigate', 'recits'\)/, 'Le bouton récits doit émettre navigate recits')
    assert.match(homeViewSource, /emit\('navigate', 'studio'\)/, 'Le bouton studio doit émettre navigate studio')
  })

  await t.test('AC-5.4-5 : Intégration dans App.vue (Desktop ET Mobile, logo brand vers accueil)', () => {
    assert.match(appVueSource, /import HomePresentationView from '\.\/components\/public\/HomePresentationView\.vue'/, 'HomePresentationView doit être importé')
    assert.match(appVueSource, /<HomePresentationView @navigate="switchTab" \/>/, 'HomePresentationView doit être connecté à switchTab')

    // Vérification du logo de marque redirigeant vers accueil
    assert.match(appVueSource, /@click="switchTab\('accueil'\)"/, 'Le logo doit rediriger vers l accueil')

    // Vérification Desktop
    const desktopNavMatch = appVueSource.match(/<nav[^>]*class="[^"]*hidden md:flex[^"]*"[^>]*>([\s\S]*?)<\/nav>/)
    assert.ok(desktopNavMatch, 'La barre de navigation desktop doit exister')
    assert.match(desktopNavMatch[1], /switchTab\('accueil'\)/, 'Le bouton Accueil doit être dans le menu desktop')
    assert.match(desktopNavMatch[1], /Accueil/, 'Le libellé Accueil doit figurer dans le menu desktop')

    // Vérification Mobile
    const mobileNavMatch = appVueSource.match(/<div[^>]*class="[^"]*md:hidden[^"]*"[^>]*>([\s\S]*?)<\/div>/)
    assert.ok(mobileNavMatch, 'La barre de navigation mobile doit exister')
    assert.match(mobileNavMatch[1], /switchTab\('accueil'\)/, 'Le bouton Accueil doit être dans le menu mobile')
    assert.match(mobileNavMatch[1], /Accueil/, 'Le libellé Accueil doit figurer dans le menu mobile')
  })

  await t.test('AC-5.4-6 : Logique réelle de résolution d état d URL (resolveNavigationState)', () => {
    // 1. Accès racine par défaut
    assert.deepEqual(resolveNavigationState('https://hierici.local/'), {
      tab: 'accueil',
      photoId: null,
      storymapSlug: null,
    })

    // 2. Paramètre tab explicite
    assert.deepEqual(resolveNavigationState('https://hierici.local/?tab=accueil'), {
      tab: 'accueil',
      photoId: null,
      storymapSlug: null,
    })
    assert.deepEqual(resolveNavigationState('https://hierici.local/?tab=decouverte'), {
      tab: 'decouverte',
      photoId: null,
      storymapSlug: null,
    })
    assert.deepEqual(resolveNavigationState('https://hierici.local/?tab=recits'), {
      tab: 'recits',
      photoId: null,
      storymapSlug: null,
    })
    assert.deepEqual(resolveNavigationState('https://hierici.local/?tab=studio'), {
      tab: 'studio',
      photoId: null,
      storymapSlug: null,
    })

    // 3. Deep link vers une photo -> découverte
    assert.deepEqual(resolveNavigationState('https://hierici.local/?photo=8903227e-1234'), {
      tab: 'decouverte',
      photoId: '8903227e-1234',
      storymapSlug: null,
    })

    // 4. Deep link vers une storymap -> récits
    assert.deepEqual(resolveNavigationState('https://hierici.local/?storymap=rade-toulon'), {
      tab: 'recits',
      photoId: null,
      storymapSlug: 'rade-toulon',
    })

    // 5. Paramètre inconnu -> repli vers accueil
    assert.deepEqual(resolveNavigationState('https://hierici.local/?unknown=123'), {
      tab: 'accueil',
      photoId: null,
      storymapSlug: null,
    })
  })

  await t.test('AC-5.4-7 : Transitions d URL et nettoyage contextuel (computeTabUrl)', () => {
    // Depuis accueil vers découverte
    assert.equal(computeTabUrl('https://hierici.local/', 'decouverte'), '/?tab=decouverte')

    // Depuis découverte vers accueil : suppression de tab et nettoyage de photo
    assert.equal(
      computeTabUrl('https://hierici.local/?tab=decouverte&photo=8903227e', 'accueil'),
      '/'
    )

    // Depuis récits vers accueil : nettoyage de storymap
    assert.equal(
      computeTabUrl('https://hierici.local/?tab=recits&storymap=rade-toulon', 'accueil'),
      '/'
    )

    // Depuis récits vers découverte : nettoyage de storymap
    assert.equal(
      computeTabUrl('https://hierici.local/?tab=recits&storymap=rade-toulon', 'decouverte'),
      '/?tab=decouverte'
    )
  })
})
