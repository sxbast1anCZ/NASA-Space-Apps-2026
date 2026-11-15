import { Database, ExternalLink, Flame, Info, Layers, Orbit, Rocket, Satellite, ShieldAlert, X } from 'lucide-react'
import { useState } from 'react'
import type { Lang } from './i18n.ts'
import { gibsTile, type Basemap } from './MapStage.tsx'

/** BRASA mark: a flame inside a satellite orbit. Drawn inline so it stays sharp at any size. */
export function BrasaLogo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="T1">
      <defs>
        <linearGradient id="bg-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#1c2440" /><stop offset="1" stopColor="#0a0e1c" />
        </linearGradient>
        <linearGradient id="fl-g" x1="0.5" y1="1" x2="0.5" y2="0">
          <stop offset="0" stopColor="#ff2d55" /><stop offset="0.45" stopColor="#ff7a1a" /><stop offset="1" stopColor="#ffd166" />
        </linearGradient>
        <radialGradient id="gl-g" cx="0.5" cy="0.62" r="0.5">
          <stop offset="0" stopColor="#ff7a1a" stopOpacity="0.55" /><stop offset="1" stopColor="#ff7a1a" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect x="1" y="1" width="62" height="62" rx="16" fill="url(#bg-g)" stroke="rgba(255,255,255,.14)" />
      <circle cx="32" cy="38" r="22" fill="url(#gl-g)" />
      <ellipse cx="32" cy="34" rx="25" ry="9" fill="none" stroke="#7aa7ff" strokeOpacity="0.55" strokeWidth="1.6" transform="rotate(-18 32 34)" />
      <path d="M32 11c2 7 11 11.5 11 22.5C43 41 38 47 32 47s-11-6-11-13.5c0-5.4 2.8-8.6 5.2-11 .4 3.6 2 5.6 4.1 6.4C29.6 22.8 30.4 16.6 32 11Z" fill="url(#fl-g)" />
      <path d="M32 30c1.2 3.2 5 5 5 9.2 0 3.4-2.3 5.8-5 5.8s-5-2.4-5-5.6c0-2.6 1.5-4 2.6-5 .2 1.4.9 2.2 1.7 2.5-.3-2.6.1-4.9.7-6.9Z" fill="#fff4d6" />
      <circle cx="54.5" cy="26.8" r="3.2" fill="#cfe0ff" stroke="#0a0e1c" strokeWidth="1.2" />
    </svg>
  )
}

/** Event badge. The official Space Apps logo shows when a copy is placed at public/logos/space-apps.png. */
export function EventBadge({ lang, onInfo }: { lang: Lang; onInfo: () => void }) {
  const [official, setOfficial] = useState(true)
  return (
    <button className="event glass" onClick={onInfo} title={lang === 'es' ? 'Acerca del proyecto' : 'About the project'}>
      {official
        ? <img src="/logos/space-apps.png" alt="NASA Space Apps Challenge" onError={() => setOfficial(false)} />
        : <span className="event-mark"><Rocket size={15} /></span>}
      <span className="event-text">
        <b>NASA Space Apps Challenge 2026</b>
        <small>{lang === 'es' ? 'Antofagasta · Desafío: Armonización de hotspots MODIS y VIIRS' : 'Antofagasta · Challenge: Harmonization of MODIS and VIIRS Hot Spots'}</small>
      </span>
      <Info size={15} className="event-info" />
    </button>
  )
}

export function Splash({ lang }: { lang: Lang }) {
  return (
    <div className="splash">
      <div className="splash-logo"><BrasaLogo size={88} /></div>
      <h1>T1</h1>
      <p>{lang === 'es' ? 'Cargando 26 años de focos armonizados…' : 'Loading 26 years of harmonized hotspots…'}</p>
      <div className="splash-bar"><i /></div>
      <small>NASA Space Apps Challenge 2026</small>
    </div>
  )
}

const BASEMAPS: { id: Basemap; es: string; en: string; noteEs: string; noteEn: string }[] = [
  { id: 'truecolor', es: 'Imagen real NASA', en: 'NASA real imagery', noteEs: 'Color verdadero del día · VIIRS / MODIS', noteEn: 'True colour of the day · VIIRS / MODIS' },
  { id: 'firecolor', es: 'Falso color incendios', en: 'Fire false colour', noteEs: 'Bandas infrarrojas: fuego y cicatrices', noteEn: 'Infrared bands: fire and burn scars' },
  { id: 'satellite', es: 'Satélite alta resolución', en: 'High-res satellite', noteEs: 'Mosaico Esri, sin fecha', noteEn: 'Esri mosaic, no date' },
  { id: 'dark', es: 'Mapa', en: 'Map', noteEs: 'Claro u oscuro según el tema', noteEn: 'Light or dark, follows the theme' },
]
const THUMB: Record<Basemap, (d: string) => string> = {
  truecolor: (d) => gibsTile('truecolor', d, '5', '18', '10'),
  firecolor: (d) => gibsTile('firecolor', d, '5', '18', '10'),
  satellite: () => 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/5/18/10',
  dark: () => `https://a.basemaps.cartocdn.com/${document.documentElement.dataset.theme === 'light' ? 'light_all' : 'dark_all'}/5/10/18.png`,
}

export function BasemapPicker({ lang, value, date, onChange, onClose }: { lang: Lang; value: Basemap; date: string; onChange: (b: Basemap) => void; onClose: () => void }) {
  return (
    <div className="basemaps glass" role="dialog">
      <div className="basemaps-head"><Layers size={14} /><b>{lang === 'es' ? 'Mapa base' : 'Basemap'}</b><button onClick={onClose}><X size={14} /></button></div>
      {BASEMAPS.map((b) => (
        <button key={b.id} className={`bm ${value === b.id ? 'on' : ''}`} onClick={() => onChange(b.id)}>
          <img src={THUMB[b.id](date)} alt="" loading="lazy" />
          <span><b>{lang === 'es' ? b.es : b.en}</b><small>{lang === 'es' ? b.noteEs : b.noteEn}</small></span>
        </button>
      ))}
    </div>
  )
}

export function About({ lang, onClose }: { lang: Lang; onClose: () => void }) {
  const es = lang === 'es'
  return (
    <div className="onboard" onClick={onClose}>
      <div className="about glass" onClick={(e) => e.stopPropagation()} role="dialog">
        <button className="close" onClick={onClose}><X size={16} /></button>
        <div className="about-head">
          <BrasaLogo size={64} />
          <div>
            <span className="eyebrow">NASA Space Apps Challenge 2026 · Antofagasta</span>
            <h1>T1</h1>
            <p>{es ? 'Calendario armonizado de actividad de fuego para Chile y Argentina, 2000–2026.' : 'Harmonized burn activity calendar for Chile and Argentina, 2000–2026.'}</p>
          </div>
        </div>
        <div className="about-grid">
          <div><Orbit size={18} /><b>{es ? 'El problema' : 'The problem'}</b>
            <p>{es ? 'MODIS (1 km, desde 2000) se retira y VIIRS (375 m, desde 2012) detecta 4 a 6 veces más puntos. Sin armonizar, el registro histórico no se puede comparar.' : 'MODIS (1 km, since 2000) is retiring and VIIRS (375 m, since 2012) detects 4 to 6 times more points. Without harmonization the record cannot be compared.'}</p></div>
          <div><Satellite size={18} /><b>{es ? 'Armonización' : 'Harmonization'}</b>
            <p>{es ? 'Cada foco MODIS se convierte a equivalente VIIRS con factores por región y mes, calibrados en 2012–2021 donde ambos sensores se superponen.' : 'Every MODIS hotspot is converted to a VIIRS equivalent with region and month factors calibrated on 2012–2021, where both sensors overlap.'}</p></div>
          <div><Flame size={18} /><b>{es ? 'Pronóstico' : 'Outlook'}</b>
            <p>{es ? 'Un modelo LightGBM por país estima dónde es más probable la actividad de fuego el día siguiente, y explica cada alerta. No predice igniciones ni hectáreas.' : 'One LightGBM model per country estimates where fire activity is most likely the next day, and explains every alert. It does not predict ignitions or hectares.'}</p></div>
          <div><ShieldAlert size={18} /><b>{es ? 'Límites' : 'Limits'}</b>
            <p>{es ? 'Un foco es una detección térmica, no un incendio. La ausencia de focos no prueba ausencia de fuego (nubes, pasadas). Los meses recientes son provisionales (NRT).' : 'A hotspot is a thermal detection, not a fire. No hotspot does not prove no fire (clouds, overpasses). Recent months are provisional (NRT).'}</p></div>
        </div>
        <h3><Database size={15} /> {es ? 'Fuentes' : 'Sources'}</h3>
        <ul className="credits">
          <li><b>NASA FIRMS</b> MODIS C6.1 · VIIRS S-NPP, NOAA-20, NOAA-21 <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noreferrer"><ExternalLink size={12} /></a></li>
          <li><b>NASA EOSDIS GIBS</b> {es ? 'imágenes de color real y falso color' : 'true and false colour imagery'} <a href="https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api" target="_blank" rel="noreferrer"><ExternalLink size={12} /></a></li>
          <li><b>IGN Argentina</b> · <b>geoBoundaries</b> {es ? 'límites regionales' : 'region boundaries'}</li>
          <li><b>Open-Meteo</b> {es ? 'viento del día en vivo' : 'wind of the live day'} · <b>Esri</b>, <b>CARTO</b>, <b>OpenStreetMap</b> {es ? 'mapas base' : 'basemaps'}</li>
          <li>{es ? 'Desafío propuesto por' : 'Challenge by'} <b>CONAE</b> (Comisión Nacional de Actividades Espaciales, Argentina)</li>
        </ul>
        <p className="foot">{es ? 'NASA no respalda este proyecto. Los nombres de agencias se citan solo como fuentes de datos.' : 'NASA does not endorse this project. Agency names are cited as data sources only.'}</p>
      </div>
    </div>
  )
}
