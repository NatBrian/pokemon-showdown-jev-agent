# Codex Takeover Checklist

This checklist is the working TODO list for auditing and repairing the repository after the Gemini/OpenCode implementation. It is deliberately separate from the implementation plan until the audit is complete.

- [x] Read the Gemini conversation database and extract the decisions, implementation claims, and validation evidence.
- [x] Read the generated implementation plan, project-alignment record, research notes, dashboard specification, README, and current git history.
- [x] Inspect every production module and test for correctness, version compatibility, and scope alignment.
- [x] Run the existing test suite and record failures, warnings, and coverage gaps.
- [x] Start the local dashboard and inspect the rendered UI in a real browser at desktop and narrow viewport sizes.
- [x] Exercise dashboard startup, WebSocket updates, inspector/history behavior, failure states, and battle-client embedding through the browser.
- [x] Validate Jev request/response handling against the documented OpenCode System One contract without exposing secrets.
- [x] Validate the Showdown/poke-env lifecycle, action legality, battle requests, public matchmaking, and cleanup behavior.
- [x] Compare the implementation with the intended Gen 9 Random Battles mechanics and fog-of-war rules.
- [x] Write a revised, evidence-based implementation plan that lists only necessary changes.
- [x] Implement the approved repairs with focused tests and keep the UI visually demo-ready.
- [x] Re-run backend tests, browser tests, and local integration checks; document any external-service limitation honestly.
- [x] Update the README and validation notes with the actual verified run instructions and remaining risks.
