import fs from 'node:fs'
import esbuild from 'esbuild'

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith('./') || specifier.startsWith('../')) {
    const parentUrl = new URL(context.parentURL)
    const targetUrl = new URL(specifier, parentUrl)
    if (!fs.existsSync(targetUrl) && fs.existsSync(new URL(targetUrl.href + '.ts'))) {
      return {
        url: targetUrl.href + '.ts',
        shortCircuit: true,
      }
    }
  }
  return nextResolve(specifier, context)
}

export async function load(url, context, nextLoad) {
  if (url.endsWith('.ts')) {
    const raw = fs.readFileSync(new URL(url), 'utf8')
    const { code } = esbuild.transformSync(raw, { loader: 'ts', format: 'esm' })
    return {
      format: 'module',
      shortCircuit: true,
      source: code,
    }
  }
  return nextLoad(url, context)
}
