import { useCallback, useEffect, useState } from 'react'

export type Edition = 'day' | 'night'

function currentEdition(): Edition {
  if (typeof document === 'undefined') return 'day'
  return document.documentElement.classList.contains('night') ? 'night' : 'day'
}

export function useTheme() {
  const [edition, setEdition] = useState<Edition>(currentEdition)

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('night', edition === 'night')
    root.classList.remove('light', 'dark')
    root.style.colorScheme = edition === 'night' ? 'dark' : 'light'
    try {
      localStorage.setItem('yv-edition', edition)
    } catch {
      /* storage may be unavailable */
    }
    const meta = document.querySelector('meta[name="theme-color"]')
    meta?.setAttribute('content', edition === 'night' ? '#17120d' : '#e8d6b5')
  }, [edition])

  const toggle = useCallback(() => {
    setEdition((value) => (value === 'day' ? 'night' : 'day'))
  }, [])

  return { edition, toggle }
}
