<script setup lang="ts">
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Progress,
  Row,
  Spin,
  Statistic,
  TabPane,
  Table,
  Tabs,
  Tag,
} from 'antdv-next'
import { onMounted, ref } from 'vue'
import { inventoryApi } from '../api/client'
import ReportsBackupPanel from '../components/ReportsBackupPanel.vue'
import type { DashboardSummary } from '../types/inventory'

const loading = ref(false)
const error = ref('')
const activeTab = ref('overview')
const summary = ref<DashboardSummary | null>(null)

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

const auditColumns = [
  { title: 'Action', dataIndex: 'action', key: 'action', width: 110 },
  { title: 'IP Address', dataIndex: 'ip_address', key: 'ip_address' },
  { title: 'Actor', dataIndex: 'actor', key: 'actor', width: 140 },
  { title: 'Time', dataIndex: 'created_at', key: 'created_at', width: 200 },
]

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
  <div style="padding: 8px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
      <h2 style="margin: 0">Public IP Inventory — Dashboard & Reports</h2>
      <Button :loading="loading" @click="loadSummary">Refresh</Button>
    </div>

    <Alert v-if="error" type="error" :title="error" show-icon style="margin-bottom: 16px" />

    <Spin :spinning="loading">
      <Tabs v-model:active-key="activeTab">
        <TabPane key="overview" tab="Dashboard Overview">
          <template v-if="summary">
            <Row :gutter="[16, 16]">
              <Col :xs="24" :sm="12" :lg="6">
                <Card>
                  <Statistic title="Total IP" :value="summary.total" />
                </Card>
              </Col>
              <Col :xs="24" :sm="12" :lg="6">
                <Card>
                  <Statistic title="Used" :value="summary.used" :value-style="{ color: '#1677ff' }" />
                </Card>
              </Col>
              <Col :xs="24" :sm="12" :lg="6">
                <Card>
                  <Statistic title="Available" :value="summary.available" :value-style="{ color: '#52c41a' }" />
                </Card>
              </Col>
              <Col :xs="24" :sm="12" :lg="6">
                <Card>
                  <Statistic title="Reserved" :value="summary.reserved" :value-style="{ color: '#fa8c16' }" />
                </Card>
              </Col>
            </Row>

            <Card title="IP Utilization" style="margin-top: 16px">
              <Progress :percent="summary.usage_percentage" status="active" />
              <div style="margin-top: 8px; opacity: 0.75">
                {{ summary.used }} of {{ summary.total }} Public IP addresses are currently Used ({{ summary.usage_percentage }}%).
              </div>
            </Card>

            <Row :gutter="[16, 16]" style="margin-top: 16px">
              <Col :xs="24" :lg="12">
                <Card title="By Provider">
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
                <Card title="By Owner & Environment">
                  <Table
                    size="small"
                    :pagination="false"
                    :data-source="summary.by_owner"
                    row-key="owner_type"
                    :columns="ownerColumns"
                  />
                  <Divider style="margin: 12px 0" />
                  <div style="display: flex; gap: 8px; flex-wrap: wrap">
                    <Tag v-for="env in summary.by_environment" :key="env.environment">
                      {{ env.environment }}: {{ env.total }}
                    </Tag>
                  </div>
                </Card>
              </Col>
            </Row>

            <Card title="Recent Activity" style="margin-top: 16px">
              <Table
                size="small"
                :pagination="false"
                row-key="id"
                :columns="auditColumns"
                :data-source="summary.recent_audits"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'action'">
                    <Tag>{{ record.action }}</Tag>
                  </template>
                  <template v-else-if="column.key === 'ip_address'">
                    {{ record.ip_address || '-' }}
                  </template>
                </template>
              </Table>
            </Card>
          </template>
        </TabPane>

        <TabPane key="reports" tab="Reports & Backup">
          <ReportsBackupPanel :summary="summary" @restored="loadSummary" />
        </TabPane>
      </Tabs>
    </Spin>
  </div>
</template>
