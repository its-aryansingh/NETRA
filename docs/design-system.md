# NETRA Design System & Instrumentation Canvas

## 1. Design Philosophy: The Cloud Cockpit

NETRA is designed not as a consumer web page, but as a precision industrial cockpit. Cloud financial anomalies represent immediate capital loss; therefore, every component prioritizes maximum data legibility, authoritative contrast, and zero ambiguity.

---

## 2. Color Tokens

All design tokens are defined in `app/globals.css` with exact hex values:

```css
:root {
  /* Surfaces & Canvas */
  --ground: #0A0D0C;       /* Obsidian abyss ground */
  --surface: #111614;      /* Elevated primary card background */
  --surface-2: #0E1312;    /* Recessed secondary background / table headers */

  /* Borders & Dividers */
  --line: #232C28;         /* Primary 1px structural container border */
  --line-soft: #1B2320;    /* Subtle interior table and divider borders */

  /* Typography */
  --text: #E8EDEA;         /* High-contrast crisp foreground */
  --text-2: #98A69F;       /* Secondary descriptive copy */
  --text-3: #808E88;       /* De-emphasized labels and unit identifiers */

  /* Semantics: Burn Velocity & Ember */
  --ember: #E9883C;        /* Real-time spend velocity accent */
  --ember-bg: #2A1810;     /* Ember tinted pill background */
  --ember-line: #5C3418;   /* Ember tinted structural border */

  /* Semantics: Safety & Recovered Mint */
  --mint: #46D6A0;         /* Verified savings and healthy states */
  --mint-bg: #0F2A20;      /* Mint tinted pill background */
  --mint-line: #1E5943;    /* Mint tinted structural border */

  /* Semantics: Warnings & Alarms */
  --amber: #D9C03C;        /* Non-critical warnings and rollbacks */
  --alarm: #F2555A;        /* Critical severity and financial runaway alerts */
}
```

---

## 3. Typography: The Strict Monospace Discipline

Three font families are loaded via Google Fonts:

1. **Familjen Grotesk (600/700)**:
   - Used exclusively for high-level headings, brand wordmark (`NETRA` with `0.14em` letter-spacing), and section anchors.
2. **IBM Plex Sans (400/500/600)**:
   - Used for narrative prose, paragraphs, explanations, and descriptive text.
3. **IBM Plex Mono (400/500/600)**:
   - **MANDATORY**: Every number, price, rate, percentage, resource ID, AWS region, timestamp, duration, and multiplier MUST be styled in `IBM Plex Mono`.
   - Why: Monospace numerals maintain uniform tabular alignment, eliminate layout shifting during live ticking counter animations, and immediately convey instrument precision.

---

## 4. Layout & Spacing Grid

- **8px Base Spacing Grid**: All paddings, margins, and gaps adhere to multiples of 8px (8px, 16px, 24px, 32px, 48px).
- **Corner Radii**:
  - `7px`: Small interactive controls, status chips, and provenance tags.
  - `9px`: Action buttons and navigation pills.
  - `12px – 14px`: Cards, hero units, and table containers.
- **Borders**: Strictly 1px (`border border-[var(--line)]`). Double-pixel borders are prohibited.
- **Icons**: Inline stroked SVG icons using 1.7px to 2.2px stroke weights. No emoji or icon font glyphs.

---

## 5. Controlled Motion

Only three purposeful animations are permitted across the application:
1. **Spend Velocity Count-Up**: Spend hero numbers ease-out smoothly over 400ms on value change.
2. **Collector Heartbeat Pulse**: Green status dot in the TopBar pulses subtly over a 2-second cycle.
3. **Finding Card Entrance**: Newly detected finding cards fade and rise 4px over 200ms.
No other decorative transitions, parallax effects, or glassmorphism are used.
