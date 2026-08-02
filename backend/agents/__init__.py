"""Agent layer.

Each pipeline stage beyond the ML model lives here as its own module so stages
compose rather than accumulating in `main.py`:

  root_cause.py   Phase 2 — diagnoses *why* a cart is at risk
  (future) intervention.py  Phase 3 — decides what to do about it
"""
