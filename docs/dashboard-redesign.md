# Dashboard Redesign

## Understanding

- The storefront, backend, model pipeline, and API contracts remain unchanged.
- The dashboard is optimized for a three-minute synchronized storefront/dashboard demo on a 16:9 display.
- Product-quality uncertainty is the flagship case: review hesitation leads to grounded help while a discount is rejected.
- The primary dashboard must work both as a guided judge experience and a live decision-operations surface.
- A selected session must expose the actual architecture path, including each component's inputs and outputs.
- Secondary evaluation evidence remains available without competing with the main session story.

## Assumptions and Constraints

- The existing React, Tailwind, Lucide, SSE, and REST implementation remains the foundation.
- The demo operates offline with synthetic identities and deterministic scenarios.
- The primary view targets 8-20 curated live sessions and settles within two seconds locally.
- Dashboard updates remain visible within one second of an SSE event.
- Authentication, real customer PII, production-scale monitoring, backend re-architecture, and storefront redesign are out of scope.
- No new automated tests are required. Functional and visual verification covers every deterministic scenario.

## Information Architecture

### Command Center

The default workspace combines a live-session rail, the four required case-study outputs, a session-specific decision pipeline, a component inspector, and the customer outcome. Selecting a session shows its latest decision by default, with earlier decisions available through a compact selector.

### Proof Lab

Scenarios, experiment outcomes, model metrics, and runtime evidence are grouped as focused proof views. Existing routes remain functional for deep links.

### System Blueprint

A simplified system-wide architecture explains deployment boundaries and the feedback loop. It is separate from the per-session pipeline, which explains one actual computation.

## Session Pipeline

The pipeline presents eight ordered stages:

1. Session Events
2. Feature Agent
3. Risk Agent
4. Root-Cause Agent
5. Policy Agent
6. Recommendation Agent
7. Explainability Agent
8. Customer Action

After session data loads, the stages activate automatically once. There are no playback controls. The completed diagram then remains static. Hover provides a concise preview; click, Enter, or Space pins structured input, transformation, output, latency, status, version, and safeguard details in the inspector. Reduced-motion users receive the completed diagram immediately.

## Visual Direction

- Near-black neutral workspace with restrained separators instead of nested cards.
- Flipkart blue for selection, teal for verified flow, coral for risk, amber for policy, green for approved outcomes, and neutral gray for silence or unavailable states.
- System sans-serif for interface text and monospace only for identifiers, versions, timing, and raw values.
- Stable 1080p three-part layout: session rail, pipeline canvas, and inspector.
- At narrower widths, the session rail becomes a selector, the pipeline wraps or becomes vertical, and the inspector follows the diagram.
- Color is never the only state indicator. Hover is never required to access information.

## Reliability States

- Loading reserves the final layout dimensions.
- Disconnected streaming preserves current data and labels it stale.
- Missing model or stage data resolves visibly to `ABSTAIN`, `NO_ACTION`, or unavailable rather than fabricated output.
- Low-risk, fatigue-protected, and control-arm decisions traverse the full visible pipeline.
- Pending outcomes are labeled pending rather than presented as successful.

## Decision Log

| Decision | Alternatives | Reason |
|---|---|---|
| Unified Decision Command Center | Pipeline-only workspace; separate demo/operations modes | One mental model serves judges and operators with less navigation. |
| Latest decision by default | First decision; combined branching session graph | Matches live operations expectations and keeps the graph readable. |
| Automatic control-free activation | Playback controls; fully static diagram | Communicates computation without turning the architecture into a media player. |
| Hover preview plus pinned selection | Hover-only detail; all raw data inline | Keeps the full path visible while preserving accessible, stable detail. |
| Semantic DOM nodes with SVG connectors | React Flow; canvas rendering | The pipeline is fixed, so a graph dependency adds complexity without useful capability. |
| Consolidated Proof Lab | Five equal top-level dashboard destinations | Evaluation evidence stays available but no longer obscures the core story. |
| Existing stack and APIs | Dashboard framework; backend aggregate endpoints | Minimizes implementation risk and preserves the working prototype. |

## Verification

- Run deterministic scenarios A-H through the live backend.
- Confirm every outcome type renders: intervention, deliberate silence, abstention, fatigue suppression, payment help, and experiment control/treatment.
- Exercise session selection, decision history, hover preview, pinned inspection, and keyboard interaction.
- Inspect 1920x1080, 1440x900, and mobile layouts for clipping, overlap, missing stages, and inaccessible details.
