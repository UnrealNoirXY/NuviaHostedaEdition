import { NextRequest, NextResponse } from "next/server";
import { BackendError, backendFetch } from "@/lib/backendClient";

type BookingOverview = Record<string, unknown>;

export async function GET(request: NextRequest) {
  try {
    const { data, setCookie } = await backendFetch<BookingOverview>("/api/bookings/overview", {
      method: "GET",
      revalidateSeconds: 20,
      headers: { Accept: "application/json" },
    }, request);

    const response = NextResponse.json(data, {
      headers: { "Cache-Control": "public, max-age=20, stale-while-revalidate=120" },
    });

    if (setCookie) {
      response.headers.set("set-cookie", setCookie);
    }

    return response;
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json({ detail: "Backend not available" }, { status: error.status });
    }

    return NextResponse.json({ detail: "Unexpected error" }, { status: 500 });
  }
}
