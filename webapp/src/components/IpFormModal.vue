<script setup lang="ts">
import { Modal } from 'antdv-next'
import { computed } from 'vue'
import IpForm from './IpForm.vue'
import type { PublicIpPayload } from '../types/inventory'

export type IpModalMode = 'create' | 'edit' | 'clone'

const props = withDefaults(
  defineProps<{
    open: boolean
    mode?: IpModalMode
    sourceIp?: string
    initial: Partial<PublicIpPayload> | null
    submitting: boolean
    serverError: string
  }>(),
  {
    mode: 'create',
    sourceIp: '',
  },
)

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'submit', payload: PublicIpPayload): void
}>()

const modalTitle = computed(() => {
  if (props.mode === 'edit') {
    return `Edit Public IP: ${props.sourceIp || props.initial?.ip_address || ''}`
  }
  if (props.mode === 'clone') {
    return `Clone Public IP (from ${props.sourceIp})`
  }
  return 'Add Public IP'
})

const submitLabel = computed(() => {
  if (props.mode === 'edit') return 'Update IP Address'
  if (props.mode === 'clone') return 'Create Cloned IP'
  return 'Add IP Address'
})
</script>

<template>
  <Modal
    :open="open"
    :title="modalTitle"
    :footer="null"
    width="720px"
    destroy-on-hidden
    @cancel="emit('update:open', false)"
  >
    <IpForm
      :initial="initial"
      :submitting="submitting"
      :server-error="serverError"
      :submit-label="submitLabel"
      @submit="(payload) => emit('submit', payload)"
      @cancel="emit('update:open', false)"
    />
  </Modal>
</template>
