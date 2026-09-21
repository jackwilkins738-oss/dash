// Joins class names, dropping anything falsy. That is all the client-side
// components need: their conditional classes never conflict with one another,
// so there is nothing for a merge step to resolve.
//
// It lives in its own file on purpose. lib/utils.ts exports `cn`, which is
// built on tailwind-merge (~9KB gzipped), and importing anything from that
// file puts the whole library in the bundle. Server components still use `cn`
// where a real merge is wanted; it costs the browser nothing there.
export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ')
}
