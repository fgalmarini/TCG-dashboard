import { Moon, Sun } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useDarkMode } from '@/lib/useDarkMode'

function navLinkClass(isActive: boolean): string {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground'
  }`
}

export function NavBar() {
  const [isDark, setIsDark] = useDarkMode()

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <span className="text-base font-semibold">TCG Dashboard</span>
        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={({ isActive }) => navLinkClass(isActive)}>
            Overview
          </NavLink>
          <NavLink to="/collection" className={({ isActive }) => navLinkClass(isActive)}>
            Collection
          </NavLink>
          <NavLink to="/catalog" className={({ isActive }) => navLinkClass(isActive)}>
            Catalog
          </NavLink>
          <NavLink to="/wishlist" className={({ isActive }) => navLinkClass(isActive)}>
            Wishlist
          </NavLink>
        </nav>
        <Button variant="ghost" size="icon" onClick={() => setIsDark(!isDark)} aria-label="Cambiar tema">
          {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </Button>
      </div>
    </header>
  )
}
