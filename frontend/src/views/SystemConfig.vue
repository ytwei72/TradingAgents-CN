<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getSystemConfig, updateSystemConfig, type ModelConfig, type PricingConfig, type SystemSettings } from '../api'

const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')
const activeTab = ref<'models' | 'pricing' | 'settings'>('models')

// 配置数据
const models = ref<ModelConfig[]>([])
const pricing = ref<PricingConfig[]>([])
const settings = reactive<SystemSettings>({
  default_provider: 'dashscope',
  default_model: 'qwen-turbo',
  enable_cost_tracking: true,
  cost_alert_threshold: 100.0,
  currency_preference: 'CNY',
  auto_save_usage: true,
  max_usage_records: 10000,
  data_dir: './data',
  cache_dir: './data/cache',
  results_dir: './results',
  auto_create_dirs: true,
  openai_enabled: false,
  finnhub_api_key: '',
  log_level: 'INFO'
})

// 编辑状态
const editingModelIndex = ref<number | null>(null)
const editingPricingIndex = ref<number | null>(null)
const newModel = ref<Partial<ModelConfig>>({})
const newPricing = ref<Partial<PricingConfig>>({})

const providerOptions = ['dashscope', 'openai', 'deepseek', 'google', 'qianfan', 'openrouter', 'siliconflow']
const currencyOptions = ['CNY', 'USD', 'EUR']
const logLevelOptions = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

// 加载配置
const loadConfig = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await getSystemConfig(['models', 'pricing', 'settings'])
    if (res.success && res.data) {
      if (res.data.models) {
        models.value = res.data.models
      }
      if (res.data.pricing) {
        pricing.value = res.data.pricing
      }
      if (res.data.settings) {
        Object.assign(settings, res.data.settings)
      }
    } else {
      error.value = res.message || '加载配置失败'
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '加载配置失败'
  } finally {
    loading.value = false
  }
}

// 保存配置
const saveConfig = async () => {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    const payload: any = {}
    
    if (activeTab.value === 'models') {
      payload.models = models.value
    } else if (activeTab.value === 'pricing') {
      payload.pricing = pricing.value
    } else if (activeTab.value === 'settings') {
      payload.settings = settings
    }
    
    const res = await updateSystemConfig(payload)
    if (res.success) {
      message.value = '配置已保存'
      // 保存后重新加载
      await loadConfig()
    } else {
      error.value = res.message || '保存失败'
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

// 保存所有配置
const saveAllConfig = async () => {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    const payload = {
      models: models.value,
      pricing: pricing.value,
      settings: settings
    }
    
    const res = await updateSystemConfig(payload)
    if (res.success) {
      message.value = '所有配置已保存'
      await loadConfig()
    } else {
      error.value = res.message || '保存失败'
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

// 模型配置操作
const startEditModel = (index: number) => {
  editingModelIndex.value = index
}

const cancelEditModel = () => {
  editingModelIndex.value = null
  newModel.value = {}
}

const saveModel = (index: number) => {
  if (index < 0) {
    // 新增
    if (newModel.value.provider && newModel.value.model_name) {
      models.value.push({
        provider: newModel.value.provider!,
        model_name: newModel.value.model_name!,
        api_key: newModel.value.api_key || '',
        base_url: newModel.value.base_url || null,
        max_tokens: newModel.value.max_tokens || 4000,
        temperature: newModel.value.temperature || 0.7,
        enabled: newModel.value.enabled ?? true
      })
      newModel.value = {}
    }
  } else {
    // 编辑现有
    editingModelIndex.value = null
  }
}

const deleteModel = (index: number) => {
  if (confirm('确定要删除此模型配置吗？')) {
    models.value.splice(index, 1)
  }
}

const addNewModel = () => {
  newModel.value = {
    provider: 'dashscope',
    model_name: '',
    api_key: '',
    base_url: null,
    max_tokens: 4000,
    temperature: 0.7,
    enabled: true
  }
}

// 定价配置操作
const startEditPricing = (index: number) => {
  editingPricingIndex.value = index
}

const cancelEditPricing = () => {
  editingPricingIndex.value = null
  newPricing.value = {}
}

const savePricing = (index: number) => {
  if (index < 0) {
    // 新增
    if (newPricing.value.provider && newPricing.value.model_name) {
      pricing.value.push({
        provider: newPricing.value.provider!,
        model_name: newPricing.value.model_name!,
        input_price_per_1k: newPricing.value.input_price_per_1k || 0,
        output_price_per_1k: newPricing.value.output_price_per_1k || 0,
        currency: newPricing.value.currency || 'CNY'
      })
      newPricing.value = {}
    }
  } else {
    // 编辑现有
    editingPricingIndex.value = null
  }
}

const deletePricing = (index: number) => {
  if (confirm('确定要删除此定价配置吗？')) {
    pricing.value.splice(index, 1)
  }
}

const addNewPricing = () => {
  newPricing.value = {
    provider: 'dashscope',
    model_name: '',
    input_price_per_1k: 0,
    output_price_per_1k: 0,
    currency: 'CNY'
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
        <h1 class="text-2xl font-bold">系统配置管理</h1>
        <p class="text-sm text-gray-400">管理模型配置、定价配置和系统设置</p>
      </div>
      <div class="flex gap-2">
        <button
          class="px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg text-sm font-semibold disabled:opacity-60 transition-colors"
          :disabled="saving || loading"
          @click="saveAllConfig"
        >
          {{ saving ? '保存中...' : '保存所有配置' }}
        </button>
        <button
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-sm font-semibold disabled:opacity-60 transition-colors"
          :disabled="saving || loading"
          @click="saveConfig"
        >
          {{ saving ? '保存中...' : '保存当前标签页' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="bg-[#1e293b] border border-gray-700 rounded-lg p-6">
      加载配置中...
    </div>

    <div v-else>
      <!-- 标签页 -->
      <div class="flex border-b border-gray-700 mb-6">
        <button
          @click="activeTab = 'models'"
          :class="[
            'px-6 py-3 font-medium text-sm transition-colors',
            activeTab === 'models'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          ]"
        >
          模型配置
        </button>
        <button
          @click="activeTab = 'pricing'"
          :class="[
            'px-6 py-3 font-medium text-sm transition-colors',
            activeTab === 'pricing'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          ]"
        >
          定价配置
        </button>
        <button
          @click="activeTab = 'settings'"
          :class="[
            'px-6 py-3 font-medium text-sm transition-colors',
            activeTab === 'settings'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          ]"
        >
          系统设置
        </button>
      </div>

      <!-- 模型配置 -->
      <div v-if="activeTab === 'models'" class="bg-[#1e293b] border border-gray-700 rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">模型配置</h2>
          <button
            @click="addNewModel"
            class="px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg text-sm font-semibold transition-colors"
          >
            新增模型
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm table-fixed">
            <thead>
              <tr class="border-b border-gray-700">
                <th class="text-left p-3 w-28">供应商</th>
                <th class="text-left p-3 w-40">模型名称</th>
                <th class="text-left p-3 min-w-[200px]">API密钥</th>
                <th class="text-left p-3 min-w-[180px]">Base URL</th>
                <th class="text-left p-3 w-24">最大Token</th>
                <th class="text-left p-3 w-20">温度</th>
                <th class="text-left p-3 w-16">启用</th>
                <th class="text-left p-3 w-20">操作</th>
              </tr>
            </thead>
            <tbody>
              <!-- 新增行 -->
              <tr v-if="newModel.provider" class="border-b border-gray-700 hover:bg-[#0f172a]">
                <td class="p-3">
                  <select v-model="newModel.provider" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1">
                    <option v-for="opt in providerOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
                <td class="p-3">
                  <input v-model="newModel.model_name" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" placeholder="模型名称" />
                </td>
                <td class="p-3">
                  <input v-model="newModel.api_key" type="password" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" placeholder="API密钥" />
                </td>
                <td class="p-3">
                  <input v-model="newModel.base_url" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" placeholder="Base URL (可选)" />
                </td>
                <td class="p-3">
                  <input v-model.number="newModel.max_tokens" type="number" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model.number="newModel.temperature" type="number" step="0.1" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <div class="flex justify-center">
                    <input v-model="newModel.enabled" type="checkbox" class="form-checkbox text-blue-500" />
                  </div>
                </td>
                <td class="p-3">
                  <div class="flex gap-2">
                    <button @click="saveModel(-1)" class="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-xs whitespace-nowrap transition-colors">保存</button>
                    <button @click="cancelEditModel" class="px-3 py-1.5 bg-gray-500 hover:bg-gray-600 rounded text-xs whitespace-nowrap transition-colors">取消</button>
                  </div>
                </td>
              </tr>
              <!-- 数据行 -->
              <tr v-for="(model, index) in models" :key="index" class="border-b border-gray-700 hover:bg-[#0f172a]">
                <td class="p-3">
                  <select v-model="model.provider" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1">
                    <option v-for="opt in providerOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
                <td class="p-3">
                  <input v-model="model.model_name" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model="model.api_key" type="password" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model="model.base_url" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" placeholder="可选" />
                </td>
                <td class="p-3">
                  <input v-model.number="model.max_tokens" type="number" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model.number="model.temperature" type="number" step="0.1" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <div class="flex justify-center">
                    <input v-model="model.enabled" type="checkbox" class="form-checkbox text-blue-500" />
                  </div>
                </td>
                <td class="p-3">
                  <button @click="deleteModel(index)" class="px-3 py-1.5 bg-rose-500 hover:bg-rose-600 rounded text-xs whitespace-nowrap transition-colors">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 定价配置 -->
      <div v-if="activeTab === 'pricing'" class="bg-[#1e293b] border border-gray-700 rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">定价配置</h2>
          <button
            @click="addNewPricing"
            class="px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg text-sm font-semibold transition-colors"
          >
            新增定价
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-700">
                <th class="text-left p-3">供应商</th>
                <th class="text-left p-3">模型名称</th>
                <th class="text-left p-3">输入价格(/1K)</th>
                <th class="text-left p-3">输出价格(/1K)</th>
                <th class="text-left p-3">货币</th>
                <th class="text-left p-3">操作</th>
              </tr>
            </thead>
            <tbody>
              <!-- 新增行 -->
              <tr v-if="newPricing.provider" class="border-b border-gray-700 hover:bg-[#0f172a]">
                <td class="p-3">
                  <select v-model="newPricing.provider" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1">
                    <option v-for="opt in providerOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
                <td class="p-3">
                  <input v-model="newPricing.model_name" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" placeholder="模型名称" />
                </td>
                <td class="p-3">
                  <input v-model.number="newPricing.input_price_per_1k" type="number" step="0.0001" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model.number="newPricing.output_price_per_1k" type="number" step="0.0001" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <select v-model="newPricing.currency" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1">
                    <option v-for="opt in currencyOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
                <td class="p-3">
                  <div class="flex gap-2">
                    <button @click="savePricing(-1)" class="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-xs whitespace-nowrap transition-colors">保存</button>
                    <button @click="cancelEditPricing" class="px-3 py-1.5 bg-gray-500 hover:bg-gray-600 rounded text-xs whitespace-nowrap transition-colors">取消</button>
                  </div>
                </td>
              </tr>
              <!-- 数据行 -->
              <tr v-for="(price, index) in pricing" :key="index" class="border-b border-gray-700 hover:bg-[#0f172a]">
                <td class="p-3">
                  <select v-model="price.provider" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1">
                    <option v-for="opt in providerOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
                <td class="p-3">
                  <input v-model="price.model_name" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model.number="price.input_price_per_1k" type="number" step="0.0001" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <input v-model.number="price.output_price_per_1k" type="number" step="0.0001" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1" />
                </td>
                <td class="p-3">
                  <select v-model="price.currency" class="w-full bg-[#0f172a] border border-gray-700 rounded p-1">
                    <option v-for="opt in currencyOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
                <td class="p-3">
                  <button @click="deletePricing(index)" class="px-3 py-1.5 bg-rose-500 hover:bg-rose-600 rounded text-xs whitespace-nowrap transition-colors">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 系统设置 -->
      <div v-if="activeTab === 'settings'" class="bg-[#1e293b] border border-gray-700 rounded-lg p-6 space-y-6">
        <h2 class="text-lg font-semibold">系统设置</h2>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- 基本设置 -->
          <section class="space-y-4">
            <h3 class="text-md font-semibold text-gray-300 border-b border-gray-700 pb-2">基本设置</h3>
            
            <div>
              <label class="block text-sm text-gray-300 mb-1">默认供应商 (default_provider)</label>
              <select v-model="settings.default_provider" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2">
                <option v-for="opt in providerOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </div>

            <div>
              <label class="block text-sm text-gray-300 mb-1">默认模型 (default_model)</label>
              <input v-model="settings.default_model" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>

            <div>
              <label class="block text-sm text-gray-300 mb-1">货币偏好 (currency_preference)</label>
              <select v-model="settings.currency_preference" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2">
                <option v-for="opt in currencyOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </div>

            <div>
              <label class="block text-sm text-gray-300 mb-1">日志级别 (log_level)</label>
              <select v-model="settings.log_level" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2">
                <option v-for="opt in logLevelOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </div>

            <div class="flex items-center space-x-2">
              <input id="enable_cost_tracking" v-model="settings.enable_cost_tracking" type="checkbox" class="form-checkbox text-blue-500" />
              <label for="enable_cost_tracking" class="text-sm text-gray-300">启用成本跟踪 (enable_cost_tracking)</label>
            </div>

            <div class="flex items-center space-x-2">
              <input id="auto_save_usage" v-model="settings.auto_save_usage" type="checkbox" class="form-checkbox text-blue-500" />
              <label for="auto_save_usage" class="text-sm text-gray-300">自动保存使用记录 (auto_save_usage)</label>
            </div>

            <div class="flex items-center space-x-2">
              <input id="auto_create_dirs" v-model="settings.auto_create_dirs" type="checkbox" class="form-checkbox text-blue-500" />
              <label for="auto_create_dirs" class="text-sm text-gray-300">自动创建目录 (auto_create_dirs)</label>
            </div>

            <div class="flex items-center space-x-2">
              <input id="openai_enabled" v-model="settings.openai_enabled" type="checkbox" class="form-checkbox text-blue-500" />
              <label for="openai_enabled" class="text-sm text-gray-300">启用 OpenAI (openai_enabled)</label>
            </div>
          </section>

          <!-- 成本与使用设置 -->
          <section class="space-y-4">
            <h3 class="text-md font-semibold text-gray-300 border-b border-gray-700 pb-2">成本与使用设置</h3>

            <div>
              <label class="block text-sm text-gray-300 mb-1">成本警告阈值 (cost_alert_threshold)</label>
              <input v-model.number="settings.cost_alert_threshold" type="number" step="0.1" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>

            <div>
              <label class="block text-sm text-gray-300 mb-1">最大使用记录数 (max_usage_records)</label>
              <input v-model.number="settings.max_usage_records" type="number" min="1" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>
          </section>

          <!-- 路径设置 -->
          <section class="space-y-4">
            <h3 class="text-md font-semibold text-gray-300 border-b border-gray-700 pb-2">路径设置</h3>

            <div>
              <label class="block text-sm text-gray-300 mb-1">数据目录 (data_dir)</label>
              <input v-model="settings.data_dir" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>

            <div>
              <label class="block text-sm text-gray-300 mb-1">缓存目录 (cache_dir)</label>
              <input v-model="settings.cache_dir" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>

            <div>
              <label class="block text-sm text-gray-300 mb-1">结果目录 (results_dir)</label>
              <input v-model="settings.results_dir" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>
          </section>

          <!-- API密钥设置 -->
          <section class="space-y-4">
            <h3 class="text-md font-semibold text-gray-300 border-b border-gray-700 pb-2">API密钥设置</h3>

            <div>
              <label class="block text-sm text-gray-300 mb-1">FinnHub API密钥 (finnhub_api_key)</label>
              <input v-model="settings.finnhub_api_key" type="password" class="w-full bg-[#0f172a] border border-gray-700 rounded p-2" />
            </div>
          </section>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
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
