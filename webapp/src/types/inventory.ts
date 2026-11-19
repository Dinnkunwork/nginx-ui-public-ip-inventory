export type OwnerType = 'Internal' | 'External'
export type EnvironmentType = '' | 'dev' | 'staging' | 'uat' | 'prod'
export type IpStatus = 'Used' | 'Available' | 'Reserved'

export interface AuditLogEntry {
  id: number
  action: string
  ip_id: number | null
  ip_address: string
  actor: string
  details: Record<string, unknown>
  created_at: string
}

export interface PublicIpRecord {
  id: number
  ip_address: string
  provider: string
  owner_type: OwnerType
  application: string
  domain: string
  environment: EnvironmentType
  server_ip: string
  status: IpStatus
  notes: string
  created_at: string
  updated_at: string
  audit_logs?: AuditLogEntry[]
}

export interface PublicIpPayload {
  ip_address: string
  provider: string
  owner_type: OwnerType
  application: string
  domain: string
  environment: EnvironmentType
  server_ip: string
  status: IpStatus
  notes: string
}

export interface IpListQuery {
  q?: string
  provider?: string
  owner_type?: string
  environment?: string
  status?: string
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface IpListResponse {
  items: PublicIpRecord[]
  total: number
  page: number
  page_size: number
  providers: string[]
}

export interface BreakdownRow {
  provider?: string
  owner_type?: string
  environment?: string
  total: number
  used?: number
  available?: number
  reserved?: number
}

export interface DashboardSummary {
  total: number
  used: number
  available: number
  reserved: number
  usage_percentage: number
  by_provider: BreakdownRow[]
  by_owner: BreakdownRow[]
  by_environment: BreakdownRow[]
  recent_audits: AuditLogEntry[]
}

export interface BackupEntry {
  filename: string
  size_bytes: number
  created_at: string
}
