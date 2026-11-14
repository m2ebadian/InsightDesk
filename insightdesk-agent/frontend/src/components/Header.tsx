import { NavLink } from 'react-router-dom'
import type { Health } from '../types'

interface Props {
  health: Health | null
  offline: boolean
}

export default function Header({ health, offline }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to="/" className="brand">
          <img src="/favicon.svg" alt="" width={26} height={26} />
          <span>InsightDesk</span>
        </NavLink>

        <nav>
          <NavLink to="/" end>
            Ask
          </NavLink>
          <NavLink to="/documents">Documents</NavLink>
          <NavLink to="/insights">Insights</NavLink>
        </nav>

        <div className={`index-status ${offline ? 'offline' : ''}`} role="status">
          {offline
            ? 'API offline'
            : health
              ? `${health.documents} docs · ${health.indexed_passages} passages`
              : 'Connecting…'}
        </div>
      </div>
    </header>
  )
}
