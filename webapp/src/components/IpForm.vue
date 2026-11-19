<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { PublicIpPayload, PublicIpRecord } from '../types/inventory'
import { isValidIpAddress } from '../utils/ipValidation'

const props = withDefaults(
  defineProps<{
    initial?: PublicIpRecord | null
    submitting?: boolean
    submitLabel?: string
    serverError?: string
  }>(),
  {
    initial: null,
    submitting: false,
    submitLabel: 'Save IP Address',
    serverError: '',
  },
)

const emit = defineEmits<{
  (e: 'submit', payload: PublicIpPayload): void
  (e: 'cancel'): void
}>()

const form = reactive<PublicIpPayload>({
  ip_address: '',
  provider: '',
  owner_type: 'Internal',
  application: '',
  domain: '',
  environment: 'prod',
  server_ip: '',
  status: 'Used',
  notes: '',
})

const validationError = ref('')

watch(
  () => props.initial,
  (rec) => {
    if (rec) {
      form.ip_address = rec.ip_address
      form.provider = rec.provider
      form.owner_type = rec.owner_type
      form.application = rec.application
      form.domain = rec.domain
      form.environment = rec.environment
      form.server_ip = rec.server_ip
      form.status = rec.status
      form.notes = rec.notes
    } else {
      form.ip_address = ''
      form.provider = ''
      form.owner_type = 'Internal'
      form.application = ''
      form.domain = ''
      form.environment = 'prod'
      form.server_ip = ''
      form.status = 'Used'
      form.notes = ''
    }
    validationError.value = ''
  },
  { immediate: true },
)

const isUsed = computed(() => form.status === 'Used')

function handleSubmit(): void {
  validationError.value = ''
  if (!isValidIpAddress(form.ip_address)) {
    validationError.value = 'Public IP must be a valid IPv4 or IPv6 address.'
    return
  }
  if (!form.provider.trim()) {
    validationError.value = 'Provider is required.'
    return
  }
  if (isUsed.value && !form.application.trim()) {
    validationError.value = 'Application is required when status is Used.'
    return
  }
  if (isUsed.value && !form.environment) {
    validationError.value = 'Environment is required when status is Used.'
    return
  }
  if (form.server_ip.trim() && !isValidIpAddress(form.server_ip)) {
    validationError.value = 'Server IP must be a valid IPv4 or IPv6 address.'
    return
  }

  emit('submit', {
    ...form,
    ip_address: form.ip_address.trim(),
    provider: form.provider.trim(),
    application: form.application.trim(),
    domain: form.domain.trim(),
    server_ip: form.server_ip.trim(),
    notes: form.notes.trim(),
  })
}
</script>

<template>
  <a-form layout="vertical" @submit.prevent="handleSubmit">
    <a-alert
      v-if="validationError || serverError"
      type="error"
      :message="validationError || serverError"
      show-icon
      style="margin-bottom: 16px"
    />

    <a-row :gutter="16">
      <a-col :xs="24" :md="12">
        <a-form-item label="Public IP Address" required>
          <a-input
            v-model:value="form.ip_address"
            placeholder="e.g. 103.10.20.10 or 2001:db8::1"
          />
        </a-form-item>
      </a-col>
      <a-col :xs="24" :md="12">
        <a-form-item label="Provider (ISP / Cloud)" required>
          <a-input v-model:value="form.provider" placeholder="e.g. Biznet, Telkom, AWS" />
        </a-form-item>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <a-col :xs="24" :md="8">
        <a-form-item label="Owner" required>
          <a-select v-model:value="form.owner_type">
            <a-select-option value="Internal">Internal</a-select-option>
            <a-select-option value="External">External</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
      <a-col :xs="24" :md="8">
        <a-form-item label="Status" required>
          <a-select v-model:value="form.status">
            <a-select-option value="Used">Used</a-select-option>
            <a-select-option value="Available">Available</a-select-option>
            <a-select-option value="Reserved">Reserved</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
      <a-col :xs="24" :md="8">
        <a-form-item label="Environment" :required="isUsed">
          <a-select v-model:value="form.environment" allow-clear placeholder="Select environment">
            <a-select-option value="">-</a-select-option>
            <a-select-option value="dev">dev</a-select-option>
            <a-select-option value="staging">staging</a-select-option>
            <a-select-option value="uat">uat</a-select-option>
            <a-select-option value="prod">prod</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <a-col :xs="24" :md="12">
        <a-form-item label="Application / Client" :required="isUsed">
          <a-input
            v-model:value="form.application"
            placeholder="Optional when Available"
          />
        </a-form-item>
      </a-col>
      <a-col :xs="24" :md="12">
        <a-form-item label="Domain">
          <a-input v-model:value="form.domain" placeholder="e.g. app.company.id" />
        </a-form-item>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <a-col :xs="24" :md="12">
        <a-form-item label="Server / Private IP">
          <a-input v-model:value="form.server_ip" placeholder="e.g. 10.10.1.15" />
        </a-form-item>
      </a-col>
      <a-col :xs="24" :md="12">
        <a-form-item label="Notes">
          <a-textarea v-model:value="form.notes" :rows="2" placeholder="Additional remarks" />
        </a-form-item>
      </a-col>
    </a-row>

    <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px">
      <a-button @click="emit('cancel')">Cancel</a-button>
      <a-button type="primary" html-type="submit" :loading="submitting">
        {{ submitLabel }}
      </a-button>
    </div>
  </a-form>
</template>
