import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { APP_CONFIG } from '@/constants/config'

export const useDocumentTitle = (title, isLoading = false, defaultTitle = APP_CONFIG.NAME) => {
  const location = useLocation()
  
  useEffect(() => {
    if (title) {
      document.title = title
    }
    
    return () => {
      document.title = defaultTitle
    }
  }, [title, location.pathname, defaultTitle])
}
