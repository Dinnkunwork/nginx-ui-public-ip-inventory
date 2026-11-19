import type {
  BackupEntry,
  DashboardSummary,
  IpListQuery,
  IpListResponse,
  PublicIpPayload,
  PublicIpRecord,
} from '../types/inventory'

export const PLUGIN_ID = 'com.company.public-ip-inventory'
const BASE_PATH = `/api/plugins/${PLUGIN_ID}/http`

export interface HttpClientLike {
  get<T>(url: string, config?: { params?: Record<string, unknown> }): Promise<{ data: T }>
  post<T>(url: string, data?: unknown): Promise<{ data: T }>
  put<T>(url: string, data?: unknown): Promise<{ data: T }>
  delete<T>(url: string, config?: { params?: Record<string, unknown>; data?: unknown }): Promise<{ data: T }>
}

let activeHttp: HttpClientLike | null = null

export function setPluginHttpClient(client: HttpClientLike | null): void {
  activeHttp = client
}

async function requestJson<T>(method: string, path: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  const query = new URLSearchParams()
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && String(v).trim() !== '') {
        query.set(k, String(v))
      }
    }
  }
  const qs = query.toString()
  const relative = qs ? `${path}?${qs}` : path

  if (activeHttp) {
    if (method === 'GET') {
      const res = await activeHttp.get<T>(relative)
      return res.data
    }
    if (method === 'POST') {
      const res = await activeHttp.post<T>(relative, body)
      return res.data
    }
    if (method === 'PUT') {
      const res = await activeHttp.put<T>(relative, body)
      return res.data
    }
    if (method === 'DELETE') {
      const res = await activeHttp.delete<T>(relative, { data: body })
      return res.data
    }
  }

  const resp = await fetch(`${BASE_PATH}${relative}`, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  const parsed = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const err = new Error(parsed.error || `Request failed (${resp.status})`) as Error & {
      fieldErrors?: Record<string, string>
    }
    err.fieldErrors = parsed.field_errors
    throw err
  }
  return parsed as T
}

export const inventoryApi = {
  getDashboardSummary(): Promise<DashboardSummary> {
    return requestJson<DashboardSummary>('GET', '/dashboard/summary')
  },
  listIps(query: IpListQuery): Promise<IpListResponse> {
    return requestJson<IpListResponse>('GET', '/ips', undefined, query as Record<string, unknown>)
  },
  getIp(id: number): Promise<PublicIpRecord> {
    return requestJson<PublicIpRecord>('GET', `/ips/${id}`)
  },
  createIp(payload: PublicIpPayload): Promise<PublicIpRecord> {
    return requestJson<PublicIpRecord>('POST', '/ips', payload)
  },
  updateIp(id: number, payload: PublicIpPayload): Promise<PublicIpRecord> {
    return requestJson<PublicIpRecord>('PUT', `/ips/${id}`, payload)
  },
  deleteIp(id: number): Promise<{ deleted: boolean; id: number; ip_address: string }> {
    return requestJson('DELETE', `/ips/${id}?confirm=true`, { confirm: true })
  },
  listBackups(): Promise<{ items: BackupEntry[] }> {
    return requestJson<{ items: BackupEntry[] }>('GET', '/backups')
  },
  createBackup(): Promise<BackupEntry> {
    return requestJson<BackupEntry>('POST', '/backups', {})
  },
  restoreBackup(filename: string): Promise<{ restored_from: string; safety_backup: string }> {
    return requestJson('POST', '/backups/restore', { filename, confirm: true })
  },
  getExportCsvUrl(query: IpListQuery): string {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && String(v).trim() !== '') {
        params.set(k, String(v))
      }
    }
    const qs = params.toString()
    return `${BASE_PATH}/reports/export.csv${qs ? `?${qs}` : ''}`
  },
}
