// The opening sequence - the preloader curtain, then the hero reveal - is
// pure CSS (app/intro.css). Nothing in it waits for JavaScript, which is the
// point: it used to be a chain of JS steps (download, hydrate, THEN start the
// preloader, THEN start the hero), so on a phone the page was blank for
// seconds while the first link in that chain arrived. As CSS it starts on the
// first paint and takes a fixed ~0.9s however slow the JS is.
//
// The one thing CSS cannot know is whether this visitor has already seen it
// this session. That is answered by a tiny script that runs in <head>, before
// the first paint, and marks the document:
//
//   <html class="pl-seen">   returning visitor: the CSS hides the whole intro
//                            immediately, so there is no flash and no wait
//   (no class)               first visit: the intro plays
//
// The flag is set the moment the intro STARTS rather than when it finishes,
// so a reload or a quick second page never replays it even if the first was
// interrupted. sessionStorage throws in a private window with site data
// blocked; that is treated as "not seen", so the intro plays, the safe default.

export const INTRO_SEEN_KEY = 'scalar-preloaded'
export const INTRO_SEEN_CLASS = 'pl-seen'

export const INTRO_HEAD_SCRIPT = `try{var d=document.documentElement,k="${INTRO_SEEN_KEY}";if(sessionStorage.getItem(k)==="1")d.classList.add("${INTRO_SEEN_CLASS}");else sessionStorage.setItem(k,"1")}catch(e){}`
