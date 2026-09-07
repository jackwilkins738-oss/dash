'use client'

import { usePathname } from 'next/navigation'

// Deliberately WhatsApp's own green, not the site's blueprint blue -
// customers recognise the colour instantly, and that recognition is the
// entire point of a corner button like this.
export function WhatsAppButton() {
  const pathname = usePathname()
  // The contact page already has its own WhatsApp card - a floating
  // duplicate on top of it just covers that card instead of helping.
  if (pathname === '/contact') return null

  return (
    <a
      href="https://wa.me/447000000000"
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Message on WhatsApp"
      className="group fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#25D366] shadow-lg shadow-black/30 transition-transform hover:scale-105 sm:bottom-7 sm:right-7"
    >
      <span
        className="absolute inset-0 -z-10 rounded-full bg-[#25D366] motion-safe:animate-ping motion-safe:[animation-duration:2.4s]"
        aria-hidden="true"
      />
      <svg
        viewBox="0 0 24 24"
        className="h-7 w-7 text-white"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.372-.025-.521-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
        <path d="M12.001 2C6.478 2 2 6.477 2 12c0 1.99.582 3.845 1.588 5.404L2 22l4.71-1.554A9.953 9.953 0 0 0 12.001 22C17.523 22 22 17.523 22 12S17.523 2 12.001 2zm0 18.2a8.174 8.174 0 0 1-4.415-1.29l-.317-.19-3.03 1.001.999-2.995-.207-.318A8.166 8.166 0 0 1 3.8 12c0-4.529 3.672-8.2 8.201-8.2 4.529 0 8.199 3.671 8.199 8.2 0 4.528-3.67 8.2-8.199 8.2z" />
      </svg>
    </a>
  )
}
