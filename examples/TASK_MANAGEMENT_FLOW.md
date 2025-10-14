# Task Management Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent CLI with Task Management                   │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ User Starts  │
│   Example    │
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│ Select Agent    │
│ Type:           │
│ 1. Simple       │
│ 2. Workflow     │
└──────┬──────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Agent Created/Retrieved                        │
│  • task_id = None                                                │
│  • context_id = None                                             │
│  • conversation_history = []                                     │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    User Sends First Message                       │
│                                                                   │
│  metadata = {}  (empty - no task_id yet)                         │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│              Agent Processes & Returns Response                   │
│                                                                   │
│  Response includes:                                              │
│    - metadata.task_id = "wf_abc123"                              │
│    - metadata.context_id = "ctx_xyz789"                          │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│               Extract & Store Task Information                    │
│                                                                   │
│  task_id = "wf_abc123"      ← Extracted from response            │
│  context_id = "ctx_xyz789"  ← Extracted from response            │
│                                                                   │
│  Display: [📋 Task ID: wf_abc123]                                │
│           [🔗 Context ID: ctx_xyz789]                            │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  User Sends Second Message                        │
│                                                                   │
│  metadata = {                                                    │
│    "task_id": "wf_abc123",      ← Same task continues           │
│    "context_id": "ctx_xyz789"                                    │
│  }                                                               │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│           Agent Processes with Task Context                       │
│                                                                   │
│  • Has conversation history                                      │
│  • Has task context from previous interaction                    │
│  • Returns response with same task_id                            │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ├─────────── User Commands ───────────┐
       │                                      │
       ▼                                      ▼
┌──────────────┐                    ┌──────────────────┐
│ Command:     │                    │ Command:         │
│   'clear'    │                    │   'newtask'      │
└──────┬───────┘                    └──────┬───────────┘
       │                                    │
       ▼                                    ▼
┌──────────────┐                    ┌──────────────────┐
│ • Reset ALL  │                    │ • Reset task_id  │
│ • task_id    │                    │ • Reset ctx_id   │
│ • context_id │                    │ • KEEP history   │
│ • history    │                    └──────────────────┘
└──────────────┘


═══════════════════════════════════════════════════════════════════
                         Streaming vs Non-Streaming
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│                     Non-Streaming Mode                           │
└─────────────────────────────────────────────────────────────────┘

User Message
     │
     ▼
┌─────────────────────┐
│ Send full request   │
│ with metadata       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Wait for complete   │
│ response            │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Extract task_id &   │
│ context_id from     │
│ response.metadata   │
└──────┬──────────────┘
       │
       ▼
Display full response


┌─────────────────────────────────────────────────────────────────┐
│                      Streaming Mode                              │
└─────────────────────────────────────────────────────────────────┘

User Message
     │
     ▼
┌─────────────────────┐
│ Send streaming      │
│ request with        │
│ metadata            │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ First chunk arrives │
│ Extract task_id &   │
│ context_id from     │
│ chunk.metadata      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Display task info   │
│ [📋 Task ID: ...]   │
│ [🔗 Context ID: ..]  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Stream content      │
│ chunks one by one   │
│ character-by-char   │
└──────┬──────────────┘
       │
       ▼
Display complete response


═══════════════════════════════════════════════════════════════════
                    Workflow Agent Execution
═══════════════════════════════════════════════════════════════════

User: "Help me write a Python function"
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Analyze Request                                      │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Prompt: "Analyze the user's request and identify         │ │
│ │          key requirements."                              │ │
│ │                                                          │ │
│ │ Agent analyzes:                                          │ │
│ │ - User wants to write a Python function                 │ │
│ │ - Need to understand what the function should do        │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Generate Response                                    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Prompt: "Generate a comprehensive response based on     │ │
│ │          the analysis."                                 │ │
│ │                                                          │ │
│ │ Agent generates:                                         │ │
│ │ - Asks clarifying questions about function requirements │ │
│ │ - Provides initial suggestions                          │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
Final response to user


═══════════════════════════════════════════════════════════════════
                     State Machine Diagram
═══════════════════════════════════════════════════════════════════

                    ┌──────────────┐
                    │  NO TASK     │
                    │ task_id=None │
                    └──────┬───────┘
                           │
                    User sends message
                           │
                           ▼
                    ┌──────────────┐
                    │ TASK CREATED │
                    │ task_id=xyz  │
                    └──┬─────────┬─┘
                       │         │
         User message  │         │  'clear' or 'newtask'
              │        │         │         │
              ▼        │         │         ▼
         ┌──────────────┐       └──► ┌──────────────┐
         │ TASK ACTIVE  │            │  NO TASK     │
         │ Same task_id │            │ task_id=None │
         └──────────────┘            └──────────────┘
                                            │
                                            │
                                     User message
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │ NEW TASK     │
                                     │ task_id=new  │
                                     └──────────────┘
```
