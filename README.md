# Round 3 — Web Enumeration (Evidence 03: The Mirror)

> **CYBERLEEK: THE INTERNET NEVER FORGETS**
> *Participant Briefing — Evidence 03: The Mirror*
> *"As the original material disappeared, copies began appearing elsewhere. One of those copies leads to an abandoned web presence. The site is almost empty now. A landing page. But the archive contains evidence that the site once looked very different. Somewhere within its remains is a connection between the original CyberLeek campaign and the material that followed it.*
> **'WHEN ONE COPY DISAPPEARS, ANOTHER USUALLY SURVIVES.'**"

---

## 1. Challenge Overview

- **Round**: 3 of 6 (Web Enumeration & Forensic Mystery)
- **Scale**: Multi-team concurrent environment (50+ teams)
- **Flag Format**: `CYBERLEEK{...}`
- **Progression**: 3 Progressive Levels. Each level requires discovering an authentic node and retrieving its genuine flag.
- **Dual Solving Approaches**:
  1. **Approach A (Tooling & Brute Force)**: Front-of-URL ffuf directory discovery + Lockout-aware Hydra/Python brute force.
  2. **Approach B (Smart Detective / Murder Mystery)**: Deeply hidden forensic Easter Eggs (XOR telemetry, header/signature correlation, transaction ledger reconstruction) allowing smart teams to bypass brute forcing in minutes.
- **Anti-LLM Defenses**:
  - **Inverted URL Topology**: Front-of-URL routing (`/<FUZZ>/<route>`) defeats naive crawler & prompt assumptions.
  - **9 Decoy Portals**: 3 fake redirects and decoy portals per level, each returning convincing dummy `CYBERLEEK{...}` flags.
  - **Honeypot Bait**: Direct crawler traps (`/flag`, `/admin`, `/robots.txt`) designed to catch automated bots and LLMs.
  - **Verification Filter**: Central investigation console (`/verify`) rejects all decoy flags and demands authentic forensic proof.

---

## 2. Quickstart & Deployment

### Dependencies
```bash
pip install -r requirements.txt