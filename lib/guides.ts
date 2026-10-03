import fs from 'node:fs'
import path from 'node:path'
import { byNewest, isGuide, type Guide } from '@/lib/guide-content'

const DIR = path.join(process.cwd(), 'content', 'guides')

// Every drafted guide in content/guides, newest first. Read at build time; a malformed file is
// skipped rather than breaking the build.
export function loadGuides(): Guide[] {
  let files: string[] = []
  try {
    files = fs.readdirSync(DIR).filter((f) => f.endsWith('.json'))
  } catch {
    return []
  }
  const guides: Guide[] = []
  for (const f of files) {
    try {
      const g: unknown = JSON.parse(fs.readFileSync(path.join(DIR, f), 'utf8'))
      if (isGuide(g) && `${g.slug}.json` === f) guides.push(g)
    } catch {
      // skipped
    }
  }
  return byNewest(guides)
}

export function guideBySlug(slug: string): Guide | undefined {
  return loadGuides().find((g) => g.slug === slug)
}
