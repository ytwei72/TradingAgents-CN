<template>
  <Transition name="modal">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      @click.self="handleClose"
    >
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 shadow-2xl w-[90vw] h-[90vh] max-w-6xl flex flex-col">
        <!-- 模态框头部 -->
        <div class="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
          <h3 class="text-lg font-semibold text-white">{{ title }}</h3>
          <button
            @click="handleClose"
            class="text-gray-400 hover:text-white transition-colors p-2 hover:bg-gray-700 rounded-lg"
            title="关闭 (ESC)"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <!-- 模态框内容 -->
        <div class="flex-1 overflow-hidden p-4 min-h-0">
          <slot>
            <JsonViewer v-if="data" :data="data" :max-height="'100%'" />
            <div v-else class="text-gray-400 text-center py-8">暂无数据</div>
          </slot>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
import JsonViewer from './JsonViewer.vue'

interface Props {
  modelValue: boolean
  title?: string
  data?: any
}

const props = withDefaults(defineProps<Props>(), {
  title: '详情',
  data: null
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const handleClose = () => {
  emit('update:modelValue', false)
}

// ESC键关闭模态框
const handleEscape = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.modelValue) {
    handleClose()
  }
}

// 监听显示状态，控制背景滚动
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  window.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEscape)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* 模态框动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active > div,
.modal-leave-active > div {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from > div,
.modal-leave-to > div {
  transform: scale(0.9);
  opacity: 0;
}
</style>

