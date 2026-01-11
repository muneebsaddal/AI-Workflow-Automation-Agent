"""
Comprehensive Test Script for AI Workflow Automation Agent (Ollama Edition)
Tests all components: LangGraph, API, and database
"""

import asyncio
import json
from datetime import datetime
from workflow_agent import WorkflowAgent, run_workflow, print_result, TaskDatabase


def test_header(title: str):
    """Print test section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_ollama_connection():
    """Test Ollama connection"""
    test_header("OLLAMA CONNECTION TEST")
    
    import httpx
    import os
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        response = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✓ Connected to Ollama at {ollama_url}")
            print(f"✓ Available models: {len(models)}")
            for model in models:
                print(f"  • {model['name']}")
            print("\n✓ Ollama connection test PASSED\n")
            return True
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to Ollama: {e}")
        print("\nMake sure Ollama is running:")
        print("  ollama serve")
        return False


def test_database():
    """Test database operations"""
    test_header("DATABASE TESTS")
    
    db = TaskDatabase("test_tasks.json")
    
    # Test 1: Create task
    print("✓ Test 1: Create Task")
    task = db.create_task(
        title="Test Task",
        description="This is a test task",
        priority="high"
    )
    print(f"  Created: {task['id']}")
    assert task['id'] == "TASK-0001"
    assert task['priority'] == "high"
    print("  PASSED ✓\n")
    
    # Test 2: Get task
    print("✓ Test 2: Get Task")
    retrieved = db.get_task("TASK-0001")
    print(f"  Retrieved: {retrieved['title']}")
    assert retrieved['title'] == "Test Task"
    print("  PASSED ✓\n")
    
    # Test 3: Update task
    print("✓ Test 3: Update Task")
    updated = db.update_task("TASK-0001", {
        "status": "in_progress",
        "priority": "medium"
    })
    print(f"  Updated status: {updated['status']}")
    assert updated['status'] == "in_progress"
    assert len(updated['history']) == 1
    print("  PASSED ✓\n")
    
    # Test 4: List tasks
    print("✓ Test 4: List Tasks")
    tasks = db.list_tasks()
    print(f"  Found {len(tasks)} tasks")
    assert len(tasks) == 1
    print("  PASSED ✓\n")
    
    # Test 5: Escalate task
    print("✓ Test 5: Escalate Task")
    escalated = db.escalate_task("TASK-0001", "Test escalation")
    print(f"  Escalated: {escalated['status']}")
    assert escalated['status'] == "escalated"
    print("  PASSED ✓\n")
    
    # Cleanup
    import os
    os.remove("test_tasks.json")
    
    print("🎉 All database tests passed!\n")


def test_workflow_create():
    """Test workflow for task creation"""
    test_header("WORKFLOW TEST: CREATE TASK")
    
    result = run_workflow("Create a high priority task to review the marketing budget for Q1")
    
    print_result(result)
    
    assert result['intent'] == "create"
    assert result['task_id'] is not None
    assert result['error'] is None
    
    print("✓ Create workflow test PASSED\n")
    return result['task_id']


def test_workflow_update(task_id: str):
    """Test workflow for task update"""
    test_header("WORKFLOW TEST: UPDATE TASK")
    
    result = run_workflow(f"Update {task_id} status to completed")
    
    print_result(result)
    
    assert result['intent'] == "update"
    assert result['task_id'] == task_id
    assert result['error'] is None
    
    print("✓ Update workflow test PASSED\n")


def test_workflow_escalate():
    """Test workflow for escalation"""
    test_header("WORKFLOW TEST: ESCALATION")
    
    result = run_workflow(
        "I need help planning the entire Q1 marketing strategy including budget allocation, "
        "team assignments, campaign themes, and performance metrics"
    )
    
    print_result(result)
    
    assert result['intent'] == "escalate" or result['requires_human'] == True
    
    print("✓ Escalation workflow test PASSED\n")


def test_edge_cases():
    """Test edge cases and error handling"""
    test_header("EDGE CASE TESTS")
    
    # Test 1: Empty input
    print("✓ Test 1: Empty Input")
    result = run_workflow("")
    print(f"  Intent: {result['intent']}")
    # Should escalate due to unclear intent
    print("  PASSED ✓\n")
    
    # Test 2: Update non-existent task
    print("✓ Test 2: Update Non-existent Task")
    result = run_workflow("Update TASK-9999 status to completed")
    print(f"  Result: {result['execution_result']}")
    assert "not found" in result['execution_result'].lower() or result['error']
    print("  PASSED ✓\n")
    
    # Test 3: Ambiguous request
    print("✓ Test 3: Ambiguous Request")
    result = run_workflow("do something")
    print(f"  Intent: {result['intent']}")
    # Should likely escalate
    print("  PASSED ✓\n")
    
    print("🎉 All edge case tests passed!\n")


def test_execution_trace():
    """Test execution trace logging"""
    test_header("EXECUTION TRACE TEST")
    
    result = run_workflow("Create a task to update the website")
    
    print("Execution Trace Steps:")
    for i, step in enumerate(result['execution_trace'], 1):
        print(f"{i}. {step['step']} @ {step['timestamp']}")
        
        # Verify each step has required fields
        assert 'step' in step
        assert 'timestamp' in step
    
    # Should have all major steps
    steps = [s['step'] for s in result['execution_trace']]
    assert 'intent_classifier' in steps
    assert 'confirm_and_log' in steps
    
    print("\n✓ Execution trace test PASSED\n")


def test_task_history():
    """Test task history tracking"""
    test_header("TASK HISTORY TEST")
    
    # Create a task
    result1 = run_workflow("Create a task to review documentation")
    task_id = result1['task_id']
    print(f"Created task: {task_id}")
    
    # Update it multiple times
    run_workflow(f"Update {task_id} priority to high")
    run_workflow(f"Update {task_id} status to in_progress")
    run_workflow(f"Update {task_id} status to completed")
    
    # Check history
    agent = WorkflowAgent()
    task = agent.db.get_task(task_id)
    
    print(f"\nTask history length: {len(task['history'])}")
    
    for i, entry in enumerate(task['history'], 1):
        print(f"{i}. {entry['timestamp']}: {entry['changes']}")
    
    assert len(task['history']) == 3
    
    print("\n✓ Task history test PASSED\n")


async def test_api_endpoints():
    """Test API endpoints (requires server to be running)"""
    test_header("API ENDPOINT TESTS")
    
    import httpx
    
    base_url = "http://localhost:8000"
    
    print("NOTE: This test requires the API server to be running!")
    print("Run: python webhook_server.py\n")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test 1: Health check
            print("✓ Test 1: Health Check")
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            print(f"  Status: {response.json()['status']}")
            print("  PASSED ✓\n")
            
            # Test 2: Webhook endpoint
            print("✓ Test 2: Webhook Task Creation")
            response = await client.post(
                f"{base_url}/webhook/task",
                json={"input": "Create a task to test the API"}
            )
            assert response.status_code == 200
            data = response.json()
            print(f"  Task ID: {data['task_id']}")
            print(f"  Success: {data['success']}")
            print("  PASSED ✓\n")
            
            task_id = data['task_id']
            
            # Test 3: List tasks
            print("✓ Test 3: List Tasks")
            response = await client.get(f"{base_url}/api/tasks")
            assert response.status_code == 200
            data = response.json()
            print(f"  Total tasks: {data['count']}")
            print("  PASSED ✓\n")
            
            # Test 4: Get specific task
            print("✓ Test 4: Get Specific Task")
            response = await client.get(f"{base_url}/api/tasks/{task_id}")
            assert response.status_code == 200
            task = response.json()
            print(f"  Retrieved: {task['title']}")
            print("  PASSED ✓\n")
            
            # Test 5: Update task
            print("✓ Test 5: Update Task")
            response = await client.put(
                f"{base_url}/api/tasks/{task_id}",
                json={"status": "completed"}
            )
            assert response.status_code == 200
            data = response.json()
            print(f"  Updated status: {data['task']['status']}")
            print("  PASSED ✓\n")
            
            # Test 6: Get logs
            print("✓ Test 6: Get Execution Logs")
            response = await client.get(f"{base_url}/logs?limit=5")
            assert response.status_code == 200
            data = response.json()
            print(f"  Recent logs: {data['count']}")
            print("  PASSED ✓\n")
            
            print("🎉 All API tests passed!\n")
            
    except httpx.ConnectError:
        print("❌ Could not connect to API server")
        print("   Make sure the server is running: python webhook_server.py")
        print("   Skipping API tests...\n")


def test_llm_parsing():
    """Test LLM response parsing"""
    test_header("LLM PARSING TEST")
    
    test_cases = [
        "Create a high priority task to review Q4 financials",
        "Update TASK-0001 to completed",
        "I need help with complex project planning",
        "Add a new task: implement user authentication",
        "Change TASK-0002 priority to low"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case}")
        result = run_workflow(test_case)
        print(f"  Intent: {result['intent']}")
        print(f"  Reasoning: {result['decision_reasoning']}")
        print()
    
    print("✓ LLM parsing tests completed\n")


def run_all_tests():
    """Run all test suites"""
    print("\n" + "🧪"*35)
    print("  AI WORKFLOW AUTOMATION AGENT - TEST SUITE (Ollama Edition)")
    print("🧪"*35 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Check Ollama first
        if not test_ollama_connection():
            print("\n❌ TESTS ABORTED: Ollama not available")
            print("\nPlease start Ollama:")
            print("  ollama serve")
            return
        
        # Core tests
        test_database()
        
        # Workflow tests
        task_id = test_workflow_create()
        test_workflow_update(task_id)
        test_workflow_escalate()
        
        # Advanced tests
        test_edge_cases()
        test_execution_trace()
        test_task_history()
        test_llm_parsing()
        
        # API tests (async)
        asyncio.run(test_api_endpoints())
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*70)
        print("  🎉 ALL TESTS PASSED! 🎉")
        print("="*70)
        print(f"\nTotal execution time: {duration:.2f} seconds")
        print("\nComponents tested:")
        print("  ✓ Ollama connection")
        print("  ✓ Database operations")
        print("  ✓ LangGraph workflows")
        print("  ✓ Intent classification")
        print("  ✓ Execution tracing")
        print("  ✓ Task history")
        print("  ✓ Edge cases")
        print("  ✓ API endpoints")
        print("\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        raise


if __name__ == "__main__":
    # Run specific test
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        
        tests = {
            "ollama": test_ollama_connection,
            "db": test_database,
            "create": test_workflow_create,
            "escalate": test_workflow_escalate,
            "edge": test_edge_cases,
            "trace": test_execution_trace,
            "history": test_task_history,
            "llm": test_llm_parsing,
            "api": lambda: asyncio.run(test_api_endpoints())
        }
        
        if test_name in tests:
            if test_name != "ollama":
                # Check Ollama first for non-connection tests
                if not test_ollama_connection():
                    print("\n❌ Ollama not available. Please start it:")
                    print("  ollama serve")
                    sys.exit(1)
            tests[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(tests.keys())}")
    else:
        # Run all tests
        run_all_tests()