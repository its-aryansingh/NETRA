"""NETRA API HTTP Server.

A standalone HTTP server that exposes NETRA's API Gateway Lambda handler
over standard HTTP. Enables running NETRA anywhere (locally, Docker, Railway, EC2)
without requiring API Gateway deployment, while directly executing real Boto3
calls to connected AWS services.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse

from netra.api import lambda_handler
from netra.config import REGION, get_logger

logger = get_logger("netra.server")


class NetraApiHandler(BaseHTTPRequestHandler):
    """Translates incoming HTTP requests to AWS Lambda API Gateway v2 events."""

    server_version = "NETRA-Sentinel/1.0"

    def do_OPTIONS(self) -> None:
        self._handle_request("OPTIONS")

    def do_GET(self) -> None:
        self._handle_request("GET")

    def do_POST(self) -> None:
        self._handle_request("POST")

    def do_PUT(self) -> None:
        self._handle_request("PUT")

    def do_DELETE(self) -> None:
        self._handle_request("DELETE")

    def _handle_request(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        raw_query = parsed.query

        # Fast health check
        if path == "/health":
            self._send_json(200, {
                "status": "ok",
                "service": "netra-api",
                "region": os.getenv("AWS_DEFAULT_REGION", REGION),
                "timestamp": int(time.time()),
            })
            return

        # Read body if present
        body = ""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")

        # Convert headers to dict
        headers = {k: v for k, v in self.headers.items()}

        # Build Lambda API Gateway v2 event
        event = {
            "version": "2.0",
            "routeKey": f"{method} {path}",
            "rawPath": path,
            "rawQueryString": raw_query,
            "queryStringParameters": dict(parse_qsl(raw_query)),
            "headers": headers,
            "requestContext": {
                "http": {
                    "method": method,
                    "path": path,
                    "protocol": self.request_version,
                    "sourceIp": self.client_address[0] if self.client_address else "127.0.0.1",
                }
            },
            "body": body,
            "isBase64Encoded": False,
        }

        try:
            resp = lambda_handler(event, None)
            status_code = resp.get("statusCode", 200)
            resp_headers = resp.get("headers", {})
            resp_body = resp.get("body", "")

            self.send_response(status_code)
            for hk, hv in resp_headers.items():
                self.send_header(hk, hv)
            if "Content-Type" not in resp_headers:
                self.send_header("Content-Type", "application/json")
            self.end_headers()

            if isinstance(resp_body, str):
                self.wfile.write(resp_body.encode("utf-8"))
            elif isinstance(resp_body, bytes):
                self.wfile.write(resp_body)
            else:
                self.wfile.write(json.dumps(resp_body).encode("utf-8"))

        except Exception as err:
            logger.error(f"Error handling {method} {path}: {err}", exc_info=True)
            self._send_json(500, {"error": str(err), "code": "INTERNAL_ERROR"})

    def _send_json(self, status: int, data: dict) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        # Route access logs through NETRA logger
        logger.info(f"{self.client_address[0]} - {format % args}")


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), NetraApiHandler)
    aws_creds = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    region = os.getenv("AWS_DEFAULT_REGION", REGION)

    print("=" * 65)
    print("  NETRA — Real-Time Cloud Spend Sentinel API Server")
    print(f"  Listening on: http://{host}:{port}")
    print(f"  AWS Region:   {region}")
    print(f"  Live AWS:     {'ENABLED (Environment Credentials)' if aws_creds else 'READY (Waiting for dynamic/IAM credentials)'}")
    print("=" * 65)
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down NETRA API Server...")
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NETRA API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to listen on")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port)
