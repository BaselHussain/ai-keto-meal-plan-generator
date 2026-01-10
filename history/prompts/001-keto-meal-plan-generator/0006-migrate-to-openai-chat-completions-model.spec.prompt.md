---
id: 0006
title: Migrate to OpenAIChatCompletionsModel
stage: spec
date: 2025-12-23
surface: agent
model: claude-sonnet-4-5
feature: 001-keto-meal-plan-generator
branch: 001-keto-meal-plan-generator
user: user
command: continue
labels: ["spec", "technical-decision", "openai-agents-sdk", "ai-integration"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-keto-meal-plan-generator/spec.md
tests:
  - None (spec phase)
---

## Prompt

User requested continuation from previous session: "Please continue the conversation from where we left it off without asking the user any further questions. Continue with the last task that you were asked to work on."

Context: User had explicitly stated: "we will not us litellm rather use OpenAIChatCompletionsModel, you can search for it in docs using context7 mcp server"

Goal: Complete migration from LiteLLM integration to OpenAIChatCompletionsModel pattern for OpenAI Agents SDK, using AsyncOpenAI client with custom base_url for Gemini API.

## Response snapshot

Completed spec migration from LiteLLM to OpenAIChatCompletionsModel:

**Updated Sections:**

1. **FR-A-001 (Line 195)**: Replaced LiteLLM-based integration with OpenAIChatCompletionsModel pattern
   - Before: "use Gemini (litellm/gemini/gemini-2.0-flash) in dev/testing"
   - After: "configure AsyncOpenAI client with custom base_url for Gemini API (dev/testing: base_url='https://generativelanguage.googleapis.com/v1beta', api_key=GEMINI_API_KEY); use standard OpenAI API client for production"

2. **Technology Stack Dependencies (Line 345)**: Removed LiteLLM extra from pip install
   - Before: `pip install "openai-agents[litellm]"`
   - After: `pip install "openai-agents"`

3. **External Service Dependencies (Line 337)**: Clarified AI service integration approach
   - Before: "AI meal plan generation (model selection based on cost/quality tradeoff)"
   - After: "AI meal plan generation via OpenAI Agents SDK; Gemini (dev/testing) accessed via AsyncOpenAI client with custom base_url; OpenAI (production) via standard AsyncOpenAI client; model selection based on environment"

**Verification:**
- Ran `grep -i "litellm"` on spec.md: No matches (all references removed)
- Clarification on Line 43 already correctly referenced OpenAIChatCompletionsModel
- FR-A-013 already correctly referenced Agent class with @function_tool decorators

**Technical Pattern Established:**
```python
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel

# Dev/Testing: Gemini via custom AsyncOpenAI client
gemini_agent = Agent(
    name="Meal Plan Generator",
    model=OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key=GEMINI_API_KEY
        )
    ),
)

# Production: OpenAI via standard client
openai_agent = Agent(
    name="Meal Plan Generator",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY)
    ),
)
```

## Outcome

- ✅ Impact: Critical technical decision implemented; spec now uses OpenAIChatCompletionsModel (NOT LiteLLM) for OpenAI Agents SDK integration; enables proper Gemini API integration via AsyncOpenAI with custom base_url
- 🧪 Tests: No tests run (specification phase)
- 📁 Files: Updated spec.md (3 sections: FR-A-001, Technology Stack, External Service Dependencies); removed all LiteLLM references
- 🔁 Next prompts: /sp.plan to create architecture plan (spec is 100% complete and technically accurate)
- 🧠 Reflection: User correction was critical; LiteLLM was incorrectly suggested initially; OpenAIChatCompletionsModel with custom AsyncOpenAI client is the correct pattern for multi-provider support in OpenAI Agents SDK

## Evaluation notes (flywheel)

- Failure modes observed: Initially suggested LiteLLM integration (incorrect); corrected after user feedback
- Graders run and results (PASS/FAIL): Not applicable (spec phase)
- Prompt variant (if applicable): continuation-after-context-limit-v1
- Next experiment (smallest change to try): None needed; spec technically complete and ready for planning
