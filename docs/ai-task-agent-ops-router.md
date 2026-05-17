# AI Task Agent Ops Router

## Business Problem

Operations teams often ask for task changes in Gmail using natural language. Some requests are simple, such as creating a follow-up task. Others update an existing task or are ambiguous enough to need a human manager.

This workflow demonstrates the original repository task agent as a practical Gmail operations router.

## Trigger

The workflow starts with a Gmail-style webhook:

```text
POST /webhook/task-agent-ops-demo
```

In production this would be a Gmail message such as:

```text
Subject: Create a high priority task to review Q4 financial reports
```

## Backend Endpoint

n8n calls:

```text
POST http://workflow-agent:8000/webhook/task
```

The backend classifies intent as:

```text
CREATE -> create a task
UPDATE -> update an existing task
ESCALATE -> route to human review
```

## Node Sequence

```text
Gmail Intake - Ops Task Request
-> Normalize Gmail Task Request
-> Request Clear Enough?
-> Attach Routing Policy Context
-> FastAPI LangGraph Task Agent
-> Append Audit Log Row
-> Requires Human Review?
-> Gmail Alert - Human Ops Review
-> Respond to Gmail Intake
```

Failure and clarification path:

```text
Normalize Gmail Task Request
-> Request Clear Enough?
-> Gmail Clarification Request
-> Respond to Gmail Intake
```

This branch catches vague emails such as "please handle this" and asks the requester for the task action, priority, and task ID if it is an update.

Non-escalated requests route through:

```text
Requires Human Review?
-> Intent is CREATE?
-> Create Task Board Card
-> Respond to Gmail Intake
```

or:

```text
Requires Human Review?
-> Intent is CREATE?
-> Update Task Board Card
-> Respond to Gmail Intake
```

## Demo Payload

```json
{
  "from": "ops-manager@company.local",
  "to": "ops-tasks@company.local",
  "subject": "Create a high priority task to review Q4 financial reports",
  "body": "Please track this for the finance operations workflow."
}
```

## Portfolio Framing

Turns natural-language Gmail requests into structured task operations using LangGraph intent routing, FastAPI webhooks, audit logging, and human-in-the-loop escalation.

