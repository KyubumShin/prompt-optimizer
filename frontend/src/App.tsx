import { Routes, Route } from 'react-router-dom'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import NewRun from './pages/NewRun'
import RunDetail from './pages/RunDetail'
import IterationDetail from './pages/IterationDetail'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewRun />} />
        <Route path="/runs/:id" element={<RunDetail />} />
        <Route path="/runs/:id/iterations/:num" element={<IterationDetail />} />
      </Routes>
    </AppShell>
  )
}
