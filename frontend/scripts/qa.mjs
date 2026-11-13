/**
 * Browser QA for the newspaper edition.
 * Uses the locally installed Chrome; no bundled browser download.
 *
 * Usage: node scripts/qa.mjs [baseUrl]
 */
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

const BASE = process.argv[2] || 'http://127.0.0.1:8000'
const OUT = join(process.cwd(), '..', 'docs', 'screenshots')
mkdirSync(OUT, { recursive: true })

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const findings = []
const report = {}

function watch(page, route) {
  const errors = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText || ''
    if (!failure.includes('ERR_ABORTED')) errors.push(`requestfailed: ${request.url()} ${failure}`)
  })
  return () => {
    if (errors.length) findings.push({ route, errors })
  }
}

async function settle(page) {
  await page.evaluate(async () => {
    const step = 420
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y)
      await new Promise((resolve) => setTimeout(resolve, 120))
    }
    window.scrollTo(0, 0)
  })
  await page.evaluate(async () => {
    const images = Array.from(document.images)
    images.forEach((image) => {
      image.loading = 'eager'
    })
    await Promise.all(
      images.map((image) =>
        Promise.race([
          image.decode().catch(() => undefined),
          new Promise((resolve) => setTimeout(resolve, 2000)),
        ]),
      ),
    )
  })
  await page.waitForTimeout(1200)
}

async function measure(page) {
  return page.evaluate(() => {
    const images = Array.from(document.querySelectorAll('img[data-newspaper-image]'))
    const loaded = images.filter((image) => image.complete && image.naturalWidth > 0)
    const failed = images
      .filter((image) => image.complete && image.naturalWidth === 0)
      .map((image) => image.getAttribute('src'))
      .slice(0, 5)
    const width = window.innerWidth
    const offenders = []
    for (const element of document.querySelectorAll('body *')) {
      const rect = element.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) continue
      if (rect.right > width + 2) {
        const style = getComputedStyle(element)
        if (style.position === 'fixed' || style.visibility === 'hidden') continue
        offenders.push({
          tag: element.tagName.toLowerCase(),
          cls: (element.className || '').toString().slice(0, 80),
          right: Math.round(rect.right),
          text: (element.textContent || '').trim().slice(0, 40),
        })
        if (offenders.length >= 4) break
      }
    }
    return {
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: width,
      height: document.body.scrollHeight,
      images: images.length,
      imagesLoaded: loaded.length,
      imagesFailed: failed,
      plates: document.querySelectorAll('svg[role="img"]').length,
      backdrop: Boolean(document.querySelector('[data-dynamic-backdrop]')),
      night: document.documentElement.classList.contains('night'),
      h1: document.querySelector('h1')?.textContent?.trim().slice(0, 80) || '',
      offenders,
    }
  })
}

const browser = await chromium.launch({ executablePath: CHROME, headless: true })

try {
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } })

  const pages = [
    { name: 'home', path: '/', shot: 'home.jpg' },
    { name: 'dashboard', path: '/dashboard', shot: 'dashboard.jpg' },
    { name: 'search', path: '/search?q=nvidia', shot: 'search.jpg' },
    { name: 'about', path: '/about', shot: 'about.jpg' },
  ]

  for (const definition of pages) {
    const done = watch(desktop, definition.path)
    await desktop.goto(`${BASE}${definition.path}`, { waitUntil: 'networkidle' })
    await desktop.waitForTimeout(1200)
    await settle(desktop)
    await desktop.screenshot({ path: join(OUT, definition.shot), fullPage: true })
    report[definition.name] = await measure(desktop)
    done()
  }

  // Event page: largest multi-source story from the archive.
  const eventHref = await desktop.evaluate(async () => {
    const response = await fetch('/api/events?sort=trending&page_size=1')
    const data = await response.json()
    return data.items?.[0] ? `/events/${data.items[0].code}` : '/dashboard'
  })
  const doneEvent = watch(desktop, eventHref)
  await desktop.goto(`${BASE}${eventHref}`, { waitUntil: 'networkidle' })
  await desktop.waitForTimeout(1200)
  await settle(desktop)
  await desktop.screenshot({ path: join(OUT, 'event.jpg'), fullPage: true })
  report.event = await measure(desktop)

  const selects = desktop.locator('button[aria-label^="Add "]')
  const selectCount = await selects.count()
  if (selectCount >= 2) {
    await selects.nth(0).click()
    await selects.nth(1).click()
    await desktop.waitForTimeout(400)
    const comparison = await desktop.locator('#comparison').isVisible()
    if (comparison) {
      await desktop.locator('#comparison').scrollIntoViewIfNeeded()
      await desktop.screenshot({ path: join(OUT, 'comparison.jpg') })
    }
    report.comparison = { rendered: comparison, selectable: selectCount }
  }
  doneEvent()

  // Night edition.
  await desktop.goto(`${BASE}/`, { waitUntil: 'networkidle' })
  await desktop.locator('button[aria-label="Switch to night edition"]').click()
  await desktop.waitForTimeout(500)
  await desktop.screenshot({ path: join(OUT, 'home-night.jpg'), fullPage: false })
  report.night = await measure(desktop)

  // Responsive checks.
  for (const width of [1024, 768, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, isMobile: width < 500, hasTouch: width < 500 })
    const done = watch(page, `${width}px /`)
    await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
    await settle(page)
    const metrics = await measure(page)
    report[`home-${width}`] = metrics
    await page.screenshot({ path: join(OUT, `home-${width}.png`), fullPage: width >= 768 })
    done()

    if (width === 390) {
      const doneEventMobile = watch(page, '390px /event')
      await page.goto(`${BASE}${eventHref}`, { waitUntil: 'networkidle' })
      await page.waitForTimeout(1000)
      await settle(page)
      report['event-390'] = await measure(page)
      await page.screenshot({ path: join(OUT, 'event-mobile.jpg'), fullPage: false })
      doneEventMobile()
    } else {
      const doneEventTablet = watch(page, `${width}px /event`)
      await page.goto(`${BASE}${eventHref}`, { waitUntil: 'networkidle' })
      await page.waitForTimeout(1000)
      report[`event-${width}`] = await measure(page)
      if (width === 768) {
        await page.screenshot({ path: join(OUT, 'event-768.jpg'), fullPage: false })
      }
      doneEventTablet()
    }

    for (const route of ['/dashboard', '/search?q=nvidia', '/about']) {
      const label = `${route}-${width}`
      const doneInner = watch(page, label)
      await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle' })
      await page.waitForTimeout(800)
      report[label] = await measure(page)
      if (width === 390 && route === '/dashboard') {
        await page.screenshot({ path: join(OUT, 'dashboard-mobile.jpg'), fullPage: false })
      }
      doneInner()
    }

    await page.close()
  }

  console.log(JSON.stringify(report, null, 2))
  if (findings.length) {
    console.log('\nBROWSER ERRORS:')
    for (const finding of findings) {
      console.log(`- ${finding.route}`)
      for (const error of finding.errors) console.log(`    ${error}`)
    }
  } else {
    console.log('\nNo console or page errors.')
  }
} finally {
  await browser.close()
}
