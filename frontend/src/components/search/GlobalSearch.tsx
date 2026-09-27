import { useEffect, useId, useRef, useState } from 'react'
import { Loader2, Search } from 'lucide-react'
import { searchInstruments } from '../../services/intelligenceApi'
import type { InstrumentSummary } from '../../types/api'
import { ASSET_CLASS_LABEL } from '../../utils/format'

const DEBOUNCE_MS = 250

type State = { status: 'idle' } | { status: 'loading' } | { status: 'ok'; items: InstrumentSummary[]; next: string | null; masterEmpty: boolean } | { status: 'error'; message: string }

// Search is Aventra's primary discovery mechanism: any instrument in the Instrument Master (synced from real listings).
export function GlobalSearch({ onSelect, placeholder = 'Search stocks, ETFs, funds, crypto, forex…', autoFocus = false, compact = false }:
  { onSelect?: (item: InstrumentSummary) => void; placeholder?: string; autoFocus?: boolean; compact?: boolean }) {
  const [query, setQuery] = useState('')
  const [state, setState] = useState<State>({ status: 'idle' })
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const listId = useId()
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const q = query.trim()
    if (!q) { setState({ status: 'idle' }); return }
    const controller = new AbortController()
    const timer = setTimeout(() => {
      setState({ status: 'loading' })
      searchInstruments(q, {}, null, controller.signal)
        .then((data) => { setState({ status: 'ok', items: data.items, next: data.next_cursor, masterEmpty: data.master_size === 0 }); setActive(0) })
        .catch((reason: unknown) => { if (!controller.signal.aborted) setState({ status: 'error', message: reason instanceof Error ? reason.message : 'Search is unavailable.' }) })
    }, DEBOUNCE_MS)
    return () => { clearTimeout(timer); controller.abort() }
  }, [query])

  useEffect(() => {
    const close = (event: MouseEvent) => { if (box.current && !box.current.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const items = state.status === 'ok' ? state.items : []
  const choose = (item: InstrumentSummary) => {
    setOpen(false)
    setQuery('')
    if (onSelect) onSelect(item)
    else window.location.assign(`/intelligence?id=${encodeURIComponent(item.instrument_id)}`)
  }
  const loadMore = async () => {
    if (state.status !== 'ok' || !state.next) return
    setLoadingMore(true)
    try {
      const data = await searchInstruments(query.trim(), {}, state.next)
      setState({ status: 'ok', items: [...state.items, ...data.items], next: data.next_cursor, masterEmpty: state.masterEmpty })
    } finally { setLoadingMore(false) }
  }
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowDown') { event.preventDefault(); setOpen(true); setActive((i) => Math.min(i + 1, items.length - 1)) }
    else if (event.key === 'ArrowUp') { event.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
    else if (event.key === 'Enter' && items[active]) { event.preventDefault(); choose(items[active]) }
    else if (event.key === 'Escape') setOpen(false)
  }

  return <div className={`global-search ${compact ? 'compact' : ''}`} ref={box}>
    <label className="sr-only" htmlFor={`${listId}-input`}>Search instruments</label>
    <div className="search-field"><Search size={15} aria-hidden="true" />
      <input id={`${listId}-input`} type="search" role="combobox" aria-expanded={open && query.trim() !== ''} aria-controls={listId} aria-autocomplete="list"
        aria-activedescendant={items[active] ? `${listId}-${active}` : undefined} value={query} placeholder={placeholder} autoFocus={autoFocus} autoComplete="off" maxLength={64}
        onChange={(event) => { setQuery(event.target.value); setOpen(true) }} onFocus={() => setOpen(true)} onKeyDown={onKeyDown} />
      {state.status === 'loading' && <Loader2 size={14} className="spinning" aria-label="Searching" />}
    </div>
    {open && query.trim() !== '' && <div className="search-results" id={listId} role="listbox">
      {state.status === 'loading' && <p className="search-state" role="status">Searching the instrument master…</p>}
      {state.status === 'error' && <p className="search-state error" role="alert">{state.message}</p>}
      {state.status === 'ok' && state.masterEmpty && <p className="search-state">The instrument master is empty — run the listing sync on the server.</p>}
      {state.status === 'ok' && !state.masterEmpty && items.length === 0 && <p className="search-state">No instruments match “{query.trim()}”.</p>}
      {items.map((item, index) => <button type="button" role="option" id={`${listId}-${index}`} aria-selected={index === active} key={item.instrument_id}
        className={`search-option ${index === active ? 'active' : ''}`} onMouseEnter={() => setActive(index)} onClick={() => choose(item)}>
        <span className="search-name">{item.name}</span>
        <span className="search-meta"><b>{item.symbol}</b>{item.exchange ? ` · ${item.exchange}` : ''}{item.currency ? ` · ${item.currency}` : ''}{item.status === 'inactive' ? ' · inactive' : ''}</span>
        <span className={`class-badge class-${item.asset_class}`}>{ASSET_CLASS_LABEL[item.asset_class] ?? item.asset_class}</span>
      </button>)}
      {state.status === 'ok' && state.next && <button type="button" className="search-more" onClick={() => void loadMore()} disabled={loadingMore}>{loadingMore ? 'Loading…' : 'Load more results'}</button>}
    </div>}
  </div>
}
