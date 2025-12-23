<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">自选股管理</h1>
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-600/20 text-blue-400 border border-blue-600/30">
          <span class="mr-1.5">📊</span>
          总数: {{ totalCount }}
        </span>
        <button
          @click="showAddModal = true"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors font-medium"
        >
          <span class="mr-1">+</span>
          添加自选股
        </button>
        <button
          @click="loadFavoriteStocks"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors font-medium"
          :disabled="loading"
        >
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="mb-6 flex items-center gap-4 flex-wrap">
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-400">分类:</label>
        <select
          v-model="filterCategory"
          @change="loadFavoriteStocks"
          class="px-3 py-1.5 bg-[#1e293b] border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">全部</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-400">标签:</label>
        <select
          v-model="filterTag"
          @change="loadFavoriteStocks"
          class="px-3 py-1.5 bg-[#1e293b] border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">全部</option>
          <option v-for="tag in tags" :key="tag" :value="tag">{{ tag }}</option>
        </select>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-400">搜索:</label>
        <input
          v-model="searchKeyword"
          @input="debouncedSearch"
          type="text"
          placeholder="股票代码/名称"
          class="px-3 py-1.5 bg-[#1e293b] border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 w-48"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && favoriteStocks.length === 0" class="flex items-center justify-center py-12">
      <div class="text-gray-400">加载中...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-400 mb-6">
      {{ error }}
    </div>

    <!-- Stock List -->
    <div v-else-if="favoriteStocks.length > 0" class="flex-1 overflow-y-auto pb-20">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="stock in favoriteStocks"
          :key="stock.stock_code"
          class="bg-[#1e293b] rounded-lg border border-gray-700 overflow-hidden transition-all hover:border-gray-600 p-4"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-lg font-bold text-white">{{ stock.stock_code }}</span>
                <span class="text-sm text-gray-400">{{ stock.stock_name || 'N/A' }}</span>
              </div>
              <div v-if="stock.category && stock.category !== 'default'" class="mb-2">
                <span class="px-2 py-1 text-xs font-semibold rounded bg-blue-600/20 text-blue-400 border border-blue-600/30">
                  {{ stock.category }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-1">
              <button
                @click="openEditModal(stock)"
                class="text-gray-400 hover:text-blue-400 transition-colors p-1"
                title="编辑"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                @click="confirmDelete(stock)"
                class="text-gray-400 hover:text-red-400 transition-colors p-1"
                title="删除"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Tags -->
          <div v-if="stock.tags && stock.tags.length > 0" class="mb-3 flex flex-wrap gap-1">
            <span
              v-for="tag in stock.tags"
              :key="tag"
              class="px-2 py-1 text-xs font-semibold rounded bg-purple-600/20 text-purple-400 border border-purple-600/30"
            >
              {{ tag }}
            </span>
          </div>

          <!-- Concept Plates -->
          <div v-if="stock.concept_plates && stock.concept_plates.length > 0" class="mb-3 flex flex-wrap gap-1">
            <span
              v-for="plate in stock.concept_plates"
              :key="plate"
              class="px-2 py-1 text-xs font-semibold rounded bg-green-600/20 text-green-400 border border-green-600/30"
            >
              概念: {{ plate }}
            </span>
          </div>

          <!-- Industry Plates -->
          <div v-if="stock.industry_plates && stock.industry_plates.length > 0" class="mb-3 flex flex-wrap gap-1">
            <span
              v-for="plate in stock.industry_plates"
              :key="plate"
              class="px-2 py-1 text-xs font-semibold rounded bg-orange-600/20 text-orange-400 border border-orange-600/30"
            >
              行业: {{ plate }}
            </span>
          </div>

          <!-- Notes -->
          <div v-if="stock.notes && stock.notes !== '无'" class="text-sm text-gray-400 mb-2 line-clamp-2">
            {{ stock.notes }}
          </div>

          <!-- Metadata -->
          <div class="text-xs text-gray-500 mt-3 pt-3 border-t border-gray-700">
            <div>添加时间: {{ formatDate(stock.created_at) }}</div>
            <div v-if="stock.updated_at && stock.updated_at !== stock.created_at">
              更新时间: {{ formatDate(stock.updated_at) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex items-center justify-center py-12">
      <div class="text-gray-400">暂无自选股记录</div>
    </div>

    <!-- Add/Edit Modal -->
    <div
      v-if="showAddModal || showEditModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6 w-full max-w-md">
        <h2 class="text-xl font-bold text-white mb-4">
          {{ showAddModal ? '添加自选股' : '编辑自选股' }}
        </h2>

        <form @submit.prevent="saveStock">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">股票代码 *</label>
              <input
                v-model="formData.stock_code"
                type="text"
                required
                :disabled="showEditModal"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 000001"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">股票名称</label>
              <input
                v-model="formData.stock_name"
                type="text"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 平安银行"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">分类</label>
              <input
                v-model="formData.category"
                type="text"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 科技股"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">标签（用逗号分隔）</label>
              <input
                v-model="tagsInput"
                type="text"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 科技,成长,蓝筹"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">概念板块（用逗号分隔）</label>
              <input
                v-model="conceptPlatesInput"
                type="text"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 人工智能,新能源,5G"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">行业板块（用逗号分隔）</label>
              <input
                v-model="industryPlatesInput"
                type="text"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 银行,证券,保险"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">备注</label>
              <textarea
                v-model="formData.notes"
                rows="3"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="备注信息..."
              />
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 mt-6">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="stockToDelete"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="stockToDelete = null"
    >
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6 w-full max-w-md">
        <h2 class="text-xl font-bold text-white mb-4">确认删除</h2>
        <p class="text-gray-300 mb-6">
          确定要删除自选股 <span class="font-semibold">{{ stockToDelete.stock_code }}</span> 吗？
        </p>
        <div class="flex items-center justify-end gap-3">
          <button
            @click="stockToDelete = null"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            @click="deleteStock"
            :disabled="saving"
            class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
          >
            {{ saving ? '删除中...' : '删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import {
  getFavoriteStocks,
  createFavoriteStock,
  updateFavoriteStock,
  deleteFavoriteStock,
  getFavoriteStocksStatistics,
  type FavoriteStock
} from '../api'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const favoriteStocks = ref<FavoriteStock[]>([])
const totalCount = ref(0)

const showAddModal = ref(false)
const showEditModal = ref(false)
const stockToDelete = ref<FavoriteStock | null>(null)

const filterCategory = ref('')
const filterTag = ref('')
const searchKeyword = ref('')

const formData = reactive({
  stock_code: '',
  stock_name: '',
  category: 'default',
  tags: [] as string[],
  concept_plates: [] as string[],
  industry_plates: [] as string[],
  notes: '无'
})

const tagsInput = ref('')
const conceptPlatesInput = ref('')
const industryPlatesInput = ref('')

const categories = ref<string[]>([])
const tags = ref<string[]>([])

// 防抖搜索
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedSearch = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    loadFavoriteStocks()
  }, 500)
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

const loadFavoriteStocks = async () => {
  loading.value = true
  error.value = ''

  try {
    const params: any = {
      limit: 1000,
      skip: 0
    }

    if (filterCategory.value) {
      params.category = filterCategory.value
    }

    if (filterTag.value) {
      params.tag = filterTag.value
    }

    const response = await getFavoriteStocks(params)
    if (response.success && response.data) {
      let stocks = response.data

      // 客户端搜索过滤
      if (searchKeyword.value) {
        const keyword = searchKeyword.value.toLowerCase()
        stocks = stocks.filter(
          (stock: FavoriteStock) =>
            stock.stock_code?.toLowerCase().includes(keyword) ||
            stock.stock_name?.toLowerCase().includes(keyword)
        )
      }

      favoriteStocks.value = stocks
      totalCount.value = response.total || stocks.length
    } else {
      error.value = response.message || '加载失败'
    }
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    const response = await getFavoriteStocksStatistics()
    if (response.success && response.data) {
      // 提取分类和标签列表
      categories.value = Object.keys(response.data.category_stats || {})
      tags.value = Object.keys(response.data.tag_stats || {})
    }
  } catch (e) {
    console.error('加载统计信息失败:', e)
  }
}

const openEditModal = (stock: FavoriteStock) => {
  formData.stock_code = stock.stock_code || ''
  formData.stock_name = stock.stock_name || ''
  formData.category = stock.category || 'default'
  formData.tags = stock.tags || []
  formData.concept_plates = stock.concept_plates || []
  formData.industry_plates = stock.industry_plates || []
  formData.notes = stock.notes || '无'
  tagsInput.value = (stock.tags || []).join(',')
  conceptPlatesInput.value = (stock.concept_plates || []).join(',')
  industryPlatesInput.value = (stock.industry_plates || []).join(',')
  showEditModal.value = true
}

const closeModal = () => {
  showAddModal.value = false
  showEditModal.value = false
  stockToDelete.value = null
  resetForm()
}

const resetForm = () => {
  formData.stock_code = ''
  formData.stock_name = ''
  formData.category = 'default'
  formData.tags = []
  formData.concept_plates = []
  formData.industry_plates = []
  formData.notes = '无'
  tagsInput.value = ''
  conceptPlatesInput.value = ''
  industryPlatesInput.value = ''
}

const saveStock = async () => {
  saving.value = true
  error.value = ''

  try {
    // 处理标签
    const tags = tagsInput.value
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)

    // 处理概念板块
    const conceptPlates = conceptPlatesInput.value
      .split(',')
      .map(plate => plate.trim())
      .filter(plate => plate.length > 0)

    // 处理行业板块
    const industryPlates = industryPlatesInput.value
      .split(',')
      .map(plate => plate.trim())
      .filter(plate => plate.length > 0)

    const stockData: any = {
      stock_code: formData.stock_code,
      stock_name: formData.stock_name || undefined,
      category: formData.category || 'default',
      tags: tags,
      concept_plates: conceptPlates,
      industry_plates: industryPlates,
      notes: formData.notes || '无'
    }

    if (showAddModal.value) {
      const response = await createFavoriteStock(stockData)
      if (response.success) {
        closeModal()
        await loadFavoriteStocks()
        await loadStatistics()
      } else {
        error.value = response.message || '创建失败'
      }
    } else {
      const response = await updateFavoriteStock(formData.stock_code, stockData)
      if (response.success) {
        closeModal()
        await loadFavoriteStocks()
        await loadStatistics()
      } else {
        error.value = response.message || '更新失败'
      }
    }
  } catch (e: any) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

const confirmDelete = (stock: FavoriteStock) => {
  stockToDelete.value = stock
}

const deleteStock = async () => {
  if (!stockToDelete.value) return

  saving.value = true
  error.value = ''

  try {
    const response = await deleteFavoriteStock(stockToDelete.value.stock_code)
    if (response.success) {
      stockToDelete.value = null
      await loadFavoriteStocks()
      await loadStatistics()
    } else {
      error.value = response.message || '删除失败'
    }
  } catch (e: any) {
    error.value = e.message || '删除失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadFavoriteStocks()
  loadStatistics()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

