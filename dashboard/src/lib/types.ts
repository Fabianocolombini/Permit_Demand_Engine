export type Metrics = {
  generated_at: string;
  as_of: string;
  definitions: Record<string, string | boolean>;
  universe: {
    tom: number;
    sam: number;
    sam_share_pct: number | null;
    min_issued: string;
    max_issued: string;
    counties: number;
    jurisdictions: number;
  };
  q1_tom_yoy: {
    annual: Array<{
      year: number;
      count: number;
      valuation: number;
      count_yoy_pct: number | null;
      valuation_yoy_pct: number | null;
    }>;
    monthly: Array<{
      year: number;
      month: number;
      count: number;
      valuation: number;
    }>;
    projection_2026_count: Projection;
    projection_2026_valuation: Projection;
    headline: {
      latest_full_year: number | null;
      yoy_count_pct: number | null;
      yoy_valuation_pct: number | null;
      y2026_ytd_count: number;
      y2026_ytg_count: number;
      y2026_full_year_count: number;
      y2026_ytd_valuation: number;
      y2026_ytg_valuation: number;
      y2026_full_year_valuation: number;
    };
  };
  q2_segment_trends: {
    annual: Array<{
      segment: string;
      year: number;
      count: number;
      valuation: number;
    }>;
    monthly: Array<{
      segment: string;
      year: number;
      month: number;
      count: number;
      valuation: number;
    }>;
  };
  q3_sam: {
    share: {
      tom_count: number;
      sam_count: number;
      sam_share_of_tom_count_pct: number | null;
      sam_valuation: number;
      tom_valuation: number;
      sam_share_of_tom_valuation_pct: number | null;
    };
    by_category: Array<{
      category: string;
      count: number;
      valuation: number;
      pct_of_sam_count: number;
      pct_of_sam_valuation: number;
    }>;
    top_counties: Array<{ county: string; count: number; valuation: number }>;
    projection_2026_count: Projection;
    projection_2026_valuation: Projection;
  };
  q4_som: {
    share_pct: number;
    sam_addressable_usd: number;
    som_usd: number;
    material_usd: number;
    labor_usd: number;
    fittings_sam_usd?: number;
    fittings_som_usd?: number;
    material_share_of_sam_pct: number;
    labor_share_of_sam_pct: number;
    assumptions_stated: Record<string, number | string>;
    imputation_method: string;
    formatted: Record<string, string | null>;
  };
  q5_near_term: {
    horizon_months: number;
    by_county: Array<{
      county: string;
      pipeline_0_3m_valuation: number;
      horizon: Array<{
        year: number;
        month: number;
        label: string;
        count: number;
        valuation: number;
        kind: string;
      }>;
    }>;
  };
  q6_contractors: {
    coverage: {
      tom: number;
      tom_with_name: number;
      tom_coverage_pct: number | null;
      sam: number;
      sam_with_name: number;
      sam_coverage_pct: number | null;
    };
    top: Array<{
      contractor_name: string;
      permits: number;
      valuation: number;
      counties: string;
      top_categories: string;
    }>;
    notes: string;
  };
  formatted_headlines: Record<string, string | null>;
};

type Projection = {
  as_of: string;
  year_end: string;
  ytd: number;
  ytg_expected: number;
  full_year_expected: number;
  method: string;
};
