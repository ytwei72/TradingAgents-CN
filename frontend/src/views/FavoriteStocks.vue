<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">自选股管理</h1>
      <div class="flex items-center gap-3">
        <button
          @click="showAnalysisModal = true"
          class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors font-medium"
          :disabled="!canAnalyze"
        >
          <span class="mr-1">📈</span>
          批量分析
        </button>
        <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-600/20 text-blue-400 border border-blue-600/30">
          <span class="mr-1.5">📊</span>
          总数: {{ totalCount }}
        </span>
        <button
          @click="showBatchImportModal = true"
          class="px-4 py-2 bg-green-700 hover:bg-green-800 text-white text-sm rounded-lg transition-colors font-medium"
        >
          <span class="mr-1">📥</span>
          批量导入
        </button>
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

    <!-- Tabs -->
    <div class="flex items-center justify-between mb-6 border-b border-gray-700">
      <div class="flex items-center gap-2">
        <button
          @click="activeTab = 'all'"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2"
          :class="activeTab === 'all' 
            ? 'text-blue-400 border-blue-400' 
            : 'text-gray-400 border-transparent hover:text-gray-300'"
        >
          全部自选
        </button>
        <button
          v-for="category in categories"
          :key="category"
          @click="activeTab = category"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2"
          :class="activeTab === category 
            ? 'text-blue-400 border-blue-400' 
            : 'text-gray-400 border-transparent hover:text-gray-300'"
        >
          {{ category }}
        </button>
      </div>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <span class="px-2 py-1 text-xs font-semibold rounded bg-orange-600/20 text-orange-400 border border-orange-600/30">行业板块</span>
          <span class="px-2 py-1 text-xs font-semibold rounded bg-green-600/20 text-green-400 border border-green-600/30">概念板块</span>
          <span class="px-2 py-1 text-xs font-semibold rounded bg-blue-600/20 text-blue-400 border border-blue-600/30">自选分类</span>
        </div>
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
    <div v-else-if="displayedStocks.length > 0" class="flex-1 overflow-y-auto pb-20">
      <!-- Card View for "全部自选" -->
      <div v-if="activeTab === 'all'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="stock in displayedStocks"
          :key="stock.stock_code"
          class="bg-[#1e293b] rounded-lg border border-gray-700 overflow-hidden transition-all hover:border-gray-600 p-4 flex flex-col"
        >
          <!-- Card Title -->
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1 flex items-center gap-2 flex-wrap">
              <span class="text-lg font-bold text-white">{{ stock.stock_name || 'N/A' }}（{{ stock.stock_code }}）</span>
              <span
                v-for="sector in (stock.sectors || []).slice(0, 1)"
                :key="sector"
                class="px-2 py-1 text-xs font-semibold rounded bg-orange-600/20 text-orange-400 border border-orange-600/30"
              >
                {{ sector }}
              </span>
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

          <!-- Card Content -->
          <div class="flex-1">
            <!-- First line: Category -->
            <div v-if="stock.category && stock.category !== 'default'" class="mb-2">
              <span class="px-2 py-1 text-xs font-semibold rounded bg-blue-600/20 text-blue-400 border border-blue-600/30">
                {{ stock.category }}
              </span>
            </div>

            <!-- Second and Third lines: Concept themes (max 2 lines) -->
            <div v-if="stock.themes && stock.themes.length > 0" class="mb-3">
              <div class="flex flex-wrap gap-1 concept-themes-container">
                <span
                  v-for="theme in stock.themes"
                  :key="theme"
                  class="px-2 py-1 text-xs font-semibold rounded bg-green-600/20 text-green-400 border border-green-600/30 concept-theme-tag"
                >
                  {{ theme }}
                </span>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="text-xs text-gray-500 mt-3 pt-3 border-t border-gray-700">
            <div>添加时间: {{ formatDate(stock.created_at) }}</div>
            <div v-if="stock.updated_at && stock.updated_at !== stock.created_at">
              更新时间: {{ formatDate(stock.updated_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Card View for Categories (4 columns) -->
      <div v-else class="grid grid-cols-1 gap-4">
        <div
          v-for="stock in displayedStocks"
          :key="stock.stock_code"
          class="bg-[#1e293b] rounded-lg border border-gray-700 overflow-hidden transition-all hover:border-gray-600 p-4"
        >
          <div class="flex items-start gap-4">
            <!-- Column 1: Company Name and Stock Code (Fixed Width) -->
            <div class="flex flex-col flex-shrink-0" style="width: 140px;">
              <div class="text-base font-semibold text-white mb-1">{{ stock.stock_name || 'N/A' }}</div>
              <div class="text-sm text-gray-400">{{ stock.stock_code }}</div>
            </div>

            <!-- Column 2: Latest Historical Data and Concept Themes (Auto Flex) -->
            <div class="flex flex-col gap-2 flex-1 min-w-0">
              <div v-if="stockHistoricalData[stock.stock_code]" class="text-sm">
                <div class="flex gap-4">
                  <!-- Left column: Date (narrow) -->
                  <div class="flex flex-col flex-shrink-0" style="width: 60px;">
                    <div class="text-white font-medium">{{ formatDataMonthDay(stockHistoricalData[stock.stock_code]?.date) }}</div>
                    <div class="text-xs text-gray-500">{{ formatDataYear(stockHistoricalData[stock.stock_code]?.date) }}</div>
                  </div>
                  <!-- Right column: Trading Data (2 rows) -->
                  <div class="flex flex-col gap-1 flex-1 text-gray-300">
                    <!-- First row: 4 fields -->
                    <div class="flex gap-4">
                      <div>开盘: <span class="text-white font-medium">{{ formatPrice(stockHistoricalData[stock.stock_code]?.open) }}</span></div>
                      <div>收盘: <span class="text-white font-medium">{{ formatPrice(stockHistoricalData[stock.stock_code]?.close) }}</span></div>
                      <div>涨跌: <span :class="getPctChangeClass(stockHistoricalData[stock.stock_code]?.pct_change)" class="font-medium">
                        {{ formatPctChange(stockHistoricalData[stock.stock_code]?.pct_change) }}
                      </span></div>
                      <div>涨跌额: <span :class="getPctChangeClass(stockHistoricalData[stock.stock_code]?.pct_change)" class="font-medium">
                        {{ formatPrice(stockHistoricalData[stock.stock_code]?.change_amount) }}
                      </span></div>
                    </div>
                    <!-- Second row: 4 fields -->
                    <div class="flex gap-4 text-xs">
                      <div class="text-gray-500">成交量: {{ formatVolume(stockHistoricalData[stock.stock_code]?.volume) }}</div>
                      <div class="text-gray-500">成交额: {{ formatAmount(stockHistoricalData[stock.stock_code]?.amount) }}</div>
                      <div class="text-gray-500">振幅: {{ formatPctChange(stockHistoricalData[stock.stock_code]?.amplitude) }}</div>
                      <div class="text-gray-500">换手率: {{ formatPctChange(stockHistoricalData[stock.stock_code]?.turnover) }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="text-sm text-gray-500">加载中...</div>
              <div v-if="stock.themes && stock.themes.length > 0" class="flex flex-wrap gap-1">
                <span
                  v-for="theme in stock.themes"
                  :key="theme"
                  class="px-2 py-1 text-xs font-semibold rounded bg-green-600/20 text-green-400 border border-green-600/30 concept-theme-tag"
                >
                  {{ theme }}
                </span>
              </div>
            </div>

            <!-- Column 3: Industry Sectors (Fixed Width) -->
            <div class="flex flex-wrap gap-1 items-start flex-shrink-0" style="width: 120px;">
              <span
                v-for="sector in (stock.sectors || [])"
                :key="sector"
                class="px-2 py-1 text-xs font-semibold rounded bg-orange-600/20 text-orange-400 border border-orange-600/30"
              >
                {{ sector }}
              </span>
            </div>

            <!-- Column 4: Action Buttons (Fixed Width) -->
            <div class="flex items-center gap-2 flex-shrink-0" style="width: 60px;">
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
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex items-center justify-center py-12">
      <div class="text-gray-400">
        {{ activeTab === 'all' ? '暂无自选股记录' : `分类"${activeTab}"中暂无自选股` }}
      </div>
    </div>

    <!-- Analysis Modal -->
    <div
      v-if="showAnalysisModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showAnalysisModal = false"
    >
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6 w-full max-w-4xl">
        <h2 class="text-xl font-bold text-white mb-4">批量分析</h2>

        <form @submit.prevent="startBatchAnalysis">
          <div class="flex gap-6">
            <!-- 左侧：自选股分类 -->
            <div class="flex-[0.5]">
              <label class="block text-sm font-medium text-gray-300 mb-1">选择分类 *</label>
              <div class="space-y-2 max-h-96 overflow-y-auto border border-gray-700 rounded-lg p-2">
                <label
                  v-for="category in availableCategories"
                  :key="category"
                  class="flex items-center space-x-2 cursor-pointer hover:bg-gray-800 p-2 rounded"
                >
                  <input
                    type="checkbox"
                    :value="category"
                    v-model="analysisForm.selectedCategories"
                    class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <span class="text-white text-sm">{{ category }}</span>
                  <span class="text-gray-400 text-xs">({{ getCategoryStockCount(category) }}只)</span>
                </label>
              </div>
            </div>

            <!-- 右侧：分析参数 -->
            <div class="flex-1 space-y-4">
              <div>
                <DateRangePicker
                  :quick-days="[]"
                  label="分析日期"
                  singleMode="start"
                  v-model:modelStartDate="analysisForm.analysis_date"
                  v-model:modelEndDate="analysisEndDate"
                  v-model:modelDays="analysisDays"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-300 mb-1">研究深度</label>
                <select
                  v-model="analysisForm.research_depth"
                  class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option :value="1">1 - 浅度</option>
                  <option :value="2">2 - 轻度</option>
                  <option :value="3">3 - 中度</option>
                  <option :value="4">4 - 深度</option>
                  <option :value="5">5 - 极深</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-300 mb-1">分析师 *</label>
                <div class="grid grid-cols-2 gap-2 border border-gray-700 rounded-lg p-2">
                  <label
                    v-for="analyst in analystOptions"
                    :key="analyst.value"
                    class="flex items-center space-x-2 cursor-pointer hover:bg-gray-800 p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      :value="analyst.value"
                      v-model="analysisForm.analysts"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                    />
                    <span class="text-white text-sm">{{ analyst.label }}</span>
                  </label>
                </div>
              </div>

              <div>
                <label class="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    v-model="analysisForm.include_sentiment"
                    class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <span class="text-white text-sm">包含情感分析</span>
                </label>
              </div>

              <div>
                <label class="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    v-model="analysisForm.include_risk_assessment"
                    class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <span class="text-white text-sm">包含风险评估</span>
                </label>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 mt-6">
            <button
              type="button"
              @click="showAnalysisModal = false"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="analyzing || analysisForm.selectedCategories.length === 0 || analysisForm.analysts.length === 0"
              class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ analyzing ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </form>
      </div>
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
              <label class="block text-sm font-medium text-gray-300 mb-1">概念板块（Theme，用逗号分隔）</label>
              <input
                v-model="themesInput"
                type="text"
                class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="例如: 人工智能,新能源,5G"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-300 mb-1">行业板块（Sector，用逗号分隔）</label>
              <input
                v-model="sectorsInput"
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

    <!-- Batch Import Modal -->
    <div
      v-if="showBatchImportModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="closeBatchImportModal"
    >
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6 w-full max-w-6xl max-h-[96vh] overflow-y-auto">
        <h2 class="text-xl font-bold text-white mb-4">批量导入自选股</h2>

        <form @submit.prevent="handleBatchImport">
          <div class="grid grid-cols-2 gap-6 mb-6">
            <!-- 左侧：板块选择 -->
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">行业板块</label>
                <div class="max-h-48 overflow-y-auto border border-gray-700 rounded-lg p-2">
                  <label
                    v-for="industry in industryList"
                    :key="`industry-${industry.name}`"
                    class="flex items-center space-x-2 cursor-pointer hover:bg-gray-800 p-2 rounded"
                  >
                    <input
                      type="radio"
                      :value="`industry-${industry.name}`"
                      v-model="batchImportForm.selectedSector"
                      @change="onSectorChange('industry', industry.name)"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500"
                    />
                    <span class="text-white text-sm">{{ industry.name }}</span>
                    <span class="text-gray-400 text-xs">({{ industry.stocks?.length || 0 }}只)</span>
                  </label>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">概念板块</label>
                <div class="max-h-48 overflow-y-auto border border-gray-700 rounded-lg p-2">
                  <label
                    v-for="concept in conceptList"
                    :key="`concept-${concept.name}`"
                    class="flex items-center space-x-2 cursor-pointer hover:bg-gray-800 p-2 rounded"
                  >
                    <input
                      type="radio"
                      :value="`concept-${concept.name}`"
                      v-model="batchImportForm.selectedSector"
                      @change="onSectorChange('concept', concept.name)"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500"
                    />
                    <span class="text-white text-sm">{{ concept.name }}</span>
                    <span class="text-gray-400 text-xs">({{ concept.stocks?.length || 0 }}只)</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- 右侧：股票列表和分类名称 -->
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-1">分类名称 *</label>
                <input
                  v-model="batchImportForm.category"
                  type="text"
                  required
                  class="w-full px-3 py-2 bg-[#0f172a] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder="例如: 银行板块"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">
                  股票列表 (已选择 {{ selectedStocks.length }} 只)
                  <button
                    type="button"
                    @click="selectAllStocks"
                    class="ml-2 text-xs text-blue-400 hover:text-blue-300"
                  >
                    全选
                  </button>
                  <button
                    type="button"
                    @click="clearAllStocks"
                    class="ml-2 text-xs text-red-400 hover:text-red-300"
                  >
                    清空
                  </button>
                </label>
                <div class="max-h-96 overflow-y-auto border border-gray-700 rounded-lg p-2">
                  <label
                    v-for="stock in availableStocks"
                    :key="stock.code"
                    class="flex items-center space-x-2 cursor-pointer hover:bg-gray-800 p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      :value="stock.code"
                      v-model="selectedStocks"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                    />
                    <span class="text-white text-sm">{{ stock.code }}</span>
                    <span class="text-gray-400 text-sm">{{ stock.name }}</span>
                  </label>
                  <div v-if="availableStocks.length === 0" class="text-gray-400 text-sm p-4 text-center">
                    请先选择一个板块
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 mt-6">
            <button
              type="button"
              @click="closeBatchImportModal"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="batchImporting || selectedStocks.length === 0 || !batchImportForm.category"
              class="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ batchImporting ? '导入中...' : '确认导入' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import {
  getFavoriteStocks,
  createFavoriteStock,
  updateFavoriteStock,
  deleteFavoriteStock,
  getFavoriteStocksStatistics,
  startBatchAnalysisSameParams,
  batchCreateFavoriteStocks,
  getConceptList,
  getIndustryList,
  getStocksByConcept,
  getStocksByIndustry,
  getStockHistoricalData,
  type FavoriteStock,
  type StockHistoricalData
} from '../api'
import DateRangePicker from '../components/DateRangePicker.vue'

const loading = ref(false)
const saving = ref(false)
const analyzing = ref(false)
const error = ref('')
const favoriteStocks = ref<FavoriteStock[]>([])
const totalCount = ref(0)
const stockHistoricalData = ref<Record<string, StockHistoricalData | null>>({})

const showAddModal = ref(false)
const showEditModal = ref(false)
const showAnalysisModal = ref(false)
const showBatchImportModal = ref(false)
const stockToDelete = ref<FavoriteStock | null>(null)

const activeTab = ref('all')
const categories = ref<string[]>([])
const tags = ref<string[]>([])

const analystOptions = [
  { value: 'market', label: '市场分析师' },
  { value: 'fundamentals', label: '基本面分析师' },
  { value: 'news', label: '新闻分析师' },
  { value: 'social', label: '社交媒体分析师' },
]

const analysisForm = reactive({
  selectedCategories: [] as string[],
  analysis_date: new Date().toISOString().split('T')[0],
  research_depth: 3,
  analysts: ['market', 'fundamentals', 'news'] as string[],
  include_sentiment: true,
  include_risk_assessment: true
})

// DateRangePicker 需要两个日期，但我们只使用 analysis_date
const analysisEndDate = ref(new Date().toISOString().split('T')[0])
const analysisDays = ref<number | null>(null)

const formData = reactive({
  stock_code: '',
  stock_name: '',
  category: 'default',
  tags: [] as string[],
  themes: [] as string[],
  sectors: [] as string[],
  notes: '无'
})

const tagsInput = ref('')
const themesInput = ref('')
const sectorsInput = ref('')

// Batch import related
const industryList = ref<Array<{ name: string; stocks?: Array<{ code: string; name: string }> }>>([])
const conceptList = ref<Array<{ name: string; stocks?: Array<{ code: string; name: string }> }>>([])
const availableStocks = ref<Array<{ code: string; name: string }>>([])
const selectedStocks = ref<string[]>([])
const batchImporting = ref(false)
const batchImportForm = reactive({
  selectedSector: '',
  sectorType: '' as 'industry' | 'concept' | '',
  category: ''
})

// 计算属性：根据activeTab过滤显示的股票
const displayedStocks = computed(() => {
  if (activeTab.value === 'all') {
    return favoriteStocks.value
  }
  return favoriteStocks.value.filter(stock => stock.category === activeTab.value)
})

// 计算属性：可用的分类列表（包括"全部自选"）
const availableCategories = computed(() => {
  return categories.value.filter(cat => cat !== 'default')
})

// 计算属性：是否可以进行分析（至少有一个分类有股票）
const canAnalyze = computed(() => {
  return availableCategories.value.some(cat => {
    return favoriteStocks.value.some(stock => stock.category === cat)
  })
})

// 获取分类中的股票数量
const getCategoryStockCount = (category: string) => {
  return favoriteStocks.value.filter(stock => stock.category === category).length
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

const formatDataMonthDay = (dateStr?: string) => {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}月${day}日`
  } catch {
    return 'N/A'
  }
}

const formatDataYear = (dateStr?: string) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    return `${year}年`
  } catch {
    return ''
  }
}

const formatVolume = (volume?: number) => {
  if (!volume && volume !== 0) return 'N/A'
  if (volume >= 100000000) {
    return (volume / 100000000).toFixed(2) + '亿'
  } else if (volume >= 10000) {
    return (volume / 10000).toFixed(2) + '万'
  }
  return volume.toString()
}

const formatAmount = (amount?: number) => {
  if (!amount && amount !== 0) return 'N/A'
  if (amount >= 100000000) {
    return (amount / 100000000).toFixed(2) + '亿'
  } else if (amount >= 10000) {
    return (amount / 10000).toFixed(2) + '万'
  }
  return amount.toFixed(2)
}

const formatPrice = (price?: number) => {
  if (!price && price !== 0) return 'N/A'
  return price.toFixed(2)
}

const formatPctChange = (pctChange?: number) => {
  if (!pctChange && pctChange !== 0) return 'N/A'
  const sign = pctChange > 0 ? '+' : ''
  return `${sign}${pctChange.toFixed(2)}%`
}

const getPctChangeClass = (pctChange?: number) => {
  if (!pctChange && pctChange !== 0) return 'text-gray-400'
  return pctChange >= 0 ? 'text-red-400' : 'text-green-400'
}

const loadStockHistoricalData = async (stockCode: string) => {
  try {
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - 30) // 获取最近30天的数据
    
    const response = await getStockHistoricalData(
      stockCode,
      startDate.toISOString().split('T')[0],
      endDate.toISOString().split('T')[0],
      30
    )
    
    if (response.success && response.data && response.data.length > 0) {
      // 获取最新的数据（按日期排序，取最后一个）
      const sortedData = response.data.sort((a, b) => {
        const dateA = new Date(a.date).getTime()
        const dateB = new Date(b.date).getTime()
        return dateA - dateB
      })
      stockHistoricalData.value[stockCode] = sortedData[sortedData.length - 1]
    } else {
      stockHistoricalData.value[stockCode] = null
    }
  } catch (e) {
    console.error(`加载股票 ${stockCode} 的历史数据失败:`, e)
    stockHistoricalData.value[stockCode] = null
  }
}

const loadStocksHistoricalData = async () => {
  const stocksToLoad = displayedStocks.value
  // 并行加载所有股票的历史数据
  await Promise.all(
    stocksToLoad.map(stock => 
      stock.stock_code ? loadStockHistoricalData(stock.stock_code) : Promise.resolve()
    )
  )
}

const loadFavoriteStocks = async () => {
  loading.value = true
  error.value = ''

  try {
    const params: any = {
      limit: 1000,
      skip: 0
    }

    const response = await getFavoriteStocks(params)
    if (response.success && response.data) {
      favoriteStocks.value = response.data
      totalCount.value = response.total || response.data.length
      // 加载完股票后，更新分类列表
      await loadStatistics()
      
      // 如果当前不在"全部自选"tab，加载历史数据
      if (activeTab.value !== 'all') {
        await loadStocksHistoricalData()
      }
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
      const categoryKeys = Object.keys(response.data.category_stats || {})
      // 确保包含所有实际存在的分类（从股票数据中提取）
      const allCategories = new Set<string>()
      favoriteStocks.value.forEach(stock => {
        if (stock.category && stock.category !== 'default') {
          allCategories.add(stock.category)
        }
      })
      // 合并统计中的分类和实际数据中的分类
      categoryKeys.forEach(cat => allCategories.add(cat))
      categories.value = Array.from(allCategories)
      tags.value = Object.keys(response.data.tag_stats || {})
    } else {
      // 如果统计接口失败，从股票数据中提取分类
      const allCategories = new Set<string>()
      favoriteStocks.value.forEach(stock => {
        if (stock.category && stock.category !== 'default') {
          allCategories.add(stock.category)
        }
      })
      categories.value = Array.from(allCategories)
    }
  } catch (e) {
    console.error('加载统计信息失败:', e)
    // 如果统计接口失败，从股票数据中提取分类
    const allCategories = new Set<string>()
    favoriteStocks.value.forEach(stock => {
      if (stock.category && stock.category !== 'default') {
        allCategories.add(stock.category)
      }
    })
    categories.value = Array.from(allCategories)
  }
}

const openEditModal = (stock: FavoriteStock) => {
  formData.stock_code = stock.stock_code || ''
  formData.stock_name = stock.stock_name || ''
  formData.category = stock.category || 'default'
  formData.tags = stock.tags || []
  formData.themes = stock.themes || []
  formData.sectors = stock.sectors || []
  formData.notes = stock.notes || '无'
  tagsInput.value = (stock.tags || []).join(',')
  themesInput.value = (stock.themes || []).join(',')
  sectorsInput.value = (stock.sectors || []).join(',')
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
  formData.themes = []
  formData.sectors = []
  formData.notes = '无'
  tagsInput.value = ''
  themesInput.value = ''
  sectorsInput.value = ''
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

    // 处理概念板块（Theme）
    const themes = themesInput.value
      .split(',')
      .map(theme => theme.trim())
      .filter(theme => theme.length > 0)

    // 处理行业板块（Sector）
    const sectors = sectorsInput.value
      .split(',')
      .map(sector => sector.trim())
      .filter(sector => sector.length > 0)

    const stockData: any = {
      stock_code: formData.stock_code,
      stock_name: formData.stock_name || undefined,
      category: formData.category || 'default',
      tags: tags,
      themes: themes,
      sectors: sectors,
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
      const response = await updateFavoriteStock(
        formData.stock_code,
        stockData,
        undefined,
        formData.category
      )
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
    const response = await deleteFavoriteStock(
      stockToDelete.value.stock_code,
      undefined,
      stockToDelete.value.category
    )
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

const startBatchAnalysis = async () => {
  if (analysisForm.selectedCategories.length === 0 || analysisForm.analysts.length === 0) {
    error.value = '请至少选择一个分类和分析师'
    return
  }

  analyzing.value = true
  error.value = ''

  try {
    // 收集所有选中分类的股票代码，去重
    const stockCodesSet = new Set<string>()
    analysisForm.selectedCategories.forEach(category => {
      favoriteStocks.value
        .filter(stock => stock.category === category)
        .forEach(stock => {
          if (stock.stock_code) {
            stockCodesSet.add(stock.stock_code)
          }
        })
    })

    const stockSymbols = Array.from(stockCodesSet)

    if (stockSymbols.length === 0) {
      error.value = '选中的分类中没有股票'
      analyzing.value = false
      return
    }

    // 调用批量分析接口
    const response = await startBatchAnalysisSameParams({
      stock_symbols: stockSymbols,
      market_type: 'A股',
      analysis_date: analysisForm.analysis_date || undefined,
      analysts: analysisForm.analysts,
      research_depth: analysisForm.research_depth,
      include_sentiment: analysisForm.include_sentiment,
      include_risk_assessment: analysisForm.include_risk_assessment
    })

    // 显示成功消息
    alert(`批量分析已启动！\n总计: ${response.total}只股票\n成功: ${response.success_count}只\n失败: ${response.failed_count}只`)
    
    // 关闭弹窗
    showAnalysisModal.value = false
    
    // 重置表单
    analysisForm.selectedCategories = []
    analysisForm.analysts = ['market', 'fundamentals', 'news']
    analysisForm.research_depth = 3
    analysisForm.include_sentiment = true
    analysisForm.include_risk_assessment = true
  } catch (e: any) {
    error.value = e.message || '批量分析启动失败'
  } finally {
    analyzing.value = false
  }
}

const loadSectorLists = async () => {
  try {
    const [industryRes, conceptRes] = await Promise.all([
      getIndustryList(),
      getConceptList()
    ])
    
    if (industryRes.success && industryRes.data) {
      industryList.value = industryRes.data.map(item => ({
        name: item.name,
        stocks: item.stocks || []
      }))
    }
    
    if (conceptRes.success && conceptRes.data) {
      conceptList.value = conceptRes.data.map(item => ({
        name: item.name,
        stocks: item.stocks || []
      }))
    }
  } catch (e) {
    console.error('加载板块列表失败:', e)
    error.value = '加载板块列表失败'
  }
}

const onSectorChange = async (type: 'industry' | 'concept', sectorName: string) => {
  batchImportForm.sectorType = type
  batchImportForm.selectedSector = `${type}-${sectorName}`
  batchImportForm.category = sectorName // 默认填入板块名称
  
  selectedStocks.value = []
  availableStocks.value = []
  
  try {
    let stocks: Array<{ code: string; name: string }> = []
    
    if (type === 'industry') {
      const response = await getStocksByIndustry([sectorName])
      if (response.success && response.data && response.data[sectorName]) {
        stocks = response.data[sectorName]
      }
    } else {
      const response = await getStocksByConcept([sectorName])
      if (response.success && response.data && response.data[sectorName]) {
        stocks = response.data[sectorName]
      }
    }
    
    availableStocks.value = stocks
  } catch (e) {
    console.error('加载板块股票列表失败:', e)
    error.value = '加载板块股票列表失败'
  }
}

const selectAllStocks = () => {
  selectedStocks.value = availableStocks.value.map(stock => stock.code)
}

const clearAllStocks = () => {
  selectedStocks.value = []
}

const closeBatchImportModal = () => {
  showBatchImportModal.value = false
  batchImportForm.selectedSector = ''
  batchImportForm.sectorType = ''
  batchImportForm.category = ''
  selectedStocks.value = []
  availableStocks.value = []
}

const handleBatchImport = async () => {
  if (selectedStocks.value.length === 0) {
    error.value = '请至少选择一只股票'
    return
  }
  
  if (!batchImportForm.category) {
    error.value = '请输入分类名称'
    return
  }
  
  batchImporting.value = true
  error.value = ''
  
  try {
    const response = await batchCreateFavoriteStocks({
      stock_codes: selectedStocks.value,
      category: batchImportForm.category,
      user_id: 'guest'
    })
    
    if (response.success) {
      alert(`批量导入完成！\n总计: ${response.data?.total || 0}只\n成功: ${response.data?.success_count || 0}只\n失败: ${response.data?.failed_count || 0}只`)
      
      // 关闭弹窗
      closeBatchImportModal()
      
      // 重新加载自选股列表
      await loadFavoriteStocks()
    } else {
      error.value = response.message || '批量导入失败'
    }
  } catch (e: any) {
    error.value = e.message || '批量导入失败'
  } finally {
    batchImporting.value = false
  }
}

// 监听activeTab变化，切换分类时加载历史数据
watch(activeTab, async (newTab) => {
  if (newTab !== 'all' && favoriteStocks.value.length > 0) {
    await loadStocksHistoricalData()
  }
})

onMounted(() => {
  loadFavoriteStocks()
  loadSectorLists()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.concept-themes-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  max-height: 3.5rem;
  overflow: hidden;
}

.concept-theme-tag {
  white-space: nowrap;
  display: inline-block;
  flex-shrink: 0;
}
</style>

