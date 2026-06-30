import { NextRequest, NextResponse } from "next/server";
import { BackendError, backendFetch } from "@/lib/backendClient";

type DeskLayout = Record<string, unknown>;

export async function GET(request: NextRequest) {
  try {
    const { data, setCookie } = await backendFetch<DeskLayout>("/api/desk/layout", {
      method: "GET",
      revalidateSeconds: 30,
      headers: {
        Accept: "application/json",
      },
    }, request);

    const response = NextResponse.json(data, {
      headers: {
        "Cache-Control": "public, max-age=30, stale-while-revalidate=300",
      },
    });

    if (setCookie) {
      response.headers.set("set-cookie", setCookie);
    }

    return response;
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json(
        { detail: "Backend not available", status: error.status },
        { status: error.status },
      );
    }

    return NextResponse.json({ detail: "Unexpected error" }, { status: 500 });
  }
}
