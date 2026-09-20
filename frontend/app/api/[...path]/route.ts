import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (
  process.env.NETRA_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const targetPath = "/" + path.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}${targetPath.startsWith("/api") ? targetPath : "/api" + targetPath}${search}`;

  // Forward incoming headers (including X-Aws-* credentials and Authorization)
  const forwardHeaders: Record<string, string> = {
    "content-type": request.headers.get("content-type") || "application/json",
  };

  const headerKeys = [
    "authorization",
    "x-aws-access-key-id",
    "x-aws-secret-access-key",
    "x-aws-session-token",
    "x-aws-region",
    "x-api-key",
  ];

  for (const key of headerKeys) {
    const val = request.headers.get(key);
    if (val) forwardHeaders[key] = val;
  }

  // Also pass environment credentials if set on the server
  if (process.env.AWS_ACCESS_KEY_ID && !forwardHeaders["x-aws-access-key-id"]) {
    forwardHeaders["x-aws-access-key-id"] = process.env.AWS_ACCESS_KEY_ID;
  }
  if (process.env.AWS_SECRET_ACCESS_KEY && !forwardHeaders["x-aws-secret-access-key"]) {
    forwardHeaders["x-aws-secret-access-key"] = process.env.AWS_SECRET_ACCESS_KEY;
  }
  if (process.env.AWS_SESSION_TOKEN && !forwardHeaders["x-aws-session-token"]) {
    forwardHeaders["x-aws-session-token"] = process.env.AWS_SESSION_TOKEN;
  }
  if (process.env.AWS_DEFAULT_REGION && !forwardHeaders["x-aws-region"]) {
    forwardHeaders["x-aws-region"] = process.env.AWS_DEFAULT_REGION;
  }

  const method = request.method;
  let body: string | undefined = undefined;
  if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
    try {
      body = await request.text();
    } catch {
      body = undefined;
    }
  }

  try {
    const backendRes = await fetch(targetUrl, {
      method,
      headers: forwardHeaders,
      body,
      cache: "no-store",
    });

    const data = await backendRes.text();
    return new NextResponse(data, {
      status: backendRes.status,
      headers: {
        "content-type": backendRes.headers.get("content-type") || "application/json",
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET, POST, OPTIONS",
        "access-control-allow-headers": "*",
      },
    });
  } catch (err: any) {
    return NextResponse.json(
      {
        error: `NETRA backend unavailable at ${BACKEND_URL}: ${err?.message || "Connection refused"}`,
        code: "BACKEND_UNREACHABLE",
        target_url: targetUrl,
      },
      {
        status: 503,
        headers: {
          "access-control-allow-origin": "*",
        },
      }
    );
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "*",
    },
  });
}
