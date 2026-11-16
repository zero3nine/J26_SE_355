export interface MetricItem {
  label: string;
  value: number;
  total_all_time: number;
  trend: string;
  category: 'submitted' | 'scraped' | 'failed' | 'clean';
  color: 'blue' | 'green' | 'red' | 'purple';
}

export interface DashboardMetricsResponse {
  status: string;
  metrics: {
    submitted_urls: MetricItem;
    successfully_scraped: MetricItem;
    failed_skipped: MetricItem;
    clean_records: MetricItem;
  };
  database: {
    jobs: number;
    versions: number;
    skill_mentions: number;
    canonical_skills: number;
    extraction_runs: number;
    import_runs: number;
    benchmarks: number;
    evaluation_runs: number;
  };
  latest_batch: {
    batch_id: string;
    started_at: string;
    completed_at: string;
    attempted: number;
    success: number;
    failed: number;
    elapsed_seconds: number;
  } | null;
  manifest_batch_count: number;
}

export interface WorkflowStep {
  step: number;
  title: string;
  description: string;
  page: string;
  status: string;
}

export interface NavigationItem {
  id: string;
  name: string;
  path: string;
  icon: string;
  type: 'react' | 'streamlit';
  isMigrated: boolean;
  isIndividual?: boolean;
  badge?: string;
}

