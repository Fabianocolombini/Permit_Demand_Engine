export type MonthlyPoint = {
  year: number;
  month: number;
  count?: number;
  valuation?: number;
  value?: number;
  kind?: "observed" | "projected";
};

export type PipelineWindow = {
  label?: string;
  days: number | null;
  start: string;
  end: string;
  sam_count: number;
  sam_valuation: number;
  material_usd: number;
  som_usd: number;
  som_material_usd: number;
  prior?: {
    start: string;
    end: string;
    sam_count: number;
    sam_valuation: number;
    material_usd: number;
    som_usd: number;
    som_material_usd: number;
  };
  growth?: {
    sam_count_pct: number | null;
    sam_valuation_pct: number | null;
    som_material_pct: number | null;
    material_usd_pct: number | null;
    compare_note: string;
  };
  reconciliation?: {
    tigre_dura_potential: number;
    sum_by_category: number;
    sum_by_county: number;
    delta_category: number;
    delta_county: number;
    ok: boolean;
  };
  by_county: Array<{
    county: string;
    fips: string | null;
    sam_count: number;
    sam_valuation: number;
    material_usd: number;
    labor_usd: number;
    som_usd: number;
    som_material_usd: number;
  }>;
  by_category: Array<{
    category: string;
    sam_count: number;
    sam_valuation: number;
    material_usd: number;
    labor_usd: number;
    som_usd: number;
    som_material_usd: number;
  }>;
  by_county_category?: Array<{
    county: string;
    category: string;
    sam_count: number;
    sam_valuation: number;
    material_usd: number;
    labor_usd: number;
    som_usd: number;
    som_material_usd: number;
  }>;
  by_contractor: Array<{
    contractor_name: string;
    permits: number;
    valuation: number;
    material_usd: number;
    som_material_usd: number;
    counties: string;
    categories: string;
    mesoregions?: string[];
    license?: string | null;
    meso_only?: boolean;
  }>;
};

export type Metrics = {
  generated_at: string;
  as_of: string;
  ytd_through_month: number;
  near_term_month: { year: number; month: number };
  definitions: Record<string, string>;
  assumptions: Record<string, number>;
  universe: {
    tom: number;
    sam: number;
    sam_share_count_pct: number | null;
    tom_valuation: number;
    sam_valuation: number;
    sam_share_valuation_pct: number | null;
    som_usd: number;
    fittings_sam_usd: number | null;
    fittings_som_usd: number;
    counties: number;
    jurisdictions: number;
  };
  tom: {
    annual: Array<{
      year: number;
      count: number;
      valuation: number;
      count_yoy_pct: number | null;
      valuation_yoy_pct: number | null;
    }>;
    ytd_comparison: Array<{
      year: number;
      through_month: number;
      count: number;
      valuation: number;
      count_yoy_pct: number | null;
      valuation_yoy_pct: number | null;
    }>;
    monthly: MonthlyPoint[];
    monthly_count_with_projection: MonthlyPoint[];
    monthly_valuation_with_projection: MonthlyPoint[];
    projection_count: Record<string, number | boolean>;
    projection_valuation: Record<string, number | boolean>;
  };
  sam_som: {
    share: {
      sam_count: number;
      tom_count: number;
      sam_share_count_pct: number | null;
      sam_valuation: number;
      tom_valuation: number;
      sam_share_valuation_pct: number | null;
      som_usd: number;
    };
    annual: Array<{
      year: number;
      count: number;
      valuation: number;
      count_yoy_pct: number | null;
      valuation_yoy_pct: number | null;
    }>;
    ytd_comparison: Array<{
      year: number;
      through_month: number;
      count: number;
      valuation: number;
      count_yoy_pct: number | null;
      valuation_yoy_pct: number | null;
    }>;
    monthly_count_with_projection: MonthlyPoint[];
    monthly_valuation_with_projection: MonthlyPoint[];
    by_category_year: Array<{
      category: string;
      year: number;
      count: number;
      valuation: number;
      material_usd: number;
      labor_usd: number;
      som_usd: number;
      som_material_usd: number;
      som_labor_usd: number;
    }>;
    by_category_ytd: Array<{
      category: string;
      year: number;
      through_month: number;
      count: number;
      valuation: number;
      material_usd: number;
      labor_usd: number;
      som_usd: number;
      count_yoy_pct: number | null;
      valuation_yoy_pct: number | null;
    }>;
    material_labor_annual: Array<{
      year: number;
      material_usd: number;
      labor_usd: number;
      valuation: number;
      som_usd: number;
      som_material_usd: number;
      som_labor_usd: number;
    }>;
    segment_annual: Array<{
      segment: string;
      year: number;
      count: number;
      valuation: number;
    }>;
    share_by_year: Array<{
      year: number;
      tom_count: number;
      sam_count: number;
      tom_valuation: number;
      sam_valuation: number;
      sam_share_count_pct: number | null;
      sam_share_valuation_pct: number | null;
      som_usd: number;
    }>;
  };
  pipeline: {
    ytd?: PipelineWindow;
    d30: PipelineWindow;
    d60: PipelineWindow;
    note: string;
  };
  regions: {
    counties: Array<{
      county: string;
      fips: string | null;
      tom_count: number;
      sam_count: number;
      tom_valuation: number;
      sam_valuation: number;
      som_usd: number;
      material_usd?: number;
      som_material_usd?: number;
    }>;
    county_by_category?: Array<{
      county: string;
      category: string;
      sam_count: number;
      sam_valuation: number;
      material_usd: number;
      labor_usd: number;
      som_usd: number;
      som_material_usd: number;
    }>;
    county_monthly_sam: Array<{
      county: string;
      year: number;
      month: number;
      count: number;
      valuation: number;
    }>;
    miami_dade: {
      jurisdictions: Array<{
        jurisdiction_id: string;
        tom_count: number;
        sam_count: number;
        tom_valuation: number;
        sam_valuation: number;
        som_usd: number;
        material_usd?: number;
        som_material_usd?: number;
      }>;
      mesoregions: Array<{
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
      }>;
      coverage_note: string;
    };
  };
  valuation_quality?: {
    policy: string;
    hard_ceiling_usd: number;
    pool_irrigation_soft_cap_usd: number;
    rows_ge_1b: number;
    declared_sum_ge_1b: number;
    rows_pool_irr_soft_capped: number;
    declared_sum_pool_irr_soft_capped: number;
    examples: Array<{
      contractor: string;
      permit_id: string;
      declared: number;
      descr: string;
    }>;
  };
  contractors: {
    coverage: {
      tom: number;
      tom_with_name: number;
      tom_coverage_pct: number | null;
      sam: number;
      sam_with_name: number;
      sam_coverage_pct: number | null;
    };
    ytd_by_permits: Contractor[];
    ytd_by_valuation: Contractor[];
    near_term_by_permits: Contractor[];
    near_term_by_valuation: Contractor[];
    near_term_label: string;
    notes: string;
  };
  formatted_headlines: Record<string, string | null>;
};

export type Contractor = {
  contractor_name: string;
  permits: number;
  valuation: number;
  counties: string;
  categories: string;
};

export type TabId = "tom" | "sam" | "pipeline" | "regions" | "contractors";
export type MetricMode = "count" | "valuation";
