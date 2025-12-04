# Second Brain – Phase I Product Definition Report (PDR)

TAGS: project:SecondBrain, type:PDR, phase:1, version:1.0

---

## 0. Purpose

Phase I defines the minimum usable Second Brain so it can be used daily and start producing cash flow.

It must:

- Give each project its own Workspace (brain).

- Provide an Ask Command menu (including Agents).

- Save and reuse outputs as assets.

- Export assets as TXT, MD, and PDF.

- Package existing assets into a Gumroad-ready product bundle.

- Run on multiple Model Engines (ChatGPT and Claude) using a simple config.

Phase II+ features (advanced lead magnets, Build Offer, custom commands UI, weekly summaries, etc.) are defined separately.

---

## 1. Scope (Phase I)

In scope:

- Workspaces (project brains).

- Ask Command menu (starter commands + Agents).

- Asset system (Save / Find / Reuse / Add).

- Export (TXT / MD / PDF).

- Document onboarding (simple).

- History (per workspace).

- Pack for Gumroad command.

- Model Engine configuration using `engines.json`.

Out of scope (for later phases):

- Full lead magnet command family.

- Structured "Build Offer" command.

- New Ask Command UI for custom commands.

- Weekly summaries and outcome dashboards.

- Advanced engine UI and open LLM expansion.

---

## 2. Workspaces (Project Brains)

A Workspace is a separate "brain" for one project or domain.

Examples:

- My Business

- Nu Skin Strategy

- Webinar OS

- Golf

Behavior:

- Each workspace has its own:

  - Documents (ingested files, pasted text).

  - Assets (prompts, pages, workflows, etc.).

  - Settings (including Brain Engine / default engine).

- Retrieval/context is scoped to the current workspace.

---

## 3. Ask Command Menu (Phase I)

There is a Command dropdown next to the Ask input with these choices:

1. Ask – Normal conversational answer.

2. Success Coach – Uses Success Coach Agent to create a simple plan: focus topic, current reality, 7–30 day goal, today's Big 3, next steps.

3. Workflow Agent – Uses Workflow Agent to produce a workflow: GOAL, TRIGGER, STEPS, NOTES.

4. Lead & Social Agent – Uses Lead & Social Agent to suggest lead sources, hooks, a 7-day content plan, and outreach messages.

5. Build Prompt – Generates a reusable prompt (title, description, instructions, variables, example usage).

6. Build Workflow – Generates a workflow using the standard GOAL/TRIGGER/STEPS/NOTES format.

7. Landing Page – Drafts a landing page (hero, problem, solution, features/benefits, social proof placeholders, FAQ, final CTA).

8. Email Sequence – Drafts a short email sequence (3–5 emails, subject + body).

9. Content Batch (Social Posts) – Generates a batch of social posts (e.g. 10 posts with hook/body/CTA).

10. Decision Record – Logs a decision (context, options, decision, rationale, next review date).

11. Build Expert Instructions – Builds an expert formula/checklist based on ~3 notable experts in a topic.

12. Build Customer Avatar – Creates an Ideal Customer Avatar (profile, goals, pains, triggers, objections, messaging angles, offer fit).

13. Pack for Gumroad – Packages selected assets into a product bundle structure and product page copy.

Labels, tooltips, and placeholders are defined in `SecondBrain_AskCommands_UI_v1.0.md`.

All commands run inside the current workspace and use that workspace's documents and assets as context.

---

## 4. Expert Instructions (Asset: expert_instructions)

Command: Build Expert Instructions

Purpose: Capture reusable "expert formulas" for a topic (e.g. landing pages, emails, photography).

Output format:

```text
EXPERT INSTRUCTIONS: <short name>

TOPIC:
<topic>

EXPERTS REFERENCED:
- <Expert 1> – <what they are known for>
- <Expert 2> – ...
- <Expert 3> – ...

CORE PRINCIPLES:
1. <principle 1>
2. <principle 2>
3. <principle 3>
...

FORMULA / CHECKLIST:
Step 1: ...
Step 2: ...
Step 3: ...

EXAMPLE USAGE:
- When doing X, follow A, B, C.

NOTES:
- <assumptions or caveats>
```



