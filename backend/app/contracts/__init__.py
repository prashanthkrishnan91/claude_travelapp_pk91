"""App-level product contracts.

Modules in this package codify product invariants that span multiple routes,
services, and persistence boundaries.  They are deliberately small,
dependency-free, and import-safe (no FastAPI/Supabase coupling) so they can
be reused from routes, services, tests, and tooling.

Current contracts:

- ``flights`` — Flights Product Contract v1: allowed/disallowed sources,
  required persistable fields, leg-type, day-mapping, source-status,
  provider seam reference.  See ``backend/app/contracts/flights.py``.
"""
