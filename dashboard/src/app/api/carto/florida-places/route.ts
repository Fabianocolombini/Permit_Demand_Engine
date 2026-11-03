import { NextResponse } from "next/server";
import { fetchFloridaPlaces } from "@/lib/carto";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Proxy CARTO SQL → Florida place markers (token stays server-side). */
export async function GET() {
  const result = await fetchFloridaPlaces();
  if (!result.ok) {
    return NextResponse.json(
      { ok: false, error: result.error },
      { status: result.status === 401 ? 401 : 502 }
    );
  }
  return NextResponse.json(
    { ok: true, count: result.places.length, places: result.places },
    { headers: { "Cache-Control": "no-store" } }
  );
}
