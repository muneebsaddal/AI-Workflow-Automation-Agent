"""
AI Workflow Automation Agent
Complete implementation with LangGraph, Redis-like storage, and execution tracing
Using Ollama with Mistral for local LLM inference
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Annotated
from enum import Enum

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration for the workflow agent"""
    # Ollama settings
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
    
    # Storage settings
    STORAGE_FILE = os.getenv("STORAGE_FILE", "tasks_db.json")
    LOGS_FILE = os.getenv("LOGS_FILE", "execution_logs.json")
    
    # Model temperature (0 = deterministic, 1 = creative)
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))


# ============================================================================
# ENUMS AND TYPES
# ============================================================================

class TaskAction(str, Enum):
    """Possible task actions"""
    CREATE = "create"
    UPDATE = "update"
    ESCALATE = "escalate"


class TaskStatus(str, Enum):
    """Task status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"


# ============================================================================
# STATE DEFINITION
# ============================================================================

class WorkflowState(TypedDict):
    """State that flows through the graph"""
    input: str
    task_id: str | None
    intent: TaskAction | None
    task_data: dict | None
    decision_reasoning: str
    execution_result: str
    execution_trace: list[dict]
    requires_human: bool
    error: str | None


# ============================================================================
# MOCK DATABASE (JSON-based)
# ============================================================================

class TaskDatabase:
    """Simple JSON-based task storage (Redis-like interface)"""
    
    def __init__(self, filepath: str = Config.STORAGE_FILE):
        self.filepath = filepath
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create storage file if it doesn't exist"""
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump({"tasks": {}, "counter": 0}, f, indent=2)
        else:
            # Validate existing file
            try:
                with open(self.filepath, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        # Empty file, initialize
                        with open(self.filepath, 'w') as fw:
                            json.dump({"tasks": {}, "counter": 0}, fw, indent=2)
                    else:
                        data = json.loads(content)
                        # Ensure required keys exist
                        if "tasks" not in data or "counter" not in data:
                            with open(self.filepath, 'w') as fw:
                                json.dump({"tasks": {}, "counter": 0}, fw, indent=2)
            except json.JSONDecodeError:
                # Corrupted file, reinitialize
                with open(self.filepath, 'w') as f:
                    json.dump({"tasks": {}, "counter": 0}, f, indent=2)
    
    def _load(self) -> dict:
        """Load database"""
        try:
            with open(self.filepath, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {"tasks": {}, "counter": 0}
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"tasks": {}, "counter": 0}
    
    def _save(self, data: dict):
        """Save database"""
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_task(self, title: str, description: str, priority: str = "medium") -> dict:
        """Create a new task"""
        db = self._load()
        db["counter"] += 1
        task_id = f"TASK-{db['counter']:04d}"
        
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "history": []
        }
        
        db["tasks"][task_id] = task
        self._save(db)
        return task
    
    def get_task(self, task_id: str) -> dict | None:
        """Get a task by ID"""
        db = self._load()
        return db["tasks"].get(task_id)
    
    def update_task(self, task_id: str, updates: dict) -> dict | None:
        """Update an existing task"""
        db = self._load()
        task = db["tasks"].get(task_id)
        
        if not task:
            return None
        
        # Log history
        task["history"].append({
            "timestamp": datetime.now().isoformat(),
            "changes": updates
        })
        
        # Apply updates
        task.update(updates)
        task["updated_at"] = datetime.now().isoformat()
        
        db["tasks"][task_id] = task
        self._save(db)
        return task
    
    def list_tasks(self, status: str | None = None) -> list[dict]:
        """List all tasks, optionally filtered by status"""
        db = self._load()
        tasks = list(db["tasks"].values())
        
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        
        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)
    
    def escalate_task(self, task_id: str, reason: str) -> dict | None:
        """Mark task as escalated"""
        return self.update_task(task_id, {
            "status": TaskStatus.ESCALATED.value,
            "escalation_reason": reason,
            "escalated_at": datetime.now().isoformat()
        })


# ============================================================================
# EXECUTION LOGGER
# ============================================================================

class ExecutionLogger:
    """Logs execution traces"""
    
    def __init__(self, filepath: str = Config.LOGS_FILE):
        self.filepath = filepath
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create logs file if it doesn't exist"""
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump([], f)
    
    def log_execution(self, state: WorkflowState):
        """Log a workflow execution"""
        try:
            with open(self.filepath, 'r') as f:
                content = f.read().strip()
                if not content:
                    logs = []
                else:
                    logs = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or doesn't exist, start fresh
            logs = []
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "input": state["input"],
            "intent": state.get("intent"),
            "task_id": state.get("task_id"),
            "result": state.get("execution_result"),
            "trace": state.get("execution_trace", []),
            "error": state.get("error")
        }
        
        logs.append(log_entry)
        
        # Keep only last 100 logs
        logs = logs[-100:]
        
        with open(self.filepath, 'w') as f:
            json.dump(logs, f, indent=2)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "input": state["input"],
            "intent": state.get("intent"),
            "task_id": state.get("task_id"),
            "result": state.get("execution_result"),
            "trace": state.get("execution_trace", []),
            "error": state.get("error")
        }
        
        logs.append(log_entry)
        
        # Keep only last 100 logs
        logs = logs[-100:]
        
        with open(self.filepath, 'w') as f:
            json.dump(logs, f, indent=2)


# ============================================================================
# GRAPH NODES
# ============================================================================

class WorkflowAgent:
    """Main workflow automation agent"""
    
    def __init__(self, model: str = None):
        """
        Initialize the agent with specified Ollama model
        
        Args:
            model: Ollama model name (mistral:latest, deepseek-coder:6.7b, gemma3:270m)
        """
        self.model_name = model or Config.OLLAMA_MODEL
        
        # Initialize Ollama LLM with CPU fallback
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=self.model_name,
            temperature=Config.TEMPERATURE,
            # Increase timeout for CPU processing
            request_timeout=120.0,
            # Force CPU usage to avoid CUDA errors
            num_gpu=0
        )
        
        self.db = TaskDatabase()
        self.logger = ExecutionLogger()
        
        print(f"🤖 Initialized agent with Ollama model: {self.model_name}")
        print(f"🖥️  Using CPU inference (GPU disabled to prevent CUDA errors)")
    
    def intent_classifier(self, state: WorkflowState) -> WorkflowState:
        """Classify the user's intent using Ollama LLM"""
        trace_entry = {
            "step": "intent_classifier",
            "timestamp": datetime.now().isoformat(),
            "model": self.model_name
        }
        
        system_prompt = """You are an intent classifier for a task management system.

Analyze the user's input and determine their intent:
- CREATE: User wants to create a new task
- UPDATE: User wants to update an existing task (must mention task ID like TASK-0001)
- ESCALATE: Issue is complex, unclear, or requires human judgment

You must respond with ONLY valid JSON, no other text.

Example response format:
{
    "intent": "CREATE",
    "reasoning": "User wants to create a new task with high priority",
    "extracted_data": {
        "task_id": null,
        "title": "Review Q4 financial reports",
        "description": "Comprehensive review of Q4 financials",
        "priority": "high",
        "status": null
    }
}

Rules:
- intent must be exactly one of: CREATE, UPDATE, or ESCALATE
- For CREATE: task_id should be null, include title and description
- For UPDATE: task_id must be provided (format: TASK-XXXX)
- For ESCALATE: use when request is unclear or complex
- priority: low, medium, or high (if mentioned)
- status: pending, in_progress, or completed (if mentioned)

Respond with ONLY the JSON object, nothing else."""

        user_message = f"User input: {state['input']}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        try:
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Clean up response - remove markdown code blocks if present
            if response_text.startswith("```"):
                # Extract JSON from code block
                lines = response_text.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_json = not in_json
                        continue
                    if in_json or (not line.strip().startswith("```")):
                        json_lines.append(line)
                response_text = '\n'.join(json_lines).strip()
            
            # Parse LLM response
            result = json.loads(response_text)
            
            state["intent"] = TaskAction(result["intent"].lower())
            state["decision_reasoning"] = result["reasoning"]
            state["task_data"] = result["extracted_data"]
            
            trace_entry["output"] = {
                "intent": state["intent"],
                "reasoning": state["decision_reasoning"]
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"Response was: {response_text[:200]}...")
            state["error"] = f"Failed to parse LLM response: {str(e)}"
            state["intent"] = TaskAction.ESCALATE
            state["decision_reasoning"] = "Could not parse AI response"
            trace_entry["error"] = str(e)
            
        except Exception as e:
            print(f"⚠️  Intent classification error: {e}")
            state["error"] = f"Intent classification failed: {str(e)}"
            state["intent"] = TaskAction.ESCALATE
            state["decision_reasoning"] = "Error during classification"
            trace_entry["error"] = str(e)
        
        state["execution_trace"].append(trace_entry)
        return state
    
    def route_decision(self, state: WorkflowState) -> Literal["create_update", "escalate"]:
        """Route based on classified intent"""
        trace_entry = {
            "step": "route_decision",
            "timestamp": datetime.now().isoformat(),
            "decision": state["intent"]
        }
        state["execution_trace"].append(trace_entry)
        
        if state["intent"] == TaskAction.ESCALATE or state.get("error"):
            return "escalate"
        return "create_update"
    
    def create_update_task(self, state: WorkflowState) -> WorkflowState:
        """Create or update a task"""
        trace_entry = {
            "step": "create_update_task",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            task_data = state["task_data"]
            
            if state["intent"] == TaskAction.CREATE:
                # Create new task
                task = self.db.create_task(
                    title=task_data.get("title", "Untitled Task"),
                    description=task_data.get("description", ""),
                    priority=task_data.get("priority", "medium")
                )
                state["task_id"] = task["id"]
                state["execution_result"] = f"✅ Task created successfully: {task['id']}"
                trace_entry["action"] = "create"
                trace_entry["task_id"] = task["id"]
                
            elif state["intent"] == TaskAction.UPDATE:
                # Update existing task
                task_id = task_data.get("task_id")
                
                if not task_id:
                    state["error"] = "No task ID provided for update"
                    state["execution_result"] = "❌ Update failed: No task ID specified"
                    trace_entry["error"] = "No task ID"
                else:
                    # Build updates dict
                    updates = {}
                    if task_data.get("status"):
                        updates["status"] = task_data["status"]
                    if task_data.get("priority"):
                        updates["priority"] = task_data["priority"]
                    if task_data.get("description"):
                        updates["description"] = task_data["description"]
                    
                    task = self.db.update_task(task_id, updates)
                    
                    if task:
                        state["task_id"] = task_id
                        state["execution_result"] = f"✅ Task updated successfully: {task_id}"
                        trace_entry["action"] = "update"
                        trace_entry["task_id"] = task_id
                        trace_entry["updates"] = updates
                    else:
                        state["error"] = f"Task {task_id} not found"
                        state["execution_result"] = f"❌ Task {task_id} not found"
                        trace_entry["error"] = "Task not found"
        
        except Exception as e:
            state["error"] = str(e)
            state["execution_result"] = f"❌ Error: {str(e)}"
            trace_entry["error"] = str(e)
        
        state["execution_trace"].append(trace_entry)
        return state
    
    def escalate_to_human(self, state: WorkflowState) -> WorkflowState:
        """Escalate to human review"""
        trace_entry = {
            "step": "escalate_to_human",
            "timestamp": datetime.now().isoformat()
        }
        
        state["requires_human"] = True
        
        # If there's a task ID, mark it as escalated
        if state.get("task_id"):
            self.db.escalate_task(
                state["task_id"],
                reason=state.get("decision_reasoning", "Complex request")
            )
            state["execution_result"] = f"⚠️ Task {state['task_id']} escalated to human review"
        else:
            state["execution_result"] = "⚠️ Request escalated to human review"
        
        trace_entry["reason"] = state.get("decision_reasoning", "Unknown")
        state["execution_trace"].append(trace_entry)
        
        return state
    
    def confirm_and_log(self, state: WorkflowState) -> WorkflowState:
        """Final confirmation and logging"""
        trace_entry = {
            "step": "confirm_and_log",
            "timestamp": datetime.now().isoformat(),
            "final_result": state["execution_result"]
        }
        
        state["execution_trace"].append(trace_entry)
        
        # Log execution
        self.logger.log_execution(state)
        
        return state
    
    def build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("intent_classifier", self.intent_classifier)
        workflow.add_node("create_update", self.create_update_task)
        workflow.add_node("escalate", self.escalate_to_human)
        workflow.add_node("confirm", self.confirm_and_log)
        
        # Set entry point
        workflow.set_entry_point("intent_classifier")
        
        # Add conditional edges from intent_classifier
        workflow.add_conditional_edges(
            "intent_classifier",
            self.route_decision,
            {
                "create_update": "create_update",
                "escalate": "escalate"
            }
        )
        
        # Both paths lead to confirmation
        workflow.add_edge("create_update", "confirm")
        workflow.add_edge("escalate", "confirm")
        
        # End after confirmation
        workflow.add_edge("confirm", END)
        
        return workflow.compile()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_workflow(user_input: str):
    """Execute the workflow with given input"""
    agent = WorkflowAgent()
    graph = agent.build_graph()
    
    # Initial state
    initial_state: WorkflowState = {
        "input": user_input,
        "task_id": None,
        "intent": None,
        "task_data": None,
        "decision_reasoning": "",
        "execution_result": "",
        "execution_trace": [],
        "requires_human": False,
        "error": None
    }
    
    # Run the graph
    result = graph.invoke(initial_state)
    
    return result


def print_result(result: WorkflowState):
    """Pretty print the result"""
    print("\n" + "="*60)
    print("WORKFLOW EXECUTION RESULT")
    print("="*60)
    print(f"\n📝 Input: {result['input']}")
    print(f"\n🎯 Intent: {result['intent']}")
    print(f"\n💭 Reasoning: {result['decision_reasoning']}")
    print(f"\n{result['execution_result']}")
    
    if result.get('task_id'):
        print(f"\n🔗 Task ID: {result['task_id']}")
    
    if result.get('requires_human'):
        print("\n⚠️  HUMAN REVIEW REQUIRED")
    
    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")
    
    print(f"\n📊 Execution Trace ({len(result['execution_trace'])} steps):")
    for i, step in enumerate(result['execution_trace'], 1):
        print(f"  {i}. {step['step']} @ {step['timestamp']}")
    
    print("\n" + "="*60 + "\n")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("AI Workflow Automation Agent (Ollama Edition)")
    print("="*60)
    print(f"Using model: {Config.OLLAMA_MODEL}")
    print("="*60)
    
    # Example 1: Create a task
    print("\n🔹 Example 1: Create Task")
    result1 = run_workflow("Create a high priority task to review Q4 financial reports")
    print_result(result1)
    
    # Example 2: Update a task
    print("\n🔹 Example 2: Update Task")
    result2 = run_workflow("Update TASK-0001 status to in_progress")
    print_result(result2)
    
    # Example 3: Escalate
    print("\n🔹 Example 3: Escalation")
    result3 = run_workflow("I need help with something complex about project budgets and resource allocation")
    print_result(result3)
    
    # View task database
    print("\n📋 Current Tasks in Database:")
    agent = WorkflowAgent()
    tasks = agent.db.list_tasks()
    for task in tasks:
        print(f"  • {task['id']}: {task['title']} [{task['status']}]")
    
    # Model comparison info
    print("\n" + "="*60)
    print("📊 Ollama Model Recommendations:")
    print("="*60)
    print("• mistral:latest (4.4GB) - RECOMMENDED for general use")
    print("  ✓ Best balance of speed and accuracy")
    print("  ✓ Good JSON formatting")
    print("  ✓ Handles complex intents well")
    print()
    print("• deepseek-coder:6.7b (3.8GB) - Good for structured tasks")
    print("  ✓ Excellent at JSON formatting")
    print("  ✓ Fast inference")
    print("  ✓ Code-focused but works for general tasks")
    print()
    print("• gemma3:270m (291MB) - Fastest, basic tasks only")
    print("  ⚠️  May struggle with complex JSON")
    print("  ✓ Very fast inference")
    print("  ✓ Use for simple create/update only")
    print()
    print("To change model: export OLLAMA_MODEL=deepseek-coder:6.7b")
    print("="*60)