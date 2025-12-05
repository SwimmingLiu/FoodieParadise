<template>
  <view class="container">
    <view class="header">
      <text class="title">吃多少</text>
      <text class="subtitle">估算餐食热量</text>
    </view>

    <!-- Upload Area -->
    <view class="upload-area" @click="chooseImage" v-if="!currentImage">
      <view class="placeholder">
        <text class="icon">📷</text>
        <text>点击上传</text>
      </view>
    </view>
    <view class="preview-area" v-else>
      <image :src="currentImage" mode="aspectFill" class="preview-image"></image>
      
      <!-- Annotations -->
      <view v-for="(item, index) in annotations" :key="index" class="annotation-box" 
            :style="{ top: item.bbox[1] + 'rpx', left: item.bbox[0] + 'rpx', width: (item.bbox[2]-item.bbox[0]) + 'rpx', height: (item.bbox[3]-item.bbox[1]) + 'rpx' }">
        <text class="annotation-label">{{ item.name }}: {{ item.calories }}kcal</text>
      </view>
      
      <view class="re-upload" @click="chooseImage">重拍</view>
    </view>

    <!-- Analysis Result -->
    <scroll-view class="result-area" scroll-y v-if="analyzing || result">
      <!-- Thoughts -->
      <view class="thoughts" v-if="thoughts.length > 0">
        <text class="thought-label">AI 思考中：</text>
        <view v-for="(t, i) in thoughts" :key="i" class="thought-item">
          {{ t }}
        </view>
      </view>

      <!-- Report with Markdown support -->
      <view class="report" v-if="result">
        <mp-html :content="parseMarkdown(result)" />
      </view>
      
      <view class="loading" v-if="analyzing && !result">
        <text>分析中...</text>
      </view>
    </scroll-view>
    
    <button class="analyze-btn" @click="startAnalysis" v-if="currentImage && !analyzing">开始分析</button>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { streamRequest } from '../../utils/request.js';
import mpHtml from 'mp-html/dist/uni-app/components/mp-html/mp-html.vue';
import { marked } from 'marked';

// Configure marked for safe and clean markdown parsing
marked.setOptions({
    breaks: true,
    gfm: true,
});

const currentImage = ref(null);
const analyzing = ref(false);
const thoughts = ref([]);
const result = ref('');
const annotations = ref([]);

const chooseImage = () => {
  uni.chooseImage({
    count: 1,
    success: (res) => {
      currentImage.value = res.tempFilePaths[0];
      resetAnalysis();
    }
  });
};

const resetAnalysis = () => {
  analyzing.value = false;
  thoughts.value = [];
  result.value = '';
  annotations.value = [];
};

const startAnalysis = () => {
  if (!currentImage.value) return;
  
  analyzing.value = true;
  
  // 1. Upload
  uni.uploadFile({
    url: 'http://localhost:8000/api/upload',
    filePath: currentImage.value,
    name: 'file',
    success: (uploadRes) => {
      const data = JSON.parse(uploadRes.data);
      const filePath = data.file_path;
      
      // 2. Stream with proper event handling
      streamRequest({
        url: 'http://localhost:8000/api/calories',
        method: 'POST',
        data: { file_path: filePath },
        onEvent: (eventType, data) => {
            if (!data) return;
            
            if (eventType === 'thought') {
                thoughts.value.push(decodeHTMLEntities(data));
            } else if (eventType === 'message') {
                result.value += decodeHTMLEntities(data);
            } else if (eventType === 'function_call') {
                try {
                    const call = JSON.parse(data);
                    if (call.action === 'annotate_image') {
                        annotations.value = call.items;
                    }
                } catch (e) {
                    console.error("Error parsing annotations", e);
                }
            }
        },
        onComplete: () => {
            analyzing.value = false;
        },
        onError: (err) => {
            console.error(err);
            result.value += "\n[错误：分析失败]";
            analyzing.value = false;
        }
      });
    },
    fail: (err) => {
        console.error(err);
        analyzing.value = false;
    }
  });
};

/**
 * Decode HTML entities (e.g., &gt; -> >)
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
 * Parse markdown content to HTML
 */
const parseMarkdown = (content) => {
    if (!content) return '';
    try {
        return marked.parse(content);
    } catch (e) {
        console.error('Markdown parse error:', e);
        return content;
    }
};
</script>

<style>
.container {
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-sizing: border-box;
}
.header {
  margin-bottom: 30rpx;
}
.title {
  font-size: 40rpx;
  font-weight: bold;
  display: block;
}
.subtitle {
  font-size: 28rpx;
  color: #666;
}
.upload-area {
  height: 400rpx;
  background-color: #f0f0f0;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30rpx;
  border: 2px dashed #ccc;
}
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
}
.icon {
  font-size: 60rpx;
  margin-bottom: 10rpx;
}
.preview-area {
  height: 400rpx;
  position: relative;
  margin-bottom: 30rpx;
}
.preview-image {
  width: 100%;
  height: 100%;
  border-radius: 20rpx;
}
.re-upload {
  position: absolute;
  bottom: 20rpx;
  right: 20rpx;
  background-color: rgba(0,0,0,0.6);
  color: #fff;
  padding: 10rpx 20rpx;
  border-radius: 30rpx;
  font-size: 24rpx;
}
.annotation-box {
  position: absolute;
  border: 2px solid #ff9800;
  background-color: rgba(255, 152, 0, 0.2);
}
.annotation-label {
  position: absolute;
  top: -30rpx;
  left: 0;
  background-color: #ff9800;
  color: #fff;
  font-size: 20rpx;
  padding: 2rpx 6rpx;
  border-radius: 4rpx;
  white-space: nowrap;
}
.result-area {
  flex: 1;
  background-color: #fff;
  border-radius: 20rpx;
  padding: 20rpx;
  border: 1px solid #eee;
  margin-bottom: 20rpx;
}
.thoughts {
  background-color: #f9f9f9;
  padding: 15rpx;
  border-radius: 10rpx;
  margin-bottom: 20rpx;
}
.thought-label {
  font-size: 24rpx;
  color: #999;
  margin-bottom: 10rpx;
  display: block;
}
.thought-item {
  font-size: 24rpx;
  color: #666;
  margin-bottom: 5rpx;
}
.report-content {
  font-size: 28rpx;
  line-height: 1.6;
  white-space: pre-wrap;
}
.analyze-btn {
  background-color: #4caf50;
  color: #fff;
  border-radius: 50rpx;
}
</style>
