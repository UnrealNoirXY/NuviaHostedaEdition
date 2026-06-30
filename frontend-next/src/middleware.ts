import { NextRequest, NextResponse } from "next/server";

const LOGIN_PATH = process.env.NEXT_PUBLIC_LOGIN_URL ?? "/login";
const SESSION_COOKIE_NAME = "sessionid";
const REFRESH_COOKIE_NAME = "refresh_token";

async function tryRefreshSession(request: NextRequest) {
  try {
    const refreshResponse = await fetch(new URL("/api/auth/refresh", request.url), {
      method: "POST",
      headers: {
        cookie: request.headers.get("cookie") ?? "",
      },
    });

    if (!refreshResponse.ok) return null;

    const setCookie = refreshResponse.headers.get("set-cookie");
    return { setCookie };
  } catch (error) {
    console.error("middleware refresh error", error);
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname === LOGIN_PATH ||
    pathname.startsWith("/api/auth/refresh") ||
    pathname.startsWith("/api/health") ||
    pathname.startsWith("/offline") ||
    pathname.startsWith("/manifest.webmanifest")
  ) {
    return NextResponse.next();
  }

  const sessionCookie = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  const hasRefresh = request.cookies.get(REFRESH_COOKIE_NAME)?.value;

  if (!sessionCookie && hasRefresh) {
    const refreshed = await tryRefreshSession(request);
    if (refreshed?.setCookie) {
      const response = NextResponse.next();
      response.headers.set("set-cookie", refreshed.setCookie);
      return response;
    }
  }

  if (!sessionCookie) {
    const loginUrl = new URL(LOGIN_PATH, request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|manifest.webmanifest|service-worker.js|api/).*)",
  ],
};
