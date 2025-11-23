export interface Source {
  id: string;
  display_name: string;
  type: string;
  chunk_count: number;
  language?: string;
  path?: string;
  url?: string;
  first_seen?: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  organization_name: string;
  billing_status: string;
  plan: string;
}

