import { ClosingCta } from '../components/home/ClosingCta'
import { Hero } from '../components/home/Hero'
import { HowItWorks } from '../components/home/HowItWorks'
import { IntelligencePreview } from '../components/home/IntelligencePreview'
import { LiveMarketData } from '../components/home/LiveMarketData'
import { Services } from '../components/home/Services'
import { WhyAventra } from '../components/home/WhyAventra'

export function Home() { return <main id="main" className="page-home"><Hero /><IntelligencePreview /><LiveMarketData /><Services /><WhyAventra /><HowItWorks /><ClosingCta /></main> }
