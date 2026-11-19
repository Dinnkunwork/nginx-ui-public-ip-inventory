<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { inventoryApi } from '../api/client'
import IpForm from '../components/IpForm.vue'
import type { PublicIpPayload } from '../types/inventory'

const router = useRouter()
const submitting = ref(false)
const serverError = ref('')

async function handleCreate(payload: PublicIpPayload): Promise<void> {
  submitting.value = true
  serverError.value = ''
  try {
    await inventoryApi.createIp(payload)
    await router.push('/public-ip-inventory/list')
  } catch (err) {
    serverError.value = err instanceof Error ? err.message : 'Failed to create Public IP'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div style="padding: 16px; max-width: 840px">
    <h2 style="margin-bottom: 16px">Add Public IP Address</h2>
    <a-card>
      <IpForm
        :submitting="submitting"
        :server-error="serverError"
        submit-label="Add IP Address"
        @submit="handleCreate"
        @cancel="router.push('/public-ip-inventory/list')"
      />
    </a-card>
  </div>
</template>
