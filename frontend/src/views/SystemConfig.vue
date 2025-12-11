<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { getSystemConfig, updateSystemConfig } from '../api'

type MongoConfig = {
  mongo_host?: string
  mongo_port?: number | null
  mongo_username?: string
  mongo_password?: string
  mongo_database?: string
  mongo_auth_source?: string
  mongo_max_connections?: number | null
  mongo_min_connections?: number | null
  mongo_connect_timeout_ms?: number | null
  mongo_socket_timeout_ms?: number | null
  mongo_server_selection_timeout_ms?: number | null
  mongo_uri?: string
  mongo_db?: string
}

type SystemConfigState = {
  llm_provider: string
  deep_think_llm: string
  quick_think_llm: string
  research_depth_default: number
  market_type_default: string
  memory_enabled: boolean
  online_tools: boolean
  online_news: boolean
  realtime_data: boolean
  max_recur_limit: number
  backend_url: string
  custom_openai_base_url: string
  data_dir: string
  results_dir: string
  data_cache_dir: string
  db: {
    mongo: MongoConfig
  }
  [key: string]: any
}

const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')

const config = reactive<SystemConfigState>({
  llm_provider: 'dashscope',
  deep_think_llm: '',
  quick_think_llm: '',
  research_depth_default: 3,
  market_type_default: '美股',
  memory_enabled: true,
  online_tools: true,
  online_news: true,
  realtime_data: false,
  max_recur_limit: 100,
  backend_url: '',
  custom_openai_base_url: '',
  data_dir: '',
  results_dir: '',
  data_cache_dir: '',
  db: {
    mongo: {
      mongo_host: '',
      mongo_port: null,
      mongo_username: '',
      mongo_password: '',
      mongo_database: '',
      mongo_auth_source: '',
      mongo_max_connections: null,
      mongo_min_connections: null,
      mongo_connect_timeout_ms: null,
      mongo_socket_timeout_ms: null,
      mongo_server_selection_timeout_ms: null,
      mongo_uri: '',
      mongo_db: ''
    }
  }
})

const providerOptions = [
  { value: 'dashscope', label: 'DashScope' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'qianfan', label: '千帆' },
  { value: 'google', label: 'Google AI' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'siliconflow', label: 'SiliconFlow' },
  { value: 'custom_openai', label: '自定义OpenAI' }
]

const marketOptions = ['A股', '港股', '美股']

function deepAssign(target: any, source: any) {
  if (!source || typeof source !== 'object') return
  Object.keys(source).forEach((key) => {
    const srcVal = source[key]
    if (srcVal && typeof srcVal === 'object' && !Array.isArray(srcVal)) {
      target[key] = target[key] || {}
      deepAssign(target[key], srcVal)
    } else {
      target[key] = srcVal
    }
  })
}

const loadConfig = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await getSystemConfig()
    if (res.success && res.data) {
      deepAssign(config, res.data)
    } else {
      error.value = res.message || '加载配置失败'
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '加载配置失败'
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    const payload = JSON.parse(JSON.stringify(config))
    const res = await updateSystemConfig(payload)
    if (res.success) {
      message.value = '配置已保存'
      deepAssign(config, res.data)
    } else {
      error.value = res.message || '保存失败'
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div class="space-y-6 text-gray-100">
    <header class="flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-bold">配置管理</h1>
        <p class="text-sm text-gray-400">基于 prepare_analysis_steps 的系统配置项</p>
      </div>
      <button
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-semibold disabled:opacity-60"
        :disabled="saving || loading"
        @click="saveConfig"
      >
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </header>

    <div v-if="loading" class="bg-[#1e293b] border border-gray-700 rounded-lg p-6">
      加载配置中...
    </div>
    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <section class="bg-[#1e293b] border border-gray-700 rounded-lg p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold">LLM 设置</h2>
            <p class="text-xs text-gray-400">llm_provider / deep_think_llm / quick_think_llm / backend_url</p>
          </div>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-300 mb-1">LLM 提供商 (llm_provider)</label>
            <select v-model="config.llm_provider" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2">
              <option v-for="item in providerOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-gray-300 mb-1">深度思考模型 (deep_think_llm)</label>
              <input v-model="config.deep_think_llm" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>
            <div>
              <label class="block text-sm text-gray-300 mb-1">快速思考模型 (quick_think_llm)</label>
              <input v-model="config.quick_think_llm" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">LLM 后端地址 (backend_url)</label>
            <input v-model="config.backend_url" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">自定义 OpenAI Base URL (custom_openai_base_url)</label>
            <input v-model="config.custom_openai_base_url" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
        </div>
      </section>

      <section class="bg-[#1e293b] border border-gray-700 rounded-lg p-6 space-y-4">
        <div>
          <h2 class="text-lg font-semibold">分析默认值</h2>
          <p class="text-xs text-gray-400">research_depth_default / market_type_default / max_recur_limit</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-300 mb-1">默认研究深度 (research_depth_default)</label>
            <input
              v-model.number="config.research_depth_default"
              type="number"
              min="1"
              max="5"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">默认市场 (market_type_default)</label>
            <select v-model="config.market_type_default" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2">
              <option v-for="item in marketOptions" :key="item" :value="item">{{ item }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">最大递归限制 (max_recur_limit)</label>
            <input
              v-model.number="config.max_recur_limit"
              type="number"
              min="1"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex items-center space-x-2">
            <input id="memory_enabled" v-model="config.memory_enabled" type="checkbox" class="form-checkbox text-blue-500" />
            <label for="memory_enabled" class="text-sm text-gray-300">启用记忆 (memory_enabled)</label>
          </div>
          <div class="flex items-center space-x-2">
            <input id="online_tools" v-model="config.online_tools" type="checkbox" class="form-checkbox text-blue-500" />
            <label for="online_tools" class="text-sm text-gray-300">在线工具 (online_tools)</label>
          </div>
          <div class="flex items-center space-x-2">
            <input id="online_news" v-model="config.online_news" type="checkbox" class="form-checkbox text-blue-500" />
            <label for="online_news" class="text-sm text-gray-300">在线新闻 (online_news)</label>
          </div>
          <div class="flex items-center space-x-2">
            <input id="realtime_data" v-model="config.realtime_data" type="checkbox" class="form-checkbox text-blue-500" />
            <label for="realtime_data" class="text-sm text-gray-300">实时数据 (realtime_data)</label>
          </div>
        </div>
      </section>

      <section class="bg-[#1e293b] border border-gray-700 rounded-lg p-6 space-y-4">
        <div>
          <h2 class="text-lg font-semibold">路径配置</h2>
          <p class="text-xs text-gray-400">data_dir / results_dir / data_cache_dir</p>
        </div>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-300 mb-1">数据目录 (data_dir)</label>
            <input v-model="config.data_dir" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">结果目录 (results_dir)</label>
            <input v-model="config.results_dir" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">数据缓存目录 (data_cache_dir)</label>
            <input v-model="config.data_cache_dir" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
        </div>
      </section>

      <section class="bg-[#1e293b] border border-gray-700 rounded-lg p-6 space-y-4">
        <div>
          <h2 class="text-lg font-semibold">数据库配置 (db.mongo)</h2>
          <p class="text-xs text-gray-400">对应 config.db.mongo 结构</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_host</label>
            <input v-model="config.db.mongo.mongo_host" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_port</label>
            <input
              v-model.number="config.db.mongo.mongo_port"
              type="number"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_username</label>
            <input v-model="config.db.mongo.mongo_username" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_password</label>
            <input v-model="config.db.mongo.mongo_password" type="password" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_database</label>
            <input v-model="config.db.mongo.mongo_database" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_auth_source</label>
            <input v-model="config.db.mongo.mongo_auth_source" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_max_connections</label>
            <input
              v-model.number="config.db.mongo.mongo_max_connections"
              type="number"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_min_connections</label>
            <input
              v-model.number="config.db.mongo.mongo_min_connections"
              type="number"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_connect_timeout_ms</label>
            <input
              v-model.number="config.db.mongo.mongo_connect_timeout_ms"
              type="number"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_socket_timeout_ms</label>
            <input
              v-model.number="config.db.mongo.mongo_socket_timeout_ms"
              type="number"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_server_selection_timeout_ms</label>
            <input
              v-model.number="config.db.mongo.mongo_server_selection_timeout_ms"
              type="number"
              class="w-full bg-[#0f172a] border border-gray-700 rounded p-2"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_uri</label>
            <input v-model="config.db.mongo.mongo_uri" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-300 mb-1">mongo_db</label>
            <input v-model="config.db.mongo.mongo_db" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
          </div>
        </div>
      </section>
    </div>

    <div class="space-y-2">
      <p v-if="message" class="text-green-400 text-sm">{{ message }}</p>
      <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.form-checkbox {
  width: 16px;
  height: 16px;
}
</style>

