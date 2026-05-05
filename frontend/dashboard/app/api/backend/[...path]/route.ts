const DEFAULT_BACKEND_URL = "https://parkreserve-ai-production.up.railway.app";

const HOP_BY_HOP_HEADERS = [
  "connection",
  "content-encoding",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
];

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.PARKRESERVE_API_PROXY_TARGET ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    DEFAULT_BACKEND_URL;

  return configuredUrl.endsWith("/") ? configuredUrl : `${configuredUrl}/`;
}

function stripHopByHopHeaders(headers: Headers) {
  HOP_BY_HOP_HEADERS.forEach((header) => headers.delete(header));
}

async function proxyRequest(request: Request, context: RouteContext) {
  const { path } = await context.params;
  const sourceUrl = new URL(request.url);
  const targetUrl = new URL(
    `${path.map(encodeURIComponent).join("/")}${sourceUrl.search}`,
    getBackendBaseUrl(),
  );
  const requestHeaders = new Headers(request.headers);
  stripHopByHopHeaders(requestHeaders);

  const method = request.method.toUpperCase();
  const body =
    method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      body,
      cache: "no-store",
      headers: requestHeaders,
      method,
    });
  } catch {
    return Response.json(
      { detail: `Could not reach backend at ${targetUrl.origin}.` },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers(response.headers);
  stripHopByHopHeaders(responseHeaders);
  responseHeaders.set("cache-control", "no-store");

  return new Response(response.body, {
    headers: responseHeaders,
    status: response.status,
    statusText: response.statusText,
  });
}

export async function GET(request: Request, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PATCH(request: Request, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: Request, context: RouteContext) {
  return proxyRequest(request, context);
}
