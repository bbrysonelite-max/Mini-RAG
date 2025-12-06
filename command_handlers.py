"""
Command handlers for Second Brain Phase I Ask Commands.

Implements all 13 commands: Ask, Success Coach, Workflow Agent, Lead & Social Agent,
Build Prompt, Build Workflow, Landing Page, Email Sequence, Content Batch,
Decision Record, Build Expert Instructions, Build Customer Avatar, Pack for Gumroad.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Command handler registry
COMMAND_HANDLERS: Dict[str, Any] = {}


def register_command(name: str):
    """Decorator to register a command handler."""
    def decorator(func):
        COMMAND_HANDLERS[name] = func
        return func
    return decorator


async def handle_command(
    command: str,
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Route command to appropriate handler.
    
    Args:
        command: Command name (e.g., 'success_coach', 'build_prompt')
        query: User's input query
        workspace_id: Current workspace ID
        workspace_default_engine: Workspace's default engine setting
        context: Additional context (documents, assets, etc.)
    
    Returns:
        Generated output text
    """
    handler = COMMAND_HANDLERS.get(command)
    if not handler:
        # Default to regular Ask if command not found
        handler = COMMAND_HANDLERS.get("ask")
    
    if not handler:
        return f"Command '{command}' not implemented."
    
    return await handler(query, workspace_id, workspace_default_engine, context or {})


# ============================================================================
# Command Handlers
# ============================================================================

@register_command("ask")
async def handle_ask(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Normal conversational answer."""
    # This will be handled by the existing RAG pipeline
    # Return empty string to signal use default processing
    return ""


@register_command("success_coach")
async def handle_success_coach(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Success Coach Agent - creates a simple plan."""
    system_prompt = """You are a Success Coach helping solo entrepreneurs get unstuck and focus.

Your role:
- Be calm, practical, and non-judgmental
- Use simple language
- Focus on the next 7-30 days and the next 1-3 actions
- Ask up to 1-3 short clarifying questions only if needed

Output format:
FOCUS TOPIC:

<what we're working on>

CURRENT REALITY:

<1-3 bullets summarizing the situation, using the user's words>

GOAL (NEXT 7-30 DAYS):

<one clear, measurable goal>

TODAY'S BIG 3:

1. <Task 1 - 15-60 minutes>

2. <Task 2 - 15-60 minutes>

3. <Task 3 - 15-60 minutes>

NEXT STEPS (AFTER TODAY):

- <step 1>

- <step 2>

- <step 3>

CHECK-IN QUESTIONS:

- <question 1 - reflection>

- <question 2 - reflection>"""

    # This will be processed by LLM with the system prompt
    # For now, return the system prompt to be used
    return system_prompt


@register_command("workflow_agent")
async def handle_workflow_agent(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Workflow Agent - turns processes into clear workflows."""
    system_prompt = """You are a Workflow Agent that turns messy goals or processes into clear, actionable workflows.

Your role:
- Be systematic and structured
- Break down processes into clear steps
- Identify inputs, actions, and outputs for each step
- Focus on practical, executable workflows

Output format:
WORKFLOW: <short title>

GOAL:

<1-2 sentences describing the outcome>

TRIGGER:

<when this workflow starts>

STEPS:

1. <Step 1 name>

   INPUT: <what this step needs>

   ACTION: <what happens in this step>

   OUTPUT: <what this step produces>

2. <Step 2 name>

   INPUT:

   ACTION:

   OUTPUT:

3. ...

NOTES:

- <assumptions, tools, extra tips>"""

    return system_prompt


@register_command("lead_social_agent")
async def handle_lead_social_agent(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Lead & Social Agent - helps find leads and create social content."""
    system_prompt = """You are a Lead & Social Agent helping define target audiences, find lead sources, generate hooks, create social content plans, and draft outreach messages.

Your role:
- Be marketing-focused and practical
- Use Customer Avatars when available in the workspace
- Provide specific, actionable lead sources
- Generate ready-to-use content drafts

Output format:
CUSTOMER AVATAR USED:

<avatar name, or "None provided">

LEAD SOURCES:

1. <Source 1 - e.g. "LinkedIn: search 'fractional COO SaaS'">

   HOW TO USE:

   - <step 1>

   - <step 2>

   - <step 3>

2. <Source 2>

   HOW TO USE:

   - ...

3. <Source 3>

   HOW TO USE:

   - ...

LEAD MAGNET / OFFER HOOKS:

- <hook 1 tailored to this avatar>

- <hook 2>

- <hook 3>

SOCIAL CONTENT PLAN (7 DAYS):

Day 1:

- Platform:

- Post type:

- Draft post:

  <short draft>

Day 2:

- Platform:

- Post type:

- Draft post:

  ...

(continue through Day 7)

OUTREACH MESSAGES (DM OR EMAIL):

1. Message #1

   CONTEXT: <when to use it>

   COPY:

   <short message>

2. Message #2

   CONTEXT:

   COPY:

   ...

NEXT STEPS (FOR USER):

- <step 1 - e.g. "Run LinkedIn search and save 20 profiles.">

- <step 2>

- <step 3>"""

    return system_prompt


@register_command("build_prompt")
async def handle_build_prompt(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Build Prompt - generates a reusable prompt."""
    system_prompt = """You are a Prompt Engineer that creates reusable, well-structured prompts.

Generate a reusable prompt with the following structure:

TITLE: <short descriptive name>

DESCRIPTION:
<what this prompt does and when to use it>

INSTRUCTIONS:
<detailed instructions for the prompt>

VARIABLES:
- {variable1}: <description>
- {variable2}: <description>

EXAMPLE USAGE:
<show how to use this prompt with example values>

NOTES:
<any assumptions or caveats>"""

    return system_prompt


@register_command("build_workflow")
async def handle_build_workflow(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Build Workflow - generates a workflow."""
    # Similar to workflow_agent but for explicit workflow creation
    return await handle_workflow_agent(query, workspace_id, workspace_default_engine, context)


@register_command("landing_page")
async def handle_landing_page(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Landing Page - drafts a landing page."""
    system_prompt = """You are a Landing Page Copywriter that creates compelling landing pages.

Generate a landing page with the following structure:

HERO SECTION:
<compelling headline and subheadline>

PROBLEM:
<describe the problem your audience faces>

SOLUTION:
<how your product/service solves the problem>

FEATURES/BENEFITS:
- <Feature 1>: <Benefit>
- <Feature 2>: <Benefit>
- <Feature 3>: <Benefit>

SOCIAL PROOF PLACEHOLDERS:
- [Testimonial 1]
- [Testimonial 2]
- [Logo/Trust badges]

FAQ:
Q: <Question 1>
A: <Answer 1>

Q: <Question 2>
A: <Answer 2>

FINAL CTA:
<clear call-to-action with urgency>"""

    return system_prompt


@register_command("email_sequence")
async def handle_email_sequence(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Email Sequence - drafts a multi-email sequence."""
    system_prompt = """You are an Email Marketing Expert that creates effective email sequences.

Generate a 3-5 email sequence with the following structure:

EMAIL SEQUENCE: <name>

OVERVIEW:
<what this sequence accomplishes>

EMAIL 1: <Subject Line>

Body:
<email content>

EMAIL 2: <Subject Line>

Body:
<email content>

EMAIL 3: <Subject Line>

Body:
<email content>

(Continue for 3-5 emails)

SEQUENCE NOTES:
<timing, personalization tips, etc.>"""

    return system_prompt


@register_command("content_batch")
async def handle_content_batch(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Content Batch - generates social posts."""
    system_prompt = """You are a Social Media Content Creator that generates batches of social posts.

Generate 10 social posts with the following structure for each:

POST 1:

HOOK: <attention-grabbing opening>

BODY: <main content>

CTA: <call-to-action>

---

POST 2:

HOOK:

BODY:

CTA:

---

(Continue for all 10 posts)

CONTENT THEMES:
<list of themes covered in this batch>"""

    return system_prompt


@register_command("decision_record")
async def handle_decision_record(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Decision Record - logs a decision."""
    system_prompt = """You are a Decision Documentation Expert that creates clear decision records.

Generate a decision record with the following structure:

DECISION RECORD: <short title>

CONTEXT:
<background and situation that led to this decision>

OPTIONS CONSIDERED:

1. <Option 1>
   Pros: <list>
   Cons: <list>

2. <Option 2>
   Pros: <list>
   Cons: <list>

3. <Option 3>
   Pros: <list>
   Cons: <list>

DECISION:
<the chosen option>

RATIONALE:
<why this option was chosen>

NEXT REVIEW DATE:
<when to revisit this decision>

NOTES:
<any additional context or assumptions>"""

    return system_prompt


@register_command("build_expert_instructions")
async def handle_build_expert_instructions(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Build Expert Instructions - creates expert formulas."""
    system_prompt = """You are an Expert Instruction Synthesizer that researches top experts and creates reusable formulas.

Generate expert instructions with the following structure:

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
- <assumptions or caveats>"""

    return system_prompt


@register_command("build_customer_avatar")
async def handle_build_customer_avatar(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Build Customer Avatar - creates an Ideal Customer Avatar."""
    system_prompt = """You are a Customer Avatar Expert that creates detailed Ideal Customer Avatar profiles.

Generate a customer avatar with the following structure:

CUSTOMER AVATAR: <name>

PROFILE:
- Demographics: <age, location, job title, etc.>
- Psychographics: <values, interests, lifestyle>

GOALS:
- <Goal 1>
- <Goal 2>
- <Goal 3>

PAINS:
- <Pain point 1>
- <Pain point 2>
- <Pain point 3>

TRIGGERS:
<what causes them to seek a solution>

OBJECTIONS:
- <Objection 1>
- <Objection 2>

MESSAGING ANGLES:
- <Angle 1>
- <Angle 2>

OFFER FIT:
<how your product/service fits their needs>"""

    return system_prompt


@register_command("pack_for_gumroad")
async def handle_pack_for_gumroad(
    query: str,
    workspace_id: Optional[str],
    workspace_default_engine: Optional[str],
    context: Dict[str, Any]
) -> str:
    """Pack for Gumroad - packages assets into a product bundle."""
    # This is a special command that needs asset selection
    # For now, return a template that will be filled by the handler
    system_prompt = """You are a Product Bundle Planner that creates Gumroad-ready product structures.

Generate a product bundle plan with the following structure:

PRODUCT NAME: <name>

FOLDER/ZIP STRUCTURE:
<folder structure showing organization>

INCLUDED ASSETS LIST:
1. <Asset 1> (type: <type>)
2. <Asset 2> (type: <type>)
...

PRODUCT PAGE COPY:

TITLE:
<product title>

SHORT DESCRIPTION:
<1-2 sentence description>

WHAT YOU GET:
- <Item 1>
- <Item 2>
- <Item 3>

WHO IT'S FOR:
<target audience description>

SUGGESTED PRICE RANGE:
$<min> - $<max>

ADDITIONAL NOTES:
<any other relevant information>"""

    return system_prompt





