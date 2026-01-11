"""
Initialize Database with Sample Data
Creates tasks_db.json and execution_logs.json with sample data
"""

import json
from datetime import datetime, timedelta


def create_sample_tasks():
    """Generate sample tasks"""
    now = datetime.now()
    
    tasks = {
        "TASK-0001": {
            "id": "TASK-0001",
            "title": "Review Q4 Financial Reports",
            "description": "Comprehensive review of Q4 2024 financial reports and budget analysis",
            "priority": "high",
            "status": "in_progress",
            "created_at": (now - timedelta(days=5)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat(),
            "history": [
                {
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "changes": {"status": "in_progress"}
                }
            ]
        },
        "TASK-0002": {
            "id": "TASK-0002",
            "title": "Update Product Documentation",
            "description": "Update user documentation with latest feature releases",
            "priority": "medium",
            "status": "pending",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": (now - timedelta(days=3)).isoformat(),
            "history": []
        },
        "TASK-0003": {
            "id": "TASK-0003",
            "title": "Client Meeting Preparation",
            "description": "Prepare presentation and materials for Acme Corp meeting",
            "priority": "high",
            "status": "completed",
            "created_at": (now - timedelta(days=7)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat(),
            "history": [
                {
                    "timestamp": (now - timedelta(days=6)).isoformat(),
                    "changes": {"status": "in_progress"}
                },
                {
                    "timestamp": (now - timedelta(days=1)).isoformat(),
                    "changes": {"status": "completed"}
                }
            ]
        },
        "TASK-0004": {
            "id": "TASK-0004",
            "title": "Code Review - Authentication Module",
            "description": "Review pull request for new authentication system",
            "priority": "high",
            "status": "pending",
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat(),
            "history": []
        },
        "TASK-0005": {
            "id": "TASK-0005",
            "title": "Marketing Campaign Analysis",
            "description": "Analyze performance metrics for Q1 marketing campaigns",
            "priority": "medium",
            "status": "in_progress",
            "created_at": (now - timedelta(days=4)).isoformat(),
            "updated_at": (now - timedelta(hours=12)).isoformat(),
            "history": [
                {
                    "timestamp": (now - timedelta(hours=12)).isoformat(),
                    "changes": {"status": "in_progress", "priority": "medium"}
                }
            ]
        }
    }
    
    return {
        "tasks": tasks,
        "counter": 5
    }


def create_sample_logs():
    """Generate sample execution logs"""
    now = datetime.now()
    
    logs = [
        {
            "timestamp": (now - timedelta(days=5)).isoformat(),
            "input": "Create a high priority task to review Q4 financial reports",
            "intent": "create",
            "task_id": "TASK-0001",
            "result": "✅ Task created successfully: TASK-0001",
            "trace": [
                {
                    "step": "intent_classifier",
                    "timestamp": (now - timedelta(days=5)).isoformat(),
                    "model": "mistral:latest",
                    "output": {
                        "intent": "create",
                        "reasoning": "User wants to create a new high priority task"
                    }
                },
                {
                    "step": "create_update_task",
                    "timestamp": (now - timedelta(days=5)).isoformat(),
                    "action": "create",
                    "task_id": "TASK-0001"
                },
                {
                    "step": "confirm_and_log",
                    "timestamp": (now - timedelta(days=5)).isoformat(),
                    "final_result": "✅ Task created successfully: TASK-0001"
                }
            ],
            "error": None
        },
        {
            "timestamp": (now - timedelta(days=3)).isoformat(),
            "input": "Create task to update product documentation",
            "intent": "create",
            "task_id": "TASK-0002",
            "result": "✅ Task created successfully: TASK-0002",
            "trace": [
                {
                    "step": "intent_classifier",
                    "timestamp": (now - timedelta(days=3)).isoformat(),
                    "model": "mistral:latest"
                },
                {
                    "step": "create_update_task",
                    "timestamp": (now - timedelta(days=3)).isoformat(),
                    "action": "create",
                    "task_id": "TASK-0002"
                }
            ],
            "error": None
        },
        {
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "input": "Update TASK-0001 status to in_progress",
            "intent": "update",
            "task_id": "TASK-0001",
            "result": "✅ Task updated successfully: TASK-0001",
            "trace": [
                {
                    "step": "intent_classifier",
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "model": "mistral:latest",
                    "output": {
                        "intent": "update",
                        "reasoning": "User wants to update existing task status"
                    }
                },
                {
                    "step": "create_update_task",
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "action": "update",
                    "task_id": "TASK-0001",
                    "updates": {"status": "in_progress"}
                }
            ],
            "error": None
        },
        {
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "input": "Update TASK-0003 status to completed",
            "intent": "update",
            "task_id": "TASK-0003",
            "result": "✅ Task updated successfully: TASK-0003",
            "trace": [
                {
                    "step": "intent_classifier",
                    "timestamp": (now - timedelta(days=1)).isoformat(),
                    "model": "mistral:latest"
                },
                {
                    "step": "create_update_task",
                    "timestamp": (now - timedelta(days=1)).isoformat(),
                    "action": "update",
                    "task_id": "TASK-0003",
                    "updates": {"status": "completed"}
                }
            ],
            "error": None
        },
        {
            "timestamp": (now - timedelta(hours=6)).isoformat(),
            "input": "I need help planning the entire Q2 marketing strategy",
            "intent": "escalate",
            "task_id": None,
            "result": "⚠️ Request escalated to human review",
            "trace": [
                {
                    "step": "intent_classifier",
                    "timestamp": (now - timedelta(hours=6)).isoformat(),
                    "model": "mistral:latest",
                    "output": {
                        "intent": "escalate",
                        "reasoning": "Complex request requiring human expertise and strategic planning"
                    }
                },
                {
                    "step": "escalate_to_human",
                    "timestamp": (now - timedelta(hours=6)).isoformat(),
                    "reason": "Complex request requiring human expertise and strategic planning"
                }
            ],
            "error": None
        }
    ]
    
    return logs


def initialize_databases():
    """Initialize both database files"""
    print("🔧 Initializing Database Files")
    print("=" * 60)
    
    # Create tasks database
    print("\n📝 Creating tasks_db.json...")
    tasks_data = create_sample_tasks()
    with open("tasks_db.json", "w") as f:
        json.dump(tasks_data, f, indent=2)
    print(f"✅ Created with {len(tasks_data['tasks'])} sample tasks")
    
    # Create execution logs
    print("\n📊 Creating execution_logs.json...")
    logs_data = create_sample_logs()
    with open("execution_logs.json", "w") as f:
        json.dump(logs_data, f, indent=2)
    print(f"✅ Created with {len(logs_data)} sample log entries")
    
    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("\nSample tasks created:")
    for task_id, task in tasks_data["tasks"].items():
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "escalated": "⚠️"
        }.get(task["status"], "📌")
        
        priority_emoji = {
            "low": "🔵",
            "medium": "🟡",
            "high": "🔴"
        }.get(task["priority"], "⚪")
        
        print(f"  {status_emoji} {task_id}: {task['title']}")
        print(f"     Priority: {priority_emoji} {task['priority']} | Status: {task['status']}")
    
    print("\n💡 Next steps:")
    print("  1. Run: python workflow_agent.py")
    print("  2. Or start API: python webhook_server.py")
    print("  3. View in browser: open web_ui.html")
    print()


if __name__ == "__main__":
    initialize_databases()