<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { inventoryApi } from '../api/client'
import IpDetailDrawer from '../components/IpDetailDrawer.vue'
import IpFormModal from '../components/IpFormModal.vue'
import type { PublicIpPayload, PublicIpRecord } from '../types/inventory'
import { statusTagColor } from '../utils/ipValidation'

const loading = ref(false)
const error = ref('')
const items = ref<PublicIpRecord[]>([])
const total = ref(0)
const providers = ref<string[]>([])

const filters = reactive({
  q: '',
  provider: '',
  owner_type: '',
  environment: '',
  status: '',
  page: 1,
  page_size: 20,
})

const modalOpen = ref(false)
const editingRecord = ref<PublicIpRecord | null>(null)
const submitting = ref(false)
const modalError = ref('')

const drawerOpen = ref(false)
const detailLoading = ref(false)
const detailRecord = ref<PublicIpRecord | null>(null)

async function loadIps(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const res = await inventoryApi.listIps(filters)
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
  editingRecord.value = null
  modalError.value = ''
  modalOpen.value = true
}

function openEdit(record: PublicIpRecord): void {
  editingRecord.value = record
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
    if (editingRecord.value) {
      await inventoryApi.updateIp(editingRecord.value.id, payload)
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

function resetFilters(): void {
  filters.q = ''
  filters.provider = ''
  filters.owner_type = ''
  filters.environment = ''
  filters.status = ''
  filters.page = 1
  loadIps()
}

onMounted(loadIps)
</script>

<template>
  <div style="padding: 16px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 style="margin: 0">IP Address List</h2>
      <a-button type="primary" @click="openCreate">Add Public IP</a-button>
    </div>

    <a-card style="margin-bottom: 16px">
      <a-row :gutter="[12, 12]">
        <a-col :xs="24" :md="6">
          <a-input-search
            v-model:value="filters.q"
            placeholder="Search IP, app, domain, server..."
            allow-clear
            @search="() => { filters.page = 1; loadIps() }"
          />
        </a-col>
        <a-col :xs="12" :md="4">
          <a-select
            v-model:value="filters.provider"
            allow-clear
            placeholder="Provider"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          >
            <a-select-option v-for="p in providers" :key="p" :value="p">{{ p }}</a-select-option>
          </a-select>
        </a-col>
        <a-col :xs="12" :md="4">
          <a-select
            v-model:value="filters.owner_type"
            allow-clear
            placeholder="Owner"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          >
            <a-select-option value="Internal">Internal</a-select-option>
            <a-select-option value="External">External</a-select-option>
          </a-select>
        </a-col>
        <a-col :xs="12" :md="4">
          <a-select
            v-model:value="filters.environment"
            allow-clear
            placeholder="Environment"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          >
            <a-select-option value="dev">dev</a-select-option>
            <a-select-option value="staging">staging</a-select-option>
            <a-select-option value="uat">uat</a-select-option>
            <a-select-option value="prod">prod</a-select-option>
          </a-select>
        </a-col>
        <a-col :xs="12" :md="4">
          <a-select
            v-model:value="filters.status"
            allow-clear
            placeholder="Status"
            style="width: 100%"
            @change="() => { filters.page = 1; loadIps() }"
          >
            <a-select-option value="Used">Used</a-select-option>
            <a-select-option value="Available">Available</a-select-option>
            <a-select-option value="Reserved">Reserved</a-select-option>
          </a-select>
        </a-col>
        <a-col :xs="24" :md="2">
          <a-button block @click="resetFilters">Reset</a-button>
        </a-col>
      </a-row>
    </a-card>

    <a-alert v-if="error" type="error" :message="error" show-icon style="margin-bottom: 16px" />

    <a-table
      :loading="loading"
      :data-source="items"
      row-key="id"
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
      :columns="[
        { title: 'Public IP', dataIndex: 'ip_address', key: 'ip_address' },
        { title: 'Provider', dataIndex: 'provider', key: 'provider' },
        { title: 'Owner', dataIndex: 'owner_type', key: 'owner_type' },
        { title: 'Application', dataIndex: 'application', key: 'application' },
        { title: 'Domain', dataIndex: 'domain', key: 'domain' },
        { title: 'Environment', dataIndex: 'environment', key: 'environment' },
        { title: 'Status', dataIndex: 'status', key: 'status' },
        { title: 'Actions', key: 'actions', width: 220 },
      ]"
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
          <a-tag :color="statusTagColor(record.status)">{{ record.status }}</a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button size="small" @click="openDetails(record)">View</a-button>
            <a-button size="small" @click="openEdit(record)">Edit</a-button>
            <a-popconfirm
              :title="`Delete Public IP ${record.ip_address}?`"
              ok-text="Delete"
              cancel-text="Cancel"
              ok-type="danger"
              @confirm="handleDelete(record)"
            >
              <a-button size="small" danger>Delete</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <IpFormModal
      v-model:open="modalOpen"
      :initial="editingRecord"
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
