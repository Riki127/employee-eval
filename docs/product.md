# Product

## Problem

Assessing whether an employee's skills are below, meeting, or exceeding
expectations for their role today relies on manual, ad-hoc review — generic
questionnaires that aren't tailored to the role, no consistent record of what
was actually asked or answered, and evaluations that vary by whoever runs
them. This app should replace that with a consistent, role-aware, AI-driven
assessment process that produces a defensible, repeatable evaluation.

## Users

- **Employee** — takes the assessment; answers a dynamic, role-relevant
  questionnaire.
- **Manager** — reviews an employee's evaluation results and rationale.
- **HR / people ops (admin)** — configures roles/tiers, launches assessment
  cycles, and has visibility across employees.

## Core functionality

- Define roles and role tiers with the expectations an employee at each tier
  should meet.
- Start an assessment session for an employee against their current role.
- AI agent dynamically generates role-relevant questions for the session,
  adapting based on prior answers within that session.
- Session context (all QA pairs) is preserved and sent to the evaluation
  agent so the evaluation reflects the full conversation, not just the last
  answer.
- Evaluation agent scores the session and produces a structured verdict:
  below / meeting / exceeding expectations for the role tier, with
  supporting rationale.
- Evaluation agent also produces a learning recommendation tailored to the
  verdict:
  - **Below expectations** — recommend what to learn to close the gap to
    the current role tier's expectations.
  - **Meeting or exceeding expectations** — recommend what to learn to
    reach the next role tier.
- Employees, managers, and admins can view past sessions and their results
  (scoped to what each role is permitted to see).

## User flows

1. **Take an assessment** — Employee starts a session for their role → AI
   asks a question → employee answers → AI asks the next role-relevant
   question using prior context → ... → session ends → evaluation agent
   scores the full session → result and learning recommendation are stored
   and shown.
2. **Review results** — Manager/admin opens a completed session → sees the
   verdict (below/meeting/exceeding), rationale, learning recommendation,
   and the underlying QA transcript.
3. **Configure roles** — Admin defines/edits a role and its tier
   expectations that the question-generation and evaluation agents use.

## Out of scope

- Payroll, compensation, or promotion decisions (this tool informs, not
  decides, those processes).
- Peer or 360-degree feedback collection.
- Real-time proctoring or anti-cheating enforcement during a session.

## Success criteria

- An employee can complete a full assessment session end-to-end without
  manual intervention.
- Evaluation verdicts are consistent for similar answers across sessions
  (same rubric applied reliably).
- Managers/admins can find and understand a past evaluation's rationale
  without needing to re-read the raw transcript.
