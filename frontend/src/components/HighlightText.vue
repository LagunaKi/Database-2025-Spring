<script setup lang="ts">
import { computed, ref } from 'vue';

const props = defineProps<{
  text: string;
  matches: Array<{
    paper_id: string;
    match_score: number;
    matched_section: string;
    paper?: {
      id: string;
      title: string;
      authors: string[];
    };
  }>;
}>();

const activeTooltip = ref<string | null>(null);

const highlightedText = computed(() => {
  if (!props.matches.length) return props.text;

  // 按匹配分数排序，优先处理高分匹配
  const sortedMatches = [...props.matches].sort((a, b) => b.match_score - a.match_score);
  
  // 为每个论文保留最高分的匹配
  const bestMatches = new Map();
  sortedMatches.forEach(match => {
    if (!bestMatches.has(match.paper_id) || 
        match.match_score > bestMatches.get(match.paper_id).match_score) {
      bestMatches.set(match.paper_id, match);
    }
  });

  let result = props.text;
  
  // 处理每个匹配
  Array.from(bestMatches.values()).forEach(match => {
    if (!match.paper || !match.matched_section) return;
    
    try {
      // 转义特殊字符用于正则表达式
      const escapedSection = match.matched_section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const sectionRegex = new RegExp(escapedSection, 'g');
      
      // 根据匹配分数计算颜色强度
      const intensity = Math.min(0.3 + (match.match_score * 0.7), 1);
      const highlightColor = `rgba(255, 215, 0, ${intensity})`;
      const borderColor = `rgba(255, 215, 0, ${intensity * 0.7})`;
      
      // 替换匹配文本
      result = result.replace(
        sectionRegex,
        `<span 
          class="highlight" 
          data-paper-id="${match.paper.id}"
          style="background-color: ${highlightColor}; border-bottom: 2px solid ${borderColor}"
          @mouseenter="activeTooltip = '${match.paper.id}'"
          @mouseleave="activeTooltip = null"
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
  if (!activeTooltip.value) return null;
  return props.matches.find(m => m.paper?.id === activeTooltip.value);
});
</script>

<template>
  <div class="highlight-container">
    <div v-html="highlightedText"></div>
    
    <Teleport to="body">
      <div 
        v-if="activeMatch?.paper"
        class="tooltip"
        :style="{
          position: 'fixed',
          zIndex: 1000,
          pointerEvents: 'none',
          backgroundColor: 'rgba(30, 30, 30, 0.95)',
          color: 'white',
          borderRadius: '6px',
          padding: '12px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(4px)'
        }"
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
}

.highlight {
  position: relative;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 2px;
  padding: 0 2px;
}

.highlight:hover {
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
}

.tooltip-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #ffd700;
  font-size: 15px;
}

.tooltip-score {
  color: #fff;
  background: rgba(255, 215, 0, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 8px;
}

.tooltip-authors {
  color: #ccc;
  font-size: 13px;
  margin-bottom: 4px;
}
</style>
