export interface BillAnalysis {
  _id: string;
  file_url: string;
  billing_period: string;
  consumption_value: number;
  consumption_unit: string;
  total_cost: number;
  carbon_footprint_kg: number;
  savings_opportunities: string[];
  trend: {
    percentage_change: number;
    direction: "increase" | "decrease" | "stable";
    compared_to_period: string;
    previous_value: number;
    previous_cost: number;
  };
  analyzed_at: string;
}

export interface ChartDataPoint {
  month: string;
  current: number;
  simulated: number;
}

export interface SimulationResult {
  id: string;
  original_co2_kg: number;
  projected_co2_kg: number;
  reduction_kg: number;
  reduction_pct: number;
  savings_usd_desc: string;
  lifestyle_impact: string;
  top_savings_sources: string[];
  chart_data: ChartDataPoint[];
}
