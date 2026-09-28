import { Activity, BrainCircuit, ChartNoAxesCombined, Newspaper, Waypoints } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type ServiceVisual = 'fingerprint' | 'anomaly' | 'news' | 'correlation' | 'risk'
export interface Service { number: string; title: string; description: string; why: string; contributes: string; icon: LucideIcon; href: string; visual: ServiceVisual }

// The five core modules (design spec §17), in pipeline order. Each links to the page that shows it on real data.
export const services: Service[] = [
  { number: '01', title: 'Behavioural Fingerprinting', visual: 'fingerprint', icon: BrainCircuit, href: '/behavioural-fingerprint',
    description: 'Learns each instrument’s own normal: a rolling robust baseline (median and MAD) for returns, volume, volatility and range.',
    why: 'An unusual day for one asset is an ordinary day for another. Deviation is measured against the asset itself, not a market-wide rule.',
    contributes: 'Feeds the anomaly ensemble and the risk score' },
  { number: '02', title: 'Anomaly Detection', visual: 'anomaly', icon: Activity, href: '/anomaly-detection',
    description: 'Combines a statistical z-score, the behavioural fingerprint and an Isolation Forest trained only on earlier sessions.',
    why: 'Each flag lists the dimensions that moved and how far, so an alert can be checked instead of trusted.',
    contributes: 'Decides which sessions need context' },
  { number: '03', title: 'News Intelligence', visual: 'news', icon: Newspaper, href: '/news-analysis',
    description: 'Links financial news to the instrument it is about and measures the sentiment of its language.',
    why: 'Price moves rarely explain themselves. Linked, dated news is the first place to look for context.',
    contributes: 'Supplies events and sentiment to correlation' },
  { number: '04', title: 'Cross-Source Correlation', visual: 'correlation', icon: Waypoints, href: '/event-correlation',
    description: 'Aligns flagged sessions with asset-linked news published around the trading session, scored for timing, asset match and strength.',
    why: 'It shows what happened at the same time, stated as temporal alignment, never as cause.',
    contributes: 'Connects market signals to events' },
  { number: '05', title: 'Explainable Risk', visual: 'risk', icon: ChartNoAxesCombined, href: '/risk-evidence',
    description: 'A transparent weighted score with every component’s contribution and a timestamped evidence chain.',
    why: 'A risk signal is only useful if you can see why it exists and which evidence supports it.',
    contributes: 'Summarises the chain for the analyst' },
]
