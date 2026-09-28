import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { useState } from 'react'

// Opens the visitor's email client addressed to VITE_CONTACT_EMAIL. Nothing is sent by Aventra itself.
export function ContactForm() {
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string }>()
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const contactEmail = import.meta.env.VITE_CONTACT_EMAIL?.trim()
    if (!contactEmail) { setStatus({ type: 'error', message: 'Message delivery is not configured yet. Please contact the Aventra team through ABES Engineering College.' }); return }
    const subject = encodeURIComponent(`Aventra enquiry from ${form.get('name')}`)
    const body = encodeURIComponent(`Name: ${form.get('name')}\nEmail: ${form.get('email')}\n\n${form.get('message')}`)
    window.location.assign(`mailto:${contactEmail}?subject=${subject}&body=${body}`)
    setStatus({ type: 'success', message: 'Your email client is opening with your message ready to send.' })
  }
  return <form className="contact-form" onSubmit={submit}>
    <div className="field-row"><label>Name<input required name="name" autoComplete="name" /></label><label>Email<input required name="email" type="email" autoComplete="email" /></label></div>
    <label>Message<textarea required name="message" rows={5} /></label>
    <button className="button button-primary button-lg" type="submit">Send message <ArrowRight size={16} aria-hidden="true" /></button>
    {status && <p className={`form-status is-${status.type}`} role={status.type === 'error' ? 'alert' : 'status'}>{status.type === 'success' && <CheckCircle2 size={15} aria-hidden="true" />} {status.message}</p>}
  </form>
}
