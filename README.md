# AI Travel Concierge — Personal Project

This project is a **personal AI-powered travel concierge** designed to help plan trips with a "Luxury for Less" mindset — combining premium experiences with smart value decisions.

---

## What this app does

The AI Concierge helps you:

- Discover **restaurants, bars, hotels, and experiences** in a destination
- See **all relevant options**, not just a curated top 3
- Understand *why* each place is recommended through a clean, one-line concierge explanation
- Add places directly into a trip itinerary

---

## Core philosophy

This is not a generic search app.

It is built to feel like a **real concierge** who:
- reads across multiple sources
- filters unreliable information
- explains recommendations clearly
- prioritizes quality and relevance over noise

---

## Architecture overview

### Frontend
- Next.js (App Router)
- React 19
- Tailwind CSS + modern UI patterns

### Backend
- FastAPI (Python)
- Supabase (database, auth)

### Infrastructure
- Vercel (frontend)
- Railway (backend)

---

## AI Concierge engine (key system)

The research engine follows a **place-first, reliability-focused architecture**:

- **Google Places = source of truth**
  - existence
  - operational status
  - rating and review count
  - addability to itinerary

- **Yelp + Foursquare = enrichment only**
  - tags
  - sentiment
  - additional signals

- **Editorial / web sources = evidence only**
  - used for reasoning
  - never directly shown as addable places

---

## Why this is different

Most travel apps:
- show generic lists
- rely heavily on ratings
- lack real reasoning

This app:
- builds **structured evidence per place**
- selects **true differentiators**
- generates **one clean, human-like explanation**
- avoids noisy or duplicated data

---

## Current focus (as of latest PR)

Recent work has focused on **open-language place understanding** for the AI Concierge:

- venue-head preservation so geo/style modifiers ("waterfront", "rooftop", "romantic") never overwrite the real venue noun ("brewery", "tapas", "sushi")
- open-class place-ask detector that admits unknown venue nouns (izakaya, tea houses, dessert bars, record stores) into Semantic Retrieval v1 without keyword-bucket maintenance
- venue-first retrieval planning with concrete neighborhood/street anchors (e.g., "Fulton Street") preserved through to provider queries
- wrong-category penalty so waterfront restaurants/parks no longer dominate brewery/sushi asks just because they share a geo modifier
- safe-reason builder no longer prints repetitive geo-targeted-search-area copy on every card and never anchors user-visible reasons on a modifier word
- structured `semantic_retrieval_v1.turn` log line now carries `venue_concept`, `location_modifiers`, `open_class_place_detected`, and wrong-category diagnostics for one-pass debuggability

---

## Project status

This is an actively evolving personal project focused on:

- improving recommendation quality
- refining UI/UX to feel premium
- building a reliable, scalable research engine

---

## Note

This repository is optimized for **personal use and rapid iteration**, not production-scale distribution.

The goal is to build a best-in-class personal concierge experience that exceeds typical consumer travel apps in clarity and usefulness.
