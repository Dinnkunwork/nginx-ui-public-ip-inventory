<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { inventoryApi } from '../api/client'
import type { BackupEntry, DashboardSummary } from '../types/inventory'

const loading = ref(false)
const error = ref('')
const success = ref('')
const summary = ref<DashboardSummary | null>(null)
const backups = ref<BackupEntry[]>([])
const backupBusy = ref(false)

const exportFilters = reactive({
  provider: '',
  owner_type: '',
  status: '',
})

async function loadReports(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [sumRes, backupRes] = await Promise.all([
      inventoryApi.getDashboardSummary(),
      inventoryApi.listBackups(),
    ])
    summary.value = sumRes
    backups.value = backupRes.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load reports'
  } finally {
    loading.value = false
  }
}

async function downloadCsv(): Promise<void> {
  error.value = ''
  try {
    const blob = await inventoryApi.exportCsvBlob(exportFilters)
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = 'public-ip-inventory.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(objectUrl)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to export CSV'
  }
}

async function triggerBackup(): Promise<void> {
  backupBusy.value = true
  error.value = ''
  success.value = ''
  try {
    const created = await inventoryApi.createBackup()
    success.value = `Backup created: ${created.filename}`
    await loadReports()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create backup'
  } finally {
    backupBusy.value = false
  }
}

async function restoreBackup(filename: string): Promise<void> {
  backupBusy.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await inventoryApi.restoreBackup(filename)
    success.value = `Restored from ${res.restored_from} (safety backup: ${res.safety_backup})`
    await loadReports()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to restore backup'
  } finally {
    backupBusy.value = false
  }
}

onMounted(loadReports)
</script>

<template>
  <div style="padding: 16px">
    <h2 style="margin-bottom: 16px">Reports & Backup</h2>

    <a-alert v-if="error" type="error" :message="error" show-icon style="margin-bottom: 16px" />
    <a-alert v-if="success" type="success" :message="success" show-icon style="margin-bottom: 16px" />

    <a-card title="Export CSV Report" style="margin-bottom: 16px">
      <a-row :gutter="[12, 12]" align="middle">
        <a-col :xs="24" :md="6">
          <a-input v-model:value="exportFilters.provider" placeholder="Filter by Provider (optional)" />
        </a-col>
        <a-col :xs="12" :md="5">
          <a-select v-model:value="exportFilters.owner_type" allow-clear placeholder="Owner" style="width: 100%">
            <a-select-option value="Internal">Internal</a-select-option>
            <a-select-option value="External">External</a-select-option>
          </a-select>
        </a-col>
        <a-col :xs="12" :md="5">
          <a-select v-model:value="exportFilters.status" allow-clear placeholder="Status" style="width: 100%">
            <a-select-option value="Used">Used</a-select-option>
            <a-select-option value="Available">Available</a-select-option>
            <a-select-option value="Reserved">Reserved</a-select-option>
          </a-select>
        </a-col>
        <a-col :xs="24" :md="4">
          <a-button type="primary" block @click="downloadCsv">Export CSV</a-button>
        </a-col>
      </a-row>
    </a-card>

    <a-spin :spinning="loading">
      <a-row v-if="summary" :gutter="[16, 16]">
        <a-col :xs="24" :lg="12">
          <a-card title="Report by Provider">
            <a-table
              size="small"
              :pagination="false"
              :data-source="summary.by_provider"
              row-key="provider"
              :columns="[
                { title: 'Provider', dataIndex: 'provider', key: 'provider' },
                { title: 'Total', dataIndex: 'total', key: 'total' },
                { title: 'Used', dataIndex: 'used', key: 'used' },
                { title: 'Available', dataIndex: 'available', key: 'available' },
                { title: 'Reserved', dataIndex: 'reserved', key: 'reserved' },
              ]"
            />
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="12">
          <a-card title="Report by Owner & Status">
            <a-table
              size="small"
              :pagination="false"
              :data-source="summary.by_owner"
              row-key="owner_type"
              :columns="[
                { title: 'Owner', dataIndex: 'owner_type', key: 'owner_type' },
                { title: 'Total', dataIndex: 'total', key: 'total' },
                { title: 'Used', dataIndex: 'used', key: 'used' },
                { title: 'Available', dataIndex: 'available', key: 'available' },
                { title: 'Reserved', dataIndex: 'reserved', key: 'reserved' },
              ]"
            />
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <a-card title="SQLite Database Backups" style="margin-top: 16px">
      <template #extra>
        <a-button type="primary" :loading="backupBusy" @click="triggerBackup">Create Backup Now</a-button>
      </template>

      <a-table
        size="small"
        :data-source="backups"
        row-key="filename"
        :pagination="false"
        :columns="[
          { title: 'Filename', dataIndex: 'filename', key: 'filename' },
          { title: 'Size (bytes)', dataIndex: 'size_bytes', key: 'size_bytes' },
          { title: 'Created At', dataIndex: 'created_at', key: 'created_at' },
          { title: 'Action', key: 'action', width: 140 },
        ]"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-popconfirm
              :title="`Restore database from ${record.filename}? A safety backup will be taken first.`"
              ok-text="Restore"
              cancel-text="Cancel"
              @confirm="restoreBackup(record.filename)"
            >
              <a-button size="small" :loading="backupBusy">Restore</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>
