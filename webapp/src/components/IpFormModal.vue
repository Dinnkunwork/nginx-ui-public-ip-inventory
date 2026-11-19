<script setup lang="ts">
import { Modal } from 'antdv-next'
import IpForm from './IpForm.vue'
import type { PublicIpPayload, PublicIpRecord } from '../types/inventory'

defineProps<{
  open: boolean
  initial: PublicIpRecord | null
  submitting: boolean
  serverError: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'submit', payload: PublicIpPayload): void
}>()
</script>

<template>
  <Modal
    :open="open"
    :title="initial ? `Edit Public IP: ${initial.ip_address}` : 'Add Public IP'"
    :footer="null"
    width="720px"
    destroy-on-hidden
    @cancel="emit('update:open', false)"
  >
    <IpForm
      :initial="initial"
      :submitting="submitting"
      :server-error="serverError"
      :submit-label="initial ? 'Update IP Address' : 'Add IP Address'"
      @submit="(payload) => emit('submit', payload)"
      @cancel="emit('update:open', false)"
    />
  </Modal>
</template>
