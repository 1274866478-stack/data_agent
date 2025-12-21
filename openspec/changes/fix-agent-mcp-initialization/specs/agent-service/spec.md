## MODIFIED Requirements

### Requirement: Agent MCP Client Initialization

The Agent service MUST initialize MCP (Model Context Protocol) clients successfully to provide database query and visualization capabilities. When MCP initialization fails due to missing dependencies (e.g., Node.js/npx), the system MUST provide clear error messages and support graceful degradation.

The system SHALL:
- Install Node.js in the Docker container to support MCP PostgreSQL server startup
- Verify that `npx` command is available before attempting to initialize MCP clients
- Provide detailed error logging when MCP initialization fails
- Support disabling MCP tools via `DISABLE_MCP_TOOLS` environment variable as a fallback mechanism
- Handle `FileNotFoundError` and other initialization failures gracefully

#### Scenario: Successful MCP initialization with Node.js installed

- **WHEN** the backend service starts with Node.js installed in the Docker container
- **AND** `npx` command is available
- **THEN** MCP PostgreSQL server should start successfully
- **AND** Agent should be able to execute SQL queries using MCP tools

#### Scenario: MCP initialization failure detection

- **WHEN** `npx` command is not available
- **THEN** the system should detect this condition early
- **AND** provide a clear error message indicating Node.js is required
- **AND** suggest using `DISABLE_MCP_TOOLS=true` as a workaround

#### Scenario: Graceful degradation when MCP disabled

- **WHEN** `DISABLE_MCP_TOOLS=true` environment variable is set
- **THEN** Agent should use custom tools instead of MCP tools
- **AND** basic functionality should still work (with reduced capabilities)

