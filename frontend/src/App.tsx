import { BrowserRouter as Router, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { CardDetailPage } from '@/pages/CardDetailPage'
import { CollectionPage } from '@/pages/CollectionPage'
import { CatalogPage } from '@/pages/CatalogPage'
import { OverviewPage } from '@/pages/OverviewPage'
import { WishlistPage } from '@/pages/WishlistPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<OverviewPage />} />
          <Route path="collection" element={<CollectionPage />} />
          <Route path="collection/:id" element={<CardDetailPage />} />
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="wishlist" element={<WishlistPage />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
