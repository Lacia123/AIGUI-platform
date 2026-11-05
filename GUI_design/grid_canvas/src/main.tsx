import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import AnnotatePage from './AnnotatePage.tsx'
import AdaptiveLayoutPage from './AdaptiveLayoutPage.tsx'

function routeFromHash(): 'home' | 'annotate' | 'layout2' {
  const h = window.location.hash.replace(/^#\/?/, '')
  if (h.startsWith('annotate')) return 'annotate'
  if (h.startsWith('layout2') || h.startsWith('flex')) return 'layout2'
  return 'home'
}

function Root() {
  const [route, setRoute] = useState(routeFromHash)

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  if (route === 'annotate') return <AnnotatePage />
  if (route === 'layout2') return <AdaptiveLayoutPage />
  return <App />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
