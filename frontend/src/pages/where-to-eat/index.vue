<template>
  <view class="container">
    <!-- Chat Area -->
    <scroll-view class="chat-area" scroll-y :scroll-into-view="scrollIntoView">
      <view v-for="(msg, index) in messages" :key="index" :id="'msg-' + index" class="message-item">
        <!-- User Message -->
        <view v-if="msg.role === 'user'" class="message user">
          <image v-if="msg.image" :src="msg.image" mode="aspectFit" class="msg-image"></image>
          <text v-if="msg.content">{{ msg.content }}</text>
        </view>

        <!-- AI Message -->
        <view v-else class="message ai">
          <!-- Thought Process (Foldable) -->
          <view v-if="msg.thoughts && msg.thoughts.length > 0" class="thought-block">
            <view class="thought-header" @click="toggleThought(index)">
              <text>Thinking Process</text>
              <text>{{ msg.showThought ? '▼' : '▶' }}</text>
            </view>
            <view v-if="msg.showThought" class="thought-content">
              <text v-for="(thought, tIndex) in msg.thoughts" :key="tIndex">{{ thought }}</text>
            </view>
          </view>

          <!-- Main Content -->
          <view class="content-block">
            <text>{{ msg.content }}</text>
          </view>

          <!-- Map Card -->
          <view v-if="msg.map" class="map-card" @click="openLocation(msg.map)">
            <text class="map-title">{{ msg.map.name }}</text>
            <text class="map-address">{{ msg.map.address }}</text>
            <view class="map-action">Click to Navigate</view>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- Input Area -->
    <view class="input-area">
      <view class="upload-btn" @click="chooseImage">
        <text>📷</text>
      </view>
      <input class="text-input" v-model="inputText" placeholder="Ask about this food..." confirm-type="send" @confirm="sendMessage" />
      <view class="send-btn" @click="sendMessage">Send</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { streamRequest } from '../../utils/request.js';

const messages = ref([]);
const inputText = ref('');
const currentImage = ref(null);
const scrollIntoView = ref('');

const chooseImage = () => {
  uni.chooseImage({
    count: 1,
    success: (res) => {
      currentImage.value = res.tempFilePaths[0];
      // Auto send if image is selected? Or wait for text?
      // For now, let's show preview or just send immediately with default text if empty
      sendMessage();
    }
  });
};

const sendMessage = () => {
  if (!currentImage.value && !inputText.value) return;

  const userMsg = {
    role: 'user',
    content: inputText.value,
    image: currentImage.value
  };
  messages.value.push(userMsg);

  const aiMsgIndex = messages.value.length;
  const aiMsg = {
    role: 'ai',
    content: '',
    thoughts: [],
    showThought: true,
    map: null
  };
  messages.value.push(aiMsg);
  
  // Scroll to bottom
  scrollIntoView.value = 'msg-' + aiMsgIndex;

  // 1. Upload Image
  uni.uploadFile({
    url: 'http://localhost:8000/api/upload',
    filePath: currentImage.value,
    name: 'file',
    success: (uploadRes) => {
      const data = JSON.parse(uploadRes.data);
      const filePath = data.file_path;
      
      // 2. Start Stream
      streamRequest({
        url: 'http://localhost:8000/api/where-to-eat',
        method: 'POST',
        data: {
            file_path: filePath,
            query: inputText.value
        },
        onChunk: (text) => {
            // Parse custom protocol
            // Format: event: ...\ndata: ...\n\n
            const lines = text.split('\n');
            let currentEvent = null;
            
            for (let line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.substring(7).trim();
                } else if (line.startsWith('data: ')) {
                    const content = line.substring(6);
                    if (!content) continue;
                    
                    if (currentEvent === 'thought') {
                        messages.value[aiMsgIndex].thoughts.push(content);
                    } else if (currentEvent === 'message') {
                        messages.value[aiMsgIndex].content += content;
                    } else if (currentEvent === 'function_call') {
                        try {
                            const call = JSON.parse(content);
                            if (call.action === 'open_map') {
                                messages.value[aiMsgIndex].map = call;
                            }
                        } catch (e) {
                            console.error("Error parsing function call", e);
                        }
                    }
                }
            }
        },
        onComplete: () => {
            console.log("Stream complete");
        },
        onError: (err) => {
            console.error("Stream error", err);
            messages.value[aiMsgIndex].content += "\n[Error: Connection failed]";
        }
      });
    },
    fail: (err) => {
        console.error("Upload failed", err);
        messages.value[aiMsgIndex].content += "\n[Error: Upload failed]";
    }
  });
  
  // Reset input
  inputText.value = '';
  currentImage.value = null;
};

const toggleThought = (index) => {
  messages.value[index].showThought = !messages.value[index].showThought;
};

const openLocation = (mapData) => {
  uni.openLocation({
    latitude: mapData.lat,
    longitude: mapData.lng,
    name: mapData.name,
    address: mapData.address
  });
};
</script>

<style>
.container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.chat-area {
  flex: 1;
  padding: 20rpx;
  background-color: #f5f5f5;
}
.message-item {
  margin-bottom: 20rpx;
}
.message {
  padding: 20rpx;
  border-radius: 10rpx;
  max-width: 80%;
}
.user {
  align-self: flex-end;
  background-color: #95ec69;
  margin-left: auto;
}
.ai {
  align-self: flex-start;
  background-color: #ffffff;
}
.msg-image {
  width: 200rpx;
  height: 200rpx;
  margin-bottom: 10rpx;
}
.thought-block {
  background-color: #f0f0f0;
  padding: 10rpx;
  margin-bottom: 10rpx;
  border-radius: 5rpx;
  font-size: 24rpx;
  color: #666;
}
.thought-header {
  display: flex;
  justify-content: space-between;
}
.map-card {
  margin-top: 10rpx;
  padding: 20rpx;
  background-color: #e8f4ff;
  border-radius: 10rpx;
  border: 1px solid #1890ff;
}
.map-title {
  font-weight: bold;
  font-size: 30rpx;
}
.map-address {
  font-size: 24rpx;
  color: #666;
}
.input-area {
  padding: 20rpx;
  background-color: #fff;
  display: flex;
  align-items: center;
  border-top: 1px solid #eee;
}
.text-input {
  flex: 1;
  border: 1px solid #ddd;
  border-radius: 30rpx;
  padding: 10rpx 20rpx;
  margin: 0 20rpx;
}
</style>
