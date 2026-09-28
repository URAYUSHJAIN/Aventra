# Aventra Design Specification

## 1. Purpose

Aventra is a financial intelligence platform designed to turn fragmented
market signals into contextual, explainable intelligence.

The interface should communicate:

> **Signal → Context → Explanation → Evidence**

The product should feel like a:

> **Financial Intelligence Instrument**

The design must not feel like a generic AI SaaS dashboard, generic admin
panel, crypto dashboard, or template landing page.

------------------------------------------------------------------------

# 2. Core Design Direction

### Visual character

**Premium dark editorial fintech + scientific data visualization +
restrained 3D**

The experience should combine:

-   editorial typography
-   strong whitespace
-   precise information hierarchy
-   financial data visualization
-   subtle spatial depth
-   meaningful 3D
-   controlled motion
-   technical details shown progressively

The design should feel sophisticated without becoming decorative.

### Design principle

> **Complex intelligence underneath. Simple interface above.**

------------------------------------------------------------------------

# 3. Brand System

## Background

Primary:

`#08090B`

Secondary surfaces:

`#0D1013`\
`#11151A`\
`#151A1F`

Use subtle tonal differences rather than heavy card borders.

## Primary intelligence accent

`#4DFF9A`

Alternative:

`#65F6A5`

Green represents intelligence, positive/stable state, action, or
confirmed signal.

Do not use green everywhere.

## Semantic colours

-   Positive/stable → green
-   Warning/elevated → amber
-   Anomaly/negative → red
-   Informational → cyan/blue
-   Neutral → muted grey

Status must not rely only on colour.

------------------------------------------------------------------------

# 4. Typography

Use an editorial display/serif style for selected major storytelling
headlines.

Use a modern sans-serif such as Inter/Geist-style typography for:

-   navigation
-   buttons
-   controls
-   body text
-   UI

Use monospace for:

-   prices
-   percentages
-   timestamps
-   IDs
-   technical values
-   model/system metadata

Typography should create hierarchy without excessive borders or cards.

------------------------------------------------------------------------

# 5. Layout

Avoid uniform card grids.

Prefer:

-   asymmetrical composition
-   large focal elements
-   whitespace
-   editorial sections
-   controlled overlap
-   spatial grouping
-   progressive disclosure
-   occasional dense analytical areas

The layout should feel intentionally composed.

Where a section is designed around a viewport, approximately one screen
of content may be used, but never hide content simply to enforce
`100vh`.

------------------------------------------------------------------------

# 6. 3D Philosophy

3D must communicate meaning.

Do not add 3D only because it looks modern.

## Behavioural Fingerprint

Represent behavioural structure spatially.

Desired conceptual state:

`stable structure → signal → local distortion → anomaly pulse → equilibrium`

## Market Intelligence

A living market visualization showing relationships and signals.

## Risk Field

A spatial risk landscape/grid where appropriate.

## Evidence Network

Connected evidence nodes representing actual relationships.

## Global Intelligence Globe

A dark globe with:

-   slow rotation
-   subtle signal arcs
-   sparse nodes
-   restrained glow
-   small mouse/parallax response
-   slow camera movement

## Data Terrain

Use subtle terrain-like geometry for the Why Aventra/footer experience.

It should represent a financial data landscape rather than literal
mountains.

Motion should be slow, approximately 10--30 seconds for major cycles.

------------------------------------------------------------------------

# 7. Motion

Motion is purposeful.

It should communicate:

-   transition
-   state
-   hierarchy
-   data change
-   spatial relationships
-   interaction

Avoid:

-   constant spinning
-   excessive particles
-   bouncing
-   aggressive parallax
-   animation on every element
-   flashy transitions

Respect:

`prefers-reduced-motion`

------------------------------------------------------------------------

# 8. Navigation

Navigation should be a premium control surface.

It should include:

-   Aventra logo/identity
-   primary navigation
-   important action/search
-   responsive mobile navigation

Avoid oversized admin-style sidebars.

Keep navigation visually quiet so content remains dominant.

------------------------------------------------------------------------

# 9. Homepage

## Hero

Primary category:

**FINANCIAL INTELLIGENCE PLATFORM**

Primary headline:

**Understand What The Market Is Really Doing.**

Supporting message should explain that Aventra brings together:

-   market behaviour
-   unusual patterns
-   news
-   cross-source events
-   risk
-   evidence

Include an instrument search.

Possible example instruments:

-   RELIANCE
-   AAPL
-   BTC
-   USDINR
-   NIFTY

Examples must not imply fabricated live values.

Hero visual:

A living 3D market/behavioural intelligence object.

------------------------------------------------------------------------

# 10. Market Intelligence Section

Core concept:

> **Market intelligence, in one view.**

The user should understand that one instrument can be investigated
through:

-   current state
-   behaviour
-   anomaly
-   news
-   events
-   risk
-   evidence

The dashboard/product visualization should emerge naturally from the
storytelling.

Closing concept:

> **From fragmented signals to one explainable view.**

CTA:

**Explore Intelligence →**

------------------------------------------------------------------------

# 11. Intelligence Workspace

The intelligence interface is a financial investigation workspace.

Recommended hierarchy:

1.  Instrument
2.  Current state
3.  Key insight
4.  Behaviour
5.  Anomaly/context
6.  News
7.  Risk
8.  Evidence

Possible tabs:

-   Overview
-   Intelligence
-   Price
-   News
-   Risk
-   Evidence
-   Financials

Only show capabilities that exist in the application.

------------------------------------------------------------------------

# 12. Behavioural Fingerprint

The behavioural fingerprint is one of Aventra's signature visuals.

It should communicate that the system learns/represents market behaviour
and identifies deviations.

It should not be merely a decorative 3D object.

Where actual data supports it, visually communicate:

-   normal behaviour
-   deviation
-   unusual signal
-   anomaly
-   contextual state

------------------------------------------------------------------------

# 13. Risk

Risk should not be represented only by one large opaque number.

Show:

-   contributing factors
-   context
-   signal relationships
-   evidence
-   supporting explanations

Use visual hierarchy so the user can understand why a risk state exists.

Do not invent risk values.

------------------------------------------------------------------------

# 14. News + Sentiment

News should be contextual.

Where available show:

-   source
-   time
-   headline
-   relevance
-   sentiment
-   relationship to instrument/event

FinBERT is a technical implementation detail.

The main UI should communicate understandable financial intelligence
rather than model jargon.

------------------------------------------------------------------------

# 15. Evidence Chain

Evidence is a signature Aventra concept.

Represent the relationship:

**Signal → Context → Event/News → Interpretation → Risk**

Possible visual forms:

-   connected nodes
-   timeline
-   evidence path
-   relationship graph

Only display relationships supported by actual backend data.

------------------------------------------------------------------------

# 16. Why Aventra

Primary concept:

**DESIGNED FOR CONTEXT**

Headline:

**Financial data is abundant. Context is not.**

## Problem story

### 01 --- Fragmented Data

PRICE\
NEWS\
EVENTS\
VOLUME\
REPORTS\
SENTIMENT

These sources exist separately.

### 02 --- Lack of Context

A market movement creates the question:

**But why?**

### 03 --- Information Overload

Multiple streams need to become:

**SIGNAL / CONTEXT / EVIDENCE**

### 04 --- Unclear Risk

**Market Movement + Behaviour + News + Events → Risk Context**

Then introduce:

-   Unified Intelligence
-   Behavioural Understanding
-   Context-Rich Insights
-   Explainable Risk

Use restrained 3D/data terrain.

Do not create an excessive glowing green landscape.

------------------------------------------------------------------------

# 17. Services

Five core modules:

### 01

**Behavioural Fingerprinting**

### 02

**Anomaly Detection**

### 03

**News Intelligence**

### 04

**Cross-Source Correlation**

### 05

**Explainable Risk**

Do not display these as five identical cards.

Each should have its own spatial/editorial treatment.

------------------------------------------------------------------------

# 18. How It Works

Show the actual product flow:

``` text
USER
↓
INSTRUMENT SEARCH
↓
INSTRUMENT RESOLUTION
↓
PROVIDER ROUTER
↓
REAL DATA
↓
VALIDATION
↓
FEATURE ENGINEERING
↓
ML INTELLIGENCE
↓
RISK + EVIDENCE
↓
USER
```

Supporting concepts may include:

-   Instrument Master
-   provider selection
-   validation/provenance
-   behavioural fingerprint
-   anomaly detection
-   financial news
-   FinBERT
-   cross-source correlation
-   risk
-   evidence

------------------------------------------------------------------------

# 19. About

Editorial opening:

> **Financial data is abundant. Context is not.**

Explain:

-   what Aventra is
-   why it exists
-   how it approaches financial intelligence
-   its research direction
-   explainability philosophy

Avoid exaggerated claims.

------------------------------------------------------------------------

# 20. Research

Research page structure:

-   Research Problem
-   Objective
-   Methodology
-   Behavioural Fingerprinting
-   Anomaly Detection
-   News Intelligence
-   Cross-Source Correlation
-   Risk & Evidence
-   Evaluation
-   Limitations
-   Future Work

Technical concepts should be explained clearly without overwhelming the
main product experience.

------------------------------------------------------------------------

# 21. Documentation

`/doc`

Use three premium floating/spatial cards:

**PATENT**

**RESEARCH PAPER**

**REVIEW PAPER**

Use actual available documents/links.

If unavailable:

**Coming Soon**

Never invent publication or patent information.

------------------------------------------------------------------------

# 22. Contact

Split-screen composition:

### Left

Contact content/form.

### Right

Subtle rotating 3D intelligence globe.

The globe should remain secondary to the contact task.

------------------------------------------------------------------------

# 23. Footer

Keep it minimal.

Include:

-   Aventra identity
-   navigation
-   documentation links
-   relevant project information

Optional subtle data terrain behind/below the footer.

The terrain should be slow and understated.

------------------------------------------------------------------------

# 24. Responsive Design

Design intentionally for:

-   large desktop
-   laptop
-   tablet
-   mobile

Do not simply scale desktop downward.

On mobile, prioritize:

``` text
Instrument
↓
Current State
↓
Key Insight
↓
Behaviour
↓
News
↓
Risk
↓
Evidence
```

3D complexity should be reduced on mobile.

Provide fallback visuals where necessary.

------------------------------------------------------------------------

# 25. Reusable UI Primitives

Recommended reusable primitives:

``` text
AventraButton
AventraInput
AventraBadge
AventraMetric
AventraPanel
AventraSection
AventraDataLabel
AventraChart
AventraSignal
AventraEvidenceNode
Aventra3DContainer
AventraNavigation
AventraFooter
AventraLoadingState
AventraEmptyState
AventraErrorState
```

Adapt to the actual project architecture.

------------------------------------------------------------------------

# 26. Asset Strategy

Reuse existing official Aventra branding.

The frontend implementation may create appropriate assets through:

-   SVG
-   CSS
-   Three.js/WebGL
-   chart/data visualization
-   optimized images where necessary

Do not create unnecessary stock-image galleries.

Do not create decorative assets without purpose.

------------------------------------------------------------------------

# 27. Accessibility

Required:

-   semantic HTML
-   keyboard navigation
-   visible focus
-   accessible forms
-   appropriate ARIA
-   sufficient contrast
-   meaningful alt text
-   reduced-motion support
-   non-colour-only status indicators

------------------------------------------------------------------------

# 28. Performance

3D and animation must not compromise usability.

Use:

-   lazy loading
-   code splitting where useful
-   controlled animation loops
-   reduced mobile complexity
-   optimized assets
-   appropriate memoization
-   static fallbacks

Avoid unnecessary heavy WebGL scenes.

------------------------------------------------------------------------

# 29. Design Do

-   Use whitespace.
-   Use strong typography.
-   Use asymmetry.
-   Use meaningful data visualization.
-   Use restrained 3D.
-   Make evidence understandable.
-   Make risk explainable.
-   Make complex intelligence feel simple.
-   Maintain consistent visual language.
-   Use real application data.

------------------------------------------------------------------------

# 30. Design Don't

Do not create:

-   generic AI dashboard layouts
-   excessive card grids
-   excessive green glow
-   neon cyberpunk styling
-   random 3D objects
-   giant decorative spheres
-   constant particle effects
-   fake financial numbers
-   fake news
-   fake risk scores
-   fake ML results
-   unnecessary stock imagery
-   excessive animation
-   inaccessible interactions
-   desktop-only layouts

------------------------------------------------------------------------

# 31. Final Experience Goal

The final product should feel like:

> **A financial intelligence instrument built for understanding market
> context.**

The visual experience should move naturally through:

**Signal → Context → Explanation → Evidence**

It should be premium, restrained, technical, editorial, spatial,
explainable, and credible.
