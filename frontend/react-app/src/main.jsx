import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import TokenGate from './TokenGate.jsx'

createRoot(document.getElementById('root')).render(
  // <StrictMode>
    <TokenGate>
      <App />
    </TokenGate>
  // </StrictMode>,
)
