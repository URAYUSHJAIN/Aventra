import { Activity, BrainCircuit, ChartNoAxesCombined, Newspaper, Waypoints } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
export interface Service { number:string; title:string; description:string; icon:LucideIcon }
export const services:Service[]=[
 {number:'01',title:'Adaptive Behavioural Fingerprinting',description:'Builds an asset-specific behavioural baseline and identifies deviations from historically observed patterns.',icon:BrainCircuit},
 {number:'02',title:'AI Financial News Analysis',description:'Analyses financial news and textual signals for suspicious or unusual patterns.',icon:Newspaper},
 {number:'03',title:'Multi-Source Anomaly Detection',description:'Combines signals from multiple financial sources to identify unusual behaviour.',icon:Activity},
 {number:'04',title:'Cross-Source Event Correlation',description:'Connects market movements with related news, sentiment and temporal events.',icon:Waypoints},
 {number:'05',title:'Risk Scoring & Evidence Chain',description:'Presents an interpretable risk signal with contributing evidence.',icon:ChartNoAxesCombined},
]
