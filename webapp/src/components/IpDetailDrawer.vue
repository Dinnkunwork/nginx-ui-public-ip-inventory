<script setup lang="ts">
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
</script>

<template>
  <a-drawer
    :open="open"
    :title="record ? `IP Details: ${record.ip_address}` : 'IP Details'"
    width="560"
    @close="emit('update:open', false)"
  >
    <a-spin :spinning="loading">
      <template v-if="record">
        <a-descriptions bordered :column="1" size="small">
          <a-descriptions-item label="Public IP">{{ record.ip_address }}</a-descriptions-item>
          <a-descriptions-item label="Provider">{{ record.provider }}</a-descriptions-item>
          <a-descriptions-item label="Owner">{{ record.owner_type }}</a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="statusTagColor(record.status)">{{ record.status }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Application">{{ record.application || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Domain">{{ record.domain || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Environment">{{ record.environment || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Server / Private IP">{{ record.server_ip || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Notes">{{ record.notes || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Created At">{{ record.created_at }}</a-descriptions-item>
          <a-descriptions-item label="Updated At">{{ record.updated_at }}</a-descriptions-item>
        </a-descriptions>

        <h4 style="margin: 20px 0 8px">Audit History</h4>
        <a-list
          size="small"
          bordered
          :data-source="record.audit_logs || []"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <span>
                <a-tag>{{ item.action }}</a-tag>
                by <strong>{{ item.actor }}</strong>
              </span>
              <span style="opacity: 0.7; font-size: 12px">{{ item.created_at }}</span>
            </a-list-item>
          </template>
        </a-list>
      </template>
    </a-spin>
  </a-drawer>
</template>
