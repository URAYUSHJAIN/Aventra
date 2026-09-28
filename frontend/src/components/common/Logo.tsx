import mark from '../../assets/aventra-mark.png'
export function Logo({ href = '/', label = 'Aventra home' }: { href?: string; label?: string }) { return <a href={href} className="logo" aria-label={label}><img src={mark} alt="" width="28" height="28" /><span>Aventra</span></a> }
