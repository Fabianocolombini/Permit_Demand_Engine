import { NextResponse } from "next/server";
import { probeCartoStatus } from "@/lib/carto";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Public status for the county map badge — never returns the access token. */
export async function GET() {
  const status = await probeCartoStatus();
  return NextResponse.json(status, {
    headers: { "Cache-Control": "no-store" },
  });
}
