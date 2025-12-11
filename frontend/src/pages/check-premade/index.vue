<template>
  <view class="container">
    <!-- Scrollable Content -->
    <scroll-view class="content-area" scroll-y :scroll-into-view="scrollIntoView" :scroll-with-animation="true">
      
      <!-- Initial State: Swiper & Upload -->
      <view v-if="!analyzing && !result && !currentImage" class="initial-state">
        <!-- Header -->
        <view class="header-section">
          <view class="header-title-row">
            <image src="https://oss.swimmingliu.cn/foodie_paradise/a58b234f-ccdf-4041-b146-724e519a4f2f.png" mode="aspectFit" class="header-icon"></image>
            <text class="header-title">查预制</text>
          </view>
          <text class="header-slogan">一眼识别预制菜，守护舌尖安全</text>
        </view>

        <!-- Card Swiper -->
        <swiper class="card-swiper" circular :previous-margin="'80rpx'" :next-margin="'80rpx'" :current="currentBannerIndex" @change="onSwiperChange">
          <swiper-item v-for="(item, index) in bannerCards" :key="index" @click="selectBannerCard(item)">
            <view :class="['card-item', currentBannerIndex === index ? 'card-active' : '']">
              <image :src="item.image" mode="aspectFill" class="card-image"></image>
            </view>
          </swiper-item>
        </swiper>

        <!-- Upload Button -->
        <view class="upload-section">
          <view class="upload-main-btn" @click="chooseImage">
            <image src="https://oss.swimmingliu.cn/foodie_paradise/f65002d6-d3cc-43ff-b5f6-2d637cf06672.svg" mode="aspectFit" class="upload-icon"></image>
            <text class="upload-text">上传菜品图片</text>
          </view>
          <text class="upload-hint">支持拍照或从相册选择</text>
        </view>
      </view>

      <!-- Analysis State -->
      <view v-else class="analysis-container">
        <!-- Image Preview -->
        <view class="preview-header">
           <image :src="currentImage" mode="aspectFill" class="result-image" @click="previewImage"></image>
           <view class="re-upload-btn" @click="resetState" v-if="!analyzing">
             <text>🔄 重拍</text>
           </view>
        </view>

        <!-- Thoughts Section (Collapsible) -->
        <view v-if="thoughts.length > 0" class="thought-card">
            <view class="thought-header" @click="toggleThoughts">
                <text class="thought-icon">🧠</text>
                <text class="thought-title">AI 思考过程</text>
                <text :class="['thought-arrow', showThoughts ? 'expanded' : '']">›</text>
            </view>
            <view v-if="showThoughts" class="thought-body">
                <text class="thought-content">{{ thoughts.join('') }}</text>
            </view>
        </view>

        <!-- Result Dashboard (Parsed from JSON) -->
        <view v-if="structuredResult" class="dashboard-card">
            <view class="dish-header">
                <text class="dish-name">{{ structuredResult.name || '识别中...' }}</text>
                <view :class="['freshness-tag', getFreshnessClass(structuredResult.freshness)]">
                    <text class="freshness-icon">{{ getFreshnessIcon(structuredResult.freshness) }}</text>
                    <text>{{ structuredResult.freshness || '分析中' }}</text>
                </view>
            </view>
            
            <view class="score-bar">
                <text class="score-label">分析可信度</text>
                <view class="progress-bg">
                    <view class="progress-fill" :style="{ width: (structuredResult.confidence || 0) + '%' }"></view>
                </view>
                <text class="score-value">{{ structuredResult.confidence || 0 }}%</text>
            </view>
            
            <!-- Stamp Animation -->
            <view v-if="structuredResult.freshness" :class="['stamp', getFreshnessClass(structuredResult.freshness)]">
                <text>{{ structuredResult.freshness }}</text>
            </view>
        </view>

        <!-- Report Cards - Split into 3 sections -->
        <!-- 如果有拆分的报告部分，显示三个卡片 -->
        <template v-if="hasReportSections">
            <!-- 鉴定结论卡片 -->
            <view v-if="reportSections.conclusion" class="section-card conclusion-card">
                <view class="section-title-row">
                    <text class="section-icon">🧐</text>
                    <text class="section-title">鉴定结论</text>
                </view>
                <view class="section-content">
                    <mp-html :content="parseMarkdown(reportSections.conclusion)" :tag-style="mpHtmlTagStyle" />
                </view>
            </view>
            
            <!-- 深度拆解卡片 -->
            <view v-if="reportSections.breakdown" class="section-card breakdown-card">
                <view class="section-title-row">
                    <text class="section-icon">🥩</text>
                    <text class="section-title">深度拆解</text>
                </view>
                <view class="section-content">
                    <mp-html :content="parseMarkdown(reportSections.breakdown)" :tag-style="mpHtmlTagStyle" />
                </view>
            </view>
            
            <!-- 综合评价卡片 -->
            <view v-if="reportSections.evaluation" class="section-card evaluation-card">
                <view class="section-title-row">
                    <text class="section-icon">📝</text>
                    <text class="section-title">综合评价</text>
                </view>
                <view class="section-content">
                    <mp-html :content="parseMarkdown(reportSections.evaluation)" :tag-style="mpHtmlTagStyle" />
                </view>
            </view>
        </template>
        
        <!-- 如果没有拆分的报告部分，显示原始报告卡片 -->
        <view v-else-if="cleanReportText" class="report-card">
            <view class="report-title-row">
                <text class="report-icon">📋</text>
                <text class="report-title">详细分析报告</text>
            </view>
            <view class="markdown-content">
                <mp-html :content="parseMarkdown(cleanReportText)" :tag-style="mpHtmlTagStyle" />
            </view>
        </view>
        
        <!-- Loading Indicator -->
        <view v-if="analyzing" class="analyzing-indicator-card">
            <view class="dot-flashing"></view>
            <text>正在通过视觉特征分析...</text>
        </view>
        
        <view style="height: 100rpx;"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue';
import { streamRequest } from '../../utils/request.js';
import { API_ENDPOINTS } from '../../config/index.js';
import mpHtml from 'mp-html/dist/uni-app/components/mp-html/mp-html.vue';
import { marked } from 'marked';

marked.setOptions({ breaks: true, gfm: true });

// Styles for mp-html
// hr: 美化 Markdown 分割线，使用渐变背景从两边透明渐变到中间灰色
const mpHtmlTagStyle = {
    p: 'margin: 10px 0; line-height: 1.8; color: #333; text-align: justify; display: inline;',
    h1: 'font-size: 18px; font-weight: bold; margin: 20px 0 10px 0;',
    h2: 'font-size: 16px; font-weight: bold; margin: 16px 0 10px 0; color: #333; border-left: 4px solid #ff9800; padding-left: 10px;',
    h3: 'font-size: 15px; font-weight: bold; margin: 14px 0 8px 0; color: #333;',
    ul: 'margin: 0; padding: 0; padding-left: 0; margin-left: 0; list-style-position: inside; line-height: 1.8;',
    ol: 'margin: 0; padding: 0; padding-left: 0; margin-left: 0; list-style-position: inside; line-height: 1.8;',
    li: 'margin: 5px 0; padding: 0; padding-left: 0; margin-left: 0; color: #555; line-height: 1.8; text-indent: 0; display: list-item;',
    strong: 'color: #000; font-weight: 700; display: inline;',
    em: 'display: inline;',
    hr: 'border: none; height: 1px; background: linear-gradient(to right, transparent, #e0e0e0 20%, #e0e0e0 80%, transparent); margin: 24px 0;'
};

// State
const bannerCards = ref([
    { image: 'https://oss.swimmingliu.cn/foodie_paradise/8c0e4d50-ffbe-4659-8c3b-6f485355ef53.jpg', title: '酸菜鱼', desc: '预制菜重灾区？' },
    { image: 'https://oss.swimmingliu.cn/foodie_paradise/9cdfa36a-5463-4178-bb74-a70a6027a646.jpg', title: '小炒黄牛肉', desc: '如何分辨现炒？' },
    { image: 'https://oss.swimmingliu.cn/foodie_paradise/d6443171-7424-4a11-b523-5d30051e4185.jpg', title: '红烧肉', desc: '看汤汁识预制' },
    { image: 'https://oss.swimmingliu.cn/foodie_paradise/dede5bee-78f7-47e5-a05b-3b81665662f6.jpg', title: '水晶虾仁', desc: '质地是关键' },
    { image: 'https://oss.swimmingliu.cn/foodie_paradise/b1dfa3df-f8b4-4310-973d-28e946fb96cf.jpg', title: '宫保鸡丁', desc: '配料统一的秘密' }
]);
const currentBannerIndex = ref(0);
const currentImage = ref(null);
const analyzing = ref(false);
const thoughts = ref([]);
const showThoughts = ref(true);
const result = ref('');
const resultJsonBlock = ref(''); // separate storage for json block
const structuredResult = ref(null);
const scrollIntoView = ref('');

// Computed
const cleanReportText = computed(() => {
    // Remove JSON block from display text if it exists
    return result.value.replace(/```json[\s\S]*?```/g, '').trim();
});

/**
 * 解析报告内容为三个部分：鉴定结论、深度拆解、综合评价
 * 根据标题关键词拆分 Markdown 内容
 */
const reportSections = computed(() => {
    const text = cleanReportText.value;
    if (!text) return { conclusion: '', breakdown: '', evaluation: '' };
    
    // 定义各部分的标题关键词（支持多种格式）
    const conclusionPatterns = ['🧐 鉴定结论', '🧐鉴定结论', '## 鉴定结论', '# 鉴定结论'];
    const breakdownPatterns = ['🥩 深度拆解', '🥩深度拆解', '## 深度拆解', '# 深度拆解'];
    const evaluationPatterns = ['📝 综合评价', '📝综合评价', '## 综合评价', '# 综合评价'];
    
    // 查找各部分的起始位置
    const findPosition = (patterns) => {
        for (const pattern of patterns) {
            const idx = text.indexOf(pattern);
            if (idx !== -1) return { index: idx, pattern };
        }
        return { index: -1, pattern: '' };
    };
    
    const conclusionPos = findPosition(conclusionPatterns);
    const breakdownPos = findPosition(breakdownPatterns);
    const evaluationPos = findPosition(evaluationPatterns);
    
    // 提取各部分内容
    let conclusion = '';
    let breakdown = '';
    let evaluation = '';
    
    // 按位置排序并提取
    const positions = [
        { name: 'conclusion', ...conclusionPos },
        { name: 'breakdown', ...breakdownPos },
        { name: 'evaluation', ...evaluationPos }
    ].filter(p => p.index !== -1).sort((a, b) => a.index - b.index);
    
    for (let i = 0; i < positions.length; i++) {
        const current = positions[i];
        const next = positions[i + 1];
        const startIdx = current.index + current.pattern.length;
        const endIdx = next ? next.index : text.length;
        const content = text.substring(startIdx, endIdx).trim();
        
        if (current.name === 'conclusion') conclusion = content;
        else if (current.name === 'breakdown') breakdown = content;
        else if (current.name === 'evaluation') evaluation = content;
    }
    
    return { conclusion, breakdown, evaluation };
});

/**
 * 检查是否有任何报告部分内容
 */
const hasReportSections = computed(() => {
    const sections = reportSections.value;
    return sections.conclusion || sections.breakdown || sections.evaluation;
});

// Methods
const onSwiperChange = (e) => {
    currentBannerIndex.value = e.detail.current;
};

const selectBannerCard = (item) => {
    currentImage.value = item.image;
    // For local static images, we need to upload them first or mock the path if backend supports it
    // Here we reuse the upload logic
    uploadAndAnalyze(item.image, true);
};

const chooseImage = () => {
    uni.chooseImage({
        count: 1,
        success: (res) => {
            currentImage.value = res.tempFilePaths[0];
            uploadAndAnalyze(res.tempFilePaths[0]);
        }
    });
};

const previewImage = () => {
    if(currentImage.value) {
        uni.previewImage({ urls: [currentImage.value] });
    }
};

const resetState = () => {
    currentImage.value = null;
    result.value = '';
    thoughts.value = [];
    structuredResult.value = null;
    analyzing.value = false;
};

const toggleThoughts = () => {
    showThoughts.value = !showThoughts.value;
};

const uploadAndAnalyze = (filePath, isStatic = false) => {
    analyzing.value = true;
    thoughts.value = [];
    result.value = '';
    structuredResult.value = null;
    showThoughts.value = true;

    // Handle static paths or remote URLs
    const fullPath = isStatic && filePath.startsWith('/') ? filePath : filePath;

    // 如果是远程图片(http/https开头)，直接使用，无需上传
    if (fullPath && (fullPath.startsWith('http://') || fullPath.startsWith('https://'))) {
        startStreamAnalysis(fullPath);
        return;
    }

    uni.uploadFile({
        url: API_ENDPOINTS.UPLOAD,
        filePath: fullPath,
        name: 'file',
        success: (uploadRes) => {
            try {
                const data = JSON.parse(uploadRes.data);
                const remotePath = data.file_path;
                startStreamAnalysis(remotePath);
            } catch (e) {
                console.error('Upload parse failed', e);
                uni.showToast({ title: '上传失败', icon: 'none' });
                analyzing.value = false;
            }
        },
        fail: (e) => {
            console.error('Upload failed', e);
            uni.showToast({ title: '网络错误', icon: 'none' });
            analyzing.value = false;
        }
    });
};

const startStreamAnalysis = (remotePath) => {
    streamRequest({
        url: API_ENDPOINTS.CHECK_PREMADE,
        method: 'POST',
        data: { file_path: remotePath },
        onEvent: (eventType, data) => {
            if (!data) return;
            const decoded = decodeHTMLEntities(data);
            
            if (eventType === 'thought') {
                thoughts.value.push(decoded);
            } else if (eventType === 'message') {
                result.value += decoded;
                extractStructuredData(result.value);
            }
        },
        onComplete: () => {
            analyzing.value = false;
            // Final extraction
            extractStructuredData(result.value);
            // Auto collapse thoughts on completion
            showThoughts.value = false;
            
            // 输出完整的 LLM 返回内容到控制台
            console.log('\n========== 查预制页面 - LLM 完整返回内容 ==========');
            console.log('\n--- 思考过程 (Thoughts) ---');
            console.log(thoughts.value.join(''));
            console.log('\n--- 结果内容 (Result) ---');
            console.log(result.value);
            console.log('\n--- 清理后的报告文本 (Clean Report) ---');
            console.log(cleanReportText.value);
            console.log('\n--- 拆分后的三个部分 (Report Sections) ---');
            console.log('鉴定结论:', reportSections.value.conclusion);
            console.log('深度拆解:', reportSections.value.breakdown);
            console.log('综合评价:', reportSections.value.evaluation);
            console.log('\n--- 结构化数据 (Structured Result) ---');
            console.log(JSON.stringify(structuredResult.value, null, 2));
            console.log('='.repeat(50) + '\n');
        },
        onError: (err) => {
            console.error(err);
            result.value += '\n\n**分析出错，请重试**';
            analyzing.value = false;
        }
    });
};

const extractStructuredData = (text) => {
    // Try to find JSON block
    const match = text.match(/```json\s*([\s\S]*?)\s*```/);
    if (match) {
        try {
            const jsonStr = match[1];
            // Fix common JSON issues if necessary
            const data = JSON.parse(jsonStr);
            structuredResult.value = data;
        } catch (e) {
            // Partial JSON, ignore until complete
        }
    }
};

const getFreshnessClass = (status) => {
    if (!status) return '';
    if (status.includes('现炒')) return 'fresh';
    if (status.includes('半预制')) return 'semi';
    return 'premade';
};

const getFreshnessIcon = (status) => {
    if (!status) return '⏳';
    if (status.includes('现炒')) return '🔥';
    if (status.includes('半预制')) return '⚠️';
    return '🧊';
};

const decodeHTMLEntities = (text) => {
    if (!text) return '';
    const entities = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&nbsp;': ' ' };
    return text.replace(/&amp;|&lt;|&gt;|&quot;|&#39;|&nbsp;/g, m => entities[m] || m);
};

const parseMarkdown = (content) => {
    if (!content) return '';
    try {
        // 先解码 HTML 实体，再解析 markdown
        const decoded = decodeHTMLEntities(content);
        // 将字面 \n 字符串替换为实际换行符
        const withNewlines = decoded.replace(/\\n/g, '\n');
        return marked.parse(withNewlines);
    } catch (e) {
        console.error('Markdown parse error:', e);
        return content;
    }
};
</script>

<style>
.container {
    height: 100vh;
    background-color: #f8f9fa;
    display: flex;
    flex-direction: column;
}

.content-area {
    flex: 1;
    height: 100%;
}


/* Initial State Layout */
.initial-state {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding-bottom: 0;
}

/* Header */
.header-section {
    padding: 60rpx 40rpx 20rpx;
    text-align: center;
}
.header-title-row {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10rpx;
}
.header-icon {
    width: 56rpx;
    height: 56rpx;
    margin-right: 12rpx;
}
.header-title {
    font-size: 48rpx;
    font-weight: 800;
    color: #333;
}
.header-slogan {
    font-size: 28rpx;
    color: #999;
}

/* Swiper */
.card-swiper {
    width: 100%;
    height: 800rpx;
    margin-top: 60rpx;
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
    padding: 60rpx 40rpx 40rpx;
    background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
    color: #fff;
    display: flex;
    flex-direction: column;
}
.card-category {
    font-size: 40rpx;
    font-weight: bold;
    margin-bottom: 10rpx;
}
.card-question {
    font-size: 28rpx;
    opacity: 0.9;
}

/* Upload Section - Pushed to bottom */
.upload-section {
    margin-top: auto;
    margin-bottom: 0;
    padding: 60rpx 60rpx 80rpx;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.upload-main-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 500rpx;
    height: 100rpx;
    background: linear-gradient(135deg, #667eea 0%, #5568e5 50%, #4361ee 100%);
    border-radius: 50rpx;
    box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.3);
    margin-bottom: 32rpx;
    color: #fff;
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
    font-weight: 500;
    font-size: 32rpx;
}
.upload-hint {
    color: #999;
    font-size: 26rpx;
}

/* Analysis Result */
.analysis-container {
    padding: 30rpx;
}

.preview-header {
    width: 100%;
    height: 400rpx;
    border-radius: 30rpx;
    overflow: hidden;
    margin-bottom: 30rpx;
    position: relative;
    box-shadow: 0 10rpx 30rpx rgba(0,0,0,0.1);
}
.result-image {
    width: 100%;
    height: 100%;
}
.re-upload-btn {
    position: absolute;
    top: 20rpx;
    right: 20rpx;
    background: rgba(0,0,0,0.6);
    color: #fff;
    padding: 10rpx 24rpx;
    border-radius: 30rpx;
    font-size: 24rpx;
    backdrop-filter: blur(10px);
}

/* Thought Card */
.thought-card {
    background: #fff;
    border-radius: 20rpx;
    padding: 24rpx;
    margin-bottom: 30rpx;
    border: 1px solid #eee;
}
.thought-header {
    display: flex;
    align-items: center;
}
.thought-icon {
    margin-right: 16rpx;
}
.thought-title {
    flex: 1;
    font-size: 28rpx;
    color: #666;
    font-weight: 600;
}
.thought-arrow {
    transform: rotate(0deg);
    transition: transform 0.3s;
    color: #999;
}
.thought-arrow.expanded {
    transform: rotate(90deg);
}
.thought-body {
    margin-top: 20rpx;
    padding-top: 20rpx;
    border-top: 1px solid #f5f5f5;
}
.thought-content {
    font-size: 24rpx;
    color: #666;
    line-height: 1.6;
}

/* Dashboard Card */
.dashboard-card {
    background: #fff;
    border-radius: 30rpx;
    padding: 40rpx;
    margin-bottom: 30rpx;
    box-shadow: 0 10rpx 40rpx rgba(0,0,0,0.08); /* Enhanced shadow */
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(0,0,0,0.02);
}
.dish-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 40rpx;
}
.dish-name {
    font-size: 40rpx;
    font-weight: 800;
    color: #333;
}
.freshness-tag {
    display: flex;
    align-items: center;
    padding: 10rpx 24rpx;
    border-radius: 100rpx;
    font-size: 26rpx;
    font-weight: 600;
}
.freshness-tag.fresh { background: #e6f7eb; color: #00b34d; }
.freshness-tag.semi { background: #fff8e1; color: #ff9800; }
.freshness-tag.premade { background: #ffebee; color: #f44336; }
.freshness-icon { margin-right: 8rpx; }

.score-bar {
    display: flex;
    align-items: center;
    gap: 20rpx;
}
.score-label {
    font-size: 26rpx;
    color: #666;
}
.progress-bg {
    flex: 1;
    height: 16rpx;
    background: #f0f0f0;
    border-radius: 10rpx;
    overflow: hidden;
}
.progress-fill {
    height: 100%;
    background: #333;
    border-radius: 10rpx;
    transition: width 0.5s ease;
}
.score-value {
    font-size: 32rpx;
    font-weight: 700;
    color: #333;
}

/* Stamp Animation */
.stamp {
    position: absolute;
    right: -20rpx;
    top: -20rpx;
    width: 200rpx;
    height: 200rpx;
    border: 6rpx solid;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transform: rotate(-20deg);
    opacity: 0.2;
    font-weight: 900;
    font-size: 50rpx;
    letter-spacing: 10rpx;
    pointer-events: none;
}
.stamp.fresh { color: #00b34d; border-color: #00b34d; }
.stamp.semi { color: #ff9800; border-color: #ff9800; }
.stamp.premade { color: #f44336; border-color: #f44336; }

/* Report Card */
.report-card {
    background: #fff;
    border-radius: 30rpx;
    padding: 40rpx;
    box-shadow: 0 10rpx 40rpx rgba(0,0,0,0.08); /* Enhanced shadow */
    margin-bottom: 40rpx;
    border: 1px solid rgba(0,0,0,0.02);
}
.report-title-row {
    display: flex;
    align-items: center;
    margin-bottom: 30rpx;
    border-bottom: 2rpx solid #f5f5f5;
    padding-bottom: 20rpx;
}
.report-icon { margin-right: 16rpx; font-size: 36rpx; }
.report-title {
    font-size: 32rpx;
    font-weight: 700;
    color: #333;
}

/* Section Cards - 三个报告卡片的通用样式 */
.section-card {
    background: #fff;
    border-radius: 24rpx;
    padding: 32rpx;
    margin-bottom: 24rpx;
    box-shadow: 0 8rpx 32rpx rgba(0,0,0,0.06);
    border: 1px solid rgba(0,0,0,0.02);
    position: relative;
    overflow: hidden;
}

.section-title-row {
    display: flex;
    align-items: center;
    margin-bottom: 24rpx;
    padding-bottom: 16rpx;
    border-bottom: 2rpx solid #f5f5f5;
}

.section-icon {
    font-size: 40rpx;
    margin-right: 16rpx;
}

.section-title {
    font-size: 32rpx;
    font-weight: 700;
    color: #333;
}

.section-content {
    line-height: 1.8;
}

/* 鉴定结论卡片 - 绿色主题 */
.conclusion-card {
    border-left: 6rpx solid #4caf50;
}
.conclusion-card .section-title-row {
    border-bottom-color: rgba(76, 175, 80, 0.2);
}
.conclusion-card .section-title {
    color: #2e7d32;
}

/* 深度拆解卡片 - 橙色主题 */
.breakdown-card {
    border-left: 6rpx solid #ff9800;
}
.breakdown-card .section-title-row {
    border-bottom-color: rgba(255, 152, 0, 0.2);
}
.breakdown-card .section-title {
    color: #e65100;
}

/* 综合评价卡片 - 蓝色主题 */
.evaluation-card {
    border-left: 6rpx solid #2196f3;
}
.evaluation-card .section-title-row {
    border-bottom-color: rgba(33, 150, 243, 0.2);
}
.evaluation-card .section-title {
    color: #1565c0;
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

.analyzing-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40rpx 0;
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
