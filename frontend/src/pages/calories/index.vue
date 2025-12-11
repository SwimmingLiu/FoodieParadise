<template>
  <view class="container">
    <!-- Scrollable Content -->
    <scroll-view class="content-area" scroll-y :scroll-into-view="scrollIntoView" :scroll-with-animation="true">
      
      <!-- Initial State: Dark Theme with Card Swiper & Upload Button -->
      <view v-if="!showResults" class="initial-state">
        <!-- Header with Logo and Title -->
        <view class="header-section">
          <view class="header-title-row">
            <image src="https://oss.swimmingliu.cn/foodie_paradise/84fb877f-7b8c-476e-bf4a-d0a1a8971414.png" mode="aspectFit" class="header-logo"></image>
            <text class="header-title">吃多少</text>
          </view>
          <text class="header-slogan">拍张美食照，AI秒算热量消耗</text>
        </view>

        <!-- Card-style Swiper -->
        <swiper class="card-swiper" circular :previous-margin="'80rpx'" :next-margin="'80rpx'" :current="currentBannerIndex" @change="onSwiperChange">
          <swiper-item v-for="(item, index) in bannerCards" :key="index" @click="selectBannerCard(item)">
            <view :class="['card-item', currentBannerIndex === index ? 'card-active' : '']">
              <image :src="item.image" mode="aspectFill" class="card-image"></image>
              <view class="card-overlay">
                <text class="card-category">{{ item.category }}</text>
                <text class="card-question">{{ item.description }}</text>
              </view>
            </view>
          </swiper-item>
        </swiper>

        <!-- Upload Button -->
        <view class="upload-section">
          <view class="upload-main-btn" @click="chooseImage">
            <image src="https://oss.swimmingliu.cn/foodie_paradise/f65002d6-d3cc-43ff-b5f6-2d637cf06672.svg" mode="aspectFit" class="upload-icon"></image>
            <text class="upload-text">上传图片</text>
          </view>
          <text class="upload-hint">一键识别，了解美食热量</text>
        </view>
      </view>

      <!-- Results Display -->
      <view v-else class="results-container">
        <!-- User Image Preview -->
        <view class="user-image-section">
          <image :src="currentImage" mode="aspectFill" class="user-image"></image>
          <view class="meal-time-badge">
            <text>{{ selectedMealTime }}</text>
          </view>
        </view>

        <!-- Thinking Process - Show if content exists (even while analyzing) -->
        <view v-if="thinkingContent" class="thought-card">
          <view class="thought-card-header" @click="toggleThinking">
            <text class="thought-icon">💡</text>
            <text class="thought-step-label">AI 思考过程</text>
            <view :class="['thought-arrow', thinkingExpanded ? 'expanded' : '']"></view>
          </view>
          <view v-if="thinkingExpanded" class="thought-card-body">
            <mp-html :content="parseMarkdown(thinkingContent)" :tag-style="mpHtmlTagStyle" />
          </view>
        </view>

        <!-- Simple Analysis Loading Indicator (Matches Check Premade Style) - Show BELOW thoughts while analyzing -->
        <view v-if="isAnalyzing" class="analyzing-indicator-card">
            <view class="dot-flashing"></view>
            <text>正在分析当前图片中的信息...</text>
        </view>

        <!-- Food Cards -->
        <view class="food-cards-section" v-if="foodItems.length > 0">
          <view class="section-title">
            <text class="section-icon">🍽️</text>
            <text>食物热量分析</text>
          </view>
          <view v-for="(item, index) in foodItems" :key="index" class="food-card">
            <view class="food-card-header">
              <text class="food-name">{{ item.name }}</text>
              <view class="calories-badge">
                <text class="calories-value">{{ item.calories }}</text>
                <text class="calories-unit">千卡</text>
              </view>
            </view>
            <view class="food-card-body">
              <view class="exercise-info">
                <text class="exercise-icon">🏃</text>
                <text class="exercise-text">{{ item.exercise }}</text>
              </view>
              <view :class="['recommendation-tag', item.is_recommended ? 'recommended' : 'not-recommended']">
                <text>{{ item.is_recommended ? '✅ 推荐食用' : '⚠️ 不建议' }}</text>
              </view>
              <view v-if="item.recommendation" class="recommendation-text">
                <text>{{ item.recommendation }}</text>
              </view>
            </view>
          </view>
        </view>

        <!-- Total Summary -->
        <view class="total-summary" v-if="totalCalories > 0">
          <view class="summary-header">
            <text class="summary-icon">📊</text>
            <text class="summary-title">总热量概览</text>
          </view>
          <view class="summary-content">
            <view class="total-calories-display">
              <text class="total-value">{{ totalCalories }}</text>
              <text class="total-unit">千卡</text>
            </view>
          </view>
        </view>

        <!-- Advice Card -->
        <view v-if="overallAdvice" class="advice-card">
            <view class="advice-header">
                <text class="advice-icon">💡</text>
                <text class="advice-title">综合建议</text>
            </view>
            <view class="advice-content">
                <text>{{ overallAdvice }}</text>
            </view>
        </view>

        <!-- Result Content -->
        <view v-if="resultContent" class="result-section">
          <mp-html :content="parseMarkdown(resultContent)" :tag-style="mpHtmlTagStyle" />
        </view>
      </view>
      
      <!-- Padding for bottom -->
      <view style="height: 120rpx;"></view>
    </scroll-view>

    <!-- Bottom Action Area - Show when in results mode -->
    <view v-if="showResults" class="bottom-action-area">
      <!-- 识别中状态 -->
      <view v-if="isAnalyzing" class="recognizing-bar">
        <view class="recognizing-btn">
          <text class="recognizing-icon">🌐</text>
          <text class="recognizing-text">分析中...</text>
        </view>
        <view class="stop-btn" @click="handleStop">
          <view class="stop-icon"></view>
        </view>
      </view>
      
      <!-- 识别完成状态 -->
      <view v-else class="completed-bar">
        <view class="result-actions">
          <view class="result-info" @click="startNewAnalysis">
            <text>重新分析</text>
            <text class="result-arrow">›</text>
          </view>
          <view class="action-icons">
            <view class="action-icon-btn" @click="copyResult">
              <text>📋</text>
            </view>
            <button class="action-icon-btn share-btn" open-type="share">
              <text>↗️</text>
            </button>
          </view>
        </view>
      </view>
      
      <!-- AI生成提示 -->
      <view class="ai-disclaimer">
        <text class="ai-disclaimer-icon">✦</text>
        <text class="ai-disclaimer-text">内容由AI生成，仅供参考</text>
      </view>
    </view>

    <!-- Meal Time Selection Modal -->
    <view v-if="showMealTimeModal" class="modal-mask" @click="closeMealTimeModal">
      <view class="meal-time-modal" @click.stop>
        <view class="modal-header">
          <text class="modal-title">选择用餐时间</text>
          <view class="modal-close" @click="closeMealTimeModal">
            <text>×</text>
          </view>
        </view>
        
        <!-- Image Preview -->
        <view class="modal-image-preview">
          <image :src="currentImage" mode="aspectFill" class="preview-image"></image>
        </view>
        
        <!-- Meal Time Options -->
        <view class="meal-time-options">
          <view v-for="(time, index) in mealTimeOptions" :key="index" 
                :class="['meal-time-option', selectedMealTime === time.value ? 'selected' : '']"
                @click="selectMealTime(time.value)">
            <text class="meal-time-emoji">{{ time.emoji }}</text>
            <text class="meal-time-label">{{ time.label }}</text>
          </view>
        </view>
        
        <!-- Submit Button -->
        <view class="modal-submit-btn" @click="submitAnalysis">
          <text class="submit-text">开始分析</text>
        </view>
      </view>
    </view>

    <!-- Loading Overlay -->
    <view v-if="isUploading" class="loading-mask">
      <text>上传中...</text>
    </view>

  </view>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { onShareAppMessage, onShareTimeline } from '@dcloudio/uni-app';
import { streamRequest } from '../../utils/request.js';
import { API_ENDPOINTS } from '../../config/index.js';
import mpHtml from 'mp-html/dist/uni-app/components/mp-html/mp-html.vue';
import { marked } from 'marked';

// Configure marked
marked.setOptions({
    breaks: true,
    gfm: true,
});

// Tag styles for mp-html
// hr: 美化 Markdown 分割线，使用渐变背景从两边透明渐变到中间灰色
const mpHtmlTagStyle = {
    ol: 'padding-left: 0; margin-left: 0; list-style-position: inside; line-height: 1.8;',
    ul: 'padding-left: 0; margin-left: 0; list-style-position: inside; line-height: 1.8;',
    li: 'padding-left: 0; margin-left: 0; text-indent: 0; line-height: 1.8; margin-bottom: 6px; display: list-item;',
    p: 'margin: 10px 0; line-height: 1.8; display: inline;',
    strong: 'display: inline; font-weight: 700;',
    em: 'display: inline;',
    h1: 'font-size: 16px; font-weight: 700; margin: 14px 0 10px 0; line-height: 1.6;',
    h2: 'font-size: 16px; font-weight: 700; margin: 14px 0 10px 0; line-height: 1.6;',
    h3: 'font-size: 16px; font-weight: 700; margin: 14px 0 10px 0; line-height: 1.6;',
    h4: 'font-size: 16px; font-weight: 700; margin: 14px 0 10px 0; line-height: 1.6;',
    hr: 'border: none; height: 1px; background: linear-gradient(to right, transparent, #e0e0e0 20%, #e0e0e0 80%, transparent); margin: 24px 0;'
};

// Banner cards for swiper
const bannerCards = ref([
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/8c0e4d50-ffbe-4659-8c3b-6f485355ef53.jpg',
        category: '热量揭秘',
        description: '这道菜热量超标了吗？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/9cdfa36a-5463-4178-bb74-a70a6027a646.jpg',
        category: '减肥必看',
        description: '减脂期能不能吃这个？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/d6443171-7424-4a11-b523-5d30051e4185.jpg',
        category: '营养分析',
        description: '这顿饭营养搭配如何？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/dede5bee-78f7-47e5-a05b-3b81665662f6.jpg',
        category: '运动消耗',
        description: '吃完需要跑多久？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/b1dfa3df-f8b4-4310-973d-28e946fb96cf.jpg',
        category: '健康饮食',
        description: '如何吃得更健康？'
    }
]);

// Meal time options
const mealTimeOptions = ref([
    { value: '早餐', label: '早餐', emoji: '🍳' },
    { value: '午餐', label: '午餐', emoji: '🍜' },
    { value: '晚餐', label: '晚餐', emoji: '🍕' },
    { value: '下午茶', label: '下午茶', emoji: '☕' },
    { value: '夜宵', label: '夜宵', emoji: '🌙' }
]);

// State
const currentBannerIndex = ref(0);
const currentImage = ref(null);
const currentRemoteFilePath = ref(null);
const scrollIntoView = ref('');
const isUploading = ref(false);
const isAnalyzing = ref(false);
const showResults = ref(false);
const showMealTimeModal = ref(false);
const selectedMealTime = ref('午餐');
const isBannerClick = ref(false);

// Analysis results
const thinkingContent = ref('');
const thinkingExpanded = ref(true);
const resultContent = ref('');
const foodItems = ref([]);
const totalCalories = ref(0);
const overallAdvice = ref('');

// 预设加载提示 - 已移除，使用简单加载状态
// const presetHints = [];
// const visibleHints = ref([]);
// let hintTimer = null;

// Request task reference
let currentRequestTask = null;

// Actions
const onSwiperChange = (e) => {
    currentBannerIndex.value = e.detail.current;
};

/**
 * 点击轮播图卡片 - 使用轮播图图片并显示用餐时间选择弹窗
 */
const selectBannerCard = (item) => {
    isBannerClick.value = true;
    currentImage.value = item.image;
    showMealTimeModal.value = true;
    
    // 上传轮播图图片
    uploadBannerImage(item.image);
};

/**
 * 上传轮播图图片
 */
const uploadBannerImage = (imagePath) => {
    // 如果是远程图片(http/https开头)，直接使用，无需上传
    if (imagePath && (imagePath.startsWith('http://') || imagePath.startsWith('https://'))) {
        currentRemoteFilePath.value = imagePath;
        isUploading.value = false;
        return;
    }

    isUploading.value = true;
    
    uni.uploadFile({
        url: API_ENDPOINTS.UPLOAD,
        filePath: imagePath,
        name: 'file',
        success: (uploadRes) => {
            try {
                const data = JSON.parse(uploadRes.data);
                currentRemoteFilePath.value = data.file_path;
                isUploading.value = false;
            } catch (e) {
                console.error("Upload parse error", e);
                uni.showToast({ title: '上传失败', icon: 'none' });
                isUploading.value = false;
            }
        },
        fail: (err) => {
            console.error("Upload error", err);
            uni.showToast({ title: '网络错误', icon: 'none' });
            isUploading.value = false;
        }
    });
};

/**
 * 选择图片 - 打开相册选择图片
 */
const chooseImage = () => {
    isBannerClick.value = false;
    uni.chooseImage({
        count: 1,
        success: (res) => {
            currentImage.value = res.tempFilePaths[0];
            uploadImage(currentImage.value);
            showMealTimeModal.value = true;
        }
    });
};

/**
 * 上传图片到服务器
 */
const uploadImage = (tempFilePath) => {
    isUploading.value = true;
    uni.uploadFile({
        url: API_ENDPOINTS.UPLOAD,
        filePath: tempFilePath,
        name: 'file',
        success: (uploadRes) => {
            try {
                const data = JSON.parse(uploadRes.data);
                currentRemoteFilePath.value = data.file_path;
            } catch (e) {
                console.error("Upload parse error", e);
                uni.showToast({ title: '上传失败', icon: 'none' });
            }
        },
        fail: (err) => {
            console.error("Upload error", err);
            uni.showToast({ title: '网络错误', icon: 'none' });
        },
        complete: () => {
            isUploading.value = false;
        }
    });
};

/**
 * 选择用餐时间
 */
const selectMealTime = (time) => {
    selectedMealTime.value = time;
};

/**
 * 关闭用餐时间弹窗
 */
const closeMealTimeModal = () => {
    showMealTimeModal.value = false;
};

/**
 * 提交分析请求
 */
const submitAnalysis = () => {
    if (!currentRemoteFilePath.value) {
        uni.showToast({ title: '图片上传中，请稍候', icon: 'none' });
        return;
    }
    
    showMealTimeModal.value = false;
    showResults.value = true;
    startAnalysis();
};

/**
 * 启动预设提示动画 - 已废弃
 */
const startPresetHints = () => {
    // visibleHints.value = [];
};

/**
 * 停止预设提示动画 - 已废弃
 */
const stopPresetHints = () => {
    // if (hintTimer) clearInterval(hintTimer);
};

/**
 * 开始分析
 */
const startAnalysis = () => {
    // 重置结果
    thinkingContent.value = '';
    resultContent.value = '';
    foodItems.value = [];
    totalCalories.value = 0;
    overallAdvice.value = '';
    isAnalyzing.value = true;
    
    // 启动预设提示动画
    startPresetHints();
    
    // 发起流式请求
    currentRequestTask = streamRequest({
        url: API_ENDPOINTS.CALORIES,
        method: 'POST',
        data: {
            file_path: currentRemoteFilePath.value,
            meal_time: selectedMealTime.value
        },
        onEvent: (eventType, data) => {
            if (!data) return;
            
            if (eventType === 'thought') {
                thinkingContent.value += decodeHTMLEntities(data);
            } else if (eventType === 'message') {
                resultContent.value += decodeHTMLEntities(data);
            } else if (eventType === 'function_call') {
                try {
                    const funcData = typeof data === 'string' ? JSON.parse(data) : data;
                    if (funcData.action === 'calories_result') {
                        // 解析食物卡片数据
                        if (funcData.food_items) {
                            foodItems.value = funcData.food_items;
                        }
                        if (funcData.total_calories) {
                            totalCalories.value = funcData.total_calories;
                        }
                        if (funcData.overall_advice) {
                            overallAdvice.value = funcData.overall_advice;
                        }
                    }
                } catch (e) {
                    console.error("Function call parse error", e);
                }
            }
        },
        onComplete: () => {
            isAnalyzing.value = false;
            currentRequestTask = null;
            stopPresetHints();
            
            // 尝试从结果内容中提取JSON数据（如果还没有通过function_call接收到）
            if (foodItems.value.length === 0 && resultContent.value) {
                extractFoodDataFromContent(resultContent.value);
            }
            
            // 清理结果内容中的原始JSON
            resultContent.value = cleanJsonFromContent(resultContent.value);
            
            console.log("Analysis complete");
        },
        onError: (err) => {
            console.error("Stream error", err);
            isAnalyzing.value = false;
            currentRequestTask = null;
            stopPresetHints();
            resultContent.value += "\n[分析失败]";
        }
    });
};

/**
 * 停止分析
 */
const handleStop = () => {
    if (currentRequestTask) {
        currentRequestTask.abort();
        currentRequestTask = null;
    }
    isAnalyzing.value = false;
    stopPresetHints();
};

/**
 * 开始新分析
 */
const startNewAnalysis = () => {
    showResults.value = false;
    currentImage.value = null;
    currentRemoteFilePath.value = null;
    thinkingContent.value = '';
    resultContent.value = '';
    foodItems.value = [];
    totalCalories.value = 0;
    overallAdvice.value = '';
};

/**
 * 切换思考过程展开/收起
 */
const toggleThinking = () => {
    thinkingExpanded.value = !thinkingExpanded.value;
};

/**
 * 复制结果
 */
const copyResult = () => {
    let content = '';
    if (foodItems.value.length > 0) {
        content = foodItems.value.map(item => 
            `${item.name}: ${item.calories}千卡 - ${item.exercise}`
        ).join('\n');
        content += `\n\n总热量: ${totalCalories.value}千卡`;
    } else if (resultContent.value) {
        content = resultContent.value;
    }
    
    if (!content) {
        uni.showToast({ title: '暂无内容可复制', icon: 'none' });
        return;
    }
    
    uni.setClipboardData({
        data: content,
        success: () => {
            uni.showToast({ title: '已复制到剪贴板', icon: 'success' });
        }
    });
};

/**
 * Decode HTML entities
 */
const decodeHTMLEntities = (text) => {
    if (!text) return '';
    const entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    };
    return text.replace(/&amp;|&lt;|&gt;|&quot;|&#39;|&nbsp;/g, (match) => entities[match] || match);
};

/**
 * 从结果内容中提取食物数据 JSON
 * 并解析为食物卡片数据
 * @param {string} content - 结果内容
 */
const extractFoodDataFromContent = (content) => {
    if (!content) return;
    
    try {
        // 尝试多种模式匹配 JSON
        
        // 模式1: 匹配 food_items 数组
        const foodItemsMatch = content.match(/"food_items"\s*:\s*\[([\s\S]*?)\]/);
        if (foodItemsMatch) {
            // 构建完整的JSON对象
            let jsonStr = `{"food_items":[${foodItemsMatch[1]}]`;
            
            // 尝试提取 total_calories
            const totalMatch = content.match(/"total_calories"\s*:\s*(\d+)/);
            if (totalMatch) {
                jsonStr += `,"total_calories":${totalMatch[1]}`;
            }
            
            // 尝试提取 overall_advice
            const adviceMatch = content.match(/"overall_advice"\s*:\s*"([^"]*(?:\\"[^"]*)*)"/);
            if (adviceMatch) {
                jsonStr += `,"overall_advice":"${adviceMatch[1]}"`;
            }
            
            jsonStr += '}';
            
            // 清理和解析 JSON
            const cleanedJson = jsonStr
                .replace(/\\n/g, ' ')
                .replace(/\n/g, ' ')
                .replace(/,\s*,/g, ',')
                .replace(/,\s*}/g, '}')
                .replace(/,\s*]/g, ']');
            
            console.log('[DEBUG] Extracted JSON:', cleanedJson);
            
            const data = JSON.parse(cleanedJson);
            
            if (data.food_items && data.food_items.length > 0) {
                foodItems.value = data.food_items;
            }
            if (data.total_calories) {
                totalCalories.value = data.total_calories;
            }
            if (data.overall_advice) {
                overallAdvice.value = data.overall_advice;
            }
        }
    } catch (e) {
        console.error('[DEBUG] Failed to extract food data:', e);
        
        // 备用方案：通过简单的字符串查找提取 advice
        // 即使JSON解析失败，也尝试获取建议
        try {
             const adviceMatch = content.match(/"overall_advice"\s*:\s*"([^"]*(?:\\"[^"]*)*)"/);
             if (adviceMatch) {
                 overallAdvice.value = adviceMatch[1];
             }
        } catch (e2) {}

        // 备用方案：使用正则表达式提取单个食物项
        try {
            const items = [];
            const itemRegex = /\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"calories"\s*:\s*(\d+)\s*,\s*"exercise"\s*:\s*"([^"]+)"\s*,\s*"recommendation"\s*:\s*"([^"]+)"\s*,\s*"is_recommended"\s*:\s*(true|false)\s*\}/g;
            let match;
            while ((match = itemRegex.exec(content)) !== null) {
                items.push({
                    name: match[1],
                    calories: parseInt(match[2]),
                    exercise: match[3],
                    recommendation: match[4],
                    is_recommended: match[5] === 'true'
                });
            }
            if (items.length > 0) {
                foodItems.value = items;
                console.log('[DEBUG] Fallback parsed items:', items);
            }
            
            // 提取总热量
            const totalMatch = content.match(/"total_calories"\s*:\s*(\d+)/);
            if (totalMatch) {
                totalCalories.value = parseInt(totalMatch[1]);
            }
            
            // 提取建议 (if not already found)
            if (!overallAdvice.value) {
                const adviceMatch = content.match(/"overall_advice"\s*:\s*"([^"]+)"/);
                if (adviceMatch) {
                    overallAdvice.value = adviceMatch[1];
                }
            }
        } catch (fallbackError) {
            console.error('[DEBUG] Fallback extraction also failed:', fallbackError);
        }
    }
};

/**
 * 从内容中清除原始JSON字符串
 * 确保原始JSON不会显示在界面上
 * @param {string} content - 原始内容
 * @returns {string} 清理后的内容
 */
const cleanJsonFromContent = (content) => {
    if (!content) return '';
    
    let cleaned = content;
    
    // 清除 food_items JSON 数组及其相关内容
    // 匹配从 "food_items" 开始到数组结束
    cleaned = cleaned.replace(/"food_items"\s*:\s*\[[\s\S]*?\]\s*,?/g, '');
    
    // 清除 total_calories
    cleaned = cleaned.replace(/"total_calories"\s*:\s*\d+\s*,?/g, '');
    
    // 清除 overall_advice
    cleaned = cleaned.replace(/"overall_advice"\s*:\s*"[^"]*(?:\\"[^"]*)*"\s*,?/g, '');
    
    // 清除 reason-content 和 answer 字段的标记
    cleaned = cleaned.replace(/"reason-content"\s*:\s*"[\s\S]*?",?/g, '');
    cleaned = cleaned.replace(/"answer"\s*:\s*"/g, '');
    
    // 清除单独的 JSON 大括号和字段残留
    cleaned = cleaned.replace(/^\s*\{\s*/g, '');
    cleaned = cleaned.replace(/\s*\}\s*$/g, '');
    
    // 清除连续的逗号
    cleaned = cleaned.replace(/,\s*,/g, ',');
    
    // 清除开头和结尾的逗号
    cleaned = cleaned.replace(/^\s*,\s*/g, '');
    cleaned = cleaned.replace(/\s*,\s*$/g, '');
    
    // 清除空白行
    cleaned = cleaned.replace(/\n\s*\n/g, '\n');
    
    // 清除结尾的引号
    cleaned = cleaned.replace(/"\s*$/g, '');
    
    return cleaned.trim();
};

/**
 * Parse markdown to HTML
 */
const parseMarkdown = (content) => {
    if (!content) return '';
    try {
        // 先解码 HTML 实体
        let decoded = decodeHTMLEntities(content);
        
        // 【修复】手动处理 Markdown 加粗语法 (**text**)，解决部分特殊符号（如中文引号）导致无法加粗的问题
        decoded = decoded.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        const withNewlines = decoded.replace(/\\n/g, '\n');
        return marked.parse(withNewlines);
    } catch (e) {
        console.error('Markdown parse error:', e);
        return content;
    }
};

/**
 * 配置微信分享
 */
onShareAppMessage(() => {
    let shareTitle = '查看这顿饭的热量！';
    if (totalCalories.value > 0) {
        shareTitle = `🍽️ 这顿饭共${totalCalories.value}千卡`;
    }
    return {
        title: shareTitle,
        path: '/pages/calories/index',
        imageUrl: currentImage.value || 'https://oss.swimmingliu.cn/foodie_paradise/66c375a3-52d8-41d0-aab9-3c2a34f835ae.png'
    };
});

onShareTimeline(() => {
    return {
        title: totalCalories.value > 0 ? `🍽️ 这顿饭共${totalCalories.value}千卡` : 'AI热量计算器',
        query: '',
        imageUrl: 'https://oss.swimmingliu.cn/foodie_paradise/66c375a3-52d8-41d0-aab9-3c2a34f835ae.png'
    };
});
</script>

<style>
.container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background-color: #f5f5f5;
}

.content-area {
    flex: 1;
    height: 0;
}

.initial-state {
    padding: 0;
    background-color: #fff;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

/* ========== Header Section ========== */
.header-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60rpx 40rpx 40rpx;
}

.header-title-row {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16rpx;
}

.header-logo {
    width: 56rpx;
    height: 56rpx;
    margin-right: 12rpx;
}

.header-title {
    font-size: 48rpx;
    font-weight: 700;
    color: #333;
}

.header-slogan {
    font-size: 26rpx;
    color: rgba(0, 0, 0, 0.5);
    text-align: center;
}

/* ========== Card Swiper ========== */
.card-swiper {
    width: 100%;
    height: 800rpx;
    margin-top: 40rpx;
}

.card-item {
    width: 100%;
    height: 720rpx;
    border-radius: 32rpx;
    overflow: hidden;
    position: relative;
    transform: scale(0.9);
    transition: transform 0.3s ease;
}

.card-active {
    transform: scale(1);
}

.card-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.card-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 40rpx 32rpx;
    background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%);
}

.card-category {
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 12rpx;
    display: block;
}

.card-question {
    font-size: 36rpx;
    font-weight: 600;
    color: #fff;
    display: block;
}

/* ========== Upload Section ========== */
.upload-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60rpx 60rpx 80rpx;
    margin-top: auto;
}

.upload-main-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 500rpx;
    height: 100rpx;
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    border: none;
    border-radius: 50rpx;
    margin-bottom: 32rpx;
    box-shadow: 0 8rpx 24rpx rgba(255, 107, 107, 0.3);
}

.upload-main-btn:active {
    opacity: 0.9;
    transform: scale(0.98);
}

.upload-icon {
    width: 48rpx;
    height: 48rpx;
    margin-right: 16rpx;
}

.upload-text {
    font-size: 32rpx;
    color: #fff;
    font-weight: 500;
}

.upload-hint {
    font-size: 26rpx;
    color: rgba(0, 0, 0, 0.4);
}

/* ========== Results Container ========== */
.results-container {
    padding: 20rpx 30rpx;
}

.user-image-section {
    position: relative;
    width: 100%;
    height: 400rpx;
    border-radius: 20rpx;
    overflow: hidden;
    margin-bottom: 24rpx;
}

.user-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.meal-time-badge {
    position: absolute;
    top: 20rpx;
    right: 20rpx;
    background-color: rgba(0, 0, 0, 0.6);
    padding: 10rpx 24rpx;
    border-radius: 30rpx;
}

.meal-time-badge text {
    color: #fff;
    font-size: 24rpx;
}

/* ========== Thought Card ========== */
.thought-card {
    background-color: #fff;
    border-radius: 20rpx;
    margin-bottom: 24rpx;
    border-left: 6rpx solid #ff6b6b;
    overflow: hidden;
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.thought-card-header {
    display: flex;
    align-items: center;
    padding: 24rpx 28rpx;
    background-color: #fafafa;
}

.thought-icon {
    font-size: 32rpx;
    margin-right: 12rpx;
}

.thought-step-label {
    font-size: 28rpx;
    font-weight: 500;
    color: #333;
}

.thought-arrow {
    width: 0;
    height: 0;
    border-left: 10rpx solid transparent;
    border-right: 10rpx solid transparent;
    border-top: 12rpx solid #999;
    transition: transform 0.3s ease;
    margin-left: auto;
}

.thought-arrow.expanded {
    transform: rotate(180deg);
}

.thought-card-body {
    padding: 20rpx 28rpx;
    border-top: 1px solid #f0f0f0;
    font-size: 28rpx;
    line-height: 1.8;
    color: #555;
}

/* ========== 预设加载提示样式 ========== */
.preset-hints {
    display: flex;
    flex-direction: column;
    gap: 16rpx;
    margin-bottom: 16rpx;
}

.preset-hint-item {
    display: flex;
    align-items: center;
    animation: fadeInUp 0.4s ease-out;
}

.hint-icon {
    font-size: 28rpx;
    margin-right: 12rpx;
}

.hint-text {
    font-size: 26rpx;
    color: #666;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(10rpx);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* ========== Food Cards Section ========== */
.food-cards-section {
    margin-bottom: 24rpx;
}

.section-title {
    display: flex;
    align-items: center;
    margin-bottom: 20rpx;
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
}

.section-icon {
    margin-right: 12rpx;
}

.food-card {
    background-color: #fff;
    border-radius: 20rpx;
    padding: 24rpx;
    margin-bottom: 20rpx;
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.food-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16rpx;
}

.food-name {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
}

.calories-badge {
    display: flex;
    align-items: baseline;
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    padding: 8rpx 20rpx;
    border-radius: 20rpx;
}

.calories-value {
    font-size: 32rpx;
    font-weight: 700;
    color: #fff;
}

.calories-unit {
    font-size: 20rpx;
    color: rgba(255, 255, 255, 0.8);
    margin-left: 4rpx;
}

.food-card-body {
    display: flex;
    flex-direction: column;
    gap: 12rpx;
}

.exercise-info {
    display: flex;
    align-items: center;
    padding: 16rpx;
    background-color: #f8f8f8;
    border-radius: 12rpx;
}

.exercise-icon {
    font-size: 28rpx;
    margin-right: 12rpx;
}

.exercise-text {
    font-size: 26rpx;
    color: #666;
}

.recommendation-tag {
    display: inline-flex;
    align-items: center;
    padding: 8rpx 16rpx;
    border-radius: 8rpx;
    font-size: 24rpx;
    width: fit-content;
}

.recommendation-tag.recommended {
    background-color: #e8f5e9;
    color: #2e7d32;
}

.recommendation-tag.not-recommended {
    background-color: #fff3e0;
    color: #ef6c00;
}

.recommendation-text {
    font-size: 24rpx;
    color: #888;
    margin-top: 8rpx;
}

/* ========== Total Summary ========== */
.total-summary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20rpx;
    padding: 24rpx;
    margin-bottom: 24rpx;
    color: #fff;
}

.summary-header {
    display: flex;
    align-items: center;
    margin-bottom: 16rpx;
}

.summary-icon {
    font-size: 28rpx;
    margin-right: 12rpx;
}

.summary-title {
    font-size: 28rpx;
    font-weight: 600;
}

.summary-content {
    display: flex;
    flex-direction: column;
    gap: 16rpx;
}

.total-calories-display {
    display: flex;
    align-items: baseline;
}

.total-value {
    font-size: 64rpx;
    font-weight: 700;
}

.total-unit {
    font-size: 28rpx;
    margin-left: 8rpx;
    opacity: 0.8;
}

/* ========== Advice Card ========== */
.advice-card {
    background-color: #fff;
    border-radius: 20rpx;
    padding: 24rpx;
    margin-bottom: 24rpx;
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
    border-left: 8rpx solid #ffd700;
}

.advice-header {
    display: flex;
    align-items: center;
    margin-bottom: 16rpx;
}

.advice-icon {
    font-size: 32rpx;
    margin-right: 12rpx;
}

.advice-title {
    font-size: 30rpx;
    font-weight: 700;
    color: #333;
}

.advice-content {
    font-size: 28rpx;
    color: #555;
    line-height: 1.6;
    background-color: #fff9c4;
    padding: 20rpx;
    border-radius: 12rpx;
}

/* ========== Result Section ========== */
.result-section {
    background-color: #fff;
    border-radius: 20rpx;
    padding: 24rpx;
    margin-bottom: 24rpx;
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

/* ========== Bottom Action Area ========== */
.bottom-action-area {
    background-color: #fff;
    padding: 16rpx 24rpx;
    padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
    border-top: 1px solid #eee;
}

.recognizing-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20rpx;
    padding: 16rpx 0;
}

.recognizing-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    height: 80rpx;
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    border-radius: 40rpx;
    gap: 12rpx;
    box-shadow: 0 4rpx 16rpx rgba(255, 107, 107, 0.3);
}

.recognizing-icon {
    font-size: 32rpx;
}

.recognizing-text {
    font-size: 30rpx;
    color: #fff;
    font-weight: 500;
}

.stop-btn {
    width: 80rpx;
    height: 80rpx;
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    border-radius: 40rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4rpx 16rpx rgba(255, 107, 107, 0.3);
}

.stop-icon {
    width: 24rpx;
    height: 24rpx;
    background-color: #fff;
    border-radius: 4rpx;
}

.completed-bar {
    padding: 16rpx 0;
}

.result-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.result-info {
    display: flex;
    align-items: center;
    padding: 16rpx 24rpx;
    background-color: #f8f8f8;
    border-radius: 40rpx;
    border: 1px solid #e8e8e8;
}

.result-info text {
    font-size: 28rpx;
    color: #333;
}

.result-arrow {
    font-size: 36rpx;
    margin-left: 8rpx;
    color: #999;
}

.action-icons {
    display: flex;
    gap: 16rpx;
}

.action-icon-btn {
    width: 72rpx;
    height: 72rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f8f8f8;
    border-radius: 36rpx;
    border: 1px solid #e8e8e8;
}

.action-icon-btn text {
    font-size: 32rpx;
}

.share-btn {
    padding: 0;
    margin: 0;
    line-height: normal;
    background-color: #f8f8f8;
}

.share-btn::after {
    border: none;
}

.ai-disclaimer {
    display: flex;
    align-items: center;
    justify-content: center;
    padding-top: 16rpx;
    gap: 8rpx;
}

.ai-disclaimer-icon {
    font-size: 24rpx;
    color: #9ca3af;
}

.ai-disclaimer-text {
    font-size: 24rpx;
    color: #9ca3af;
}

/* ========== Meal Time Modal ========== */
.modal-mask {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    z-index: 1000;
}

.meal-time-modal {
    width: 100%;
    max-height: 85vh;
    background-color: #fff;
    border-radius: 32rpx 32rpx 0 0;
    padding: 32rpx;
    padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
    position: relative;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24rpx;
}

.modal-title {
    font-size: 36rpx;
    font-weight: 600;
    color: #333;
}

.modal-close {
    width: 60rpx;
    height: 60rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f0f0f0;
    border-radius: 50%;
}

.modal-close text {
    font-size: 40rpx;
    color: #666;
    line-height: 1;
}

.modal-image-preview {
    width: 100%;
    height: 300rpx;
    border-radius: 20rpx;
    overflow: hidden;
    margin-bottom: 24rpx;
}

.preview-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.meal-time-options {
    display: flex;
    flex-wrap: wrap;
    gap: 16rpx;
    margin-bottom: 32rpx;
}

.meal-time-option {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: calc(33.33% - 12rpx);
    padding: 24rpx 16rpx;
    background-color: #f5f5f5;
    border-radius: 16rpx;
    border: 2px solid transparent;
    transition: all 0.2s ease;
}

.meal-time-option.selected {
    background-color: #fff3e0;
    border-color: #ff6b6b;
}

.meal-time-emoji {
    font-size: 40rpx;
    margin-bottom: 8rpx;
}

.meal-time-label {
    font-size: 26rpx;
    color: #333;
}

.modal-submit-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 88rpx;
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    border-radius: 44rpx;
    box-shadow: 0 8rpx 24rpx rgba(255, 107, 107, 0.3);
}

.modal-submit-btn:active {
    transform: scale(0.98);
    opacity: 0.9;
}

.submit-text {
    font-size: 32rpx;
    font-weight: 600;
    color: #fff;
}

/* ========== Loading Mask ========== */
.loading-mask {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255,255,255,0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 999;
}

/* Loading Indicator Card */
.analyzing-indicator-card {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40rpx;
    background: #fff;
    border-radius: 24rpx;
    margin-bottom: 24rpx;
    box-shadow: 0 8rpx 32rpx rgba(0,0,0,0.06);
    color: #999;
    font-size: 26rpx;
}

.dot-flashing {
    width: 10rpx;
    height: 10rpx;
    background-color: #999;
    border-radius: 50%;
    animation: dot-flashing 1s infinite linear alternate;
    margin-right: 20rpx;
    position: relative;
    left: -15rpx;
}

@keyframes dot-flashing {
    0% { background-color: #999; }
    50% { background-color: #ccc; }
    100% { background-color: #eee; }
}
</style>
