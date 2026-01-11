"""
FastAPI Webhook Server for n8n Integration
Exposes the workflow agent via HTTP endpoints
Using Ollama for local LLM inference
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
from datetime import datetime

# Import the workflow agent
from workflow_agent import WorkflowAgent, run_workflow, WorkflowState, TaskDatabase


# ============================================================================
# API MODELS
# ============================================================================

class TaskRequest(BaseModel):
    """Request model for task operations"""
    input: str = Field(..., description="Natural language task description")
    webhook_url: Optional[str] = Field(None, description="Callback URL for async results")
    model: Optional[str] = Field(None, description="Ollama model to use (mistral:latest, deepseek-coder:6.7b, gemma3:270m)")


class TaskResponse(BaseModel):
    """Response model for task operations"""
    success: bool
    task_id: Optional[str]
    intent: Optional[str]
    result: str
    reasoning: str
    requires_human: bool
    execution_trace: list
    timestamp: str


class TaskCreate(BaseModel):
    """Direct task creation model"""
    title: str
    description: str
    priority: str = "medium"


class TaskUpdate(BaseModel):
    """Direct task update model"""
    status: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None


class WebhookPayload(BaseModel):
    """Webhook callback payload"""
    task_id: Optional[str]
    result: str
    status: str
    timestamp: str


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="AI Workflow Automation Agent API (Ollama Edition)",
    description="Webhook server for n8n integration using local Ollama models",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
agent = WorkflowAgent()


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.post("/webhook/task", response_model=TaskResponse)
async def webhook_task_handler(request: TaskRequest):
    """
    Main webhook endpoint for n8n
    Processes natural language task requests using Ollama
    """
    try:
        # Create agent with specified model if provided
        if request.model:
            agent_instance = WorkflowAgent(model=request.model)
            graph = agent_instance.build_graph()
            
            # Initial state
            initial_state: WorkflowState = {
                "input": request.input,
                "task_id": None,
                "intent": None,
                "task_data": None,
                "decision_reasoning": "",
                "execution_result": "",
                "execution_trace": [],
                "requires_human": False,
                "error": None
            }
            
            result = graph.invoke(initial_state)
        else:
            # Use default model
            result = run_workflow(request.input)
        
        # Build response
        response = TaskResponse(
            success=result.get("error") is None,
            task_id=result.get("task_id"),
            intent=result.get("intent"),
            result=result.get("execution_result", ""),
            reasoning=result.get("decision_reasoning", ""),
            requires_human=result.get("requires_human", False),
            execution_trace=result.get("execution_trace", []),
            timestamp=datetime.now().isoformat()
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/task/async")
async def webhook_task_async(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Async webhook endpoint
    Returns immediately and sends result to callback URL
    """
    if not request.webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url required for async processing")
    
    # Add task to background
    background_tasks.add_task(process_async_task, request.input, request.webhook_url)
    
    return {
        "status": "processing",
        "message": "Task queued for processing",
        "callback_url": request.webhook_url
    }


async def process_async_task(user_input: str, webhook_url: str):
    """Process task asynchronously and send result to webhook"""
    import httpx
    
    try:
        # Run workflow
        result = run_workflow(user_input)
        
        # Prepare callback payload
        payload = WebhookPayload(
            task_id=result.get("task_id"),
            result=result.get("execution_result", ""),
            status="success" if result.get("error") is None else "error",
            timestamp=datetime.now().isoformat()
        )
        
        # Send to callback URL
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload.dict())
            
    except Exception as e:
        # Send error to callback
        error_payload = {
            "task_id": None,
            "result": f"Error: {str(e)}",
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=error_payload)


# ============================================================================
# DIRECT API ENDPOINTS (Alternative to natural language)
# ============================================================================

@app.post("/api/tasks", response_model=dict)
async def create_task_direct(task: TaskCreate):
    """
    Create a task directly (bypasses LLM)
    Useful for structured API calls
    """
    try:
        result = agent.db.create_task(
            title=task.title,
            description=task.description,
            priority=task.priority
        )
        return {
            "success": True,
            "task": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task"""
    task = agent.db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.put("/api/tasks/{task_id}")
async def update_task_direct(task_id: str, updates: TaskUpdate):
    """Update a task directly"""
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = agent.db.update_task(task_id, update_dict)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "success": True,
        "task": result
    }


@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None):
    """List all tasks, optionally filtered by status"""
    tasks = agent.db.list_tasks(status)
    return {
        "count": len(tasks),
        "tasks": tasks
    }


@app.post("/api/tasks/{task_id}/escalate")
async def escalate_task(task_id: str, reason: str = "Manual escalation"):
    """Escalate a task to human review"""
    result = agent.db.escalate_task(task_id, reason)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "success": True,
        "task": result
    }


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check if Ollama is accessible
    import httpx
    import os
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_status = "unknown"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                ollama_status = "connected"
                models = response.json().get("models", [])
                available_models = [m["name"] for m in models]
            else:
                ollama_status = "error"
                available_models = []
    except:
        ollama_status = "disconnected"
        available_models = []
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AI Workflow Automation Agent (Ollama Edition)",
        "ollama": {
            "status": ollama_status,
            "url": ollama_url,
            "available_models": available_models
        }
    }


@app.get("/logs")
async def get_logs(limit: int = 10):
    """Get recent execution logs"""
    import json
    try:
        with open(agent.logger.filepath, 'r') as f:
            logs = json.load(f)
        return {
            "count": len(logs),
            "logs": logs[-limit:]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/reset")
async def reset_database():
    """Reset the entire database (USE WITH CAUTION)"""
    import os
    
    try:
        # Remove files
        if os.path.exists(agent.db.filepath):
            os.remove(agent.db.filepath)
        if os.path.exists(agent.logger.filepath):
            os.remove(agent.logger.filepath)
        
        # Reinitialize
        agent.db._ensure_file_exists()
        agent.logger._ensure_file_exists()
        
        return {
            "success": True,
            "message": "Database reset successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import os
    
    print("🚀 Starting AI Workflow Automation Agent API (Ollama Edition)")
    print("="*60)
    print("📍 Webhook endpoint: http://localhost:8000/webhook/task")
    print("📍 API docs: http://localhost:8000/docs")
    print("📍 Health check: http://localhost:8000/health")
    print("="*60)
    print(f"🤖 Default Ollama model: {os.getenv('OLLAMA_MODEL', 'mistral:latest')}")
    print(f"🔗 Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print("="*60)
    print("\n⚠️  Make sure Ollama is running: ollama serve")
    print("Available models: ollama list\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
