import { ExternalLink, GraduationCap, MapPin } from 'lucide-react'
import { ContactForm } from '../components/contact/ContactForm'
import { Scene3D } from '../components/visual/Scene3D'
import { REPOSITORY_URL } from '../data/project'

export function ContactPage() {
  return <main id="main" className="page page-contact">
    <div className="wrap contact-grid">
      <div className="contact-copy">
        <p className="eyebrow">CONTACT</p>
        <h1 className="display-title">Get in <em>touch.</em></h1>
        <p className="section-intro">Write to the team with questions about Aventra, the research or the platform, collaboration on evaluation, or feedback on the analysis.</p>
        <ContactForm />
        <ul className="contact-details">
          <li><GraduationCap size={16} aria-hidden="true" /><div><strong>Research project</strong><span>B.Tech final-year project, ABES Engineering College</span></div></li>
          <li><MapPin size={16} aria-hidden="true" /><div><strong>Location</strong><span>Ghaziabad, Uttar Pradesh, India</span></div></li>
          <li><ExternalLink size={16} aria-hidden="true" /><div><strong>Source code</strong><a href={REPOSITORY_URL} target="_blank" rel="noreferrer">github.com/URAYUSHJAIN/Aventra</a></div></li>
        </ul>
      </div>
      <div className="contact-visual">
        <Scene3D scene="globe" />
        <p className="visual-caption">Nodes: the project’s home and the market centres behind Aventra’s permitted data providers.</p>
      </div>
    </div>
  </main>
}
