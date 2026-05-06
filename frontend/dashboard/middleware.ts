import { NextRequest, NextResponse } from "next/server";

const AUTH_REALM = "ParkReserve AI";

function unauthorized() {
  return new NextResponse("Authentication required.", {
    headers: {
      "WWW-Authenticate": `Basic realm="${AUTH_REALM}", charset="UTF-8"`,
    },
    status: 401,
  });
}

function parseBasicAuth(header: string | null) {
  if (!header?.startsWith("Basic ")) {
    return null;
  }

  try {
    const decoded = atob(header.slice("Basic ".length));
    const separatorIndex = decoded.indexOf(":");
    if (separatorIndex === -1) {
      return null;
    }

    return {
      password: decoded.slice(separatorIndex + 1),
      username: decoded.slice(0, separatorIndex),
    };
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const expectedPassword = process.env.DASHBOARD_PASSWORD?.trim();
  if (!expectedPassword) {
    return NextResponse.next();
  }

  const expectedUsername = process.env.DASHBOARD_USERNAME?.trim() || "parkreserve";
  const credentials = parseBasicAuth(request.headers.get("authorization"));

  if (
    credentials?.username !== expectedUsername ||
    credentials.password !== expectedPassword
  ) {
    return unauthorized();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
