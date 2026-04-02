import React from 'react'
import ReactDOM from 'react-dom/client'
import './i18n'
import { AuthProvider } from './AuthContext'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <AuthProvider>
    <App />
  </AuthProvider>
)
