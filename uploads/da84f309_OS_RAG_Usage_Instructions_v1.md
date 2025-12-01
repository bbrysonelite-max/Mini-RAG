<!--
RAG-META:
filename: OS_RAG_Usage_Instructions_v1.md
namespace: os_core
tags: scope:os, type:instructions, status:active
-->

# OS RAG Usage – Commands, Tags, and Ingestion Rules (v1)

## 1. Namespaces

Use these namespaces in your RAG:

- `os_core`  
  Global OS, templates, rituals, index, instructions.

- `project_alienprobe`  
  Core Alien Probe docs (system prompt, PDR, blueprint, decisions).

- `project_alienprobe_marketing`  
  Alien Probe marketing assets (sales pages, emails, DM scripts).

- `project_alienprobe_reports`  
  Alien Probe fulfillment and report workflows.

- Future projects:  
  `project_{lowercase_name}`  
  e.g. `project_ai_me`, `project_wannagolfbuddy`.


## 2. Tag Schema

Apply tags consistently to every document.

**Required tags (minimum):**

- `scope:`  
  - `scope:os`  
  - `scope:project`  
  - `scope:asset`  
  - `scope:decision`  
  - `scope:experiment`

- `project:` (for project docs)  
  - Example: `project:AlienProbeReport`

- `type:`  
  - `type:system-prompt`  
  - `type:template`  
  - `type:blueprint`  
  - `type:PDR`  
  - `type:sales-page`  
  - `type:workflow`  
  - `type:dm-script`  
  - `type:decision`  
  - `type:experiment`  
  - `type:test-suite`  
  - `type:index`  
  - `type:instructions`

- `status:`  
  - `status:draft`  
  - `status:active`  
  - `status:deprecated`  
  - `status:killed`  
  - `status:VALIDATING`  
  - `status:LIVE`

**Optional tags:**

- `subtype:` (for templates, e.g. `subtype:project-system-prompt`)
- `version:` if your RAG supports key-value tagging.


## 3. File Naming and Versioning Rules

**Filename pattern:**

`{Project}_{ArtifactType}_{ShortDescription}_v{N}.md`

Examples:

- `Global_OS_System_Prompt_v2_With_Glossary.md`  
- `Project_AlienProbeReport_v1.md`  
- `AlienProbe_SalesPage_Free+DeepProbe_v1.md`  
- `AlienProbe_PDR_v1.md`

**Versioning:**

- v1: first usable draft.  
- Bump to v2, v3, etc. only when structure/content changes meaningfully.  
- Keep old versions; mark them with `status:deprecated` if replaced by a newer version.


## 4. Ingestion Checklist

When you ingest any document into RAG:

1. **Choose namespace**
   - OS-level: `os_core`
   - Alien Probe: `project_alienprobe` (and related namespaces)
   - Future projects: `project_{name}`

2. **Set tags** (at least in the text header or metadata)
   - `scope:...`
   - `type:...`
   - `status:...`
   - `project:...` for project docs

3. **Confirm filename**
   - Follows `{Project}_{ArtifactType}_{ShortDescription}_v{N}.md`.

4. **Update index**
   - Add or update an entry in `RAG_Index_Core_v1.md` when you create an important new artifact.


## 5. LLM Glue Commands (Cheat Sheet)

Use these in ChatGPT/Cursor (you don’t have to memorize them; they live here).

### 5.1 OS Summary

> **Command: OS Summary**  
> “Using my `Global_OS_System_Prompt_v2_With_Glossary`, summarize:
> - My core operating principles in 5–10 bullets.
> - How you and I should work together today in 3–5 bullets.”

### 5.2 Daily OS Check-In

> **Command: Daily OS Check-In**  
> “Daily OS check-in:
> 1. Here is my current energy and constraints for today: [describe].
> 2. Here are the 1–3 most important outcomes I could move today: [list].
> 
> Using the Global OS and my active projects, give me:
> - A short prioritized list of 3–5 tasks for today.
> - Each task must be finishable in one sitting.
> - Mark tasks by project.”

### 5.3 Weekly Portfolio Review

> **Command: Weekly Portfolio Review**  
> “Run a Weekly Portfolio Review using my Global OS:
> - Assume I want at most 3–5 active projects.
> - For each active project, show:
>   - Status (IDEA / VALIDATING / BUILDING / LIVE),
>   - Primary metric,
>   - The most important validation or revenue task for this week.
> - If it looks like I’m overloaded, recommend projects to park or kill and explain why.”

### 5.4 Alien Probe Summary

> **Command: Alien Probe Summary**  
> “Using `Project_AlienProbeReport_v1` and any related artifacts from the Alien Probe namespaces, summarize:
> - Current status and main offer structure (Free Probe vs Deep Probe),
> - Current primary metric and target,
> - Last known validation experiments and results,
> - The next 3 concrete actions I should take this week to move Alien Probe forward.”

### 5.5 Overwhelm Mode

> **Command: Overwhelm Mode**  
> “I’m in Overwhelm Mode. I feel fried and my cognitive load is high.
> - Briefly summarize my current OS priorities.
> - Give me at most 1–3 tiny, finishable tasks I can do today that are low friction but still meaningful.
> - Don’t expand the scope or introduce new projects.”


## 6. Multi-Model Collaboration Rule

For major artifacts (system prompts, PDRs, core sales pages):

- Creation:
  - Use one primary model/persona to draft.

- Review:
  - Optionally use a different model/persona to critique and stress-test.

- Decision:
  - Pick a final version and log it with a Decision Record.
  - Mark chosen version `status:active`; others can be `status:deprecated` if kept.


## 7. Ingestion Priority (Bootstrap Order)

When setting up or rebuilding RAG, ingest in this order:

1. `Global_OS_System_Prompt_v2_With_Glossary.md` → `os_core`  
2. `OS_RAG_Usage_Instructions_v1.md` → `os_core`  
3. `Project_Prompt_Template_v2.md` → `os_core`  
4. `Project_AlienProbeReport_v1.md` → `project_alienprobe`  
5. `OS_Prompt_Tests_v1.md` → `os_core`  
6. `OS_Execution_Rules_v1.md` → `os_core`  
7. `RAG_Index_Core_v1.md` → `os_core`
