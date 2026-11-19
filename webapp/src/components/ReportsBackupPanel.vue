<script setup lang="ts">
import {
  Alert,
  Button,
  Card,
  Col,
  Input,
  Popconfirm,
  Row,
  Select,
  Table,
} from 'antdv-next'
import { onMounted, reactive, ref } from 'vue'
import { inventoryApi } from '../api/client'
import type { BackupEntry, DashboardSummary } from '../types/inventory'

defineProps<{
  summary: DashboardSummary | null
}>()

const emit = defineEmits<{
  (e: 'restored'): void
}>()

const error = ref('')
const success = ref('')
const backups = ref<BackupEntry[]>([])
const backupBusy = ref(false)

const exportFilters = reactive({
  provider: '',
  owner_type: undefined as string | undefined,
  status: undefined as string | undefined,
})

const ownerOptions = [
  { label: 'Internal', value: 'Internal' },
  { label: 'External', value: 'External' },
]

const statusOptions = [
  { label: 'Used', value: 'Used' },
  { label: 'Available', value: 'Available' },
  { label: 'Reserved', value: 'Reserved' },
]

const providerColumns = [
  { title: 'Provider', dataIndex: 'provider', key: 'provider' },
  { title: 'Total', dataIndex: 'total', key: 'total' },
  { title: 'Used', dataIndex: 'used', key: 'used' },
  { title: 'Available', dataIndex: 'available', key: 'available' },
  { title: 'Reserved', dataIndex: 'reserved', key: 'reserved' },
]

const ownerColumns = [
  { title: 'Owner', dataIndex: 'owner_type', key: 'owner_type' },
  { title: 'Total', dataIndex: 'total', key: 'total' },
  { title: 'Used', dataIndex: 'used', key: 'used' },
  { title: 'Available', dataIndex: 'available', key: 'available' },
  { title: 'Reserved', dataIndex: 'reserved', key: 'reserved' },
]

const backupColumns = [
  { title: 'Filename', dataIndex: 'filename', key: 'filename' },
  { title: 'Size (bytes)', dataIndex: 'size_bytes', key: 'size_bytes' },
  { title: 'Created At', dataIndex: 'created_at', key: 'created_at' },
  { title: 'Action', key: 'action', width: 140 },
]

async function loadBackups(): Promise<void> {
  try {
    const res = await inventoryApi.listBackups()
    backups.value = res.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load backups'
  }
}

async function downloadCsv(): Promise<void> {
  error.value = ''
  try {
    const blob = await inventoryApi.exportCsvBlob({
      provider: exportFilters.provider,
      owner_type: exportFilters.owner_type || '',
      status: exportFilters.status || '',
    })
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
    await loadBackups()
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
    await loadBackups()
    emit('restored')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to restore backup'
  } finally {
    backupBusy.value = false
  }
}

onMounted(loadBackups)
</script>

<template>
  <div>
    <Alert v-if="error" type="error" :title="error" show-icon style="margin-bottom: 16px" />
    <Alert v-if="success" type="success" :title="success" show-icon style="margin-bottom: 16px" />

    <Card title="Export CSV Report" style="margin-bottom: 16px">
      <Row :gutter="[12, 12]" align="middle">
        <Col :xs="24" :md="6">
          <Input v-model:value="exportFilters.provider" placeholder="Filter by Provider (optional)" />
        </Col>
        <Col :xs="12" :md="5">
          <Select
            v-model:value="exportFilters.owner_type"
            :options="ownerOptions"
            allow-clear
            placeholder="Owner"
            style="width: 100%"
          />
        </Col>
        <Col :xs="12" :md="5">
          <Select
            v-model:value="exportFilters.status"
            :options="statusOptions"
            allow-clear
            placeholder="Status"
            style="width: 100%"
          />
        </Col>
        <Col :xs="24" :md="4">
          <Button type="primary" block @click="downloadCsv">Export CSV</Button>
        </Col>
      </Row>
    </Card>

    <Row v-if="summary" :gutter="[16, 16]">
      <Col :xs="24" :lg="12">
        <Card title="Report by Provider">
          <Table
            size="small"
            :pagination="false"
            :data-source="summary.by_provider"
            row-key="provider"
            :columns="providerColumns"
          />
        </Card>
      </Col>

      <Col :xs="24" :lg="12">
        <Card title="Report by Owner & Status">
          <Table
            size="small"
            :pagination="false"
            :data-source="summary.by_owner"
            row-key="owner_type"
            :columns="ownerColumns"
          />
        </Card>
      </Col>
    </Row>

    <Card title="SQLite Database Backups" style="margin-top: 16px">
      <template #extra>
        <Button type="primary" :loading="backupBusy" @click="triggerBackup">Create Backup Now</Button>
      </template>

      <Table
        size="small"
        :data-source="backups"
        row-key="filename"
        :pagination="false"
        :columns="backupColumns"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <Popconfirm
              :title="`Restore database from ${record.filename}? A safety backup will be taken first.`"
              ok-text="Restore"
              cancel-text="Cancel"
              @confirm="restoreBackup(String(record.filename))"
            >
              <Button size="small" :loading="backupBusy">Restore</Button>
            </Popconfirm>
          </template>
        </template>
      </Table>
    </Card>
  </div>
</template>
