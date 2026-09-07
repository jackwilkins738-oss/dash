'use client'

import dynamic from 'next/dynamic'

// Code-split out of the main page bundle - this pulls in Three.js and two
// postprocessing passes, none of which should count against the page's
// own script-parse budget or compete with real interactivity on load.
export const PowerCable = dynamic(() => import('@/components/power-cable').then((m) => m.PowerCable), {
  ssr: false,
})
