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
  kgMatches?: Array<{ head: string; relation: string; tail: string; source: string; matched_section: string; score?: number }>;
}>();

// 明确activeTooltip的类型为Ref<{id: string, x: number, y: number} | null>
const activeTooltip = ref<{id: string, x: number, y: number} | null>(null);
const clickedMatch = ref<Match | null>(null);

/*[新修改]处理模型回答的高亮显示逻辑*/
const highlightedText = computed(() => {
  const kgMatches = props.kgMatches ?? [];
  let result = props.text;
  if (kgMatches.length) {
    kgMatches.forEach((match, idx) => {
      if (!match.matched_section) return;
      // 转义正则特殊字符
      const escaped = match.matched_section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      // 全局替换所有出现的位置
      const reg = new RegExp(escaped, 'g');
      result = result.replace(reg, `<span class='kg-highlight' title='${match.head} | ${match.relation} | ${match.tail}'>${match.matched_section}</span>`);
    });
    return result;
  }
  // 论文高亮逻辑保持不变
  if (!props.matches.length) return props.text;

  // 1. 处理论文高亮
  if (props.matches.length) {
    const sortedMatches = [...props.matches].sort((a, b) => b.match_score - a.match_score);
    const bestMatches = new Map();
    sortedMatches.forEach(match => {
      if (!bestMatches.has(match.paper_id) || 
          match.match_score > bestMatches.get(match.paper_id).match_score) {
        bestMatches.set(match.paper_id, match);
      }
    });
    Array.from(bestMatches.values()).forEach(match => {
      if (!match.paper || !match.matched_section) return;
      try {
        const escapedSection = match.matched_section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const sectionRegex = new RegExp(escapedSection, 'g');
        const intensity = Math.min(0.1 + (match.match_score * 0.1), 0.3);
        const highlightColor = `rgba(144, 238, 144, ${intensity})`;
        const borderColor = `rgba(100, 200, 100, ${intensity * 0.7})`;
        const textColor = intensity > 0.5 ? 'rgba(0, 0, 0, 0.9)' : 'inherit';
        result = result.replace(
          sectionRegex,
          `<span 
            class="highlight" 
            data-paper-id="${match.paper.id}"
            style="background-color: ${highlightColor}; border-bottom: 2px solid ${borderColor}; color: ${textColor}; font-weight: ${intensity > 0.6 ? 'bold' : 'normal'}; padding: 0 2px; border-radius: 3px;"
          >
            ${match.matched_section}
          </span>`
        );
      } catch (e) { console.error('Error highlighting match:', e); }
    });
  }

  // 2. 处理KG三元组高亮
  if (kgMatches.length) {
    kgMatches.forEach((triple, idx) => {
      // 只高亮source片段
      if (!triple.source) return;
      try {
        const escapedSection = triple.source.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const sectionRegex = new RegExp(escapedSection, 'g');
        result = result.replace(
          sectionRegex,
          `<span 
            class='kg-highlight' 
            data-kg-idx='${idx}'
            style='background: #333; color: #fff; border-radius: 3px; padding: 0 2px; font-weight: bold;'
          >${triple.source}</span>`
        );
      } catch (e) { console.error('Error highlighting KG:', e); }
    });
  }
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

// 新增KG三元组tooltip逻辑
const activeKGIdx = ref<number|null>(null);
const activeKGPos = ref<{x: number, y: number}|null>(null);

// 修改钩子写法
onMounted(() => {
  nextTick(() => {
    setupEventListeners();
    setupKGEventListeners();
  });
});

onUpdated(() => {
  nextTick(() => {
    setupEventListeners();
    setupKGEventListeners();
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

function setupKGEventListeners() {
  const kgHighlights = document.querySelectorAll<HTMLElement>('.kg-highlight');
  kgHighlights.forEach((span) => {
    const idx = span.getAttribute('data-kg-idx');
    if (idx === null) return;
    span.onmouseenter = (e) => {
      activeKGIdx.value = Number(idx);
      const mouseEvent = e as MouseEvent;
      activeKGPos.value = { x: mouseEvent.clientX + 15, y: mouseEvent.clientY + 15 };
      if (activeTooltip.value) activeTooltip.value = null;
    };
    span.onmousemove = (e) => {
      // 让tooltip跟随鼠标
      const mouseEvent = e as MouseEvent;
      activeKGPos.value = { x: mouseEvent.clientX + 15, y: mouseEvent.clientY + 15 };
    };
    span.onmouseleave = () => {
      activeKGIdx.value = null;
      activeKGPos.value = null;
    };
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
          left: `${activeTooltip.x}px`,
          top: `${activeTooltip.y}px`,
          zIndex: 1000,
          pointerEvents: 'none',
          backgroundColor: 'rgba(30, 30, 30, 0.95)',
          color: 'white',
          borderRadius: '6px',
          padding: '12px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }"
      >
        <div class="match-tooltip">
          <div class="match-title">{{ activeMatch.paper.title }}</div>
          <div class="match-authors">{{ activeMatch.paper.authors?.join(', ') }}</div>
          <div class="match-score">匹配度: {{ (activeMatch.match_score * 100).toFixed(1) }}%</div>
          <div class="match-section">{{ activeMatch.matched_section }}</div>
        </div>
      </div>
      <div
        v-if="activeKGIdx !== null && props.kgMatches && props.kgMatches[activeKGIdx] && activeKGPos"
        class="kg-tooltip"
        :style="{
          position: 'fixed',
          left: activeKGPos.x + 'px',
          top: activeKGPos.y + 'px',
          zIndex: 1000,
          pointerEvents: 'none',
          backgroundColor: '#222',
          color: '#fff',
          borderRadius: '6px',
          padding: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          border: '1px solid rgba(255,255,255,0.1)',
        }"
      >
        <div><b>知识三元组</b></div>
        <div>实体1: {{ props.kgMatches[activeKGIdx].head }}</div>
        <div>关系: {{ props.kgMatches[activeKGIdx].relation }}</div>
        <div>实体2: {{ props.kgMatches[activeKGIdx].tail }}</div>
        <div style="font-size:12px;color:#aaa;margin-top:4px;">来源: {{ props.kgMatches[activeKGIdx].source }}</div>
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
  background: linear-gradient(90deg, #fffbe6 0%, #ffe58f 100%);
  color: #222;
  border-radius: 3px;
  padding: 0 2px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.highlight:hover {
  background: #ffd700;
  color: #000;
}

.kg-highlight {
  background: #bbbbbb00;
  color: #fff;
  border-radius: 4px;
  padding: 0 4px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
  position: relative;
  z-index: 2;
}
.kg-highlight:hover {
  background: #bbbbbb00;
  box-shadow: 0 0 0 8px #e0e0e0aa;
}

.kg-tooltip {
  font-size: 18px;
  line-height: 1.7;
  background: #222;
  color: #fff;
  border-radius: 12px;
  padding: 20px 28px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
  border: 1.5px solid rgba(255,255,255,0.15);
  pointer-events: none;
  z-index: 1000;
  min-width: 320px;
  max-width: 480px;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
}
.kg-tooltip b {
  font-size: 20px;
  color: #ffd700;
  margin-bottom: 10px;
  display: block;
}
.kg-tooltip div {
  margin-bottom: 6px;
}
.kg-tooltip div:last-child {
  margin-bottom: 0;
}

.match-tooltip {
  font-size: 14px;
  line-height: 1.6;
}

.match-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #ffd700;
  font-size: 15px;
}

.match-score {
  color: #fff;
  background: rgba(255, 215, 0, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 8px;
}

.match-authors {
  color: #ccc;
  font-size: 13px;
  margin-bottom: 4px;
}
</style>

<style>
.kg-highlight {
  background: #333;
  color: #fff;
  border-radius: 4px;
  padding: 0 4px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
  position: relative;
  z-index: 2;
}
.kg-highlight:hover {
  background: #333;
  box-shadow: 0 0 0 8px #e0e0e0aa;
}
.kg-tooltip {
  font-size: 18px;
  line-height: 1.7;
  background: #222;
  color: #fff;
  border-radius: 12px;
  padding: 20px 28px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
  border: 1.5px solid rgba(255,255,255,0.15);
  pointer-events: none;
  z-index: 1000;
  min-width: 320px;
  max-width: 480px;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
}
.kg-tooltip b {
  font-size: 20px;
  color: #ffd700;
  margin-bottom: 10px;
  display: block;
}
.kg-tooltip div {
  margin-bottom: 6px;
}
.kg-tooltip div:last-child {
  margin-bottom: 0;
}
</style>
