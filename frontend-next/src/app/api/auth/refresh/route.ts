import { NextRequest, NextResponse } from "next/server";
import { BackendError, backendFetch } from "@/lib/backendClient";

export async function POST(request: NextRequest) {
  try {
    const { data, setCookie } = await backendFetch<Record<string, unknown>>("/auth/refresh", {
      method: "POST",
      cache: "no-store",
      headers: {
        "content-type": "application/json",
      },
      body: await request.text(),
    }, request);

    const response = NextResponse.json(data);
    if (setCookie) {
      response.headers.set("set-cookie", setCookie);
    }
    return response;
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json(
        { detail: "Unable to refresh session" },
        { status: error.status },
      );
    }

    return NextResponse.json({ detail: "Unexpected error" }, { status: 502 });
  }
}
