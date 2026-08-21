# Research report visual system

## Design intent

Use a bright, calm UX-research deck aesthetic: large black Chinese headlines, generous white space, soft rounded cards, modular research steps, and restrained 3D-like depth. Keep purple-blue as the primary identity; use coral, mint, and warm yellow only as semantic accents.

## Tokens

- Canvas: `#F7F7FC`; surface: `#FFFFFF`; ink: `#171827`; muted: `#667085`.
- Primary: `#5B4BFF`; blue: `#3578FF`; violet: `#8A5CFF`.
- Coral: `#FF7A66`; mint: `#35C995`; sun: `#F7B928`.
- Radius: 20–34px for major cards, 12–16px for controls.
- Border: cool neutral at 8–12% opacity. Shadow: wide, soft, low opacity.

Use one dominant accent per chart and encode categories with color plus labels, shapes, or patterns. Never use decorative 3D perspective for quantitative marks.

## Layout

1. Hero: editorial headline + research-stage composition + core KPIs.
2. Research path: discover → define → analyze → synthesize → validate.
3. Snapshot: samples, coverage, quality, and method caveats.
4. Landscape: distribution, time, aspects, topics, emotion, and co-occurrence.
5. Experience: journey, pains, needs, contradictions, HMW, opportunity matrix.
6. Model: only when enabled; show split, baselines, holdout metrics, importance, and caveat.
7. Evidence lab: filters, table, excerpts, IDs, provenance, download.

## Motion

Use motion to explain hierarchy, never to decorate every element.

- 400–700ms scroll reveal with 40–80ms stagger.
- KPI count-up once when visible.
- SVG bars/lines/donuts animate from zero once.
- Hero objects float within 4–8px and pause on hover.
- Cards may use a maximum 2-degree pointer tilt on fine-pointer devices.
- Respect `prefers-reduced-motion: reduce`; disable transforms, transitions, and smooth scroll.

## Visualization rules

- Inspect schema and quality before plotting.
- Match chart to question: distributions, cohorts, time, relationships, or networks.
- Show denominators and the exact count behind percentages.
- Prefer full distributions to bars of means when continuous values matter.
- Label axes and units. Avoid dual axes unless indispensable.
- Keep opportunity axes evidence-based: `sample impact/severity` × `evidence confidence`, not invented engineering feasibility.
- State what would surprise or invalidate the intended takeaway.
- Keep observations, model results, interpretations, and recommendations visually distinct.

## Accessibility and QA

- Minimum 4.5:1 text contrast for normal text.
- All controls have keyboard focus styles and accessible labels.
- Charts have summaries or tabular equivalents.
- Do not rely on hover for essential evidence.
- Verify 1440px desktop, 1024px tablet, and 390px mobile views.
- Confirm no external fonts, CDN scripts, remote images, or network-dependent assets.

