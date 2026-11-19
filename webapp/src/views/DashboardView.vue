<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { inventoryApi } from '../api/client'
import type { DashboardSummary } from '../types/inventory'

const loading = ref(false)
const error = ref('')
const summary = ref<DashboardSummary | null>(null)

async function loadSummary(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    summary.value = await inventoryApi.getDashboardSummary()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load dashboard summary'
  } finally {
    loading.value = false
  }
}

onMounted(loadSummary)
</script>

<template>
  <div style="padding: 16px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 style="margin: 0">Public IP Inventory Dashboard</h2>
      <a-button :loading="loading" @click="loadSummary">Refresh</a-button>
    </div>

    <a-alert v-if="error" type="error" :message="error" show-icon style="margin-bottom: 16px" />

    <a-spin :spinning="loading">
      <template v-if="summary">
        <a-row :gutter="[16, 16]">
          <a-col :xs="24" :sm="12" :lg="6">
            <a-card>
              <a-statistic title="Total IP" :value="summary.total" />
            </a-card>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="6">
            <a-card>
              <a-statistic title="Used" :value="summary.used" :value-style="{ color: '#1677ff' }" />
            </a-card>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="6">
            <a-card>
              <a-statistic title="Available" :value="summary.available" :value-style="{ color: '#52c41a' }" />
            </a-card>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="6">
            <a-card>
              <a-statistic title="Reserved" :value="summary.reserved" :value-style="{ color: '#fa8c16' }" />
            </a-card>
          </a-col>
        </a-row>

        <a-card title="IP Utilization" style="margin-top: 16px">
          <a-progress :percent="summary.usage_percentage" status="active" />
          <div style="margin-top: 8px; opacity: 0.75">
            {{ summary.used }} of {{ summary.total }} Public IP addresses are currently Used ({{ summary.usage_percentage }}%).
          </div>
        </a-card>

        <a-row :gutter="[16, 16]" style="margin-top: 16px">
          <a-col :xs="24" :lg="12">
            <a-card title="By Provider">
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
            <a-card title="By Owner & Environment">
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
              <a-divider style="margin: 12px 0" />
              <div style="display: flex; gap: 8px; flex-wrap: wrap">
                <a-tag v-for="env in summary.by_environment" :key="env.environment">
                  {{ env.environment }}: {{ env.total }}
                </a-tag>
              </div>
            </a-card>
          </a-col>
        </a-row>

        <a-card title="Recent Activity" style="margin-top: 16px">
          <a-list size="small" :data-source="summary.recent_audits">
            <template #renderItem="{ item }">
              <a-list-item>
                <span>
                  <a-tag>{{ item.action }}</a-tag>
                  <strong>{{ item.ip_address || '-' }}</strong>
                  <span style="margin-left: 8px; opacity: 0.75">by {{ item.actor }}</span>
                </span>
                <span style="opacity: 0.7; font-size: 12px">{{ item.created_at }}</span>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </template>
    </a-spin>
  </div>
</template>
