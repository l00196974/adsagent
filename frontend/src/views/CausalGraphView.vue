<template>
  <div class="causal-graph-view">
    <!-- 左侧：图谱列表 -->
    <el-aside width="300px" class="graph-list-sidebar">
      <el-card>
        <template #header>
          <div class="sidebar-header">
            <span>事理图谱列表</span>
            <el-button size="small" type="primary" @click="loadGraphs">刷新</el-button>
          </div>
        </template>

        <div v-loading="loadingGraphs" class="graph-list">
          <el-empty v-if="graphs.length === 0" description="暂无事理图谱" />

          <div
            v-for="graph in graphs"
            :key="graph.id"
            class="graph-item"
            :class="{ active: selectedGraphId === graph.id }"
            @click="selectGraph(graph.id)"
          >
            <div class="graph-item-header">
              <span class="graph-name">{{ graph.graph_name }}</span>
              <el-button
                size="small"
                type="danger"
                text
                @click.stop="deleteGraph(graph.id)"
              >
                删除
              </el-button>
            </div>
            <div class="graph-item-meta">
              <el-tag size="small">{{ graph.total_patterns }} 模式</el-tag>
              <el-tag size="small" type="info">{{ graph.total_users }} 用户</el-tag>
            </div>
            <div class="graph-item-time">{{ formatTime(graph.created_at) }}</div>
          </div>
        </div>
      </el-card>
    </el-aside>

    <!-- 中间：图谱可视化 -->
    <el-container class="main-content">
      <el-main>
        <el-card v-loading="loadingGraph" class="visualization-card">
          <template #header>
            <div class="card-header">
              <span>事理图谱可视化</span>
              <div v-if="currentGraph">
                <el-tag>{{ currentGraph.graph_name }}</el-tag>
                <el-tag type="info">{{ currentGraph.analysis_focus }}</el-tag>
              </div>
            </div>
          </template>

          <div v-if="!currentGraph" class="empty-state">
            <el-empty description="请从左侧选择一个事理图谱" />
          </div>

          <div v-else class="graph-container">
            <!-- 图谱可视化区域 -->
            <div ref="graphCanvas" class="graph-canvas"></div>

            <!-- 图例 -->
            <div class="graph-legend">
              <h4>图例</h4>
              <div class="legend-item">
                <span class="legend-node event"></span>
                <span>事件节点</span>
              </div>
              <div class="legend-item">
                <span class="legend-node feature"></span>
                <span>特征节点</span>
              </div>
              <div class="legend-item">
                <span class="legend-node result"></span>
                <span>结果节点</span>
              </div>
              <div class="legend-item">
                <span class="legend-edge sequential"></span>
                <span>顺承关系</span>
              </div>
              <div class="legend-item">
                <span class="legend-edge causal"></span>
                <span>因果关系</span>
              </div>
              <div class="legend-item">
                <span class="legend-edge conditional"></span>
                <span>条件关系</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-main>

      <!-- 右侧：图谱信息 -->
      <el-aside width="350px" class="info-sidebar">
        <el-card v-if="currentGraph">
          <template #header>
            <span>图谱信息</span>
          </template>

          <div class="info-section">
            <h4>基本信息</h4>
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="图谱名称">
                {{ currentGraph.graph_name }}
              </el-descriptions-item>
              <el-descriptions-item label="分析重点">
                {{ currentGraph.analysis_focus }}
              </el-descriptions-item>
              <el-descriptions-item label="节点数量">
                {{ currentGraph.graph_data.nodes?.length || 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="边数量">
                {{ currentGraph.graph_data.edges?.length || 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatTime(currentGraph.created_at) }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <el-divider />

          <div class="info-section">
            <h4>关键洞察</h4>
            <ul class="insights-list">
              <li v-for="(insight, index) in currentGraph.insights" :key="index">
                {{ insight }}
              </li>
            </ul>
          </div>
        </el-card>
      </el-aside>
    </el-container>

    <!-- 底部：AI问答抽屉 -->
    <el-drawer
      v-model="qaDrawerVisible"
      title="AI问答"
      direction="btt"
      size="40%"
    >
      <div class="qa-container">
        <div class="example-questions">
          <h4>示例问题</h4>
          <el-button
            v-for="(example, index) in exampleQuestions"
            :key="index"
            size="small"
            @click="askExample(example)"
          >
            {{ example }}
          </el-button>
        </div>

        <el-divider />

        <div class="qa-input">
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            placeholder="请输入您的问题..."
          />
          <el-button
            type="primary"
            :loading="asking"
            :disabled="!question.trim()"
            @click="askQuestion"
          >
            提问
          </el-button>
        </div>

        <div v-if="answer" class="qa-answer">
          <h4>回答</h4>
          <div class="answer-content">{{ answer }}</div>
        </div>
      </div>
    </el-drawer>

    <!-- 浮动按钮：打开问答 -->
    <el-button
      v-if="currentGraph"
      class="qa-fab"
      type="primary"
      circle
      size="large"
      @click="qaDrawerVisible = true"
    >
      <el-icon><ChatDotRound /></el-icon>
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'
import { listCausalGraphs, getCausalGraph, deleteCausalGraph as deleteGraphAPI, queryCausalGraph } from '@/api'
import * as d3 from 'd3'

const route = useRoute()

// 数据
const graphs = ref([])
const selectedGraphId = ref(null)
const currentGraph = ref(null)
const loadingGraphs = ref(false)
const loadingGraph = ref(false)
const qaDrawerVisible = ref(false)
const question = ref('')
const answer = ref('')
const asking = ref(false)
const graphCanvas = ref(null)

const exampleQuestions = [
  '宝马7系应该推荐给哪些用户？',
  '高收入用户的转化路径是什么？',
  '如何提高用户的购买转化率？',
  '用户流失的主要原因是什么？'
]

// 加载图谱列表
const loadGraphs = async () => {
  loadingGraphs.value = true
  try {
    const response = await listCausalGraphs(50, 0)
    if (response.success) {
      graphs.value = response.data.graphs || []
    }
  } catch (error) {
    console.error('加载图谱列表失败:', error)
  } finally {
    loadingGraphs.value = false
  }
}

// 选择图谱
const selectGraph = async (graphId) => {
  selectedGraphId.value = graphId
  loadingGraph.value = true
  try {
    const response = await getCausalGraph(graphId)
    if (response.success) {
      currentGraph.value = response.data
      await nextTick()
      renderGraph()
    }
  } catch (error) {
    console.error('加载图谱失败:', error)
  } finally {
    loadingGraph.value = false
  }
}

// 删除图谱
const deleteGraph = async (graphId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个事理图谱吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteGraphAPI(graphId)
    ElMessage.success('删除成功')

    if (selectedGraphId.value === graphId) {
      selectedGraphId.value = null
      currentGraph.value = null
    }

    await loadGraphs()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除图谱失败:', error)
    }
  }
}

// 渲染图谱
const renderGraph = () => {
  if (!graphCanvas.value || !currentGraph.value) {
    return
  }

  const container = graphCanvas.value
  container.innerHTML = ''

  const width = container.clientWidth
  const height = container.clientHeight || 600

  const graphData = currentGraph.value.graph_data
  const nodes = graphData.nodes || []
  const edges = graphData.edges || []

  if (nodes.length === 0) {
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: #909399;">图谱数据为空，没有节点</div>'
    return
  }

  // 验证边的引用（兼容 source/target 和 from/to 两种字段名）
  const nodeIds = new Set(nodes.map(n => String(n.id)))

  const validEdges = edges.map(e => {
    // 兼容不同的字段名
    const source = e.source || e.from
    const target = e.target || e.to
    return {
      ...e,
      source: String(source),
      target: String(target)
    }
  }).filter(e => {
    const hasSource = nodeIds.has(e.source)
    const hasTarget = nodeIds.has(e.target)
    if (!hasSource || !hasTarget) {
      console.warn('无效的边:', {
        edge: e,
        source: e.source,
        target: e.target,
        sourceExists: hasSource,
        targetExists: hasTarget
      })
    }
    return hasSource && hasTarget
  })

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)

  const g = svg.append('g')

  // 添加缩放功能
  const zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  svg.call(zoom)

  // 定义箭头标记
  const defs = svg.append('defs')

  // 不同类型的箭头
  const arrowTypes = [
    { id: 'arrow-sequential', color: '#909399' },
    { id: 'arrow-causal', color: '#409EFF' },
    { id: 'arrow-conditional', color: '#E6A23C' }
  ]

  arrowTypes.forEach(arrow => {
    defs.append('marker')
      .attr('id', arrow.id)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 30)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', arrow.color)
  })

  // 过滤掉自环边（从节点指向自己的边）
  const nonSelfEdges = validEdges.filter(e => {
    const sourceId = typeof e.source === 'object' ? e.source.id : e.source
    const targetId = typeof e.target === 'object' ? e.target.id : e.target
    return sourceId !== targetId
  })

  // 创建力导向图
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(nonSelfEdges).id(d => d.id).distance(150))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))

  // 绘制边（不显示大箭头）
  const link = g.append('g')
    .selectAll('line')
    .data(nonSelfEdges)
    .enter()
    .append('line')
    .attr('class', d => `edge ${d.relation_type}`)
    .attr('stroke', d => {
      if (d.relation_type === 'sequential') return '#909399'
      if (d.relation_type === 'causal') return '#409EFF'
      return '#E6A23C'
    })
    .attr('stroke-width', d => Math.max(2, (d.probability || 0.5) * 5))
    .attr('stroke-opacity', 0.6)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      ElMessageBox.alert(`
        <div style="text-align: left;">
          <p><strong>关系类型：</strong>${d.relation_type === 'sequential' ? '顺序关系' : d.relation_type === 'causal' ? '因果关系' : '条件关系'}</p>
          <p><strong>关系描述：</strong>${d.relation_desc || d.relation || '无'}</p>
          <p><strong>概率：</strong>${(d.probability * 100).toFixed(1)}%</p>
          <p><strong>置信度：</strong>${(d.confidence * 100).toFixed(1)}%</p>
          <p><strong>支持数：</strong>${d.support_count || 'N/A'}</p>
          <p><strong>从：</strong>${nodes.find(n => n.id === d.source.id)?.name || d.source}</p>
          <p><strong>到：</strong>${nodes.find(n => n.id === d.target.id)?.name || d.target}</p>
        </div>
      `, '边详情', {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '关闭'
      })
    })
    .on('mouseenter', function(event, d) {
      d3.select(this)
        .attr('stroke-width', Math.max(4, (d.probability || 0.5) * 8))
    })
    .on('mouseleave', function(event, d) {
      d3.select(this)
        .attr('stroke-width', Math.max(2, (d.probability || 0.5) * 5))
    })

  // 绘制流动的三角形箭头
  const particles = g.append('g')
    .selectAll('path')
    .data(nonSelfEdges)
    .enter()
    .append('path')
    .attr('d', 'M0,-4 L8,0 L0,4 Z')  // 三角形路径
    .attr('fill', d => {
      if (d.relation_type === 'sequential') return '#909399'
      if (d.relation_type === 'causal') return '#409EFF'
      return '#E6A23C'
    })
    .attr('opacity', 0.9)
    .style('pointer-events', 'none')

  // 粒子动画
  function animateParticles() {
    particles.each(function(d) {
      const particle = d3.select(this)
      const duration = 2000 // 2秒完成一次流动

      function move() {
        // 计算角度
        const dx = d.target.x - d.source.x
        const dy = d.target.y - d.source.y
        const angle = Math.atan2(dy, dx) * 180 / Math.PI

        particle
          .attr('transform', `translate(${d.source.x},${d.source.y}) rotate(${angle})`)
          .transition()
          .duration(duration)
          .ease(d3.easeLinear)
          .attrTween('transform', function() {
            return function(t) {
              const x = d.source.x + (d.target.x - d.source.x) * t
              const y = d.source.y + (d.target.y - d.source.y) * t
              const dx = d.target.x - d.source.x
              const dy = d.target.y - d.source.y
              const angle = Math.atan2(dy, dx) * 180 / Math.PI
              return `translate(${x},${y}) rotate(${angle})`
            }
          })
          .on('end', move)
      }

      move()
    })
  }

  // 绘制节点
  const node = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', 20)
    .attr('fill', d => {
      if (d.type === 'event') return '#409EFF'
      if (d.type === 'feature') return '#67C23A'
      return '#F56C6C'
    })
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      ElMessageBox.alert(`
        <div style="text-align: left;">
          <p><strong>节点ID：</strong>${d.id}</p>
          <p><strong>节点名称：</strong>${d.name}</p>
          <p><strong>节点类型：</strong>${d.type === 'event' ? '事件' : d.type === 'feature' ? '特征' : '结果'}</p>
          <p><strong>描述：</strong>${d.description || '无'}</p>
        </div>
      `, '节点详情', {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '关闭'
      })
    })
    .on('mouseenter', function() {
      d3.select(this)
        .attr('r', 25)
        .attr('stroke-width', 3)
    })
    .on('mouseleave', function() {
      d3.select(this)
        .attr('r', 20)
        .attr('stroke-width', 2)
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))

  // 添加节点标签
  const label = g.append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text(d => d.name)
    .attr('font-size', 12)
    .attr('dx', 25)
    .attr('dy', 5)
    .style('pointer-events', 'none')

  // 更新位置
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    label
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })

  // 启动粒子动画
  setTimeout(() => {
    animateParticles()
  }, 1000)

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

// 提问
const askQuestion = async () => {
  if (!question.value.trim() || !selectedGraphId.value) return

  asking.value = true
  answer.value = ''

  try {
    const response = await queryCausalGraph(selectedGraphId.value, question.value)
    if (response.success) {
      answer.value = response.data.answer
    }
  } catch (error) {
    console.error('提问失败:', error)
  } finally {
    asking.value = false
  }
}

// 使用示例问题
const askExample = (exampleQuestion) => {
  question.value = exampleQuestion
  askQuestion()
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadGraphs()

  // 如果URL中有graphId参数，自动选择
  if (route.params.graphId) {
    selectGraph(parseInt(route.params.graphId))
  }
})

watch(() => route.params.graphId, (newId) => {
  if (newId) {
    selectGraph(parseInt(newId))
  }
})
</script>

<style scoped>
.causal-graph-view {
  display: flex;
  height: calc(100vh - 60px);
  position: relative;
}

.graph-list-sidebar {
  border-right: 1px solid #EBEEF5;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.graph-list {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.graph-item {
  padding: 15px;
  border-bottom: 1px solid #EBEEF5;
  cursor: pointer;
  transition: all 0.3s;
}

.graph-item:hover {
  background-color: #F5F7FA;
}

.graph-item.active {
  background-color: #ECF5FF;
  border-left: 3px solid #409EFF;
}

.graph-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.graph-name {
  font-weight: 500;
  color: #303133;
}

.graph-item-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.graph-item-time {
  font-size: 12px;
  color: #909399;
}

.main-content {
  flex: 1;
  display: flex;
}

.visualization-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}

.graph-container {
  position: relative;
  height: calc(100vh - 250px);
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

.graph-legend {
  position: absolute;
  top: 20px;
  right: 20px;
  background: white;
  padding: 15px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.graph-legend h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
}

.legend-node {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin-right: 8px;
}

.legend-node.event {
  background-color: #409EFF;
}

.legend-node.feature {
  background-color: #67C23A;
}

.legend-node.result {
  background-color: #F56C6C;
}

.legend-edge {
  width: 30px;
  height: 2px;
  margin-right: 8px;
}

.legend-edge.sequential {
  background-color: #909399;
}

.legend-edge.causal {
  background-color: #409EFF;
  height: 3px;
}

.legend-edge.conditional {
  background: repeating-linear-gradient(
    to right,
    #E6A23C 0,
    #E6A23C 5px,
    transparent 5px,
    transparent 10px
  );
}

.info-sidebar {
  border-left: 1px solid #EBEEF5;
  overflow-y: auto;
}

.info-section {
  margin-bottom: 20px;
}

.info-section h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #303133;
}

.insights-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.insights-list li {
  padding: 8px 0;
  border-bottom: 1px solid #EBEEF5;
  font-size: 13px;
  color: #606266;
}

.insights-list li:last-child {
  border-bottom: none;
}

.qa-container {
  padding: 20px;
}

.example-questions {
  margin-bottom: 20px;
}

.example-questions h4 {
  margin: 0 0 10px 0;
}

.example-questions .el-button {
  margin: 5px;
}

.qa-input {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.qa-input .el-input {
  flex: 1;
}

.qa-answer {
  margin-top: 20px;
}

.qa-answer h4 {
  margin: 0 0 10px 0;
}

.answer-content {
  padding: 15px;
  background-color: #F5F7FA;
  border-radius: 4px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.qa-fab {
  position: fixed;
  bottom: 40px;
  right: 40px;
  width: 60px;
  height: 60px;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>
