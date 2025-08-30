# FastMCP Refactor Implementation Guide

## Project Context
Sim RaceCenter Agent exposes race telemetry data (NATS JetStream + SQLite) to LLM tooling via MCP protocol, powering a Director chat responder using Gemini's native tool calling.

## Current State Analysis
- ✅ FastMCP SDK implementation in `sdk_server.py`
- ✅ Gemini tool session integration
- ✅ NATS telemetry listener with StateCache
- ⚠️ Missing: Structured test coverage
- ⚠️ Missing: Configuration validation
- ⚠️ Missing: Error handling tests

## Phase 1: Core MCP Server Tests

### 1.1 Tool Registration Tests (`test_mcp_tools.py`)
```python
# Test each tool is properly registered
def test_tool_catalog():
    """Verify all tools are discoverable via list_tools"""
    # Expected tools: race_state, driver_standings, recent_incidents, 
    # lap_times, tire_strategy, flag_status, weather_conditions
    
def test_tool_schemas():
    """Validate each tool has correct parameter schemas"""
    # Check required/optional params, types, descriptions
    
def test_tool_metadata():
    """Ensure all tools return schema_version and generated_at"""
```

### 1.2 StateCache Integration Tests (`test_state_cache.py`)
```python
def test_cache_initialization():
    """Verify StateCache starts with empty state"""
    
def test_telemetry_update():
    """Test cache updates from NATS messages"""
    
def test_cache_fallback():
    """Ensure tools work without active cache (test mode)"""
```

### 1.3 Context Injection Tests (`test_context.py`)
```python
def test_context_propagation():
    """Verify Context object reaches tools correctly"""
    
def test_lifespan_management():
    """Test server startup/shutdown with NATS connection"""
```

## Phase 2: Gemini Integration Tests

### 2.1 Tool Session Tests (`test_gemini_session.py`)
```python
def test_session_initialization():
    """Verify GeminiToolSession starts MCP client correctly"""
    # Check stdio transport, timeout handling
    
def test_tool_discovery():
    """Ensure Gemini sees all MCP tools"""
    
def test_tool_invocation():
    """Test Gemini can call MCP tools and get responses"""
```

### 2.2 End-to-End Chat Tests (`test_director_chat.py`)
```python
def test_simple_query():
    """Test: 'Who is leading?' returns driver info"""
    
def test_multi_tool_query():
    """Test: 'Compare top 3 drivers' lap times' uses multiple tools"""
    
def test_no_tool_query():
    """Test: 'Hello' returns no response (as designed)"""
```

## Phase 3: Configuration Simplification

### 3.1 Environment Variables (Minimal Set)
```bash
# Required
GEMINI_API_KEY=...           # Gemini API access

# Optional with Smart Defaults
LLM_ANSWER_MODEL=gemini-2.0-flash-exp  # Model selection
MCP_START_TIMEOUT=30         # MCP client timeout
NATS_URL=nats://localhost:4222  # Telemetry source
```

### 3.2 Settings Validation (`test_config.py`)
```python
def test_required_env_vars():
    """Verify error on missing GEMINI_API_KEY"""
    
def test_default_values():
    """Check all optional configs have sensible defaults"""
    
def test_config_override():
    """Test env var precedence over defaults"""
```

## Phase 4: Implementation Checklist

### Step 1: Create Test Infrastructure
- [ ] Create `tests/mcp/` directory structure
- [ ] Set up pytest fixtures for:
  - Mock NATS connection
  - Mock StateCache
  - Mock Gemini client
- [ ] Create test data fixtures (sample race states)

### Step 2: Implement Core Tests
- [ ] Write and pass tool registration tests
- [ ] Write and pass context injection tests
- [ ] Write and pass metadata validation tests

### Step 3: Refactor for Testability
- [ ] Extract tool implementations to separate module
- [ ] Create dependency injection for StateCache
- [ ] Add error handling with specific exceptions

### Step 4: Gemini Integration Tests
- [ ] Mock Gemini SDK for unit tests
- [ ] Create integration test with real Gemini (API key required)
- [ ] Add retry logic for transient failures

### Step 5: Documentation Updates
- [ ] Update README with test running instructions
- [ ] Document mock vs integration test separation
- [ ] Add troubleshooting guide

## Test Execution Strategy

### Unit Tests (No External Dependencies)
```bash
pytest tests/unit -v
# Runs fast, no API keys needed
# Uses mocks for NATS, Gemini, MCP client
```

### Integration Tests (Requires Services)
```bash
pytest tests/integration -v --gemini-api-key=$GEMINI_API_KEY
# Requires: NATS server, Gemini API key
# Tests real tool invocations
```

### Smoke Test (Manual Verification)
```bash
# Terminal 1: Start NATS (if needed)
docker run -p 4222:4222 nats:latest

# Terminal 2: Run MCP server standalone
python -m sim_racecenter_agent.mcp.sdk_server

# Terminal 3: Test with MCP Inspector
mcp dev src/sim_racecenter_agent/mcp/sdk_server.py

# Terminal 4: Run agent with chat
python scripts/run_agent.py
```

## Success Criteria

1. **Test Coverage**: >80% for core modules
2. **Tool Reliability**: All tools return valid JSON with metadata
3. **Gemini Integration**: Successfully processes 3 query types:
   - Single tool query
   - Multi-tool query
   - No-tool query (ignored)
4. **Configuration**: Works with only `GEMINI_API_KEY` set
5. **Error Handling**: Graceful degradation when NATS unavailable

## Common Pitfalls to Avoid

1. **Don't mock FastMCP internals** - Test through public API
2. **Don't hardcode tool names** - Discover via list_tools
3. **Don't assume NATS is running** - Provide fallback data
4. **Don't test Gemini's reasoning** - Test integration, not AI quality
5. **Don't mix unit and integration tests** - Clear separation

## Migration Path from Legacy

### Remove/Deprecate:
- `reasoning.py` - Replaced by Gemini's native planning
- HTTP transport code - FastMCP is stdio-only
- JSON-RPC shim - Use native MCP protocol
- Builder pattern dicts - Use @mcp.tool decorator

### Preserve:
- NATS telemetry listener
- StateCache logic
- Core tool implementations (refactored)

## Validation Checklist

### FastMCP Compliance ✓
- [ ] Uses official FastMCP decorators
- [ ] Implements async tool functions
- [ ] Provides Context parameter
- [ ] Returns JSON-serializable dicts
- [ ] No custom protocol extensions

### Gemini SDK Integration ✓
- [ ] Uses google.genai Python SDK
- [ ] Implements lazy session initialization
- [ ] Handles tool discovery automatically
- [ ] Processes tool results correctly

## Next Steps for Copilot Implementation

1. **Generate test files first** - Use this guide's test specifications
2. **Run tests to find gaps** - Let failing tests guide implementation
3. **Refactor incrementally** - One tool at a time
4. **Validate with smoke tests** - Manual verification between changes
5. **Document assumptions** - Add comments for non-obvious decisions

## Example Test Generation Prompt for Copilot

"Generate pytest tests for the MCP server tools based on these specifications:
- Each tool must be registered and discoverable
- Each tool must return a dict with schema_version and generated_at
- Tools must handle missing Context gracefully
- Use mock StateCache for unit tests
Focus on test_mcp_tools.py first."
