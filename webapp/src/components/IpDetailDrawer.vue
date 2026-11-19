<script setup lang="ts">
import {
  Descriptions,
  DescriptionsItem,
  Drawer,
  Spin,
  Table,
  Tag,
} from 'antdv-next'
import type { PublicIpRecord } from '../types/inventory'
import { statusTagColor } from '../utils/ipValidation'

defineProps<{
  open: boolean
  record: PublicIpRecord | null
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
}>()

const auditColumns = [
  { title: 'Action', dataIndex: 'action', key: 'action', width: 100 },
  { title: 'Actor', dataIndex: 'actor', key: 'actor', width: 120 },
  { title: 'Time', dataIndex: 'created_at', key: 'created_at' },
]
</script>

<template>
  <Drawer
    :open="open"
    :title="record ? `IP Details: ${record.ip_address}` : 'IP Details'"
    :size="560"
    @close="emit('update:open', false)"
  >
    <Spin :spinning="loading">
      <template v-if="record">
        <Descriptions bordered :column="1" size="small">
          <DescriptionsItem label="Public IP">{{ record.ip_address }}</DescriptionsItem>
          <DescriptionsItem label="Provider">{{ record.provider }}</DescriptionsItem>
          <DescriptionsItem label="Owner">{{ record.owner_type }}</DescriptionsItem>
          <DescriptionsItem label="Status">
            <Tag :color="statusTagColor(record.status)">{{ record.status }}</Tag>
          </DescriptionsItem>
          <DescriptionsItem label="Application">{{ record.application || '-' }}</DescriptionsItem>
          <DescriptionsItem label="Domain">{{ record.domain || '-' }}</DescriptionsItem>
          <DescriptionsItem label="Environment">{{ record.environment || '-' }}</DescriptionsItem>
          <DescriptionsItem label="Server / Private IP">{{ record.server_ip || '-' }}</DescriptionsItem>
          <DescriptionsItem label="Notes">{{ record.notes || '-' }}</DescriptionsItem>
          <DescriptionsItem label="Created At">{{ record.created_at }}</DescriptionsItem>
          <DescriptionsItem label="Updated At">{{ record.updated_at }}</DescriptionsItem>
        </Descriptions>

        <h4 style="margin: 20px 0 8px">Audit History</h4>
        <Table
          size="small"
          :pagination="false"
          row-key="id"
          :columns="auditColumns"
          :data-source="record.audit_logs || []"
        >
          <template #bodyCell="{ column, record: audit }">
            <template v-if="column.key === 'action'">
              <Tag>{{ audit.action }}</Tag>
            </template>
          </template>
        </Table>
      </template>
    </Spin>
  </Drawer>
</template>
