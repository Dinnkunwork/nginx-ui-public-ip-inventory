<script setup lang="ts">
import {
  Alert,
  Button,
  Col,
  Form,
  FormItem,
  Input,
  Row,
  Select,
  TextArea,
} from 'antdv-next'
import { computed, reactive, ref, watch } from 'vue'
import type { PublicIpPayload } from '../types/inventory'
import { isValidIpAddress } from '../utils/ipValidation'

const props = withDefaults(
  defineProps<{
    initial?: Partial<PublicIpPayload> | null
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

const OWNER_OPTIONS = [
  { label: 'Internal', value: 'Internal' },
  { label: 'External', value: 'External' },
]

const STATUS_OPTIONS = [
  { label: 'Used', value: 'Used' },
  { label: 'Available', value: 'Available' },
  { label: 'Reserved', value: 'Reserved' },
]

const ENVIRONMENT_OPTIONS = [
  { label: '-', value: '' },
  { label: 'dev', value: 'dev' },
  { label: 'staging', value: 'staging' },
  { label: 'uat', value: 'uat' },
  { label: 'prod', value: 'prod' },
]

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
      form.ip_address = rec.ip_address ?? ''
      form.provider = rec.provider ?? ''
      form.owner_type = rec.owner_type ?? 'Internal'
      form.application = rec.application ?? ''
      form.domain = rec.domain ?? ''
      form.environment = rec.environment ?? ''
      form.server_ip = rec.server_ip ?? ''
      form.status = rec.status ?? 'Used'
      form.notes = rec.notes ?? ''
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
    environment: form.environment || '',
    server_ip: form.server_ip.trim(),
    notes: form.notes.trim(),
  })
}
</script>

<template>
  <Form layout="vertical" @submit.prevent="handleSubmit">
    <Alert
      v-if="validationError || serverError"
      type="error"
      :title="validationError || serverError"
      show-icon
      style="margin-bottom: 16px"
    />

    <Row :gutter="16">
      <Col :xs="24" :md="12">
        <FormItem label="Public IP Address" required>
          <Input
            v-model:value="form.ip_address"
            placeholder="e.g. 103.10.20.10 or 2001:db8::1"
          />
        </FormItem>
      </Col>
      <Col :xs="24" :md="12">
        <FormItem label="Provider (ISP / Cloud)" required>
          <Input v-model:value="form.provider" placeholder="e.g. Biznet, Telkom, AWS" />
        </FormItem>
      </Col>
    </Row>

    <Row :gutter="16">
      <Col :xs="24" :md="8">
        <FormItem label="Owner" required>
          <Select v-model:value="form.owner_type" :options="OWNER_OPTIONS" style="width: 100%" />
        </FormItem>
      </Col>
      <Col :xs="24" :md="8">
        <FormItem label="Status" required>
          <Select v-model:value="form.status" :options="STATUS_OPTIONS" style="width: 100%" />
        </FormItem>
      </Col>
      <Col :xs="24" :md="8">
        <FormItem label="Environment" :required="isUsed">
          <Select
            v-model:value="form.environment"
            :options="ENVIRONMENT_OPTIONS"
            allow-clear
            placeholder="Select environment"
            style="width: 100%"
          />
        </FormItem>
      </Col>
    </Row>

    <Row :gutter="16">
      <Col :xs="24" :md="12">
        <FormItem label="Application / Client" :required="isUsed">
          <Input
            v-model:value="form.application"
            placeholder="Optional when Available"
          />
        </FormItem>
      </Col>
      <Col :xs="24" :md="12">
        <FormItem label="Domain">
          <Input v-model:value="form.domain" placeholder="e.g. app.company.id" />
        </FormItem>
      </Col>
    </Row>

    <Row :gutter="16">
      <Col :xs="24" :md="12">
        <FormItem label="Server / Private IP">
          <Input v-model:value="form.server_ip" placeholder="e.g. 10.10.1.15" />
        </FormItem>
      </Col>
      <Col :xs="24" :md="12">
        <FormItem label="Notes">
          <TextArea v-model:value="form.notes" :rows="2" placeholder="Additional remarks" />
        </FormItem>
      </Col>
    </Row>

    <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px">
      <Button @click="emit('cancel')">Cancel</Button>
      <Button type="primary" html-type="submit" :loading="submitting">
        {{ submitLabel }}
      </Button>
    </div>
  </Form>
</template>
