<template>
  <div class="space-y-3">
    <label v-if="label" class="text-sm font-medium text-gray-300 block">
      {{ label }}
    </label>
    <div
      v-if="quickDays && quickDays.length"
      class="flex items-center space-x-2 bg-[#0f172a] p-1 rounded-lg border border-gray-600"
    >
      <button
        v-for="dayOption in quickDays"
        :key="dayOption"
        @click="onSelectDays(dayOption)"
        class="px-3 py-1.5 text-sm rounded-md transition-colors flex-1"
        :class="modelDays === dayOption ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700'"
      >
        近{{ dayOption }}天
      </button>
    </div>
    <div class="flex items-center space-x-2">
      <div class="flex-1 relative">
        <input
          type="date"
          :value="modelStartDate"
          @input="onStartInput($event)"
          class="date-input w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 pr-10 border border-gray-600 hover:border-blue-500 transition-colors"
          :placeholder="startPlaceholder"
          @change="onDateChange('start')"
          :id="startInputId"
        />
        <label
          :for="startInputId"
          class="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-blue-400 hover:text-blue-300 transition-colors z-10"
          @click="openDatePicker(startInputId)"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </label>
      </div>
      <template v-if="!isSingleMode">
        <span class="text-gray-400 font-medium">{{ rangeSeparator }}</span>
        <div class="flex-1 relative">
          <input
            type="date"
            :value="modelEndDate"
            @input="onEndInput($event)"
            class="date-input w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 pr-10 border border-gray-600 hover:border-blue-500 transition-colors"
            :placeholder="endPlaceholder"
            @change="onDateChange('end')"
            :id="endInputId"
          />
          <label
            :for="endInputId"
            class="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-blue-400 hover:text-blue-300 transition-colors z-10"
            @click="openDatePicker(endInputId)"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </label>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelStartDate: string
    modelEndDate: string
    modelDays: number | null
    quickDays?: number[]
    label?: string
    startPlaceholder?: string
    endPlaceholder?: string
    rangeSeparator?: string
    startInputId?: string
    endInputId?: string
    /**
     * 单日期模式：
     * - 'start' 只展示开始日期输入框
     * - 'end' 只展示结束日期输入框
     * - undefined / null：正常区间模式（默认）
     */
    singleMode?: 'start' | 'end' | null
    /**
     * 在单日期模式下，另一端日期的默认值（如：今天的日期字符串 'YYYY-MM-DD'）
     * 只在「另一端为空」时自动填充一次，之后可由父组件自行控制。
     */
    defaultOtherDate?: string | null
  }>(),
  {
    quickDays: () => [1, 3, 7],
    label: '',
    startPlaceholder: '开始日期',
    endPlaceholder: '结束日期',
    rangeSeparator: '至',
    startInputId: undefined,
    endInputId: undefined,
    singleMode: null,
    defaultOtherDate: null
  }
)

const emit = defineEmits<{
  (e: 'update:modelStartDate', value: string): void
  (e: 'update:modelEndDate', value: string): void
  (e: 'update:modelDays', value: number | null): void
  (e: 'change', payload: { startDate: string; endDate: string; days: number | null }): void
}>()

const startInputId = computed(() => props.startInputId || 'start-date-input')
const endInputId = computed(() => props.endInputId || 'end-date-input')
const isSingleMode = computed(() => props.singleMode === 'start' || props.singleMode === 'end')

const formatDate = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const onSelectDays = (days: number) => {
  // 计算日期范围：结束日期为今天，开始日期为days天前
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days + 1) // +1 表示包含今天
  
  const startDateStr = formatDate(startDate)
  const endDateStr = formatDate(endDate)
  
  emit('update:modelDays', days)
  emit('update:modelStartDate', startDateStr)
  emit('update:modelEndDate', endDateStr)
  emit('change', {
    startDate: startDateStr,
    endDate: endDateStr,
    days
  })
}

const onStartInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:modelStartDate', value)
  emit('update:modelDays', null)

  // 单日期模式下，如仅展示开始日期，则在结束日期为空时自动填充默认值
  if (props.singleMode === 'start' && !props.modelEndDate && props.defaultOtherDate) {
    emit('update:modelEndDate', props.defaultOtherDate)
  }
}

const onEndInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:modelEndDate', value)
  emit('update:modelDays', null)

  // 单日期模式下，如仅展示结束日期，则在开始日期为空时自动填充默认值
  if (props.singleMode === 'end' && !props.modelStartDate && props.defaultOtherDate) {
    emit('update:modelStartDate', props.defaultOtherDate)
  }
}

const onDateChange = (_type: 'start' | 'end') => {
  emit('change', {
    startDate: props.modelStartDate,
    endDate: props.modelEndDate,
    days: props.modelDays
  })
}

const openDatePicker = (inputId: string) => {
  const input = document.getElementById(inputId) as HTMLInputElement | null
  if (!input) return

  if ('showPicker' in input && typeof (input as any).showPicker === 'function') {
    ;(input as any).showPicker()
  } else {
    input.focus()
    input.click()
  }
}

/**
 * 使用示例：
 *
 * 1）普通区间模式（带快捷「近 N 天」按钮）
 * <DateRangePicker
 *   label="📅 时间范围"
 *   :quick-days="[1, 3, 7]"
 *   v-model:modelStartDate="startDate"
 *   v-model:modelEndDate="endDate"
 *   v-model:modelDays="days"
 *   @change="({ startDate, endDate, days }) => { ... }"
 * />
 *
 * 2）单日期模式：只展示开始日期，结束日期默认今天
 * <DateRangePicker
 *   :quick-days="[]"
 *   label="分析日期"
 *   singleMode="start"
 *   :defaultOtherDate="today"
 *   v-model:modelStartDate="analysisDate"
 *   v-model:modelEndDate="endDate"
 * />
 *
 * 3）单日期模式：只展示结束日期，开始日期默认今天
 * <DateRangePicker
 *   :quick-days="[]"
 *   label="结束日期"
 *   singleMode="end"
 *   :defaultOtherDate="today"
 *   v-model:modelStartDate="startDate"
 *   v-model:modelEndDate="endDate"
 * />
 */
</script>

<style scoped>
.date-input {
  color-scheme: dark;
  position: relative;
}

.date-input::-webkit-calendar-picker-indicator {
  display: none;
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
  pointer-events: none;
}

.date-input::-moz-calendar-picker-indicator {
  display: none;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.date-input::-webkit-datetime-edit-text {
  color: #e5e7eb;
}

.date-input::-webkit-datetime-edit-month-field,
.date-input::-webkit-datetime-edit-day-field,
.date-input::-webkit-datetime-edit-year-field {
  color: #e5e7eb;
}

.date-input::-webkit-datetime-edit-month-field:focus,
.date-input::-webkit-datetime-edit-day-field:focus,
.date-input::-webkit-datetime-edit-year-field:focus {
  background-color: rgba(59, 130, 246, 0.2);
  color: #ffffff;
  border-radius: 2px;
}

.date-input:focus {
  border-color: #3b82f6;
  background-color: #0f172a;
}

.date-input:hover {
  border-color: #3b82f6;
}

.date-input::-webkit-calendar-picker-indicator {
  color-scheme: dark;
}
</style>


