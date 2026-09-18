"""
NETRA Model Context Protocol (MCP) Server.
Supports both AWS Lambda execution (HTTP / Function URL) and stdio (Claude Desktop / Cursor).
Exposes the 4 NETRA tools over the official MCP JSON-RPC protocol.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
import boto3

from netra.mcp.tools import netra_dry_run, netra_execute, netra_rollback, netra_status

MCP_TOOLS_MANIFEST: List[Dict[str, Any]] = [
    {
        "name": "netra_dry_run",
        "description": "Preview proposed remediation plan and evaluate policy without mutating AWS resources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finding_id": {"type": "string", "description": "The unique finding identifier"}
            },
            "required": ["finding_id"],
        },
    },
    {
        "name": "netra_execute",
        "description": "Execute human-approved remediation. REQUIRES a valid, unexpired HMAC approval token minted by the operator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finding_id": {"type": "string", "description": "The unique finding identifier"},
                "approval_token": {"type": "string", "description": "Cryptographic HMAC-SHA256 approval token"}
            },
            "required": ["finding_id", "approval_token"],
        },
    },
    {
        "name": "netra_rollback",
        "description": "Restore a terminated resource from an EBS safeguard snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "audit_id": {"type": "string", "description": "Audit log identifier containing snapshot reference"}
            },
            "required": ["audit_id"],
        },
    },
    {
        "name": "netra_status",
        "description": "Query live account burn rate (₹/hr), baseline multiple, and credit runway.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def dispatch_tool(name: str, args: Dict[str, Any], session: Optional[boto3.Session] = None) -> Dict[str, Any]:
    """Route tool call to corresponding implementation."""
    if name == "netra_dry_run":
        return netra_dry_run(args.get("finding_id", ""), session=session)
    elif name == "netra_execute":
        return netra_execute(args.get("finding_id", ""), args.get("approval_token", ""), session=session)
    elif name == "netra_rollback":
        return netra_rollback(args.get("audit_id", ""), session=session)
    elif name == "netra_status":
        return netra_status(session=session)
    else:
        return {"error": f"Unknown tool '{name}'", "ok": False}


def handle_jsonrpc(request: Dict[str, Any], session: Optional[boto3.Session] = None) -> Dict[str, Any]:
    """Process a single JSON-RPC 2.0 / MCP request."""
    method = request.get("method")
    req_id = request.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS_MANIFEST},
        }

    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = dispatch_tool(tool_name, arguments, session=session)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
        }

    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "netra-mcp-actions", "version": "3.0.0"},
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"},
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for HTTP / Function URL invocation."""
    try:
        body = event.get("body")
        if isinstance(body, str):
            req = json.loads(body)
        elif isinstance(body, dict):
            req = body
        else:
            req = event

        response = handle_jsonrpc(req)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }


def stdio_server():
    """Local stdio runner for Claude Desktop or Cursor integration."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            res = handle_jsonrpc(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as err:
            err_res = {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(err)}}
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    stdio_server()
