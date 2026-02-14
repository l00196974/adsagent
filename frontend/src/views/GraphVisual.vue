<template>
  <div class="graph-visual">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识图谱可视化</span>
          <div class="header-actions">
            <el-button-group>
              <el-button @click="loadGraphData" :loading="loading">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
              <el-button @click="resetView">
                <el-icon><View /></el-icon> 重置
              </el-button>
            </el-button-group>
          </div>
        </div>
      </template>
      
      <el-row :gutter="20">
        <!-- 左侧控制面板 -->
        <el-col :span="5">
          <el-card shadow="never" class="control-panel">
            <template #header>统计信息</template>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="实体数量">
                {{ entityCount }}
              </el-descriptions-item>
              <el-descriptions-item label="关系数量">
                {{ relationCount }}
              </el-descriptions-item>
              <el-descriptions-item label="用户数量">
                {{ userCount }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
          
          <el-card shadow="never" style="margin-top: 16px">
            <template #header>图例</template>
            <div class="legend">
              <div class="legend-item">
                <span class="dot item"></span> 商品
              </div>
              <div class="legend-item">
                <span class="dot poi"></span> POI
              </div>
              <div class="legend-item">
                <span class="dot app"></span> APP
              </div>
              <div class="legend-item">
                <span class="dot user"></span> 用户
              </div>
            </div>
          </el-card>
          
          <!-- 搜索功能 -->
          <el-card shadow="never" style="margin-top: 16px">
            <template #header>
              <span>搜索实体</span>
            </template>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索商品/POI/APP..."
              clearable
              @keyup.enter="handleSearch"
              size="small"
            >
              <template #append>
                <el-button @click="handleSearch" :loading="searching">
                  <el-icon><Search /></el-icon>
                </el-button>
              </template>
            </el-input>

            <el-select
              v-model="searchType"
              placeholder="筛选类型"
              clearable
              size="small"
              style="margin-top: 8px; width: 100%"
            >
              <el-option label="商品" value="Item" />
              <el-option label="POI" value="POI" />
              <el-option label="APP" value="APP" />
              <el-option label="用户" value="User" />
            </el-select>
            
            <div v-if="searchResults.length > 0" class="search-results">
              <div 
                v-for="entity in searchResults" 
                :key="entity.id"
                class="search-result-item"
                @click="handleEntityClick(entity)"
              >
                <el-tag size="small" :type="getEntityTagType(entity.type)">
                  {{ entity.type }}
                </el-tag>
                <span>{{ entity.properties?.name || entity.id }}</span>
              </div>
            </div>
          </el-card>
          
          <!-- AI查询 -->
          <el-card shadow="never" style="margin-top: 16px">
            <template #header>
              <span>AI智能查询</span>
            </template>
            <el-input
              v-model="aiQuestion"
              type="textarea"
              :rows="3"
              placeholder="例如：喜欢打高尔夫的用户偏好什么品牌？"
              size="small"
            />
            <el-button 
              type="primary" 
              size="small"
              @click="handleAIQuery"
              :loading="aiQuerying"
              :disabled="!aiQuestion.trim()"
              style="margin-top: 8px; width: 100%"
            >
              <el-icon><ChatDotRound /></el-icon> AI查询
            </el-button>
            <div v-if="aiQueryResult" class="ai-result">
              <el-input
                type="textarea"
                :rows="4"
                v-model="aiQueryResult"
                readonly
                size="small"
                style="margin-top: 8px"
              />
            </div>
          </el-card>
        </el-col>
        
        <!-- 图谱可视化区域 -->
        <el-col :span="19">
          <div class="graph-container" ref="graphContainer">
            <div v-if="loading" class="loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              加载中...
            </div>
            <svg ref="svgRef" width="100%" height="600"></svg>
          </div>

          <!-- 节点和边详情展示区域 -->
          <el-row :gutter="20" style="margin-top: 20px">
            <!-- 节点详情 -->
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>节点详情</span>
                </template>
                <div v-if="selectedEntity" class="entity-details">
                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="ID">
                      {{ selectedEntity.id }}
                    </el-descriptions-item>
                    <el-descriptions-item label="类型">
                      <el-tag :type="getEntityTagType(selectedEntity.type)" size="small">
                        {{ selectedEntity.type }}
                      </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="名称">
                      {{ selectedEntity.properties?.name || selectedEntity.properties?.poi_name || selectedEntity.properties?.app_name || selectedEntity.id }}
                    </el-descriptions-item>
                    <el-descriptions-item
                      v-for="(value, key) in selectedEntity.properties"
                      :key="key"
                      :label="key"
                    >
                      {{ formatPropertyValue(value) }}
                    </el-descriptions-item>
                  </el-descriptions>
                  <el-button
                    type="primary"
                    size="small"
                    @click="handleExpand"
                    :loading="expanding"
                    style="margin-top: 8px; width: 100%"
                  >
                    <el-icon><Connection /></el-icon> 扩展关系
                  </el-button>
                  <el-slider
                    v-model="expandDepth"
                    :min="1"
                    :max="3"
                    :marks="{1: '1层', 2: '2层', 3: '3层'}"
                    size="small"
                    style="margin-top: 8px"
                  />
                </div>
                <el-empty v-else description="点击图谱中的节点查看详情" :image-size="60" />
              </el-card>
            </el-col>

            <!-- 边详情 -->
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>关系详情</span>
                </template>
                <div v-if="selectedEdge" class="edge-details">
                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="关系类型">
                      <el-tag type="success" size="small">
                        {{ selectedEdge.type }}
                      </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="起点">
                      {{ selectedEdge.from }}
                    </el-descriptions-item>
                    <el-descriptions-item label="终点">
                      {{ selectedEdge.to }}
                    </el-descriptions-item>
                    <el-descriptions-item
                      v-for="(value, key) in selectedEdge.properties"
                      :key="key"
                      :label="key"
                    >
                      {{ formatPropertyValue(value) }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
                <el-empty v-else description="点击图谱中的边查看详情" :image-size="60" />
              </el-card>
            </el-col>
          </el-row>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Refresh, View, Search, Connection, ChatDotRound } from '@element-plus/icons-vue'
import * as d3 from 'd3'
import {
  queryGraph,
  searchEntities,
  expandEntity,
  aiGraphQuery,
  getEntityTypes
} from '../api'

const svgRef = ref(null)
const graphContainer = ref(null)
const loading = ref(false)
const searching = ref(false)
const expanding = ref(false)
const aiQuerying = ref(false)

const graphData = ref({ entities: [], relations: [] })
const displayData = ref({ entities: [], relations: [] })
const searchResults = ref([])
const searchKeyword = ref('')
const searchType = ref('')
const selectedEntity = ref(null)
const selectedEdge = ref(null)
const expandDepth = ref(2)
const aiQuestion = ref('')
const aiQueryResult = ref('')
const entityTypes = ref([])

// 格式化属性值
const formatPropertyValue = (value) => {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

const entityCount = computed(() => displayData.value.entities?.length || 0)
const relationCount = computed(() => displayData.value.relations?.length || 0)
const userCount = computed(() => {
  return displayData.value.entities?.filter(e => e.type === 'User').length || 0
})

const loadGraphData = async () => {
  loading.value = true
  try {
    console.log('开始加载图谱数据...')
    const res = await queryGraph()
    console.log('图谱数据加载成功:', res)

    if (!res || !res.data) {
      console.error('API返回数据格式错误:', res)
      ElMessage.error('加载图谱数据失败: 数据格式错误')
      return
    }

    graphData.value = res.data
    displayData.value = {
      entities: res.data.entities?.slice(0, 100) || [],
      relations: res.data.relations?.slice(0, 200) || []
    }

    console.log(`图谱数据已加载: ${displayData.value.entities.length} 个实体, ${displayData.value.relations.length} 个关系`)
    renderGraph()
  } catch (e) {
    console.error('加载图谱数据失败:', e)
    ElMessage.error('加载图谱数据失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    searchResults.value = []
    return
  }
  
  searching.value = true
  try {
    const res = await searchEntities(
      searchKeyword.value,
      searchType.value || null,
      20
    )
    searchResults.value = res.data || []
  } catch (e) {
    console.error('搜索失败', e)
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

const handleEntityClick = (entity) => {
  selectedEntity.value = entity
  renderGraph(entity.id)
}

const handleExpand = async () => {
  if (!selectedEntity.value) return
  
  expanding.value = true
  try {
    const res = await expandEntity(
      selectedEntity.value.id,
      expandDepth.value,
      50
    )
    
    if (res.code === 0 && res.data) {
      const newEntities = res.data.entities || []
      const newRelations = res.data.relations || []
      
      const existingEntityIds = new Set(displayData.value.entities.map(e => e.id))
      const existingRelationIds = new Set(
        displayData.value.relations.map(r => `${r.from}-${r.to}`)
      )
      
      const filteredEntities = newEntities.filter(e => !existingEntityIds.has(e.id))
      const filteredRelations = newRelations.filter(
        r => !existingRelationIds.has(`${r.from}-${r.to}`)
      )
      
      displayData.value = {
        entities: [...displayData.value.entities, ...filteredEntities].slice(0, 150),
        relations: [...displayData.value.relations, ...filteredRelations].slice(0, 300)
      }
      
      renderGraph()
    }
  } catch (e) {
    console.error('扩展失败', e)
  } finally {
    expanding.value = false
  }
}

const handleAIQuery = async () => {
  if (!aiQuestion.value.trim()) return
  
  aiQuerying.value = true
  aiQueryResult.value = ''
  
  try {
    const res = await aiGraphQuery(aiQuestion.value, expandDepth.value, 50)
    
    if (res.code === 0) {
      aiQueryResult.value = res.data?.answer || JSON.stringify(res.data, null, 2)
      
      if (res.data?.entities) {
        displayData.value = {
          entities: res.data.entities,
          relations: res.data.relations || []
        }
        renderGraph()
      }
    } else {
      aiQueryResult.value = '查询失败: ' + (res.message || '未知错误')
    }
  } catch (e) {
    console.error('AI查询失败', e)
    aiQueryResult.value = '查询失败: ' + e.message
  } finally {
    aiQuerying.value = false
  }
}

const renderGraph = (highlightNodeId = null) => {
  if (!svgRef.value) return
  
  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()
  
  const width = graphContainer.value?.clientWidth || 800
  const height = 600
  
  const entities = displayData.value.entities || []
  const relations = displayData.value.relations || []
  
  if (!entities.length) return
  
  const entitySet = new Set(entities.map(e => e.id))
  const relevantRelations = relations.filter(r => 
    entitySet.has(r.from) && entitySet.has(r.to)
  )
  
  const nodes = entities.map(e => ({ 
    id: e.id, 
    ...e,
    isHighlighted: e.id === highlightNodeId
  }))
  const links = relevantRelations.map(r => ({
    source: r.from,
    target: r.to,
    weight: r.weight || 0.5,
    type: r.type || 'RELATED',
    properties: r.properties || {},
    from: r.from,
    to: r.to
  }))
  
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(40))
  
  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .enter().append('line')
    .attr('stroke', '#909399')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', d => Math.max(1, d.weight * 4))

  // Add invisible wider lines for easier clicking
  const linkHitArea = svg.append('g')
    .selectAll('line')
    .data(links)
    .enter().append('line')
    .attr('stroke', 'transparent')
    .attr('stroke-width', 10)  // Wider invisible hit area
    .attr('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()  // Prevent event bubbling
      selectedEdge.value = d
      selectedEntity.value = null
      console.log('Edge clicked:', d)
    })
  
  const linkLabels = svg.append('g')
    .selectAll('text')
    .data(links)
    .enter().append('text')
    .text(d => d.type || '')
    .attr('font-size', 8)
    .attr('fill', '#909399')
    .attr('text-anchor', 'middle')
  
  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter().append('circle')
    .attr('r', d => getNodeSize(d.type))
    .attr('fill', d => getNodeColor(d.type))
    .attr('stroke', d => d.isHighlighted ? '#F56C6C' : '#fff')
    .attr('stroke-width', d => d.isHighlighted ? 4 : 2)
    .attr('cursor', 'pointer')
    .on('click', (event, d) => {
      selectedEntity.value = d
      selectedEdge.value = null  // Clear edge selection when clicking node
      renderGraph(d.id)
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
  
  const labels = svg.append('g')
    .selectAll('text')
    .data(nodes)
    .enter().append('text')
    .text(d => d.properties?.name || d.id.split(':')[1] || d.id)
    .attr('font-size', d => getNodeSize(d.type) / 2 + 4)
    .attr('dx', d => getNodeSize(d.type) + 4)
    .attr('dy', 4)
    .attr('fill', '#333')
    .attr('pointer-events', 'none')
  
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    linkHitArea
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    linkLabels
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2)

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    labels
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })
  
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  }
  
  function dragged(event) {
    event.subject.fx = event.x
    event.subject.fy = event.y
  }
  
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  }
}

const getNodeSize = (type) => {
  const map = {
    'Event': 15,    // 事件节点中等大小
    'Item': 25,
    'POI': 20,
    'APP': 18,
    'User': 10
  }
  return map[type] || 12
}

const getNodeColor = (type) => {
  const map = {
    'Event': '#F56C6C',   // 事件节点用红色
    'Item': '#E6A23C',
    'POI': '#67C23A',
    'APP': '#909399',
    'User': '#409EFF'
  }
  return map[type] || '#409EFF'
}

const getEntityTagType = (type) => {
  const map = {
    'Event': 'danger',    // 事件节点用danger标签
    'Item': 'warning',
    'POI': 'success',
    'APP': 'info',
    'User': 'primary'
  }
  return map[type] || 'info'
}

const resetView = () => {
  searchKeyword.value = ''
  searchResults.value = []
  selectedEntity.value = null
  aiQuestion.value = ''
  aiQueryResult.value = ''
  displayData.value = {
    entities: graphData.value.entities?.slice(0, 100) || [],
    relations: graphData.value.relations?.slice(0, 200) || []
  }
  renderGraph()
}

const handleResize = () => renderGraph()

onMounted(() => {
  loadGraphData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.graph-container {
  position: relative;
  min-height: 600px;
  background: #fafafa;
  border-radius: 4px;
}

.loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  z-index: 100;
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.item { background: #E6A23C; }
.dot.poi { background: #67C23A; }
.dot.app { background: #909399; }
.dot.user { background: #409EFF; }

.control-panel {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.search-results {
  margin-top: 12px;
  max-height: 150px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.search-result-item:hover {
  background: #f5f5f5;
}

.selected-entity {
  text-align: center;
}

.ai-result {
  margin-top: 12px;
}
</style>
