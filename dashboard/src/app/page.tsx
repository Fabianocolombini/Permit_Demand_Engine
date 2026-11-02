import LandingDashboard from "@/components/LandingDashboard";
import type { Metrics } from "@/lib/types";
import { readFile } from "fs/promises";
import path from "path";

async function loadMetrics(): Promise<Metrics> {
  const file = path.join(process.cwd(), "public", "data", "metrics.json");
  const raw = await readFile(file, "utf8");
  return JSON.parse(raw) as Metrics;
}

export default async function Home() {
  const data = await loadMetrics();
  return <LandingDashboard data={data} />;
}
