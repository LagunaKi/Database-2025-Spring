<script setup lang="ts">
import type { Ref } from 'vue';
import { ref, onMounted, onUpdated, nextTick, computed } from 'vue';

/*[新修改]模型回答与论文匹配的数据结构*/
interface Match {
  paper_id: string;       // 匹配到的论文ID
  match_score: number;    // 匹配分数(0-1)
  matched_section: string; // 匹配到的文本片段
  paper?: {               // 匹配到的论文信息
    id: string;
    title: string;
    authors: string[];
  };
}

const props = defineProps<{
  text: string;
  matches: Match[];
}>();

// 明确activeTooltip的类型为Ref<{id: string, x: number, y: number} | null>
const activeTooltip = ref<{id: string, x: number, y: number} | null>(null);
const clickedMatch = ref<Match | null>(null);

/*[新修改]处理模型回答的高亮显示逻辑*/
const highlightedText = computed(() => {
  if (!props.matches.length) return props.text;

  // 1. 按匹配分数排序，优先处理高分匹配
  const sortedMatches = [...props.matches].sort((a, b) => b.match_score - a.match_score);
  
  // 2. 为每个论文保留最高分的匹配
  const bestMatches = new Map();
  sortedMatches.forEach(match => {
    if (!bestMatches.has(match.paper_id) || 
        match.match_score > bestMatches.get(match.paper_id).match_score) {
      bestMatches.set(match.paper_id, match);
    }
  });

  let result = props.text;
  
  // 3. 处理每个匹配项
  Array.from(bestMatches.values()).forEach(match => {
    if (!match.paper || !match.matched_section) return;
    
    try {
      // 3.1 转义特殊字符用于正则表达式匹配
      const escapedSection = match.matched_section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const sectionRegex = new RegExp(escapedSection, 'g');
      
      // 3.2 根据匹配分数计算高亮颜色强度
      const intensity = Math.min(0.1 + (match.match_score * 0.1), 0.3);
      const highlightColor = `rgba(144, 238, 144, ${intensity})`;
      const borderColor = `rgba(100, 200, 100, ${intensity * 0.7})`;
      const textColor = intensity > 0.5 ? 'rgba(0, 0, 0, 0.9)' : 'inherit';
      
      // 3.3 替换匹配文本为高亮显示的HTML元素
      result = result.replace(
        sectionRegex,
        `<span 
          class="highlight" 
          data-paper-id="${match.paper.id}"
          style="
            background-color: ${highlightColor}; 
            border-bottom: 2px solid ${borderColor};
            color: ${textColor};
            font-weight: ${intensity > 0.6 ? 'bold' : 'normal'};
            padding: 0 2px;
            border-radius: 3px;
          "
        >
          ${match.matched_section}
        </span>`
      );
    } catch (e) {
      console.error('Error highlighting match:', e);
    }
  });
  
  return result;
});

const activeMatch = computed(() => {
  if (clickedMatch.value) return clickedMatch.value;
  if (!activeTooltip.value?.id) return null;
  return props.matches.find(m => m.paper?.id === activeTooltip.value?.id);
});

const handleHighlightClick = (match: Match) => {
  clickedMatch.value = match;
  setTimeout(() => {
    clickedMatch.value = null;
  }, 2000);
};

// 修改钩子写法
onMounted(() => {
  nextTick(() => {
    setupEventListeners();
  });
});

onUpdated(() => {
  nextTick(() => {
    setupEventListeners();
  });
});

// 使用WeakMap存储事件监听器
const eventListenersMap = new WeakMap<HTMLElement, {
  mouseenter: (e: MouseEvent) => void;
  mousemove: (e: MouseEvent) => void;
  mouseleave: () => void;
  click: () => void;
}>();

// 显式定义方法
/*[新修改]设置高亮文本的事件监听器，处理鼠标交互*/
function setupEventListeners() {
  const highlights = document.querySelectorAll<HTMLElement>('.highlight');
  
  highlights.forEach(span => {
    const listeners = eventListenersMap.get(span);
    if (listeners) {
      span.removeEventListener('mouseenter', listeners.mouseenter);
      span.removeEventListener('mousemove', listeners.mousemove);
      span.removeEventListener('mouseleave', listeners.mouseleave);
      span.removeEventListener('click', listeners.click);
      eventListenersMap.delete(span);
    }
  });

  highlights.forEach((span) => {
    const paperId = span.getAttribute('data-paper-id');
    if (!paperId) return;
    
    const match = props.matches.find(m => m.paper?.id === paperId);
    if (!match) return;

    const mouseenterHandler = (e: MouseEvent) => {
      activeTooltip.value = {
        id: paperId,
        x: e.clientX + 15,
        y: e.clientY + 15
      };
    };
    
    const mousemoveHandler = (e: MouseEvent) => {
      if (activeTooltip.value?.id === paperId) {
        activeTooltip.value.x = e.clientX + 15;
        activeTooltip.value.y = e.clientY + 15;
      }
    };
    
    const mouseleaveHandler = () => {
      activeTooltip.value = null;
    };
    
    const clickHandler = () => {
      // 点击时处理高亮点击事件
      handleHighlightClick(match);
    };

    span.addEventListener('mouseenter', mouseenterHandler);
    span.addEventListener('mousemove', mousemoveHandler);
    span.addEventListener('mouseleave', mouseleaveHandler);
    span.addEventListener('click', clickHandler);

    eventListenersMap.set(span, {
      mouseenter: mouseenterHandler,
      mousemove: mousemoveHandler,
      mouseleave: mouseleaveHandler,
      click: clickHandler
    });
  });
}
</script>

<template>
  <div class="highlight-container">
    <div v-html="highlightedText"></div>
    
    <Teleport to="body">
      <div 
        v-if="activeMatch?.paper && activeTooltip"
        class="tooltip"
        :style="{
          position: 'fixed',
          left: '50%',
          top: `${activeTooltip.y}px`,
          zIndex: 1000,
          pointerEvents: 'none',
          backgroundColor: 'rgba(30, 30, 30, 0.95)',
          color: 'white',
          borderRadius: '6px',
          padding: '12px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(4px)',
          transform: 'translate(-50%, -100%)',
          transition: 'all 0.1s ease-out',
          maxWidth: '400px'
        }"
        @mouseenter.stop
        @mouseleave="activeTooltip = null"
      >
        <div class="tooltip-title">{{ activeMatch.paper.title }}</div>
        <div class="tooltip-score">匹配度: {{ (activeMatch.match_score * 100).toFixed(1) }}%</div>
        <div v-if="activeMatch.paper.authors?.length" class="tooltip-authors">
          作者: {{ activeMatch.paper.authors.join(', ') }}
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.highlight-container {
  position: relative;
  line-height: 1.6;
}

.highlight {
  position: relative;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 2px;
  padding: 0 2px;
  display: inline;
  line-height: inherit;
}

.highlight:hover {
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
  z-index: 10;
}

.tooltip-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #ffd700;
  font-size: 14px;
  line-height: 1.4;
}

.tooltip-score {
  color: #fff;
  background: rgba(255, 215, 0, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 8px;
  font-size: 12px;
}

.tooltip-authors {
  color: #ccc;
  font-size: 12px;
  line-height: 1.4;
}
</style>
