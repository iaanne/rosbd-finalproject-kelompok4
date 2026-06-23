import { useState, useEffect, useCallback, useRef } from 'react'

const API = ''
const PAIRS = ['IDR', 'THB', 'MYR', 'SGD', 'PHP', 'VND']
const ALL = [...PAIRS, 'CNY', 'DXY']
const CLUSTER_NAMES = { 0: 'Pro-Dollar', 1: 'Transisi', 2: 'Mendekati Yuan' }
const CLUSTER_COLORS = { 0: '#E97366', 1: '#EAC26B', 2: '#72BC8F' }

async function api(path) {
  try {
    const r = await fetch(`${API}${path}`, { signal: AbortSignal.timeout(5000) })
    return r.ok ? r.json() : []
  } catch { return [] }
}

function fmt(v, dec = 2) {
  if (v == null || (typeof v === 'number' && v !== v)) return '—'
  return Number(v).toLocaleString('id-ID', { minimumFractionDigits: dec, maximumFractionDigits: dec })
}

function fmtPrice(v) {
  if (v == null || (typeof v === 'number' && v !== v)) return '—'
  if (v >= 1000) return fmt(v, 0)
  if (v >= 10) return fmt(v, 2)
  return fmt(v, 4)
}

function buildIKR(features, clusterInfo) {
  if (!features || !features.length) return [50, 'Sedang', 'orange']
  const last = features[0]
  const cDxy = last.corr_dxy_20d ?? 0.5
  const vol = last.volatility_20d ?? 0.2
  let penalty = 0
  if (clusterInfo) {
    const idr = clusterInfo.find(c => c.currency_pair === 'IDR')
    if (idr) {
      if (idr.is_outlier) penalty += 20
      if (idr.cluster_label === 2) penalty += 15
    }
  }
  const ikr = Math.min(100, Math.max(0, Math.round(cDxy * 50 + vol * 80 + penalty)))
  if (ikr >= 70) return [ikr, 'Tinggi', 'red']
  if (ikr >= 45) return [ikr, 'Sedang–Tinggi', 'orange']
  if (ikr >= 25) return [ikr, 'Sedang', 'blue']
  return [ikr, 'Rendah', 'green']
}

function Chip({ text, kind }) {
  const m = {
    red: 'bg-red-bg text-red-brand',
    orange: 'bg-orange-bg text-orange-brand',
    green: 'bg-green-bg text-green-brand',
    blue: 'bg-blue-bg text-blue-brand',
    gray: 'bg-gray-bg text-text-soft',
  }
  return <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold ${m[kind] || m.gray}`}>{text}</span>
}

function GaugeSVG({ val }) {
  const v = Math.max(0, Math.min(100, val))
  const cx = 110, cy = 115, r = 88
  const a = 180 + (v / 100) * 180
  const rad = a * Math.PI / 180
  const nx = cx + (r - 18) * Math.cos(rad)
  const ny = cy + (r - 18) * Math.sin(rad)
  const pt = (a2) => {
    const r2 = a2 * Math.PI / 180
    return [cx + r * Math.cos(r2), cy + r * Math.sin(r2)]
  }
  const [gx, gy] = pt(225)
  const [yx, yy] = pt(306)
  const arc = (x1, y1, x2, y2) => `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`
  return (
    <svg viewBox="0 0 220 135" width="100%" style={{ maxHeight: 135 }}>
      <path d={arc(cx - r, cy, gx, gy)} fill="none" stroke="#72BC8F" strokeWidth="16" strokeLinecap="round" />
      <path d={arc(gx, gy, yx, yy)} fill="none" stroke="#EAC26B" strokeWidth="16" />
      <path d={arc(yx, yy, cx + r, cy)} fill="none" stroke="#E97366" strokeWidth="16" strokeLinecap="round" />
      <line x1={cx} y1={cy} x2={nx.toFixed(1)} y2={ny.toFixed(1)} stroke="rgba(255,255,255,0.85)" strokeWidth="3" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="6" fill="rgba(255,255,255,0.85)" />
      <text x="16" y={cy + 3} fontSize="10" fill="rgba(255,255,255,0.3)">0</text>
      <text x="195" y={cy + 3} fontSize="10" fill="rgba(255,255,255,0.3)">100</text>
    </svg>
  )
}

function ScatterPlot({ data, features }) {
  if (!data || !data.length) return <div className="text-sm text-text-soft py-2">Belum ada data clustering</div>
  const W = 400, H = 320, PAD = 40
  const pts = data.map(c => {
    const featArr = (features || {})[c.currency_pair] || []
    const fd = featArr.length ? featArr[0] : {}
    return { pair: c.currency_pair, x: fd.corr_dxy_20d ?? 0.5, y: fd.corr_cny_20d ?? 0.3, vol: fd.volatility_20d ?? 0.2, label: c.cluster_label }
  })
  const xMin = Math.min(...pts.map(p => p.x)) - 0.1, xMax = Math.max(...pts.map(p => p.x)) + 0.1
  const yMin = Math.min(...pts.map(p => p.y)) - 0.1, yMax = Math.max(...pts.map(p => p.y)) + 0.1
  const sx = (v) => PAD + ((v - xMin) / (xMax - xMin)) * (W - 2 * PAD)
  const sy = (v) => H - PAD - ((v - yMin) / (yMax - yMin)) * (H - 2 * PAD)
  return (
    <svg viewBox={`0 0 ${W} ${H + 20}`} width="100%" style={{ maxHeight: 340 }}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="rgba(255,255,255,0.1)" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="rgba(255,255,255,0.1)" />
      <text x={W / 2} y={H + 15} fontSize="9" fill="rgba(255,255,255,0.3)" textAnchor="middle">corr_dxy → ketergantungan USD</text>
      <text x={10} y={H / 2} fontSize="9" fill="rgba(255,255,255,0.3)" textAnchor="middle" transform={`rotate(-90 10 ${H / 2})`}>corr_cny → kedekatan Yuan</text>
      <text x={PAD} y={H - PAD + 14} fontSize="8" fill="rgba(255,255,255,0.3)">{fmt(xMin, 2)}</text>
      <text x={W - PAD} y={H - PAD + 14} fontSize="8" fill="rgba(255,255,255,0.3)" textAnchor="end">{fmt(xMax, 2)}</text>
      <text x={PAD - 6} y={PAD + 4} fontSize="8" fill="rgba(255,255,255,0.3)" textAnchor="end">{fmt(yMax, 2)}</text>
      <text x={PAD - 6} y={H - PAD + 4} fontSize="8" fill="rgba(255,255,255,0.3)" textAnchor="end">{fmt(yMin, 2)}</text>
      {pts.map(p => {
        const r = Math.max(8, Math.min(22, 8 + p.vol * 35))
        const col = p.pair === 'IDR' ? '#097fe8' : (CLUSTER_COLORS[p.label] || '#B0BEC5')
        return (
          <g key={p.pair}>
            <circle cx={sx(p.x)} cy={sy(p.y)} r={r} fill={col} fillOpacity="0.85" stroke="#fff" strokeWidth="1.5" />
            <text x={sx(p.x)} y={sy(p.y) + 0.4} fontSize="7" fill="#fff" textAnchor="middle" fontWeight="700">{p.pair}</text>
          </g>
        )
      })}
    </svg>
  )
}

function TrendChart({ features }) {
  if (!features || features.length < 2) return <div className="text-sm text-text-soft py-2">Data features IDR belum cukup</div>
  const W = 400, H = 200, PAD = 30
  const pts = features.filter(f => f.ts).sort((a, b) => new Date(a.ts) - new Date(b.ts))
  const cDxy = pts.map(p => p.corr_dxy_20d != null ? p.corr_dxy_20d : null).filter(v => v != null)
  const vol = pts.map(p => p.volatility_20d != null ? p.volatility_20d : null).filter(v => v != null)
  if (!cDxy.length && !vol.length) return <div className="text-sm text-text-soft py-2">Data corr_dxy & volatility belum tersedia (butuh 20+ titik data untuk rolling window)</div>
  const allV = [...cDxy, ...vol]
  let yMin = Math.min(...allV), yMax = Math.max(...allV)
  if (yMax - yMin < 0.1) { const m = (yMin + yMax) / 2; yMin = m - 0.25; yMax = m + 0.25 }
  const sx = (i) => PAD + (i / (pts.length - 1)) * (W - 2 * PAD)
  const sy = (v) => H - PAD - ((v - yMin) / (yMax - yMin)) * (H - 2 * PAD)
  const cDxyPath = cDxy.map((v, i) => `${i === 0 ? 'M' : 'L'} ${sx(i).toFixed(1)} ${sy(v).toFixed(1)}`).join(' ')
  const volPath = vol.map((v, i) => `${i === 0 ? 'M' : 'L'} ${sx(i).toFixed(1)} ${sy(v).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H + 10}`} width="100%" style={{ maxHeight: 210 }}>
      {yMax >= 0.6 && (
        <rect x={PAD} y={sy(0.6)} width={W - 2 * PAD} height={sy(0) - sy(0.6)} fill="rgba(233,115,102,.12)" rx="3" />
      )}
      {yMax >= 0.6 && (
        <text x={W - PAD - 2} y={sy(0.6) + 10} fontSize="7" fill="#E97366" textAnchor="end">zona ambang</text>
      )}
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="rgba(255,255,255,0.1)" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="rgba(255,255,255,0.1)" />
      <text x={W / 2} y={H + 6} fontSize="8" fill="rgba(255,255,255,0.3)" textAnchor="middle">waktu →</text>
      {cDxy.length > 1 && <path d={cDxyPath} fill="none" stroke="#097fe8" strokeWidth="2.5" />}
      {vol.length > 1 && <path d={volPath} fill="none" stroke="#D9730D" strokeWidth="2" strokeDasharray="4 3" />}
      {cDxy.length > 0 && <circle cx={sx(pts.length - 1)} cy={sy(cDxy[cDxy.length - 1])} r="3" fill="#097fe8" />}
      {vol.length > 0 && <circle cx={sx(pts.length - 1)} cy={sy(vol[vol.length - 1])} r="3" fill="#D9730D" />}
    </svg>
  )
}

function TC({ sym, price, pct, green }) {
  const cls = pct == null ? 'flat' : pct >= 0 ? 'up' : 'down'
  const clsMap = { up: 'text-green-brand', down: 'text-red-brand', flat: 'text-text-faint' }
  const arr = pct == null ? '–' : pct >= 0 ? '▴' : '▾'
  const ch = pct != null ? `${arr} ${Math.abs(pct).toFixed(2).replace('.', ',')}%` : '—'
  return (
    <div className="flex-none min-w-[108px] px-4 py-2.5 border-r border-border-soft text-center last:border-r-0" style={green ? { background: 'rgba(114,188,143,.08)' } : {}}>
      <div className="text-[11px] font-bold text-text-soft tracking-wide">{sym}</div>
      <div className="text-sm font-semibold tabular-nums mt-0.5">{fmtPrice(price)}</div>
      <div className={`text-[11px] font-semibold mt-px ${clsMap[cls]}`}>{ch}</div>
    </div>
  )
}

export default function App() {
  const [lens, setLens] = useState('investor')
  const [forex, setForex] = useState({})
  const [features, setFeatures] = useState({})
  const [cluster, setCluster] = useState([])
  const [notifs, setNotifs] = useState([])
  const [ikrVal, setIkrVal] = useState(50)
  const [ikrLabel, setIkrLabel] = useState('Sedang')
  const [ikrChip, setIkrChip] = useState('orange')
  const [time, setTime] = useState(new Date())
  const isInv = lens === 'investor'
  const mounted = useRef(true)

  const load = useCallback(async () => {
    if (!mounted.current) return
    const fx = {}
    await Promise.all(ALL.map(async p => { fx[p] = await api(`/api/forex-rates/${p}?limit=2`) }))
    setForex(fx)
    const fidr = await api('/api/features/IDR?limit=50')
    const allFeats = { IDR: fidr }
    const batches = await api('/api/batches?limit=5') || []
    const allClusterResults = {}
    for (const b of batches) {
      const r = await api(`/api/clustering-results/${b}`)
      if (r && r.length) {
        for (const c of r) {
          const key = c.currency_pair
          if (!allClusterResults[key] || new Date(c.ts) > new Date(allClusterResults[key].ts)) {
            allClusterResults[key] = c
          }
        }
      }
    }
    const latestCluster = Object.values(allClusterResults)
    setCluster(latestCluster)
    for (const c of latestCluster) {
      if (!allFeats[c.currency_pair]) allFeats[c.currency_pair] = await api(`/api/features/${c.currency_pair}?limit=1`)
    }
    setFeatures(allFeats)
    const n = await api('/api/notifications?limit=10')
    setNotifs(n || [])
    const [ik, il, ic] = buildIKR(fidr, latestCluster)
    setIkrVal(ik); setIkrLabel(il); setIkrChip(ic)
    setTime(new Date())
  }, [])

  useEffect(() => {
    load()
    const iv = setInterval(load, 60000)

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    let ws = null
    const connectWS = () => {
      ws = new WebSocket(`${protocol}//${window.location.host}/ws`)
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg) {
            const notif = {
              type: msg.type || 'notification',
              title: msg.title || msg.message || 'Update',
              message: msg.message || '',
              ts: msg.ts || new Date().toISOString(),
            }
            setNotifs(prev => [notif, ...prev].slice(0, 10))
            if (msg.type === 'clustering_done') load()
          }
        } catch {}
      }
      ws.onclose = () => {
        if (mounted.current) setTimeout(connectWS, 5000)
      }
      ws.onerror = () => ws.close()
    }
    connectWS()

    return () => { mounted.current = false; clearInterval(iv); if (ws) ws.close() }
  }, [load])

  const fxFeat = (p) => {
    const arr = features[p] || []
    return arr.length ? arr[0] : {}
  }

  const cny = forex.CNY || []
  const cnyCur = cny.length ? (cny[cny.length - 1].close || cny[cny.length - 1].open) : null
  const cnyPrev = cny.length >= 2 ? (cny[cny.length - 2].close || cny[cny.length - 2].open) : cnyCur

  const cells = []
  for (const p of PAIRS) {
    const d = forex[p] || []
    const cur = d.length ? (d[d.length - 1].close || d[d.length - 1].open) : null
    const prev = d.length >= 2 ? (d[d.length - 2].close || d[d.length - 2].open) : cur
    const pct = (cur && prev) ? ((cur - prev) / prev * 100) : null
    cells.push(<TC key={`usd-${p}`} sym={`${p}/USD`} price={cur} pct={pct} />)
  }
  for (const p of PAIRS) {
    const d = forex[p] || []
    const cur = d.length ? (d[d.length - 1].close || d[d.length - 1].open) : null
    const prev = d.length >= 2 ? (d[d.length - 2].close || d[d.length - 2].open) : cur
    let cross = null, crossPct = null
    if (cur != null && cnyCur != null) {
      cross = cur / cnyCur
      const crossPrev = (prev != null && cnyPrev != null) ? prev / cnyPrev : cross
      crossPct = crossPrev ? ((cross - crossPrev) / crossPrev * 100) : null
    }
    cells.push(<TC key={`cny-${p}`} sym={`${p}/CNY`} price={cross} pct={crossPct} green />)
  }
  for (const p of ['CNY', 'DXY']) {
    const d = forex[p] || []
    const cur = d.length ? (d[d.length - 1].close || d[d.length - 1].open) : null
    const prev = d.length >= 2 ? (d[d.length - 2].close || d[d.length - 2].open) : cur
    const pct = (cur && prev) ? ((cur - prev) / prev * 100) : null
    cells.push(<TC key={p} sym={p === 'CNY' ? 'CNY/USD' : 'DXY'} price={cur} pct={pct} />)
  }

  let kpiCards = []
  if (isInv) {
    const counts = {}, outliers = [], hedges = []
    for (const c of cluster) {
      counts[c.cluster_label] = (counts[c.cluster_label] || 0) + 1
      if (c.is_outlier) outliers.push(c.currency_pair)
      if (c.cluster_label === 2) hedges.push(c.currency_pair)
    }
    const cStr = [2, 1, 0].map(i => counts[i] || 0).join(' · ')
    let mostVol = '-', mostVolVal = 0
    for (const p of PAIRS) {
      const fd = fxFeat(p)
      const v = fd.volatility_20d || 0
      if (v > mostVolVal) { mostVolVal = v; mostVol = p }
    }
    const outC = outliers.length ? <Chip text={`${outliers.join(', ')} anomali`} kind="red" /> : 'Tidak ada'
    kpiCards = [
      { l: 'Komposisi cluster', v: cStr || '-', c: 'Pro-Dollar · Transisi · Yuan' },
      { l: 'Outlier hari ini', v: String(outliers.length), c: outC },
      { l: 'Paling volatil', v: mostVol, c: mostVolVal ? `volatility ${fmt(mostVolVal)}` : '-' },
      { l: 'Sinyal hedging aktif', v: String(hedges.length), c: hedges.length ? hedges.join(', ') : 'Tidak ada' },
    ]
  } else {
    const total = cluster.length || 6
    let idrRank = 1
    const ranked = [...cluster].sort((a, b) => (b.cluster_label === 2) - (a.cluster_label === 2) || (b.is_outlier ? 1 : 0) - (a.is_outlier ? 1 : 0))
    for (let i = 0; i < ranked.length; i++) { if (ranked[i].currency_pair === 'IDR') { idrRank = i + 1; break } }
    const idrCl = cluster.find(c => c.currency_pair === 'IDR')
    const corr = features.IDR?.length ? features.IDR[0].corr_dxy_20d : null
    const corrC = corr != null ? (corr > 0 ? '▲ naik' : '▼ turun') : '-'
    const status = idrCl?.is_outlier ? 'Kritis' : ikrVal >= 45 ? 'Waspada' : 'Aman'
    const statusC = idrCl?.is_outlier ? 'red' : ikrVal >= 45 ? 'orange' : 'green'
    kpiCards = [
      { l: 'Indeks Kerentanan IDR', v: String(ikrVal), c: <Chip text={ikrLabel} kind={ikrChip} /> },
      { l: 'Ranking IDR', v: `#${idrRank} / ${total}`, c: `paling rentan ke-${idrRank} ASEAN` },
      { l: 'Δ corr_dxy IDR', v: fmt(corr), c: corrC },
      { l: 'Status alert IDR', v: '—', c: <Chip text={status} kind={statusC} /> },
    ]
  }

  const alertPairs = []
  for (const c of cluster) {
    const fd = fxFeat(c.currency_pair)
    const vol = fd.volatility_20d || 0
    if (c.is_outlier || vol > 0.5) {
      alertPairs.push({ pair: c.currency_pair, label: c.is_outlier ? '⚠ outlier' : '↗ volatile' })
    }
  }
  const calloutType = isInv ? (cluster.some(c => c.is_outlier) ? 'kritis' : alertPairs.length ? 'warn' : null) : null

  const ranked = [...cluster].sort((a, b) => (b.cluster_label === 2) - (a.cluster_label === 2) || (b.is_outlier ? 1 : 0) - (a.is_outlier ? 1 : 0))

  const iconMap = { cluster_change: '⚠', clustering_done: '◉', outlier: '◉', high_volatility: '↗', forex_update: '↗', notification: 'ℹ', info: 'ℹ' }
  const kindMap = { cluster_change: 'red', clustering_done: 'orange', outlier: 'orange', high_volatility: 'orange', forex_update: 'blue', notification: 'blue', info: 'blue' }
  const bgMap = { red: ['rgba(233,115,102,.08)', '#E97366'], orange: ['rgba(222,146,85,.08)', '#DE9255'], blue: ['rgba(94,159,232,.1)', '#5E9FE8'] }

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 flex-shrink-0 bg-surface border-r border-border-soft p-6">
        <div className="sticky top-6">
          <h2 className="text-lg m-0 mb-0.5">📈 Monitoring</h2>
          <p className="text-xs text-text-soft m-0 mb-4">Dedolarisasi ASEAN</p>
          <hr className="border-none border-t border-border-soft my-4" />
          <p className="text-[11px] uppercase tracking-wide text-text-faint font-semibold m-0 mb-2">Pilih Dashboard</p>
          <button
            className={`block w-full text-left px-3.5 py-2.5 mb-1 border border-transparent rounded-lg bg-transparent text-text-soft text-sm font-semibold cursor-pointer transition-all duration-150 hover:text-white hover:bg-surface-hover ${lens === 'investor' ? '!bg-bg-dark !text-blue-brand shadow-md' : ''}`}
            onClick={() => setLens('investor')}
          >👤 Investor</button>
          <button
            className={`block w-full text-left px-3.5 py-2.5 mb-1 border border-transparent rounded-lg bg-transparent text-text-soft text-sm font-semibold cursor-pointer transition-all duration-150 hover:text-white hover:bg-surface-hover ${lens === 'bi' ? '!bg-bg-dark !text-blue-brand shadow-md' : ''}`}
            onClick={() => setLens('bi')}
          >🏛️ Bank Indonesia</button>
          <hr className="border-none border-t border-border-soft my-4" />
          <p className="text-xs text-text-soft my-1">🔄 Auto-refresh tiap 60 detik</p>
          <p className="text-xs text-text-soft my-1">⏱ {time.toLocaleTimeString('id-ID')}</p>
          <button
            className="block w-full py-2 mt-3 border border-border-soft rounded-lg bg-bg-dark text-text-soft text-sm font-semibold cursor-pointer transition-all duration-150 hover:border-blue-brand hover:text-white"
            onClick={load}
          >↻ Refresh Data</button>
        </div>
      </aside>

      <main className="flex-1 max-w-7xl p-7 pb-16">
        <div className="flex items-center justify-between gap-4 mb-2 flex-wrap">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">📈</span>
            <div>
              <h1 className="text-[22px] m-0">Monitoring Dedolarisasi ASEAN</h1>
              <div className="text-text-soft text-sm mt-px">
                <span className="inline-flex items-center text-xs font-semibold text-text-soft">
                  <span className="w-2 h-2 rounded-full bg-green-brand inline-block mr-1.5 align-middle shadow-[0_0_0_0_rgba(114,188,143,0.6)]" style={{ animation: 'pulse-dot 1.8s infinite' }}></span>
                  LIVE
                </span>
                · 6 mata uang ASEAN + CNY + DXY · update tiap 60 detik
              </div>
            </div>
          </div>
          <div className="text-xs font-semibold px-4 py-2 rounded-lg border border-border-soft bg-surface whitespace-nowrap">
            {isInv ? '👤 Investor' : '🏛️ Bank Indonesia'}
          </div>
        </div>

        <div className="flex gap-0 overflow-x-auto border border-border-soft rounded-xl bg-surface my-3.5 shadow-lg ticker">
          {cells}
        </div>

        <div className="grid grid-cols-4 gap-3.5 mb-3.5 max-md:grid-cols-2">
          {kpiCards.map((k, i) => (
            <div className="border border-border-soft rounded-xl bg-surface shadow-lg p-3.5" key={i}>
              <div className="text-xs text-text-soft font-semibold">{k.l}</div>
              <div className="text-2xl font-bold tracking-tight mt-1">{k.v}</div>
              <div className="text-xs text-text-soft mt-1">{k.c}</div>
            </div>
          ))}
        </div>

        {calloutType && isInv && (
          <div className={`flex items-start gap-4 px-4 py-3.5 rounded-xl mb-4 ${
            calloutType === 'kritis' ? 'bg-red-bg border border-red-800/25' : 'bg-orange-bg border border-orange-800/25'
          }`}>
            <span className="text-lg flex-shrink-0 mt-px">{calloutType === 'kritis' ? '🚨' : '⚠️'}</span>
            <div>
              <div className="text-sm font-bold">
                {calloutType === 'kritis' ? 'Perhatian — perlu rebalancing portfolio' : 'Waspada — pergerakan signifikan terdeteksi'}
              </div>
              <div className="text-xs text-text-soft mt-0.5 leading-normal">
                {alertPairs.map(a => `<strong>${a.pair}</strong> (${a.label})`).join(', ') + '. Pantau perkembangan dan pertimbangkan hedging.'}
              </div>
            </div>
          </div>
        )}

        <div className="h-4" />

        <div className="grid grid-cols-12 gap-3.5 mb-3.5">
          <div className="col-span-7 max-lg:col-span-12 border border-border-soft rounded-xl bg-surface shadow-lg p-4">
            <h3 className="text-sm font-semibold m-0 mb-0.5">Peta Cluster Mata Uang</h3>
            <p className="text-xs text-text-soft m-0 mb-3">
              {isInv ? 'Kandidat diversifikasi; hindari kuadran Pro-Dollar (kanan-bawah).' : 'Pantau apakah IDR (biru) bergeser ke kuadran rentan dibanding peer ASEAN.'}
            </p>
            <ScatterPlot data={cluster} features={features} />
            <div className="flex flex-wrap gap-3 mt-2 text-xs text-text-soft">
              <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full inline-block flex-none" style={{ background: '#E97366' }} />Pro-Dollar</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full inline-block flex-none" style={{ background: '#EAC26B' }} />Transisi</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full inline-block flex-none" style={{ background: '#72BC8F' }} />Mendekati Yuan</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full inline-block flex-none" style={{ background: '#097fe8' }} />IDR (fokus)</span>
              <span className="text-text-faint">○ ukuran = volatilitas</span>
            </div>
          </div>
          <div className="col-span-5 max-lg:col-span-12 border border-border-soft rounded-xl bg-surface shadow-lg p-4">
            <h3 className="text-sm font-semibold m-0 mb-0.5">Indeks Kerentanan IDR (IKR)</h3>
            <p className="text-xs text-text-soft m-0 mb-3">
              {isInv ? 'Risiko IDR untuk portofolio berbasis Rupiah.' : 'Seberapa rentan IDR & apakah mendekati ambang intervensi.'}
            </p>
            <div className="flex items-center gap-3.5 flex-wrap">
              <GaugeSVG val={ikrVal} />
              <div className="text-center">
                <div className="text-4xl font-bold tracking-tight leading-none">{ikrVal}</div>
                <Chip text={ikrLabel} kind={ikrChip} />
              </div>
            </div>
            {ranked.length > 0 && (
              <ul className="list-none p-0 mt-2.5">
                {ranked.slice(0, 6).map((c, i) => (
                  <li key={c.currency_pair} className={`flex justify-between text-sm py-1.5 border-b border-border-soft last:border-b-0 ${c.currency_pair === 'IDR' ? 'font-bold text-blue-brand' : 'text-text-soft'}`}>
                    <span>{i + 1}. {c.currency_pair}</span>
                    <span>{c.cluster_name || CLUSTER_NAMES[c.cluster_label] || '-'}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="grid grid-cols-12 gap-3.5 mb-3.5">
          <div className="col-span-7 max-lg:col-span-12 border border-border-soft rounded-xl bg-surface shadow-lg p-4">
            <h3 className="text-sm font-semibold m-0 mb-0.5">Tren corr_dxy & Volatilitas IDR</h3>
            <p className="text-xs text-text-soft m-0 mb-3">
              {isInv ? 'Timing hedging saat garis menembus pita ambang.' : 'Early warning saat ketergantungan USD / volatilitas melonjak.'}
            </p>
            <TrendChart features={features.IDR} />
            <div className="flex flex-wrap gap-3 mt-2 text-xs text-text-soft">
              <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full inline-block flex-none" style={{ background: '#097fe8' }} />corr_dxy IDR</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full inline-block flex-none" style={{ background: '#D9730D' }} />volatility_20d IDR</span>
            </div>
          </div>
          <div className="col-span-5 max-lg:col-span-12 border border-border-soft rounded-xl bg-surface shadow-lg p-4">
            <h3 className="text-sm font-semibold m-0 mb-0.5">🔔 Alert Feed <span className="text-xs font-medium text-text-soft">(WebSocket)</span></h3>
            <p className="text-xs text-text-soft m-0 mb-3">
              {isInv ? 'Trigger rebalancing / hedging.' : 'Trigger evaluasi intervensi.'}
            </p>
            {notifs.length > 0 ? (
              notifs.slice(0, 8).map((n, i) => {
                const ntype = n.type || 'info'
                const k = kindMap[ntype] || 'blue'
                const [bg, fg] = bgMap[k]
                const icon = iconMap[ntype] || 'ℹ'
                const title = n.title || n.message || 'Update'
                const ts = n.ts || ''
                const d = (() => {
                  try {
                    if (!ts) return '-'
                    const dt = new Date(ts.replace('Z', '+00:00'))
                    const now = new Date()
                    const isToday = dt.toDateString() === now.toDateString()
                    return isToday
                      ? dt.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
                      : dt.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
                  } catch { return '-' }
                })()
                return (
                  <div className="flex gap-2.5 p-2.5 rounded-lg bg-bg-dark mb-2" key={n.id || `${ntype}-${i}`}>
                    <div className="w-[26px] h-[26px] rounded-lg grid place-items-center flex-shrink-0 text-sm" style={{ background: bg, color: fg }}>{icon}</div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold leading-tight truncate">{title}</div>
                      <div className="text-[11px] text-text-soft mt-0.5">{d}</div>
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="text-sm text-text-soft py-2">Belum ada notifikasi</div>
            )}
          </div>
        </div>

        <div className="border border-border-soft rounded-xl bg-surface shadow-lg overflow-hidden">
          <div className="p-3.5 pb-0">
            <h3 className="text-sm font-semibold m-0 mb-0.5">Tabel Outlier / Anomali (DBSCAN)</h3>
            <p className="text-xs text-text-soft m-0 mb-3">
              {isInv ? 'Mata uang yang harus diwaspadai sebelum mengambil posisi.' : 'Deteksi tekanan tak normal pada IDR & kawasan.'}
            </p>
          </div>
          {cluster.length > 0 ? (
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="text-left px-3.5 py-2.5 text-xs text-text-soft border-b border-border-soft font-semibold bg-surface-hover">Mata uang</th>
                  <th className="text-left px-3.5 py-2.5 text-xs text-text-soft border-b border-border-soft font-semibold bg-surface-hover">Cluster</th>
                  <th className="text-left px-3.5 py-2.5 text-xs text-text-soft border-b border-border-soft font-semibold bg-surface-hover">corr_dxy</th>
                  <th className="text-left px-3.5 py-2.5 text-xs text-text-soft border-b border-border-soft font-semibold bg-surface-hover">corr_cny</th>
                  <th className="text-left px-3.5 py-2.5 text-xs text-text-soft border-b border-border-soft font-semibold bg-surface-hover">volatility</th>
                  <th className="text-left px-3.5 py-2.5 text-xs text-text-soft border-b border-border-soft font-semibold bg-surface-hover">Status</th>
                </tr>
              </thead>
              <tbody>
                {cluster.map(c => {
                  const fd = fxFeat(c.currency_pair)
                  const cname = c.cluster_name || CLUSTER_NAMES[c.cluster_label] || '-'
                  const cKind = c.cluster_label === 0 ? 'red' : c.cluster_label === 1 ? 'orange' : 'green'
                  const sKind = c.is_outlier ? 'red' : 'gray'
                  return (
                    <tr key={c.currency_pair}>
                      <td className="px-3.5 py-2.5 text-sm border-b border-border-soft"><strong>{c.currency_pair}</strong></td>
                      <td className="px-3.5 py-2.5 text-sm border-b border-border-soft"><Chip text={cname} kind={cKind} /></td>
                      <td className="px-3.5 py-2.5 text-sm border-b border-border-soft">{fmt(fd.corr_dxy_20d)}</td>
                      <td className="px-3.5 py-2.5 text-sm border-b border-border-soft">{fmt(fd.corr_cny_20d)}</td>
                      <td className="px-3.5 py-2.5 text-sm border-b border-border-soft">{fmt(fd.volatility_20d)}</td>
                      <td className="px-3.5 py-2.5 text-sm border-b border-border-soft"><Chip text={c.is_outlier ? 'Outlier' : 'Normal'} kind={sKind} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <div className="text-sm text-text-soft p-5">Belum ada data clustering — jalankan POST /api/run-clustering</div>
          )}
        </div>

        <p className="text-xs text-text-faint text-center mt-6">
          ⏱ Data diperbarui otomatis — {time.toLocaleDateString('id-ID')} {time.toLocaleTimeString('id-ID')}
        </p>
      </main>
    </div>
  )
}
