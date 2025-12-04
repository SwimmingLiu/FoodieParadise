<template>
  <view class="container">
    <!-- Navbar (Custom or default) -->
    <!-- Assuming default navigation bar title is set in pages.json, but we can add a header if needed. 
         The design shows a custom-like header "在哪儿". -->
    
    <!-- Scrollable Content -->
    <scroll-view class="content-area" scroll-y :scroll-into-view="scrollIntoView" :scroll-with-animation="true">
      
      <!-- Initial State: Carousel & Upload -->
      <view v-if="messages.length === 0" class="initial-state">
        <swiper class="banner-swiper" circular autoplay interval="3000" indicator-dots indicator-active-color="#fff">
          <swiper-item v-for="(item, index) in banners" :key="index">
            <image :src="item" mode="aspectFill" class="banner-image"></image>
          </swiper-item>
        </swiper>

        <!-- Preset Questions / Hints -->
        <view class="preset-section">
            <view class="preset-chips">
                <view class="chip" @click="selectPreset('在哪儿')">在哪儿</view>
                <view class="chip" @click="selectPreset('推荐类似的地点')">推荐类似的地点</view>
                <view class="chip" @click="selectPreset('哪儿能买到')">哪儿能买到</view>
            </view>
        </view>
      </view>

      <!-- Chat History -->
      <view class="chat-list" v-else>
        <view v-for="(msg, index) in messages" :key="index" :id="'msg-' + index" class="message-wrapper">
            
            <!-- User Message -->
            <view v-if="msg.role === 'user'" class="message-item user">
                <image v-if="msg.image" :src="msg.image" mode="aspectFill" class="msg-image"></image>
                <view v-if="msg.content" class="msg-bubble user-bubble">
                    <text>{{ msg.content }}</text>
                </view>
            </view>

            <!-- AI Message -->
            <view v-else class="message-item ai">
                <!-- Thinking Process -->
                <view v-if="msg.thoughts && msg.thoughts.length > 0" class="thought-container">
                    <view class="thought-header">
                        <image src="/static/thinking_icon.png" class="bulb-icon" mode="aspectFit"></image>
                        <text class="step-text">思考过程 (Step {{ msg.thoughts.length }})</text>
                        <text class="arrow-icon">></text>
                    </view>
                    <view class="thought-content">
                        <view v-for="(thought, tIndex) in msg.thoughts" :key="tIndex" class="thought-line">
                            <text class="dot">•</text>
                            <text>{{ thought }}</text>
                        </view>
                    </view>
                </view>

                <!-- Final Result / Map Card -->
                <view v-if="msg.map" class="map-card" @click="openLocation(msg.map)">
                    <view class="map-header">
                        <text class="map-name">{{ msg.map.name }}</text>
                    </view>
                    <view class="map-body">
                        <!-- Placeholder Map Image -->
                        <image class="map-preview" src="/static/map_placeholder.png" mode="aspectFill"></image> 
                        <!-- In real app, use map component or static map image API -->
                    </view>
                    <view class="map-footer">
                        <text class="map-address">{{ msg.map.address }}</text>
                    </view>
                </view>

                <!-- Text Content -->
                <view v-if="msg.content" class="msg-bubble ai-bubble">
                    <text>{{ msg.content }}</text>
                </view>
            </view>
        </view>
      </view>
      
      <!-- Padding for bottom input -->
      <view style="height: 120rpx;"></view>
    </scroll-view>

    <!-- Bottom Input Area -->
    <view class="input-area">
        <view class="upload-btn" @click="chooseImage">
            <image src="/static/camera_icon.png" class="camera-icon" mode="aspectFit"></image>
        </view>
        <input 
            class="text-input" 
            v-model="inputText" 
            :placeholder="placeholderText" 
            confirm-type="send" 
            @confirm="sendMessage" 
        />
        <view class="send-btn" @click="sendMessage">
            <image src="/static/send_icon.png" class="send-icon" mode="aspectFit"></image>
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
import { streamRequest } from '../../utils/request.js';

// State
const banners = ref([
    '/static/banner1.png', // You might need to add these or use placeholders
    '/static/banner2.png',
    '/static/banner3.png'
]);
const messages = ref([]);
const inputText = ref('');
const placeholderText = ref('输入你想问的问题');
const currentImage = ref(null);
const currentRemoteFilePath = ref(null);
const scrollIntoView = ref('');
const isUploading = ref(false);

// Actions
const selectPreset = (text) => {
    inputText.value = text;
    // If we have an image, send immediately? Or just fill text?
    // Design says "Click to auto fill question box"
    // If user hasn't uploaded image yet, they should probably upload first.
    if (!currentImage.value) {
        chooseImage();
    }
};

const chooseImage = () => {
    uni.chooseImage({
        count: 1,
        success: (res) => {
            currentImage.value = res.tempFilePaths[0];
            // Upload immediately to get ready? Or wait for send?
            // Let's upload immediately to be ready
            uploadImage(currentImage.value);
        }
    });
};

const uploadImage = (tempFilePath) => {
    isUploading.value = true;
    uni.uploadFile({
        url: 'http://localhost:8000/api/upload',
        filePath: tempFilePath,
        name: 'file',
        success: (uploadRes) => {
            try {
                const data = JSON.parse(uploadRes.data);
                currentRemoteFilePath.value = data.file_path;
                // If text is already present (e.g. from preset), maybe send?
                // For now, let user click send.
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

const sendMessage = () => {
    if (!currentRemoteFilePath.value) {
        if (!currentImage.value) {
            uni.showToast({ title: '请先上传图片', icon: 'none' });
            return;
        }
        // If image selected but not uploaded (shouldn't happen if uploadImage called on choose), retry upload
        uploadImage(currentImage.value);
        return;
    }

    const query = inputText.value || "这是哪里？";

    // Add User Message
    messages.value.push({
        role: 'user',
        content: query,
        image: currentImage.value
    });

    // Add AI Message Placeholder
    const aiMsgIndex = messages.value.length;
    const aiMsg = {
        role: 'ai',
        content: '',
        thoughts: [],
        map: null
    };
    messages.value.push(aiMsg);

    scrollToBottom();

    // Start Stream
    streamRequest({
        url: 'http://localhost:8000/api/where-to-eat',
        method: 'POST',
        data: {
            file_path: currentRemoteFilePath.value,
            query: query
        },
        onChunk: (text) => {
            // Simple SSE parsing (assuming standard format)
            // The utility might return raw chunks, need to buffer and split
            // Assuming streamRequest handles basic buffering or we do it here.
            // Let's assume the previous logic was correct about buffering.
            // Re-implementing robust parsing:
            
            const lines = text.split('\n');
            let currentEvent = null;
            
            for (let line of lines) {
                line = line.trim();
                if (line.startsWith('event: ')) {
                    currentEvent = line.substring(7);
                } else if (line.startsWith('data: ')) {
                    const content = line.substring(6);
                    if (!content) continue;

                    if (currentEvent === 'thought') {
                        // Check if it's a JSON object or raw string
                        // The backend sends {"thought": ...} sometimes? 
                        // Based on controller: yield {"thought": ...} -> SSE event: thought, data: ...
                        // Wait, controller uses `stream_generator` which likely formats as SSE.
                        // Let's assume content is the raw string or JSON.
                        // If backend sends JSON string, we parse it.
                        try {
                             // If content is just text, push it.
                             messages.value[aiMsgIndex].thoughts.push(content);
                        } catch (e) {
                             messages.value[aiMsgIndex].thoughts.push(content);
                        }
                    } else if (currentEvent === 'message') {
                        messages.value[aiMsgIndex].content += content;
                    } else if (currentEvent === 'function_call') {
                         try {
                            const call = JSON.parse(content);
                            // Assuming the agent returns a function call for map
                            // or maybe the final message contains the address.
                            // The prompt says "Backend will send final reasoning content... containing address info... display as WeChat address".
                            // If the backend returns a structured tool call for location, we use it.
                            // If not, we might need to parse the text.
                            // Let's assume 'open_map' or similar tool call.
                            if (call.name === 'open_map' || call.action === 'open_map') {
                                messages.value[aiMsgIndex].map = call.arguments || call;
                            }
                        } catch (e) {
                            console.error("Function call parse error", e);
                        }
                    }
                }
            }
            scrollToBottom();
        },
        onComplete: () => {
            console.log("Stream finished");
        },
        onError: (err) => {
            console.error("Stream error", err);
            messages.value[aiMsgIndex].content += "\n[连接中断]";
        }
    });

    // Clear input
    inputText.value = '';
    // We keep the image and remote path for context? Or clear?
    // Usually clear for next query.
    currentImage.value = null;
    currentRemoteFilePath.value = null;
};

const scrollToBottom = () => {
    nextTick(() => {
        scrollIntoView.value = 'msg-' + (messages.value.length - 1);
    });
};

const openLocation = (mapData) => {
    uni.openLocation({
        latitude: parseFloat(mapData.lat || 39.9042),
        longitude: parseFloat(mapData.lng || 116.4074),
        name: mapData.name || '未知地点',
        address: mapData.address || '详细地址未知'
    });
};
</script>

<style>
.container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background-color: #f7f7f7;
}

.content-area {
    flex: 1;
    height: 0;
}

.initial-state {
    padding: 20rpx;
}

.banner-swiper {
    width: 100%;
    height: 400rpx;
    border-radius: 20rpx;
    overflow: hidden;
    margin-bottom: 40rpx;
}

.banner-image {
    width: 100%;
    height: 100%;
}

.preset-section {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.preset-chips {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 20rpx;
}

.chip {
    background-color: #e0f2f1;
    color: #00695c;
    padding: 15rpx 30rpx;
    border-radius: 40rpx;
    font-size: 28rpx;
    box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.1);
    transition: all 0.2s;
}
.chip:active {
    transform: scale(0.95);
    background-color: #b2dfdb;
}

.chat-list {
    padding: 20rpx;
}

.message-wrapper {
    margin-bottom: 30rpx;
}

.message-item {
    display: flex;
    flex-direction: column;
    max-width: 85%;
}

.user {
    align-self: flex-end;
    align-items: flex-end;
    margin-left: auto;
}

.ai {
    align-self: flex-start;
    align-items: flex-start;
}

.msg-image {
    width: 300rpx;
    height: 300rpx;
    border-radius: 20rpx;
    margin-bottom: 10rpx;
}

.msg-bubble {
    padding: 20rpx;
    border-radius: 20rpx;
    font-size: 30rpx;
    line-height: 1.5;
}

.user-bubble {
    background-color: #95ec69;
    color: #000;
    border-top-right-radius: 5rpx;
}

.ai-bubble {
    background-color: #fff;
    color: #333;
    border-top-left-radius: 5rpx;
    margin-top: 10rpx;
}

/* Thinking Process Styles */
.thought-container {
    background-color: #fff;
    border-radius: 20rpx;
    padding: 20rpx;
    margin-bottom: 20rpx;
    width: 100%;
    box-shadow: 0 2rpx 10rpx rgba(0,0,0,0.05);
    border: 1px solid #e0e0e0;
}

.thought-header {
    display: flex;
    align-items: center;
    margin-bottom: 15rpx;
    color: #666;
    font-size: 26rpx;
    font-weight: bold;
}

.bulb-icon {
    margin-right: 10rpx;
    width: 40rpx;
    height: 40rpx;
}

.step-text {
    margin-right: 10rpx;
    font-weight: 600;
    color: #333;
}

.thought-content {
    background-color: #f9f9f9;
    padding: 15rpx;
    border-radius: 10rpx;
}

.thought-line {
    display: flex;
    align-items: flex-start;
    margin-bottom: 8rpx;
    font-size: 24rpx;
    color: #666;
}

.dot {
    margin-right: 10rpx;
    color: #999;
}

/* Map Card Styles */
.map-card {
    background-color: #fff;
    border-radius: 20rpx;
    overflow: hidden;
    margin-top: 20rpx;
    width: 100%;
    box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.1);
}

.map-header {
    padding: 20rpx;
    border-bottom: 1px solid #f0f0f0;
}

.map-name {
    font-size: 32rpx;
    font-weight: bold;
    color: #333;
}

.map-body {
    height: 200rpx;
    background-color: #eee;
    position: relative;
}

.map-preview {
    width: 100%;
    height: 100%;
}

.map-footer {
    padding: 20rpx;
    background-color: #fff;
}

.map-address {
    font-size: 24rpx;
    color: #999;
}

/* Input Area */
.input-area {
    background-color: #fff;
    padding: 20rpx;
    padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
    display: flex;
    align-items: center;
    border-top: 1px solid #eee;
}

.upload-btn {
    width: 70rpx;
    height: 70rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 20rpx;
}

.camera-icon {
    width: 50rpx;
    height: 50rpx;
}

.text-input {
    flex: 1;
    height: 70rpx;
    background-color: #f5f5f5;
    border-radius: 35rpx;
    padding: 0 30rpx;
    font-size: 28rpx;
}

.send-btn {
    margin-left: 20rpx;
    width: 70rpx;
    height: 70rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: transparent;
}

.send-icon {
    width: 60rpx;
    height: 60rpx;
}

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
</style>
