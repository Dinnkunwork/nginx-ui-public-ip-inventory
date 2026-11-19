<script setup lang="ts">
import {
  Alert,
  Button,
  Card,
  Col,
  InputSearch,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
} from 'antdv-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { inventoryApi } from '../api/client'
import IpDetailDrawer from '../components/IpDetailDrawer.vue'
import IpFormModal, { type IpModalMode } from '../components/IpFormModal.vue'
import type { PublicIpPayload, PublicIpRecord } from '../types/inventory'
import { statusTagColor, suggestNextIpAddress } from '../utils/ipValidation'

const loading = ref(false)
const error = ref('')
const items = ref<PublicIpRecord[]>([])
const total = ref(0)
const providers = ref<string[]>([])

const filters = reactive({
  q: '',
  provider: undefined as string | undefined,
  owner_type: undefined as string | undefined,
  environment: undefined as string | undefined,
  status: undefined as string | undefined,
  page: 1,
  page_size: 20,
})

const providerOptions = computed(() => providers.value.map((p) => ({ label: p, value: p })))
const ownerOptions = [
  { label: 'Internal', value: 'Internal' },
  { label: 'External', value: 'External' },
]
const envOptions = [
  { label: 'dev', value: 'dev' },
  { label: 'staging', value: 'staging' },
  { label: 'uat', value: 'uat' },
  { label: 'prod', value: 'prod' },
]
const statusOptions = [
  { label: 'Used', value: 'Used' },
  { label: 'Available', value: 'Available' },
  { label: 'Reserved', value: 'Reserved' },
]

const columns = [
  { title: 'Public IP', dataIndex: 'ip_address', key: 'ip_address' },
  { title: 'Provider', dataIndex: 'provider', key: 'provider' },
  { title: 'Owner', dataIndex: 'owner_type', key: 'owner_type' },
  { title: 'Application', dataIndex: 'application', key: 'application' },
  { title: 'Domain', dataIndex: 'domain', key: 'domain' },
  { title: 'Environment', dataIndex: 'environment', key: 'environment' },
  { title: 'Status', dataIndex: 'status', key: 'status' },
  { title: 'Actions', key: 'actions', width: 280 },
]

const modalOpen = ref(false)
const modalMode = ref<IpModalMode>('create')
const modalSourceIp = ref('')
const editingId = ref<number | null>(null)
const formInitial = ref<Partial<PublicIpPayload> | null>(null)
const submitting = ref(false)
const modalError = ref('')

const drawerOpen = ref(false)
const detailLoading = ref(false)
const detailRecord = ref<PublicIpRecord | null>(null)

async function loadIps(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const res = await inventoryApi.listIps({
      q: filters.q,
      provider: filters.provider || '',
      owner_type: filters.owner_type || '',
      environment: filters.environment || '',
      status: filters.status || '',
      page: filters.page,
      page_size: filters.page_size,
    })
    items.value = res.items
    total.value = res.total
    providers.value = res.providers
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load IP inventory'
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  modalMode.value = 'create'
  modalSourceIp.value = ''
  editingId.value = null
  formInitial.value = null
  modalError.value = ''
  modalOpen.value = true
}

function openEdit(record: PublicIpRecord): void {
  modalMode.value = 'edit'
  modalSourceIp.value = record.ip_address
  editingId.value = record.id
  formInitial.value = {
    ip_address: record.ip_address,
    provider: record.provider,
    owner_type: record.owner_type,
    application: record.application,
    domain: record.domain,
    environment: record.environment,
    server_ip: record.server_ip,
    status: record.status,
    notes: record.notes,
  }
  modalError.value = ''
  modalOpen.value = true
}

function openClone(record: PublicIpRecord): void {
  modalMode.value = 'clone'
  modalSourceIp.value = record.ip_address
  editingId.value = null
  formInitial.value = {
    ip_address: suggestNextIpAddress(record.ip_address),
    provider: record.provider,
    owner_type: record.owner_type,
    application: record.application,
    domain: record.domain,
    environment: record.environment,
    server_ip: record.server_ip,
    status: record.status,
    notes: record.notes,
  }
  modalError.value = ''
  modalOpen.value = true
}

async function openDetails(record: PublicIpRecord): Promise<void> {
  drawerOpen.value = true
  detailLoading.value = true
  try {
    detailRecord.value = await inventoryApi.getIp(record.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load IP details'
  } finally {
    detailLoading.value = false
  }
}

async function handleSave(payload: PublicIpPayload): Promise<void> {
  submitting.value = true
  modalError.value = ''
  try {
    if (modalMode.value === 'edit' && editingId.value !== null) {
      await inventoryApi.updateIp(editingId.value, payload)
    } else {
      await inventoryApi.createIp(payload)
    }
    modalOpen.value = false
    await loadIps()
  } catch (err) {
    modalError.value = err instanceof Error ? err.message : 'Failed to save IP record'
  } finally {
    submitting.value = false
  }
}

async function handleDelete(record: PublicIpRecord): Promise<void> {
  try {
    await inventoryApi.deleteIp(record.id)
    await loadIps()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete IP record'
  }
}

async function exportFilteredCsv(): Promise<void> {
  error.value = ''
  try {
    const blob = await inventoryApi.exportCsvBlob({
      q: filters.q,
      provider: filters.provider || '',
      owner_type: filters.owner_type || '',
      environment: filters.environment || '',
      status: filters.status || '',
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

function resetFilters(): void {
  filters.q = ''
  filters.provider = undefined
  filters.owner_type = undefined
  filters.environment = undefined
  filters.status = undefined
  filters.page = 1
  loadIps()
}

onMounted(loadIps)
</script>

<template>
  <div style="padding: 8px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 style="margin: 0">IP Address List</h2>
      <Space>
        <Button @click="exportFilteredCsv">Export CSV</Button>
        <Button type="primary" @click="openCreate">Add Public IP</Button>
      </Space>
    </div>

    <Card style="margin-bottom: 16px">
      <Row :gutter="[12, 12]">
        <Col :xs="24" :md="6">
          <InputSearch
            v-model:value="filters.q"
            placeholder="Search IP, app, domain, server..."
            allow-clear
            @search="() => { filters.page = 1; loadIps() }"
          />
        </Col>
        <Col :xs="12" :md="4">
          <Select
            v-model:value="filters.provider"
            :options="providerOptions"
            allow-clear
            placeholder="Provider"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          />
        </Col>
        <Col :xs="12" :md="4">
          <Select
            v-model:value="filters.owner_type"
            :options="ownerOptions"
            allow-clear
            placeholder="Owner"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          />
        </Col>
        <Col :xs="12" :md="4">
          <Select
            v-model:value="filters.environment"
            :options="envOptions"
            allow-clear
            placeholder="Environment"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          />
        </Col>
        <Col :xs="12" :md="4">
          <Select
            v-model:value="filters.status"
            :options="statusOptions"
            allow-clear
            placeholder="Status"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          />
        </Col>
        <Col :xs="24" :md="2">
          <Button block @click="resetFilters">Reset</Button>
        </Col>
      </Row>
    </Card>

    <Alert v-if="error" type="error" :title="error" show-icon style="margin-bottom: 16px" />

    <Table
      :loading="loading"
      :data-source="items"
      row-key="id"
      :columns="columns"
      :pagination="{
        current: filters.page,
        pageSize: filters.page_size,
        total,
        showSizeChanger: true,
        onChange: (page: number, pageSize: number) => {
          filters.page = page
          filters.page_size = pageSize
          loadIps()
        },
      }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'application'">
          {{ record.application || '-' }}
        </template>
        <template v-else-if="column.key === 'domain'">
          {{ record.domain || '-' }}
        </template>
        <template v-else-if="column.key === 'environment'">
          {{ record.environment || '-' }}
        </template>
        <template v-else-if="column.key === 'status'">
          <Tag :color="statusTagColor(record.status)">{{ record.status }}</Tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <Space>
            <Button size="small" @click="openDetails(record as PublicIpRecord)">View</Button>
            <Button size="small" @click="openEdit(record as PublicIpRecord)">Edit</Button>
            <Button size="small" @click="openClone(record as PublicIpRecord)">Clone</Button>
            <Popconfirm
              :title="`Delete Public IP ${record.ip_address}?`"
              ok-text="Delete"
              cancel-text="Cancel"
              ok-type="danger"
              @confirm="handleDelete(record as PublicIpRecord)"
            >
              <Button size="small" danger>Delete</Button>
            </Popconfirm>
          </Space>
        </template>
      </template>
    </Table>

    <IpFormModal
      v-model:open="modalOpen"
      :mode="modalMode"
      :source-ip="modalSourceIp"
      :initial="formInitial"
      :submitting="submitting"
      :server-error="modalError"
      @submit="handleSave"
    />

    <IpDetailDrawer
      v-model:open="drawerOpen"
      :record="detailRecord"
      :loading="detailLoading"
    />
  </div>
</template>
