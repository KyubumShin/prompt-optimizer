import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/new', label: 'New Run' },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-indigo-600">
            Prompt Optimizer
          </Link>
          <nav className="flex gap-4">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  location.pathname === item.path
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        {children}
      </main>
    </div>
  )
}
