import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// The full-screen map is the app. The earlier calendar app stays at /#classic.
const classic = location.hash === '#classic'
// Switching between the two apps (a link to #classic, or Back) reloads the page to load the other one.
addEventListener('hashchange', () => location.reload())
const load = classic
  ? Promise.all([import('./App.tsx'), import('./index.css')]).then(([m]) => m.default)
  : import('./studio/Studio.tsx').then((m) => m.default)

load.then((Root) =>
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <Root />
    </StrictMode>,
  ),
)
