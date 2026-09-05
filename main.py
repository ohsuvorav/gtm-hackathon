#!/usr/bin/env python3
"""Read-only SurferSEO MCP explorer.

The script delegates OAuth to ``mcp-remote``. On the first run it opens Surfer's
login/consent page; later runs reuse the OAuth session cached by mcp-remote.

No Python packages are required. Node.js/npm must be installed because the
remote Streamable HTTP MCP server is bridged to stdio with npx.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


CLIENT_INFO = {"name": "surferseo-readonly-explorer", "version": "0.1.0"}
PROTOCOL_VERSION = "2025-03-26"
DEFAULT_SERVER_URL = "https://mcp.surferseo.com/mcp"


class McpError(RuntimeError):
    """Raised when the MCP process or server returns an error."""


class StdioMcpClient:
    def __init__(self, server_url: str) -> None:
        remote_package = os.environ.get("MCP_REMOTE_PACKAGE", "mcp-remote")
        self._process = subprocess.Popen(
            ["npx", "--yes", remote_package, server_url],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # OAuth URLs and diagnostics remain visible to the person running it.
            stderr=None,
            text=True,
            bufsize=1,
        )
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        self._messages: queue.Queue[dict[str, Any] | BaseException] = queue.Queue()
        self._next_id = 1
        threading.Thread(target=self._read_messages, daemon=True).start()

    def _read_messages(self) -> None:
        assert self._process.stdout is not None
        try:
            for line in self._process.stdout:
                line = line.strip()
                if line:
                    self._messages.put(json.loads(line))
        except BaseException as exc:  # Surface reader/JSON failures to request().
            self._messages.put(exc)

    def _send(self, message: dict[str, Any]) -> None:
        assert self._process.stdin is not None
        self._process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request_id = self._next_id
        self._next_id += 1
        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params
        self._send(message)

        while True:
            try:
                incoming = self._messages.get(timeout=1)
            except queue.Empty:
                exit_code = self._process.poll()
                if exit_code is not None:
                    raise McpError(f"mcp-remote exited unexpectedly ({exit_code})")
                continue
            if isinstance(incoming, BaseException):
                raise McpError(f"Could not read mcp-remote output: {incoming}")
            # Ignore server notifications and responses to unrelated request IDs.
            if incoming.get("id") != request_id:
                continue
            if "error" in incoming:
                error = incoming["error"]
                raise McpError(
                    f"MCP {method} failed ({error.get('code', 'unknown')}): "
                    f"{error.get('message', error)}"
                )
            return incoming.get("result")

    def connect(self) -> None:
        self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self.notify("notifications/initialized")

    def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params = {"cursor": cursor} if cursor else None
            result = self.request("tools/list", params)
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            details = _text_content(result) or json.dumps(result)
            raise McpError(f"Surfer tool {name!r} returned an error: {details}")
        if result.get("structuredContent") is not None:
            return result["structuredContent"]
        text = _text_content(result)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    def close(self) -> None:
        if self._process.poll() is None:
            if self._process.stdin:
                self._process.stdin.close()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.terminate()

    def __enter__(self) -> "StdioMcpClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _text_content(result: dict[str, Any]) -> str:
    return "\n".join(
        block.get("text", "")
        for block in result.get("content", [])
        if block.get("type") == "text"
    )


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _require_workspace_id(args: argparse.Namespace) -> int:
    workspace_id = args.workspace_id or os.environ.get("SURFER_WORKSPACE_ID")
    if not workspace_id:
        raise McpError(
            "Provide --workspace-id or set SURFER_WORKSPACE_ID. "
            "Run 'workspaces' first to discover it."
        )
    return int(workspace_id)


def _keyword_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("data", []):
        raw_difficulty = item.get("avg_difficulty")
        rows.append(
            {
                "keyword": item.get("main_keyword"),
                "title": item.get("title"),
                "topic": item.get("topic_title"),
                "location": item.get("location"),
                "search_volume": item.get("search_volume"),
                # Surfer's MCP returns basis points; its UI displays / 100.
                "difficulty": (
                    raw_difficulty / 100 if raw_difficulty is not None else None
                ),
                "recommendation_score": item.get("score"),
                "reasons": ",".join(item.get("reasons") or []),
                "content_editor_id": item.get("content_editor_id"),
            }
        )
    return rows


def _write_csv(rows: list[dict[str, Any]], output: Path) -> None:
    if not rows:
        print("No keyword recommendations returned; CSV was not created.")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} keyword recommendations to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server-url",
        default=os.environ.get("SURFER_MCP_URL", DEFAULT_SERVER_URL),
        help=f"Surfer MCP URL (default: {DEFAULT_SERVER_URL})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("smoke", help="List tools and workspaces (read-only)")
    subparsers.add_parser("tools", help="List exposed Surfer MCP tools")
    subparsers.add_parser("workspaces", help="List Surfer workspaces (read-only)")

    keywords = subparsers.add_parser(
        "keywords", help="Fetch Topical Map/write recommendations (read-only)"
    )
    keywords.add_argument("--workspace-id", type=int)
    keywords.add_argument("--limit", type=int, default=100)
    keywords.add_argument("--output", type=Path, help="Optional CSV output path")
    keywords.add_argument(
        "--raw", action="store_true", help="Print the complete MCP response as JSON"
    )

    editors = subparsers.add_parser(
        "content-editors", help="List recent Content Editors (read-only)"
    )
    editors.add_argument("--workspace-id", type=int)
    editors.add_argument("--page-size", type=int, default=25)

    score = subparsers.add_parser("score", help="Read one Content Editor score")
    score.add_argument("--workspace-id", type=int)
    score.add_argument("--content-editor-id", type=int, required=True)

    call = subparsers.add_parser("call", help="Call any get/list tool by name")
    call.add_argument("tool_name")
    call.add_argument(
        "--arguments", default="{}", help="Tool arguments as a JSON object"
    )
    return parser


def run(args: argparse.Namespace, client: StdioMcpClient) -> None:
    if args.command in {"smoke", "tools"}:
        tools = client.list_tools()
        print(f"Connected. Surfer exposed {len(tools)} tools.")
        if args.command == "tools":
            for tool in sorted(tools, key=lambda item: item["name"]):
                print(f"- {tool['name']}: {tool.get('description', '').splitlines()[0]}")
            return

    if args.command in {"smoke", "workspaces"}:
        _print_json(
            client.call_tool(
                "workspace__list",
                {"page": 1, "page_size": 100, "sort": "name", "order": "asc"},
            )
        )
        return

    if args.command == "keywords":
        payload = client.call_tool(
            "recommendation__list",
            {
                "workspace_id": _require_workspace_id(args),
                "type": "write",
                "sort": "score",
                "order": "desc",
                "limit": args.limit,
                "page": 1,
                "page_size": args.limit,
            },
        )
        rows = _keyword_rows(payload)
        if args.output:
            _write_csv(rows, args.output)
        if args.raw:
            _print_json(payload)
        elif not args.output:
            _print_json(rows)
        return

    if args.command == "content-editors":
        _print_json(
            client.call_tool(
                "content_editor__list",
                {
                    "workspace_id": _require_workspace_id(args),
                    "page": 1,
                    "page_size": args.page_size,
                },
            )
        )
        return

    if args.command == "score":
        _print_json(
            client.call_tool(
                "content_score__get",
                {
                    "workspace_id": _require_workspace_id(args),
                    "content_editor_id": args.content_editor_id,
                },
            )
        )
        return

    if args.command == "call":
        operation = args.tool_name.rsplit("__", 1)[-1]
        if not operation.startswith(("get", "list")):
            raise McpError(
                "The explorer blocks non-read operations. "
                "Use a tool whose final operation starts with 'get' or 'list'."
            )
        arguments = json.loads(args.arguments)
        if not isinstance(arguments, dict):
            raise McpError("--arguments must decode to a JSON object")
        _print_json(client.call_tool(args.tool_name, arguments))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        with StdioMcpClient(args.server_url) as client:
            run(args, client)
        return 0
    except (McpError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
