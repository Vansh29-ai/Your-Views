import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export function NotFound() {
  return (
    <div className="container-paper py-20 text-center">
      <p className="kicker">Page Not in This Edition</p>
      <h1 className="masthead mt-4 text-[clamp(4rem,14vw,9rem)] leading-none text-ink">404</h1>
      <p className="mx-auto mt-2 max-w-md font-body text-[15px] leading-relaxed text-ink-soft">
        This page appears to have been left out of the print run. It may have been re-typeset, or
        the address was set incorrectly.
      </p>
      <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
        <Link to="/" className="paper-button-solid">
          <ArrowLeft size={12} /> Return to the front page
        </Link>
        <Link to="/dashboard" className="paper-button">
          Browse the archive
        </Link>
      </div>
    </div>
  )
}
