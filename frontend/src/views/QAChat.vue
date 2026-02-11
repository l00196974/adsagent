<template>
  <div class="qa-chat">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>智能问答</span>
          </template>
          
          <div class="chat-container" ref="chatContainer">
            <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
              <div class="message-content">
                <div class="message-text" v-html="formatMessage(msg.content)"></div>
              </div>
            </div>
            <div v-if="loading" class="loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在思考...
            </div>
          </div>
          
          <div class="input-area">
            <el-input
              v-model="question"
              placeholder="输入问题，如：喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？"
              @keyup.enter="ask"
              size="large"
            >
              <template #append>
                <el-button @click="ask" :loading="loading" type="primary">
                  提问
                </el-button>
              </template>
            </el-input>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>快捷问题</template>
          <el-tag 
            v-for="(q, i) in exampleQuestions" 
            :key="i"
            @click="question = q"
            class="example-tag"
            type="info"
            effect="plain"
          >
            {{ q }}
          </el-tag>
        </el-card>
        
        <el-card style="margin-top: 20px">
          <template #header>问答历史</template>
          <el-timeline v-if="history.length > 0">
            <el-timeline-item
              v-for="(item, i) in history"
              :key="i"
              :timestamp="item.time"
              placement="top"
            >
              <el-card shadow="never" class="history-item" @click="loadHistory(i)">
                {{ item.question.substring(0, 30) }}...
              </el-card>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无历史记录" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { askQuestion } from '../api'

const route = useRoute()
const chatContainer = ref(null)
const question = ref('')
const loading = ref(false)
const messages = ref([
  { role: 'assistant', content: '您好！我是广告知识图谱助手，基于知识图谱和事理图谱，可以帮您：\n\n1. 分析用户画像特征\n2. 比较不同品牌/车型的人群差异\n3. 生成投放策略建议\n4. 预测用户流失风险\n\n请输入您的问题。' }
])
const history = ref([])
const exampleQuestions = [
  '喜欢打高尔夫的用户是宝马7系高潜还是奔驰S系高潜？',
  '高收入人群对豪华轿车的品牌偏好是什么？',
  '针对商务人士应该投放哪些素材？',
  '什么样的用户容易流失？',
  '宝马7系和奔驰S级的目标人群有什么区别？'
]

const formatMessage = (content) => {
  return content.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

const ask = async () => {
  if (!question.value.trim()) return
  
  messages.value.push({ role: 'user', content: question.value })
  loading.value = true
  
  try {
    const res = await askQuestion(question.value)
    const answerData = res.data
    
    if (answerData.answer) {
      messages.value.push({ role: 'assistant', content: answerData.answer })
      history.value.unshift({
        question: question.value,
        answer: answerData.answer,
        time: new Date().toLocaleString()
      })
    } else {
      ElMessage.warning('未能获取有效回答')
    }
  } catch (e) {
    ElMessage.error('问答失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
    question.value = ''
    await nextTick()
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  }
}

const loadHistory = (index) => {
  const item = history.value[index]
  messages.value = [
    { role: 'assistant', content: '已为您加载历史问答' },
    { role: 'user', content: item.question },
    { role: 'assistant', content: item.answer }
  ]
}

onMounted(() => {
  if (route.query.q) {
    question.value = route.query.q
  }
})
</script>

<style scoped>
.chat-container {
  height: 450px;
  overflow-y: auto;
  padding: 15px;
  border: 1px solid #DCDFE6;
  border-radius: 4px;
  margin-bottom: 15px;
  background: #fafafa;
}

.message {
  margin-bottom: 15px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-content {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.user .message-content {
  background: #409EFF;
  color: white;
}

.message.assistant .message-content {
  background: white;
  border: 1px solid #DCDFE6;
  color: #303133;
}

.message-text {
  line-height: 1.6;
  white-space: pre-wrap;
}

.input-area {
  display: flex;
  gap: 10px;
}

.example-tag {
  margin: 5px;
  cursor: pointer;
  transition: all 0.3s;
}

.example-tag:hover {
  background: #409EFF;
  color: white;
}

.loading {
  text-align: center;
  color: #909399;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.history-item {
  cursor: pointer;
  transition: all 0.3s;
}

.history-item:hover {
  background: #f5f7fa;
}
</style>
