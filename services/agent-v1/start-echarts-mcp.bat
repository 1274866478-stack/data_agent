@echo off
echo ============================================
echo Starting mcp-echarts MCP Server
echo Transport: SSE
echo Endpoint: http://localhost:3033/sse
echo ============================================
mcp-echarts -t sse -p 3033
