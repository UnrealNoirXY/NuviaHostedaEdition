import { headers } from "next/headers";
import type { NextRequest } from "next/server";

const backendOrigin =
  process.env.NEXT_PUBLIC_DJANGO_ORIGIN?.trim() ||
  process.env.DJANGO_API_URL?.trim() ||
  "http://localhost:8000";

const absoluteUrlPattern = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//;

type FetchOptions = RequestInit & {
  path?: string;
  revalidateSeconds?: number;
};

export class BackendError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "BackendError";
    this.status = status;
  }
}

export async function backendFetch<T>(
  path: string,
  init: FetchOptions = {},
  request?: NextRequest,
): Promise<{ data: T; setCookie?: string | null }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  const mergedHeaders = new Headers(init.headers ?? {});
  const incomingHeaders = request?.headers ?? (await headers());
  const cookieHeader = incomingHeaders.get("cookie") ?? "";
  if (cookieHeader) {
    mergedHeaders.set("cookie", cookieHeader);
  }

  const targetUrl = resolveBackendUrl(path).toString();

  const response = await fetch(targetUrl, {
    ...init,
    headers: mergedHeaders,
    signal: controller.signal,
    credentials: "include",
    next:
      init.revalidateSeconds !== undefined
        ? { revalidate: init.revalidateSeconds }
        : init.next,
  });

  clearTimeout(timeout);

  const setCookie = response.headers.get("set-cookie");
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new BackendError(detail || "Upstream error", response.status);
  }

  const data = (await response.json().catch(() => ({}))) as T;
  return { data, setCookie };
}

export function getBackendOrigin() {
  return backendOrigin;
}

export function isAllowedBackendHost(target: URL, backend: URL) {
  return target.protocol === backend.protocol && target.host === backend.host;
}

export function resolveBackendUrl(path: string, origin: string = backendOrigin) {
  const backendUrl = new URL(origin);

  if (path.startsWith("//")) {
    throw new Error("Protocol-relative URLs are not allowed for backend requests");
  }

  if (absoluteUrlPattern.test(path)) {
    const absoluteUrl = new URL(path);

    if (!isAllowedBackendHost(absoluteUrl, backendUrl)) {
      throw new Error(`Absolute URLs must target the backend origin (${backendUrl.origin})`);
    }

    return absoluteUrl;
  }

  return new URL(path, backendUrl);
}
