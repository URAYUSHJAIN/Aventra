# Aventra — UI/UX Design Specification

## 1. Design Goal

Aventra should feel like a **premium financial intelligence product**, not a generic AI landing page.

Visual direction:

**Dark financial terminal + premium product website + restrained 3D depth**

Avoid:
- generic AI/robot imagery
- excessive neon/glow
- particle backgrounds
- excessive glassmorphism
- random decorative animation
- stock-template sections
- overcrowded cards

The current hero design is the visual baseline: dark navy/charcoal, cyan/teal technical accents, orange/gold actions, large white typography and a financial 3D visual.

---

## 2. Color System

```text
Background  #071216 / #0B171B / #0E1C21
Surface     #102126 / #13282E
Border      #1E3940 / #28464C
Primary     #F6A51A / #FFB52E
Cyan        #26D9D2 / #25C9D4
Text        #F4F7F8
Muted       #94A6AA
```

Orange = primary actions/highlights.  
Cyan = technical labels, active states and subtle accents.  
White = main content.  
Grey = secondary content.

---

## 3. Typography

Use one modern font consistently:

- Inter
- Manrope
- Plus Jakarta Sans

Hero heading:

```text
Desktop: 72–96px
Tablet: 48–64px
Mobile: 38–48px
Weight: 600–700
Line-height: 0.95–1.05
```

---

## 4. Global Viewport Rule

The landing page should be designed for a laptop viewport.

Use:

```css
min-height: 100svh;
```

Major landing sections should visually fit within approximately one screen where practical.

Primary desktop test sizes:

```text
1440 × 900
1366 × 768
1280 × 720
```

Do not clip content to force exactly `100vh`. Smaller screens must remain usable.

---

# 5. Navbar

The current navbar is too generic.

Desktop:

```text
[ Aventra Logo ]

          Home   About Us   Services   Contact

                                  [ Explore ]
```

Remove unnecessary desktop icons such as profile/search unless they become real product features.

Dimensions:

```text
max-width: 1240–1320px
height: 64–72px
top margin: 18–24px
border radius: 18–22px
```

Use a subtle translucent dark surface and thin border.

Use the existing Aventra logo asset.

### Interaction

Navigation links:

```text
normal → white
hover  → cyan
active → cyan underline/indicator
```

Primary CTA:

```text
orange
```

Mobile:

```text
[ Logo ]                         [ Menu ]
```

Menu opens:

```text
Home
About Us
Services
Contact
Docs
```

---

# 6. Hero — First Screen

Layout:

```text
┌──────────────────────────────────────────────────┐
│ NAVBAR                                           │
│                                                  │
│ AI-POWERED FINANCIAL INTELLIGENCE               │
│                                                  │
│ Detect Hidden                                   │
│ Patterns.                                       │
│ Understand                                      │
│ Market Risk.                 3D VISUAL          │
│                                                  │
│ short description                               │
│                                                  │
│ [ Explore Intelligence ] [ How It Works ]       │
└──────────────────────────────────────────────────┘
```

Hero copy:

**Detect Hidden Patterns. Understand Market Risk.**

Description:

> Aventra combines market behaviour, financial news, sentiment and temporal signals to identify unusual patterns and provide contextual, explainable risk insights.

Buttons:

```text
Explore Intelligence
How It Works
```

Do not let the CTA fall below the first laptop viewport.

---

# 7. Hero 3D Visual

Keep the existing financial visual direction but make it feel like a designed product composition.

Layer:

```text
dark background
→ subtle cyan/orange light
→ financial monitor
→ main 3D object
→ chart layers
→ 2–3 small information cards
→ shadow
```

Maximum floating cards: **3**.

Examples:

```text
ANOMALY REVIEW
Unusual volume detected

RISK SIGNAL
Context required

SENTIMENT SHIFT
Negative signal
```

Use slow motion only:

```text
translateY ± 6–10px
rotateZ ± 1deg
5–8 seconds
```

No bouncing or aggressive rotation.

---

# 8. About Aventra

Keep it compact.

```text
ABOUT AVENTRA

A financial intelligence layer
for understanding unusual
market behaviour.

Short explanation.

Market data     News
Behaviour       Context
Risk            Evidence
```

Use typography and separators instead of a grid of generic cards.

---

# 9. Live Market Intelligence

Section title:

**Market Intelligence**

Subheading:

> Live market context, behaviour and signals in one view.

Layout:

```text
Asset Search

Price     Change     Volume     Volatility

┌─────────────────────────┬──────────────────┐
│ Market Chart            │ Market Signal    │
│                         │                  │
└─────────────────────────┴──────────────────┘
```

Show real backend-driven data:

- price
- percentage change
- volume
- volatility
- anomaly state
- relevant market signal

Frontend must call Flask; do not directly couple UI components to the provider.

---

# 10. Services — Intelligence Suite

Five capabilities:

### 01 — Behavioural Fingerprinting
Understand normal behaviour for an asset.

### 02 — Anomaly Detection
Identify unusual price, volume and volatility behaviour.

### 03 — AI Financial News Analysis
Analyse financial text and sentiment using FinBERT.

### 04 — Cross-Source Event Correlation
Connect market anomalies with relevant financial events/news.

### 05 — Risk & Evidence
Turn multiple signals into contextual, explainable evidence.

Do not make five identical flat cards.

Use large numbered sections/cards with subtle depth.

Hover:

```text
translateY(-6px)
small scale
cyan/orange accent
```

---

# 11. How It Works

Title:

**From Signal to Evidence**

Desktop:

```text
01 Market Data
      ↓
02 Behaviour
      ↓
03 Anomaly
      ↓
04 News Context
      ↓
05 Correlation
      ↓
06 Evidence
```

Use a thin cyan connection line.

On mobile, convert this to a vertical timeline.

Do not use six oversized cards.

---

# 12. Behavioural Fingerprinting Showcase

This is the core product feature.

Left:

```text
CORE INTELLIGENCE

Adaptive Behavioural
Fingerprinting

Understand what normal
behaviour looks like.
```

Right:

```text
┌──────────────────────────────┐
│ Normal Behaviour             │
│ ───────────────────────────  │
│ historical baseline          │
│                              │
│ Current Behaviour            │
│ ──────────────────────●────  │
│ current deviation            │
└──────────────────────────────┘
```

Use a real line chart/baseline visualization.

---

# 13. Research & Documentation

Create three floating 3D cards.

```text
┌──────────────┐
│ PATENT       │
│ Aventra      │
│ Core Concept │
│ View →       │
└──────────────┘

┌──────────────┐
│ RESEARCH     │
│ PAPER        │
│ View →       │
└──────────────┘

┌──────────────┐
│ REVIEW PAPER │
│ Coming Soon  │
│ Stay tuned   │
└──────────────┘
```

Use subtle depth:

```text
perspective: 1200px
translateZ
shadow
```

Hover:

```text
translateY(-12px)
scale(1.025)
```

Avoid dramatic rotations.

Documentation route:

```text
/doc
```

Patent and research-paper cards should link to their actual documents/routes.

---

# 14. Documentation Page

Route:

```text
/doc
```

Structure:

```text
Documentation

Aventra
├── System Overview
├── Architecture
├── Behavioural Fingerprinting
├── Anomaly Detection
├── Financial News Analysis
├── Event Correlation
├── Risk & Evidence
├── Research
└── Patent
```

Desktop can use a left documentation navigation rail.

Mobile should use stacked navigation/dropdown.

---

# 15. Contact Page

Keep contact compact.

Desktop:

```text
┌──────────────────────┬────────────────────────┐
│ Let's connect.       │                        │
│                      │       3D EARTH         │
│ Research             │       / GLOBE         │
│ Technical            │                        │
│ Collaboration        │                        │
│                      │                        │
└──────────────────────┴────────────────────────┘
```

Approximately 50% text / 50% visual.

Do not create a huge traditional contact form.

Content:

```text
Let's connect.

Have a research collaboration,
technical question, or project inquiry?

Email
Portfolio
GitHub / LinkedIn
```

---

# 16. Contact 3D Earth

Use a proper dark 3D globe.

Characteristics:

- slow rotation
- dark surface
- subtle cyan/orange illumination
- atmospheric glow
- premium depth

Rotation:

```text
20–40 seconds
```

Do not spin quickly.

---

# 17. Footer

Keep the footer minimal.

```text
AVENTRA

Detect hidden patterns.
Understand market risk.

Home   About   Services   Contact   Docs

© 2026 Aventra
```

Use a subtle text hover effect on `AVENTRA`:

- letter spacing expansion
- subtle cyan glow
- slight vertical movement

No giant footer sitemap.

---

# 18. Homepage Order

Final landing page:

```text
01 Hero
02 About Aventra
03 Market Intelligence
04 Intelligence Suite
05 How It Works
06 Behavioural Fingerprinting
07 Research & Documentation
08 Contact CTA
09 Footer
```

Do not add unnecessary sections.

---

# 19. Visual Rhythm

Alternate:

```text
large visual
→ information
→ interactive data
→ process
→ deep feature
→ research
→ contact
```

This prevents the page from becoming a wall of cards.

---

# 20. 3D Design Language

Create depth through:

```text
perspective
layering
shadows
blur
z-index
subtle transforms
lighting
```

Use:

```css
perspective: 1200px;
transform-style: preserve-3d;
backface-visibility: hidden;
```

Do not rely on:

- giant card rotations
- excessive neon
- floating random objects
- constant animation

---

# 21. Motion

Allowed:

- fade
- slide
- small scale
- subtle parallax
- 3D hover
- line reveal
- metric count-up for real data
- slow globe rotation

Avoid:

- bouncing
- spinning cards
- scroll hijacking
- constant background animation

Support:

```css
@media (prefers-reduced-motion: reduce)
```

Disable decorative motion when enabled.

---

# 22. Responsive Rules

### Desktop

Use two-column layouts where appropriate.

### Tablet

Reduce hero typography and spacing. Collapse navbar.

### Mobile

Use:

```text
single column
smaller typography
reduced 3D depth
vertical service sections
vertical How It Works timeline
```

Hero order:

```text
heading
description
CTA
visual
```

---

# 23. Routes

Required:

```text
/
 /about
 /services
 /contact
 /doc
```

Optional service routes:

```text
/services/fingerprint
/services/anomaly
/services/news
/services/correlation
/services/risk
```

Every visible button/link must have a real destination.

---

# 24. Component Structure

Use:

```text
Navbar
Hero
About
MarketIntelligence
ServiceSuite
HowItWorks
FingerprintShowcase
ResearchCards
Contact
Footer
```

Frontend stack:

```text
React
TypeScript
Vite
Tailwind CSS
React Router
```

Keep API calls in a service layer.

---

# 25. Asset Rules

Use existing Aventra assets first.

Suggested:

```text
assets/
├── logo
├── hero
├── market
├── research
├── documents
└── contact
```

Do not introduce unrelated stock imagery.

The product should visually depend on:

- Aventra logo
- financial visualization
- actual market data
- UI composition
- controlled 3D elements

---

# 26. Current Design Improvements

### Navbar

Problem:
- too generic
- unnecessary empty space
- CTA feels disconnected

Fix:
- compact navigation
- stronger logo
- clear active state
- fewer controls
- better spacing

### Hero

Problem:
- floating labels compete with main visual
- CTA can fall below shorter laptop screens
- visual hierarchy can be tighter

Fix:
- keep hero within first screen
- maximum three floating labels
- move CTA higher
- stronger depth
- contained visual

### Overall

The page should communicate:

```text
DATA
 ↓
BEHAVIOUR
 ↓
SIGNAL
 ↓
CONTEXT
 ↓
EVIDENCE
```

not simply “AI + finance”.

---

# 27. Definition of Done

- [ ] Hero fits a laptop screen.
- [ ] Navbar is compact and premium.
- [ ] Existing Aventra logo asset is used.
- [ ] No unnecessary desktop icons.
- [ ] Hero has controlled 3D depth.
- [ ] No generic AI/robot aesthetic.
- [ ] Dark/cyan/orange palette is consistent.
- [ ] Live Market Intelligence is visible.
- [ ] Market data is backend-driven.
- [ ] Five services are represented.
- [ ] How It Works explains the complete pipeline.
- [ ] Fingerprinting has a dedicated visual showcase.
- [ ] Research section has three floating cards.
- [ ] Patent card works.
- [ ] Research paper card works.
- [ ] Review paper says Coming Soon.
- [ ] `/doc` exists.
- [ ] Documentation card routes to `/doc`.
- [ ] Contact is approximately 50/50 text and globe.
- [ ] Globe has subtle rotation.
- [ ] Footer is minimal.
- [ ] Footer links to documentation.
- [ ] Aventra footer text has subtle hover interaction.
- [ ] Mobile is fully responsive.
- [ ] Reduced-motion support exists.
- [ ] No dead links.
- [ ] No excessive animation.
- [ ] No unnecessary AI-themed decoration.

---

# 28. Final UX Principle

Aventra should **not** look like another AI startup landing page.

It should look like:

> **A serious financial intelligence product that happens to use AI.**

Every visual decision should reinforce:

**Market → Behaviour → Anomaly → Context → Correlation → Risk → Evidence.**
