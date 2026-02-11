<template>
  <div class="graph-visual">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识图谱可视化</span>
          <div>
            <el-button @click="loadGraphData">刷新</el-button>
          </div>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="never">
            <template #header>统计信息</template>
            <el-descriptions :column="1" border>
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
          
          <el-card shadow="never" style="margin-top: 20px">
            <template #header>图例</template>
            <div class="legend">
              <div class="legend-item">
                <span class="dot brand"></span> 品牌
              </div>
              <div class="legend-item">
                <span class="dot model"></span> 车型
              </div>
              <div class="legend-item">
                <span class="dot interest"></span> 兴趣
              </div>
              <div class="legend-item">
                <span class="dot user"></span> 用户
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="18">
          <div class="graph-container" ref="graphContainer">
            <div v-if="loading" class="loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              加载中...
            </div>
            <svg ref="svgRef" width="100%" height="500"></svg>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import * as d3 from 'd3'
import { queryGraph, getBrandCorrelation } from '../api'

const svgRef = ref(null)
const graphContainer = ref(null)
const loading = ref(false)
const graphData = ref({ entities: [], relations: [] })

const entityCount = computed(() => graphData.value.entities?.length || 0)
const relationCount = computed(() => graphData.value.relations?.length || 0)
const userCount = computed(() => {
  return graphData.value.entities?.filter(e => e.type === 'User').length || 0
})

const loadGraphData = async () => {
  loading.value = true
  try {
    const res = await queryGraph()
    graphData.value = res.data
    renderGraph()
  } catch (e) {
    console.error('加载图谱数据失败', e)
  } finally {
    loading.value = false
  }
}

const renderGraph = () => {
  if (!svgRef.value || !graphData.value.entities.length) return
  
  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()
  
  const width = svgRef.value.clientWidth || 800
  const height = 500
  
  const entities = graphData.value.entities.slice(0, 50)
  const relations = graphData.value.relations.slice(0, 100)
  
  const entitySet = new Set(entities.map(e => e.id))
  const relevantRelations = relations.filter(r => 
    entitySet.has(r.from) && entitySet.has(r.to)
  )
  
  const nodes = entities.map(e => ({ id: e.id, ...e }))
  const links = relevantRelations.map(r => ({ source: r.from, target: r.to, weight: r.weight || 0.5 }))
  
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(30))
  
  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .enter().append('line')
    .attr('stroke', '#999')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', d => d.weight * 3)
  
  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter().append('circle')
    .attr('r', d => {
      const type = d.type || 'User'
      if (type === 'Brand') return 20
      if (type === 'Model') return 18
      if (type === 'Interest') return 15
      return 8
    })
    .attr('fill', d => {
      const type = d.type || 'User'
      if (type === 'Brand') return '#E6A23C'
      if (type === 'Model') return '#67C23A'
      if (type === 'Interest') return '#909399'
      return '#409EFF'
    })
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
  
  const labels = svg.append('g')
    .selectAll('text')
    .data(nodes)
    .enter().append('text')
    .text(d => d.properties?.name || d.id)
    .attr('font-size', 10)
    .attr('dx', 12)
    .attr('dy', 4)
    .attr('fill', '#333')
  
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
    
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

onMounted(() => {
  loadGraphData()
  window.addEventListener('resize', () => renderGraph())
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.graph-container {
  position: relative;
  min-height: 500px;
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
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.brand { background: #E6A23C; }
.dot.model { background: #67C23A; }
.dot.interest { background: #909399; }
.dot.user { background: #409EFF; }
</style>
