<!--
RAG-META:
filename: OS_RAG_Commands_CheatSheet_v1.md
namespace: os_core
tags: scope:os, type:instructions, subtype:commands-cheatsheet, status:active
-->

# OS RAG Commands Cheat Sheet – v1

This is the minimal set of prompts/commands you actually need to remember.
Everything else can be looked up here or in `OS_RAG_Usage_Instructions_v1.md`.

You can paste these into ChatGPT/Cursor (or any LLM) and adapt the wording lightly.

---

## 1. OS-Level Commands

### 1.1. OS Summary (remind me how this thing works)

**Command:**

> Using my `Global_OS_System_Prompt_v2_With_Glossary`, summarize:
> - My core operating principles in 5–10 bullets.
> - How you and I should work together today in 3–5 bullets.

Use this when you feel lost or are coming back after a break.

---

### 1.2. Daily OS Check-In (what do I do today?)

**Command:**

> Daily OS check-in:
> 1. Here is my current energy and constraints for today: [describe].
> 2. Here are the 1–3 most important outcomes I could move today: [list].
> 
> Using the Global OS and my active projects, give me:
> - A short prioritized list of 3–5 tasks for today.
> - Each task must be finishable in one sitting.
> - Mark tasks by project.

Use this once at the start of your work block.

---

### 1.3. Weekly Portfolio Review (am I over-extended?)

**Command:**

> Run a Weekly Portfolio Review using my Global OS:
> - Assume I want at most 3–5 active projects.
> - For each active project, show:
>   - Status (IDEA / VALIDATING / BUILDING / LIVE),
>   - Primary metric,
>   - The most important validation or revenue task for this week.
> - If it looks like I’m overloaded, recommend which projects to park or kill and explain why.

Use this once a week.

---

### 1.4. Overwhelm Mode (I’m fried)

**Command:**

> I’m in Overwhelm Mode. I feel fried and my cognitive load is high.
> 
> Using my Global OS:
> - Briefly summarize my current OS priorities.
> - Give me at most 1–3 tiny, finishable tasks I can do today that are low friction but still meaningful.
> - Don’t expand the scope or introduce new projects.

Use this when you’re cooked and just need small, meaningful moves.

---

## 2. Alien Probe Project Commands

These assume `Project_AlienProbeReport_v1.md` and related files are in RAG.

### 2.1. Alien Probe Summary (where is this project at?)

**Command:**

> Using `Project_AlienProbeReport_v1` and any related Alien Probe artifacts in RAG, summarize:
> - Current status and main offer structure (Free Probe vs Deep Probe),
> - Current primary metric and target,
> - Last known validation experiments and results (even if approximate),
> - The next 3 concrete actions I should take this week to move Alien Probe forward.

Use when you’re coming back to Alien Probe after a gap.

---

### 2.2. Alien Probe – Validation Plan (how do I get Deep Probe sales?)

**Command:**

> Using my Global OS and `Project_AlienProbeReport_v1`, design a **simple validation plan** to get the first 10 Deep Probe sales.
> 
> Include:
> - 3–5 specific experiments (DMs, emails, posts, calls) I can actually run,
> - For each experiment:
>   - Who to contact,
>   - What to send/say (script or outline),
>   - The success metric,
> - A suggested order to run them in over the next 30 days.

Use when you want to make Alien Probe move real money, not just tweak documents.

---

### 2.3. Alien Probe – Asset Creation (give me the thing)

**Command (sales page example):**

> Using my Global OS and `Project_AlienProbeReport_v1`, create:
> - A one-page offer / sales page for Free Probe + Deep Probe for small business owners.
> 
> Follow the structure:
> - Headline,
> - Subhead,
> - Who this is for,
> - The problem,
> - The promise,
> - What they get (Free Probe vs Deep Probe),
> - Price and guarantee (if any),
> - Clear call-to-action.
> 
> At the end, suggest:
> - A filename,
> - RAG tags,
> for this asset.

You can swap “sales page” for “DM script”, “email sequence”, “PDR v1”, etc.

---

## 3. Decision & OS Tools Commands

### 3.1. Create a Decision Record

**Command:**

> I’m about to make a decision about: [brief topic, e.g., Deep Probe price].
> 
> Using my Global OS and the `OS_Execution_Rules_v1` Decision Record template, draft a Decision Record that includes:
> - Decision ID,
> - Context,
> - Options considered,
> - Chosen option and reasons,
> - Related metrics and time window,
> - Next review condition.

Use this for any big choice (pricing, avatar, main offer, kill/park call).

---

### 3.2. Freedom Map Check (am I about to overbuild?)

**Command:**

> Run a Freedom Map check on this build idea:
> [describe the build you’re thinking about].
> 
> Using my Global OS:
> - Tell me if I’m about to build too big without validation.
> - Suggest the smallest, fastest validation experiment I should run first instead of the big build.
> - If you still think the big build makes sense after that, explain why.

Use this before committing to any heavy build.

---

## 4. Quick Reminder: How to Talk About RAG in Prompts

If you want the model to **explicitly use your RAG docs**, say things like:

> “Using my `Global_OS_System_Prompt_v2_With_Glossary` and any relevant project/system files in RAG, help me…”  

or

> “Assume you have access to my OS files (`Global_OS_System_Prompt_v2_With_Glossary`, `OS_RAG_Usage_Instructions_v1`, `Project_AlienProbeReport_v1`) and answer…”

This nudges the model to reason *as if* it’s sitting on top of that context.

---

## 5. Minimal Set to Remember

If you remember nothing else, remember these **four commands**:

1. **Daily OS Check-In** – “What do I do today?”  
2. **Weekly Portfolio Review** – “Am I overextended?”  
3. **Alien Probe Summary** – “Where’s Alien Probe at?”  
4. **Overwhelm Mode** – “I’m fried; give me 1–3 tiny moves.”

Everything else lives in this cheat sheet.
