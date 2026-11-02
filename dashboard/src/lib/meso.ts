/** Approximate centers for Miami-Dade mesoregion drill-down markers. */
export const MIAMI_DADE_MESO_CENTERS: Record<string, [number, number]> = {
  "City of Miami": [25.7617, -80.1918],
  Homestead: [25.4687, -80.4776],
  Kendall: [25.6795, -80.3474],
  "Miami Lakes": [25.9087, -80.3086],
  "Miami Gardens": [25.942, -80.2456],
  Doral: [25.8195, -80.3553],
  "Opa Locka": [25.9023, -80.2503],
  Aventura: [25.9565, -80.1392],
  "Sunny Isles": [25.9429, -80.1231],
  Hialeah: [25.8576, -80.2781],
  "Miami Beach": [25.7907, -80.13],
  "West Miami": [25.7634, -80.2967],
  Pinecrest: [25.667, -80.3081],
  "South Miami": [25.7076, -80.2934],
  "North Miami": [25.8901, -80.1867],
  "Unincorporated / other Miami-Dade": [25.55, -80.45],
};

export type MesoRegion = {
  area: string;
  tom_count: number;
  sam_count: number;
  tom_valuation: number;
  sam_valuation: number;
  som_usd: number;
  material_usd?: number;
  labor_usd?: number;
  som_material_usd?: number;
  note?: string;
};
