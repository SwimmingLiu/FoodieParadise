<template>
  <view class="container">
    <view class="header">
      <text class="title">Check Pre-made</text>
      <text class="subtitle">Upload a photo to analyze freshness</text>
    </view>

    <!-- Upload Area -->
    <view class="upload-area" @click="chooseImage" v-if="!currentImage">
      <view class="placeholder">
        <text class="icon">📷</text>
        <text>Tap to Upload</text>
      </view>
    </view>
    <view class="preview-area" v-else>
      <image :src="currentImage" mode="aspectFill" class="preview-image"></image>
      <view class="re-upload" @click="chooseImage">Retake</view>
    </view>

    <!-- Analysis Result -->
    <scroll-view class="result-area" scroll-y v-if="analyzing || result">
      <!-- Thoughts -->
      <view class="thoughts" v-if="thoughts.length > 0">
        <text class="thought-label">AI Thinking:</text>
        <view v-for="(t, i) in thoughts" :key="i" class="thought-item">
          {{ t }}
        </view>
      </view>

      <!-- Report -->
      <view class="report" v-if="result">
        <text class="report-content">{{ result }}</text>
      </view>
      
      <view class="loading" v-if="analyzing && !result">
        <text>Analyzing...</text>
      </view>
    </scroll-view>
    
    <button class="analyze-btn" @click="startAnalysis" v-if="currentImage && !analyzing">Analyze</button>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { streamRequest } from '../../utils/request.js';

const currentImage = ref(null);
const analyzing = ref(false);
const thoughts = ref([]);
const result = ref('');

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
      
      // 2. Stream
      streamRequest({
        url: 'http://localhost:8000/api/check-premade',
        method: 'POST',
        data: { file_path: filePath },
        onChunk: (text) => {
            const lines = text.split('\n');
            let currentEvent = null;
            for (let line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.substring(7).trim();
                } else if (line.startsWith('data: ')) {
                    const content = line.substring(6);
                    if (!content) continue;
                    
                    if (currentEvent === 'thought') {
                        thoughts.value.push(content);
                    } else if (currentEvent === 'message') {
                        result.value += content; // Markdown content
                    }
                }
            }
        },
        onComplete: () => {
            analyzing.value = false;
        },
        onError: (err) => {
            console.error(err);
            result.value += "\n[Error: Analysis failed]";
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
  background-color: #ff9800;
  color: #fff;
  border-radius: 50rpx;
}
</style>
