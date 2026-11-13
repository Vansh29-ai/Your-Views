import { Route, Routes } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { AppShell } from '@/components/layout/AppShell'
import { About } from '@/pages/About'
import { Dashboard } from '@/pages/Dashboard'
import { EventDetails } from '@/pages/EventDetails'
import { Home } from '@/pages/Home'
import { NotFound } from '@/pages/NotFound'
import { SearchPage } from '@/pages/SearchPage'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Home />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="events/:code" element={<EventDetails />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
