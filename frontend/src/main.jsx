import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

/* ── Design System Styles (order matters) ──── */
import './styles/tokens.css'
import './styles/global.css'
import './styles/animations.css'
import './styles/shared.css'
import './styles/responsive.css'
/* Component styles imported where used */

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
