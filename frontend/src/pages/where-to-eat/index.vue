<template>
  <view class="container">
    <!-- Navbar (Custom or default) -->
    <!-- Assuming default navigation bar title is set in pages.json, but we can add a header if needed. 
         The design shows a custom-like header "在哪儿". -->
    
    <!-- Scrollable Content -->
    <scroll-view class="content-area" scroll-y :scroll-into-view="scrollIntoView" :scroll-with-animation="true">
      
      <!-- Initial State: Dark Theme with Card Swiper & Upload Button -->
      <view v-if="messages.length === 0" class="initial-state">
        <!-- Header with Logo and Title -->
        <view class="header-section">
          <view class="header-title-row">
            <image src="https://oss.swimmingliu.cn/foodie_paradise/878b89c5-2835-4308-a2ee-e928f31a0026.png" mode="aspectFit" class="header-logo"></image>
            <text class="header-title">去哪吃</text>
          </view>
          <text class="header-slogan">拍张美食照，AI秒定位附近同款</text>
        </view>

        <!-- Card-style Swiper -->
        <swiper class="card-swiper" circular :previous-margin="'80rpx'" :next-margin="'80rpx'" :current="currentBannerIndex" @change="onSwiperChange">
          <swiper-item v-for="(item, index) in bannerCards" :key="index" @click="selectBannerCard(item)">
            <view :class="['card-item', currentBannerIndex === index ? 'card-active' : '']">
              <image :src="item.image" mode="aspectFill" class="card-image"></image>
              <view class="card-overlay">
                <text class="card-category">{{ item.category }}</text>
                <text class="card-question">{{ item.question }}</text>
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
          <text class="upload-hint">一键识别，发现身边的美味</text>
        </view>
      </view>

      <!-- Chat History -->
      <view class="chat-list" v-else>
        <view v-for="(msg, index) in messages" :key="index" :id="'msg-' + index" class="message-wrapper">
            
            <!-- User Message - Keep bubble style for user -->
            <view v-if="msg.role === 'user'" class="user-message-section">
                <image v-if="msg.image" :src="msg.image" mode="aspectFill" class="user-msg-image"></image>
                <view v-if="msg.content" class="user-bubble">
                    <text>{{ msg.content }}</text>
                </view>
            </view>

            <!-- AI Message - Direct display without bubble -->
            <view v-else class="ai-message-section">
                <!-- Thinking Process with Steps - Card with left accent border -->
                <view v-if="msg.thinkingContent" class="thought-card">
                    <view class="thought-card-header" @click="toggleThinking(index)">
                        <text class="thought-icon">💡</text>
                        <text class="thought-step-label">{{ getCurrentStep(msg.thinkingContent) }}</text>
                        <view :class="['thought-arrow', msg.expanded ? 'expanded' : '']"></view>
                    </view>
                    <view v-if="msg.expanded !== false" class="thought-card-body">
                        <view class="thought-steps-timeline">
                            <view v-for="(step, stepIdx) in parseSteps(msg.thinkingContent)" :key="stepIdx" class="timeline-step">
                                <!-- 圆点 -->
                                <view class="timeline-dot"></view>
                                <!-- 连接线（非最后一项时显示） -->
                                <view v-if="stepIdx < parseSteps(msg.thinkingContent).length - 1" class="timeline-line"></view>
                                <!-- 内容 -->
                                <view class="timeline-content">
                                    <view class="timeline-step-header">
                                        <text class="timeline-step-title">{{ step.title }}</text>
                                    </view>
                                    <view class="timeline-step-body">
                                        <mp-html :content="parseMarkdown(step.content)" :tag-style="mpHtmlTagStyle" />
                                    </view>
                                </view>
                            </view>
                        </view>
                    </view>
                </view>

                <!-- Result Content - Direct display -->
                <view v-if="msg.content" class="result-section">
                    <mp-html :content="parseMarkdown(msg.content)" :tag-style="mpHtmlTagStyle" />
                </view>

                <!-- Location Cards - Display address text only, no map -->
                <view v-if="msg.maps && msg.maps.length > 0" class="maps-section">
                    <view v-for="(mapData, mapIdx) in msg.maps" :key="mapIdx" class="location-card-simple" @click="openLocation(mapData)">
                        <text class="location-pin-icon">📍</text>
                        <view class="location-info">
                            <text class="location-name-text">{{ mapData.name }}</text>
                            <text v-if="mapData.address" class="location-address-text">{{ mapData.address }}</text>
                        </view>
                        <text class="location-arrow">›</text>
                    </view>
                </view>

                <!-- Legacy single map support - also simplified -->
                <view v-else-if="msg.map" class="location-card-simple" @click="openLocation(msg.map)">
                    <text class="location-pin-icon">📍</text>
                    <view class="location-info">
                        <text class="location-name-text">{{ msg.map.name }}</text>
                        <text v-if="msg.map.address" class="location-address-text">{{ msg.map.address }}</text>
                    </view>
                    <text class="location-arrow">›</text>
                </view>
            </view>
        </view>
      </view>
      
      <!-- Padding for bottom input -->
      <view style="height: 120rpx;"></view>
    </scroll-view>

    <!-- Bottom Action Area - Show when in chat mode -->
    <view v-if="messages.length > 0" class="bottom-action-area">
        <!-- 识别中状态 -->
        <view v-if="isRecognizing" class="recognizing-bar">
            <view class="recognizing-btn">
                <text class="recognizing-icon">🌐</text>
                <text class="recognizing-text">识别中...</text>
            </view>
            <view class="stop-btn" @click="handleStop">
                <view class="stop-icon"></view>
            </view>
        </view>
        
        <!-- 识别完成状态 -->
        <view v-else class="completed-bar">
            <view v-if="!showNewConversation" class="result-actions">
                <view class="result-info" @click="toggleNewConversation">
                    <text>已完成图片分析</text>
                    <text class="result-arrow">›</text>
                </view>
                <view class="action-icons">
                    <view class="action-icon-btn" @click="copyResult">
                        <text>📋</text>
                    </view>
                    <view class="action-icon-btn" @click="regenerateResult">
                        <text>🔄</text>
                    </view>
                    <button class="action-icon-btn share-btn" open-type="share">
                        <text>↗️</text>
                    </button>
                </view>
            </view>
            <view v-else class="new-conversation-bar">
                <view class="new-conversation-btn" @click="startNewConversation">
                    <text class="new-conv-icon">💬</text>
                    <text class="new-conv-text">新对话</text>
                </view>
            </view>
        </view>
        
        <!-- AI生成提示 -->
        <view class="ai-disclaimer">
            <text class="ai-disclaimer-icon">✦</text>
            <text class="ai-disclaimer-text">内容由AI生成，仅供参考</text>
        </view>
    </view>

    <!-- Upload Modal with Question Input -->
    <view v-if="showUploadModal" class="upload-modal-mask" @click="closeUploadModal">
        <view class="upload-modal" @click.stop>
            <view class="modal-close" @click="closeUploadModal">
                <text>×</text>
            </view>
            
            <!-- Image Preview -->
            <view class="modal-image-preview">
                <image :src="currentImage" mode="aspectFill" class="preview-image"></image>
                <view class="reupload-btn" @click="reuploadImage">
                    <text class="reupload-icon">🖼️</text>
                    <text class="reupload-text">重新上传</text>
                </view>
            </view>
            
            <!-- Preset Questions -->
            <view class="preset-questions">
                <view class="preset-btn" @click="selectPresetQuestion('店铺在哪儿')">
                    <text>店铺在哪儿</text>
                </view>
                <view class="preset-btn" @click="selectPresetQuestion('哪儿可以买到')">
                    <text>哪儿可以买到</text>
                </view>
                <view class="preset-btn" @click="selectPresetQuestion('杭州的类似店铺')">
                    <text>杭州的类似店铺</text>
                </view>
            </view>
            
            <!-- Custom Question Input -->
            <view class="modal-input-area">
                <input 
                    class="modal-input" 
                    v-model="modalInputText" 
                    placeholder="【可选】输入你想问的问题"
                />
            </view>
            
            <!-- Submit Button -->
            <view class="modal-submit-btn" @click="submitWithQuestion">
                <text class="submit-text">开始识别</text>
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
import { ref, nextTick, onMounted } from 'vue';
import { onShareAppMessage, onShareTimeline } from '@dcloudio/uni-app';
import { streamRequest } from '../../utils/request.js';
import mpHtml from 'mp-html/dist/uni-app/components/mp-html/mp-html.vue';
import { marked } from 'marked';

// Configure marked for safe and clean markdown parsing
marked.setOptions({
    breaks: true, // Convert \n to <br>
    gfm: true,    // GitHub Flavored Markdown
});

// Tag styles for mp-html to override default list indentation
// Ensures all content aligns to the left edge with improved line spacing
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

// State
const bannerCards = ref([
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/8c0e4d50-ffbe-4659-8c3b-6f485355ef53.jpg',
        category: '餐厅推荐',
        question: '这家餐厅在哪儿？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/9cdfa36a-5463-4178-bb74-a70a6027a646.jpg',
        category: '美食探店',
        question: '北京有没有类似的店？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/d6443171-7424-4a11-b523-5d30051e4185.jpg',
        category: '特色小吃',
        question: '这是哪里的特色美食？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/dede5bee-78f7-47e5-a05b-3b81665662f6.jpg',
        category: '网红打卡',
        question: '这个网红店在哪儿？'
    },
    {
        image: 'https://oss.swimmingliu.cn/foodie_paradise/b1dfa3df-f8b4-4310-973d-28e946fb96cf.jpg',
        category: '探店攻略',
        question: '在哪儿能吃到这个？'
    }
]);
const currentBannerIndex = ref(0);
const messages = ref([]);
const inputText = ref('');
const placeholderText = ref('输入你想问的问题');
const currentImage = ref(null);
const currentRemoteFilePath = ref(null);
const scrollIntoView = ref('');
const isUploading = ref(false);

// Upload Modal State
const showUploadModal = ref(false);
const modalInputText = ref('');
const isBannerClick = ref(false);  // 标记是否是轮播图点击

// Recognition State - 识别状态控制
const isRecognizing = ref(false);  // 是否正在识别中
const showNewConversation = ref(false);  // 是否显示新会话按钮
let currentRequestTask = null;  // 当前请求任务引用，用于停止

// 保存最后一次查询信息，用于重新生成
let lastQuery = ref({
    image: null,
    remoteFilePath: null,
    question: ''
});

// Actions
const onSwiperChange = (e) => {
    currentBannerIndex.value = e.detail.current;
};

/**
 * 点击轮播图卡片 - 直接使用轮播图图片发送请求
 * @param {Object} item - 轮播图项目，包含 image 和 question
 */
const selectBannerCard = (item) => {
    isBannerClick.value = true;
    currentImage.value = item.image;
    inputText.value = item.question;
    
    // 轮播图是本地静态资源，直接发送请求
    // 由于是本地图片路径，需要先上传到服务器
    uploadBannerAndSend(item.image, item.question);
};

/**
 * 上传轮播图并发送查询请求
 * @param {string} imagePath - 本地图片路径
 * @param {string} question - 预设问题
 */
const uploadBannerAndSend = (imagePath, question) => {
    isUploading.value = true;
    
    // 如果是远程图片(http/https开头)，直接使用，无需上传
    if (imagePath && (imagePath.startsWith('http://') || imagePath.startsWith('https://'))) {
        currentRemoteFilePath.value = imagePath;
        isUploading.value = false;
        
        // 自动发送消息
        inputText.value = question;
        sendMessage();
        return;
    }
    
    // 对于静态资源图片，使用完整URL路径上传
    const fullPath = imagePath.startsWith('/static') 
        ? imagePath  // 相对路径，使用uploadFile时会自动处理
        : imagePath;
    
    uni.uploadFile({
        url: 'http://localhost:8000/api/upload',
        filePath: fullPath,
        name: 'file',
        success: (uploadRes) => {
            try {
                const data = JSON.parse(uploadRes.data);
                currentRemoteFilePath.value = data.file_path;
                isUploading.value = false;
                
                // 自动发送消息
                inputText.value = question;
                sendMessage();
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

const selectPreset = (text) => {
    inputText.value = text;
    if (!currentImage.value) {
        chooseImage();
    }
};

/**
 * 选择图片 - 打开相册/相机选择图片后显示弹窗
 */
const chooseImage = () => {
    isBannerClick.value = false;
    uni.chooseImage({
        count: 1,
        success: (res) => {
            currentImage.value = res.tempFilePaths[0];
            // 上传图片
            uploadImage(currentImage.value);
            // 显示弹窗让用户输入问题
            showUploadModal.value = true;
            modalInputText.value = '';
        }
    });
};

/**
 * 重新上传图片 - 在弹窗中点击重新上传
 */
const reuploadImage = () => {
    uni.chooseImage({
        count: 1,
        success: (res) => {
            currentImage.value = res.tempFilePaths[0];
            uploadImage(currentImage.value);
        }
    });
};

/**
 * 关闭上传弹窗
 */
const closeUploadModal = () => {
    showUploadModal.value = false;
};

/**
 * 选择预设问题
 * @param {string} question - 预设问题文本
 */
const selectPresetQuestion = (question) => {
    modalInputText.value = question;
};

/**
 * 提交图片和问题 - 从弹窗中点击开始识别
 */
const submitWithQuestion = () => {
    if (!currentRemoteFilePath.value) {
        uni.showToast({ title: '图片上传中，请稍候', icon: 'none' });
        return;
    }
    
    // 使用弹窗中的问题
    inputText.value = modalInputText.value || '这是哪里？';
    showUploadModal.value = false;
    sendMessage();
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
        thinkingContent: '',  // Single string for all thinking content
        isThinking: true,     // Whether AI is still thinking
        expanded: true,       // Whether thinking section is expanded
        map: null,
        maps: []              // Array to support multiple map locations
    };
    messages.value.push(aiMsg);

    scrollToBottom();
    
    // 设置识别状态
    isRecognizing.value = true;
    showNewConversation.value = false;

    // Accumulators for complete content
    let completeThoughts = '';  // Accumulate all thinking content as single string
    let completeResult = '';    // Store all result content

    // Start Stream with proper event handling
    currentRequestTask = streamRequest({
        url: 'http://localhost:8000/api/where-to-eat',
        method: 'POST',
        data: {
            file_path: currentRemoteFilePath.value,
            query: query
        },
        // Use the new onEvent callback for properly parsed SSE events
        onEvent: (eventType, data) => {
            if (!data) return;
            
            if (eventType === 'thought') {
                // Decode and accumulate thought content as single string
                const decodedData = decodeHTMLEntities(data);
                completeThoughts += decodedData;
                
                // Update thinking content (streaming accumulation)
                messages.value[aiMsgIndex].thinkingContent = completeThoughts;
                messages.value[aiMsgIndex].isThinking = true;
            } else if (eventType === 'message') {
                // Append message content (supports streaming markdown)
                const decodedData = decodeHTMLEntities(data);
                messages.value[aiMsgIndex].content += decodedData;
                completeResult += decodedData;
            } else if (eventType === 'function_call') {
                try {
                    const call = JSON.parse(data);
                    // Handle map location function call - support multiple locations
                    if (call.name === 'open_map' || call.action === 'open_map') {
                        const mapData = call.arguments || call;
                        // Add to maps array for multiple locations with deduplication
                        if (!messages.value[aiMsgIndex].maps) {
                            messages.value[aiMsgIndex].maps = [];
                        }
                        // Check for duplicate locations based on name, address and coordinates
                        const isDuplicate = messages.value[aiMsgIndex].maps.some(existingMap => {
                            const existingLat = existingMap.lat || existingMap.latitude;
                            const existingLng = existingMap.lng || existingMap.longitude;
                            const newLat = mapData.lat || mapData.latitude;
                            const newLng = mapData.lng || mapData.longitude;
                            // Check if same location by name, address or coordinates (within small tolerance)
                            return existingMap.name === mapData.name || 
                                   existingMap.address === mapData.address ||
                                   (Math.abs(existingLat - newLat) < 0.0001 && Math.abs(existingLng - newLng) < 0.0001);
                        });
                                    
                        if (!isDuplicate) {
                            messages.value[aiMsgIndex].maps.push(mapData);
                            // Also set single map for backwards compatibility
                            if (!messages.value[aiMsgIndex].map) {
                                messages.value[aiMsgIndex].map = mapData;
                            }
                        }
                    }
                } catch (e) {
                    console.error("Function call parse error", e);
                }
            }
            scrollToBottom();
        },
        onComplete: () => {
            // Mark thinking as complete
            messages.value[aiMsgIndex].isThinking = false;

            // Extract and parse location JSON from result content
            // Handle multiple formats: ```json...```, escaped JSON with \", regular JSON
            const extractedLocation = extractLocationFromContent(completeResult);
            
            if (extractedLocation.mapData) {
                // Add to maps if valid (must have name field)
                if (!messages.value[aiMsgIndex].maps) {
                    messages.value[aiMsgIndex].maps = [];
                }
                
                // Deduplication check
                const isDuplicate = messages.value[aiMsgIndex].maps.some(existingMap => {
                    return existingMap.name === extractedLocation.mapData.name;
                });
                
                if (!isDuplicate) {
                    messages.value[aiMsgIndex].maps.push(extractedLocation.mapData);
                    // Set legacy single map
                    if (!messages.value[aiMsgIndex].map) {
                        messages.value[aiMsgIndex].map = extractedLocation.mapData;
                    }
                }
                
                // Remove JSON from text content
                messages.value[aiMsgIndex].content = extractedLocation.cleanContent;
                console.log('Successfully parsed location:', extractedLocation.mapData.name);
            }
            
            // Print complete thinking process and result to console
            console.log('\n========== 完整思考过程 (Think) ==========');
            console.log(decodeHTMLEntities(completeThoughts));
            console.log('\n========== 完整推理结果 (Result) ==========');
            console.log(decodeHTMLEntities(completeResult));
            console.log('==========================================\n');
            
            console.log("Stream finished");
            
            // 更新识别状态
            isRecognizing.value = false;
            currentRequestTask = null;
        },
        onError: (err) => {
            console.error("Stream error", err);
            messages.value[aiMsgIndex].isThinking = false;
            messages.value[aiMsgIndex].content += "\n[连接中断]";
            
            // 更新识别状态
            isRecognizing.value = false;
            currentRequestTask = null;
        }
    });

    // 保存最后一次查询信息
    lastQuery.value = {
        image: currentImage.value,
        remoteFilePath: currentRemoteFilePath.value,
        question: query
    };

    // Clear input
    inputText.value = '';
    // We keep the image and remote path for context? Or clear?
    // Usually clear for next query.
    currentImage.value = null;
    currentRemoteFilePath.value = null;
};

/**
 * 复制AI结果到剪贴板
 */
const copyResult = () => {
    // 获取最新的AI消息内容
    const aiMessages = messages.value.filter(msg => msg.role === 'ai');
    if (aiMessages.length === 0) {
        uni.showToast({ title: '暂无内容可复制', icon: 'none' });
        return;
    }
    
    const lastAiMsg = aiMessages[aiMessages.length - 1];
    const content = lastAiMsg.content || '';
    
    if (!content) {
        uni.showToast({ title: '暂无内容可复制', icon: 'none' });
        return;
    }
    
    uni.setClipboardData({
        data: content,
        success: () => {
            uni.showToast({ title: '已复制到剪贴板', icon: 'success' });
        },
        fail: () => {
            uni.showToast({ title: '复制失败', icon: 'none' });
        }
    });
};

/**
 * 重新生成结果
 */
const regenerateResult = () => {
    if (!lastQuery.value.remoteFilePath) {
        uni.showToast({ title: '请先上传图片', icon: 'none' });
        return;
    }
    
    if (isRecognizing.value) {
        uni.showToast({ title: '正在识别中...', icon: 'none' });
        return;
    }
    
    // 恢复上次查询信息
    currentImage.value = lastQuery.value.image;
    currentRemoteFilePath.value = lastQuery.value.remoteFilePath;
    inputText.value = lastQuery.value.question;
    
    // 移除上一个AI回复（用于重新生成）
    if (messages.value.length > 0) {
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg.role === 'ai') {
            messages.value.pop();
        }
    }
    
    // 重新发送请求
    sendMessage();
};

const scrollToBottom = () => {
    nextTick(() => {
        scrollIntoView.value = 'msg-' + (messages.value.length - 1);
    });
};

const openLocation = (mapData) => {
    // Handle both lat/lng and latitude/longitude formats from backend
    const latitude = parseFloat(mapData.lat || mapData.latitude || 39.9042);
    const longitude = parseFloat(mapData.lng || mapData.longitude || 116.4074);
    
    uni.openLocation({
        latitude: latitude,
        longitude: longitude,
        name: mapData.name || '未知地点',
        address: mapData.address || '详细地址未知'
    });
};

/**
 * 停止当前识别请求
 */
const handleStop = () => {
    if (currentRequestTask) {
        currentRequestTask.abort();
        currentRequestTask = null;
    }
    isRecognizing.value = false;
};

/**
 * 开始新对话 - 重置所有状态
 */
const startNewConversation = () => {
    messages.value = [];
    currentImage.value = null;
    currentRemoteFilePath.value = null;
    inputText.value = '';
    isRecognizing.value = false;
    showNewConversation.value = false;
};

/**
 * 切换显示新对话按钮
 */
const toggleNewConversation = () => {
    showNewConversation.value = !showNewConversation.value;
};

/**
 * Decode HTML entities (e.g., &gt; -> >)
 * Handles both named and numeric HTML entities
 * @param {string} text - Text with HTML entities
 * @returns {string} Decoded text
 */
const decodeHTMLEntities = (text) => {
    if (!text) return '';
    
    // Named entities mapping (comprehensive list using unicode escapes for special chars)
    const entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
        '&nbsp;': ' ',
        '&ndash;': '\u2013',
        '&mdash;': '\u2014',
        '&lsquo;': '\u2018',
        '&rsquo;': '\u2019',
        '&ldquo;': '\u201C',
        '&rdquo;': '\u201D',
        '&hellip;': '\u2026',
        '&copy;': '\u00A9',
        '&reg;': '\u00AE',
        '&trade;': '\u2122'
    };
    
    // Replace named entities
    let result = text.replace(/&amp;|&lt;|&gt;|&quot;|&#39;|&apos;|&nbsp;|&ndash;|&mdash;|&lsquo;|&rsquo;|&ldquo;|&rdquo;|&hellip;|&copy;|&reg;|&trade;/g, 
        (match) => entities[match] || match);
    
    // Decode numeric entities (e.g., &#60; -> <, &#x3E; -> >)
    result = result.replace(/&#(\d+);/g, (match, dec) => String.fromCharCode(dec));
    result = result.replace(/&#x([0-9a-fA-F]+);/g, (match, hex) => String.fromCharCode(parseInt(hex, 16)));
    
    return result;
};

/**
 * Extract location JSON from content and return parsed data with cleaned content
 * Handles multiple JSON formats:
 * 1. Markdown code blocks: ```json {...} ```
 * 2. Escaped JSON with \" quotes
 * 3. Regular JSON with " quotes
 * @param {string} content - Content that may contain location JSON
 * @returns {{mapData: Object|null, cleanContent: string}} Parsed map data and cleaned content
 */
const extractLocationFromContent = (content) => {
    if (!content) return { mapData: null, cleanContent: content };
    
    let jsonStr = null;
    let matchedText = null;
    let mapData = null;
    
    // Pattern 1: Match ```json ... ``` markdown code blocks
    const codeBlockMatch = content.match(/```json\s*([\s\S]*?)```/);
    if (codeBlockMatch) {
        jsonStr = codeBlockMatch[1].trim();
        matchedText = codeBlockMatch[0];
    }
    
    // Pattern 2: If no code block, look for JSON object starting with { and containing "name"
    if (!jsonStr) {
        // Match JSON that starts with { and contains name, address, latitude, longitude
        // Handle both escaped (\\" or \") and regular (") quotes
        const jsonObjectMatch = content.match(/\{[\s\S]*?["\\]name["\\][\s\S]*?["\\]longitude["\\]\s*:\s*[\d.-]+\s*\}/);
        if (jsonObjectMatch) {
            jsonStr = jsonObjectMatch[0];
            matchedText = jsonObjectMatch[0];
        }
    }
    
    // Pattern 3: Try to find any JSON-like structure with name field
    if (!jsonStr) {
        // Look for {"name": or {\"name\":
        const simpleMatch = content.match(/\{\s*(?:\\"|")?name(?:\\"|")?\s*:\s*(?:\\"|")?[^}]+\}/);
        if (simpleMatch) {
            jsonStr = simpleMatch[0];
            matchedText = simpleMatch[0];
        }
    }
    
    if (jsonStr) {
        try {
            // Clean up the JSON string
            let cleanedJsonStr = jsonStr
                // Remove literal \n (backslash followed by n)
                .replace(/\\n/g, ' ')
                // Replace escaped quotes \" with regular quotes "
                .replace(/\\"/g, '"')
                // Replace double backslashes with single
                .replace(/\\\\/g, '\\')
                // Clean up any markdown artifacts
                .replace(/\*\*/g, '')
                .trim();
            
            console.log('Attempting to parse JSON:', cleanedJsonStr);
            mapData = JSON.parse(cleanedJsonStr);
            
            // Validate that we have required fields
            if (!mapData.name) {
                console.log('JSON parsed but no name field found');
                mapData = null;
            }
        } catch (e) {
            console.error('JSON parse error:', e.message);
            console.error('Original JSON string:', jsonStr);
            
            // Fallback: Try to extract data using regex if JSON parsing fails
            try {
                const nameMatch = jsonStr.match(/["\\]?name["\\]?\s*:\s*["\\]?([^"\\,}]+)["\\]?/);
                const addressMatch = jsonStr.match(/["\\]?address["\\]?\s*:\s*["\\]?([^"\\,}]+)["\\]?/);
                const latMatch = jsonStr.match(/["\\]?latitude["\\]?\s*:\s*([\d.-]+)/);
                const lngMatch = jsonStr.match(/["\\]?longitude["\\]?\s*:\s*([\d.-]+)/);
                
                if (nameMatch) {
                    mapData = {
                        name: nameMatch[1].trim(),
                        address: addressMatch ? addressMatch[1].trim() : '',
                        latitude: latMatch ? parseFloat(latMatch[1]) : 0,
                        longitude: lngMatch ? parseFloat(lngMatch[1]) : 0
                    };
                    console.log('Extracted location via regex fallback:', mapData.name);
                }
            } catch (fallbackError) {
                console.error('Fallback extraction also failed:', fallbackError);
            }
        }
    }
    
    // Create clean content by removing the matched JSON text
    let cleanContent = content;
    if (matchedText && mapData) {
        cleanContent = content.replace(matchedText, '').trim();
        // Also clean up any remaining empty code block markers
        cleanContent = cleanContent.replace(/```\s*```/g, '').trim();
    }
    
    return { mapData, cleanContent };
};

/**
 * Parse markdown content to HTML
 * @param {string} content - Markdown content
 * @returns {string} HTML content
 */
const parseMarkdown = (content) => {
    if (!content) return '';
    try {
        // First decode HTML entities, then parse markdown
        const decoded = decodeHTMLEntities(content);
        // Replace literal \n strings with actual newlines for proper line break rendering
        const withNewlines = decoded.replace(/\\n/g, '\n');
        return marked.parse(withNewlines);
    } catch (e) {
        console.error('Markdown parse error:', e);
        return content;
    }
};

/**
 * Toggle thinking section expansion
 * @param {number} msgIndex - Message index
 */
const toggleThinking = (msgIndex) => {
    const msg = messages.value[msgIndex];
    if (msg) {
        msg.expanded = !msg.expanded;
    }
};

/**
 * Parse thinking content into structured Steps
 * Extracts Step 0, Step 1, Step 2, etc. from the thinking content
 * Filters out content after "最终结果" to avoid duplicate display
 * @param {string} content - Raw thinking content
 * @returns {Array} Array of step objects with title and content
 */
const parseSteps = (content) => {
    if (!content) return [];
    
    // 过滤掉"最终结果"及其之后的内容，避免重复显示
    // 与后端的分割标记保持一致，支持多种格式
    let filteredContent = content;
    
    // 检查多种格式的"最终结果"分割标记
    const finalResultPatterns = [
        '---',              // Markdown分隔线
        '# 最终推荐',        // 中文一级标题
        '## 🏪 店铺推荐',    // 中文二级标题带emoji  
        '🏪 店铺推荐',       // 仅emoji开头
        '**最终推荐**',      // 加粗文本
        '# Final Result',   // 英文一级标题
        '## Final Result',  // 英文二级标题
        '\n🔍 根据',         // 其他可能的开头
        '\n🔍根据'
    ];
    
    for (const pattern of finalResultPatterns) {
        const index = filteredContent.indexOf(pattern);
        if (index !== -1) {
            filteredContent = filteredContent.substring(0, index);
            break;  // 找到第一个匹配的就停止
        }
    }
    
    const steps = [];
    // Match patterns like "• Step 0", "• Step 1", etc.
    const stepPattern = /•\s*Step\s+(\d+)([\s\S]*?)(?=•\s*Step\s+\d+|$)/g;
    let match;
    
    while ((match = stepPattern.exec(filteredContent)) !== null) {
        const stepNum = match[1];
        const stepContent = match[2].trim();
        steps.push({
            title: `Step ${stepNum}`,
            content: stepContent
        });
    }
    
    // If no steps found, return the whole content as a single item
    if (steps.length === 0 && filteredContent.trim()) {
        return [{
            title: '分析中',
            content: filteredContent
        }];
    }
    
    return steps;
};

/**
 * Get the current step display text for the header
 * Shows the last step number being processed
 * @param {string} content - Thinking content
 * @returns {string} Step display text like "Step 3"
 */
const getCurrentStep = (content) => {
    if (!content) return '思考中...';
    
    // Find the last Step number mentioned
    const stepMatches = content.match(/Step\s+(\d+)/g);
    if (stepMatches && stepMatches.length > 0) {
        const lastStep = stepMatches[stepMatches.length - 1];
        return lastStep;
    }
    return '思考中...';
};

/**
 * 配置微信分享给朋友
 */
onShareAppMessage(() => {
    // 获取最新的AI消息内容作为分享摘要
    const aiMessages = messages.value.filter(msg => msg.role === 'ai');
    let shareTitle = '看看这家店在哪里！';
    let shareDesc = 'AI智能识别餐厅位置';
    let imageUrl = 'https://oss.swimmingliu.cn/foodie_paradise/878b89c5-2835-4308-a2ee-e928f31a0026.png';
    
    if (aiMessages.length > 0) {
        const lastAiMsg = aiMessages[aiMessages.length - 1];
        // 提取店铺名称作为标题
        if (lastAiMsg.maps && lastAiMsg.maps.length > 0) {
            shareTitle = `🍽️ ${lastAiMsg.maps[0].name || '美食探店'}`;
        } else if (lastAiMsg.map && lastAiMsg.map.name) {
            shareTitle = `🍽️ ${lastAiMsg.map.name}`;
        }
        // 提取内容摘要
        if (lastAiMsg.content) {
            shareDesc = lastAiMsg.content.substring(0, 50).replace(/[#*`\n]/g, '') + '...';
        }
    }
    
    // 获取用户上传的图片作为分享图片
    const userMessages = messages.value.filter(msg => msg.role === 'user' && msg.image);
    if (userMessages.length > 0) {
        imageUrl = userMessages[userMessages.length - 1].image;
    }
    
    return {
        title: shareTitle,
        desc: shareDesc,
        path: '/pages/where-to-eat/index',
        imageUrl: imageUrl
    };
});

/**
 * 配置分享到朋友圈
 */
onShareTimeline(() => {
    const aiMessages = messages.value.filter(msg => msg.role === 'ai');
    let shareTitle = '看看这家店在哪里！';
    
    if (aiMessages.length > 0) {
        const lastAiMsg = aiMessages[aiMessages.length - 1];
        if (lastAiMsg.maps && lastAiMsg.maps.length > 0) {
            shareTitle = `🍽️ ${lastAiMsg.maps[0].name || '美食探店'}`;
        } else if (lastAiMsg.map && lastAiMsg.map.name) {
            shareTitle = `🍽️ ${lastAiMsg.map.name}`;
        }
    }
    
    return {
        title: shareTitle,
        query: '',
        imageUrl: 'https://oss.swimmingliu.cn/foodie_paradise/878b89c5-2835-4308-a2ee-e928f31a0026.png'
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
    background: linear-gradient(135deg, #667eea 0%, #5568e5 50%, #4361ee 100%);
    border: none;
    border-radius: 50rpx;
    margin-bottom: 32rpx;
    box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.3);
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

/* Chat List - Clean layout */
.chat-list {
    padding: 20rpx 30rpx;
}

.message-wrapper {
    margin-bottom: 30rpx;
}

/* User Message Section */
.user-message-section {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}

.user-msg-image {
    width: 400rpx;
    height: 300rpx;
    border-radius: 16rpx;
    margin-bottom: 16rpx;
    box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.1);
}

.user-bubble {
    background-color: #fff;
    color: #333;
    padding: 20rpx 28rpx;
    border-radius: 20rpx;
    border-top-right-radius: 6rpx;
    font-size: 30rpx;
    line-height: 1.5;
    max-width: 80%;
    border: 1px solid #e8e8e8;
    box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

/* AI Message Section - Direct display without bubble */
.ai-message-section {
    width: 100%;
}

/* ========== Thought Card Styles ========== */
.thought-card {
    background-color: #fff;
    border-radius: 20rpx;
    margin-bottom: 28rpx;
    border-left: 6rpx solid #e0e0e0;
    overflow: hidden;
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.thought-card-header {
    display: flex;
    align-items: center;
    padding: 24rpx 28rpx;
    cursor: pointer;
    background-color: #fafafa;
    transition: background-color 0.2s ease;
}

.thought-card-header:active {
    background-color: #f0f0f0;
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
    padding: 20rpx 28rpx 28rpx 28rpx;
    border-top: 1px solid #f0f0f0;
    background-color: #fff;
}

/* Steps Container with left connecting line */
.thought-steps-container {
    position: relative;
    padding-left: 20rpx;
}

.thought-steps-container::before {
    content: '';
    position: absolute;
    left: 8rpx;
    top: 30rpx;
    bottom: 30rpx;
    width: 3rpx;
    background-color: #e0e0e0;
}

/* Individual Step in Thought */
.thought-step {
    position: relative;
    padding: 24rpx 0;
    padding-left: 24rpx;
}

.thought-step:not(:last-child) {
    border-bottom: 2rpx solid #d0d0d0;
    padding-bottom: 28rpx;
    margin-bottom: 20rpx;
}

.thought-step-header {
    display: flex;
    align-items: center;
    margin-bottom: 12rpx;
}

.thought-bullet {
    font-size: 32rpx;
    color: #333;
    margin-right: 12rpx;
    font-weight: bold;
    line-height: 1;
}

.thought-step-title {
    font-size: 28rpx;
    font-weight: 600;
    color: #333;
}

.thought-step-content {
    text-align: left;
    font-size: 28rpx;
    line-height: 1.9;
    color: #555;
}

/* Thought content mp-html styles */
.thought-step-content :deep(.node) {
    font-size: 28rpx !important;
    line-height: 1.9 !important;
    color: #555 !important;
    text-align: left !important;
}

.thought-step-content :deep(ul),
.thought-step-content :deep(ol) {
    padding-left: 24rpx;
    margin: 12rpx 0;
    text-align: left;
}

.thought-step-content :deep(li) {
    margin: 10rpx 0;
    font-size: 28rpx;
    line-height: 1.8;
    text-align: left;
    list-style-position: outside;
    padding-left: 0;
}

.thought-step-content :deep(p) {
    margin: 10rpx 0;
    text-align: left;
    line-height: 1.9;
}

.thought-step-content :deep(strong) {
    font-weight: 600;
    color: #333;
}

/* ========== Result Section Styles ========== */
.result-section {
    padding: 16rpx 8rpx;
    margin-bottom: 28rpx;
}

/* Result mp-html base styles */
.result-section :deep(.node) {
    font-size: 28rpx !important;
    line-height: 2.0 !important;
    color: #333 !important;
}

/* 段落样式优化 - 增加间距减少密集感 */
.result-section :deep(p) {
    margin: 28rpx 0;
    line-height: 2.2;
    font-size: 28rpx;
}

/* 标题样式优化 - 保持一致的字体大小但有不同样式 */
.result-section :deep(h1),
.result-section :deep(h2),
.result-section :deep(h3),
.result-section :deep(h4) {
    font-weight: 700;
    color: #222;
    margin: 28rpx 0 18rpx 0;
    line-height: 1.6;
    font-size: 28rpx;
}

.result-section :deep(strong) {
    font-weight: 700;
    color: #222;
}

/* 列表样式优化 - 所有内容左对齐 */
.result-section :deep(ul),
.result-section :deep(ol) {
    padding-left: 0;
    margin: 20rpx 0;
    margin-left: 0;
    list-style-position: inside;
}

.result-section :deep(li) {
    margin: 20rpx 0;
    font-size: 28rpx;
    line-height: 2.2;
    color: #444;
    list-style-position: inside;
    padding-left: 0;
    margin-left: 0;
    text-indent: 0;
}

/* 嵌套列表也保持左对齐 */
.result-section :deep(ul ul),
.result-section :deep(ul ol),
.result-section :deep(ol ul),
.result-section :deep(ol ol) {
    padding-left: 0;
    margin-left: 1em;
}

.result-section :deep(li li) {
    padding-left: 0;
    margin-left: 0;
}

/* 引用块样式 */
.result-section :deep(blockquote) {
    border-left: 6rpx solid #e0e0e0;
    padding: 16rpx 24rpx;
    margin: 20rpx 0;
    background-color: #fafafa;
    border-radius: 0 8rpx 8rpx 0;
    color: #555;
    font-style: italic;
    font-size: 28rpx;
    line-height: 2.0;
}

/* 代码样式 */
.result-section :deep(code) {
    background-color: #f5f5f5;
    padding: 4rpx 10rpx;
    border-radius: 6rpx;
    font-size: 28rpx;
    color: #d14;
}

/* 分隔线样式 */
.result-section :deep(hr) {
    border: none;
    border-top: 1px solid #eee;
    margin: 28rpx 0;
}

/* ========== Simplified Location Card Styles ========== */
.maps-section {
    width: 100%;
    margin-top: 8rpx;
}

.location-card-simple {
    display: flex;
    align-items: center;
    padding: 28rpx 24rpx;
    background-color: #fff;
    border-radius: 16rpx;
    margin-bottom: 20rpx;
    border: 1px solid #e8e8e8;
    box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
    transition: background-color 0.2s ease;
}

.location-card-simple:active {
    background-color: #f8f8f8;
}

.location-pin-icon {
    font-size: 40rpx;
    margin-right: 20rpx;
    flex-shrink: 0;
}

.location-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.location-name-text {
    font-size: 30rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 8rpx;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.location-address-text {
    font-size: 26rpx;
    color: #888;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.location-arrow {
    font-size: 48rpx;
    color: #ccc;
    margin-left: 16rpx;
    flex-shrink: 0;
}

/* Legacy location card styles - kept for compatibility */
.location-card {
    background-color: #fff;
    border-radius: 16rpx;
    overflow: hidden;
    margin-bottom: 24rpx;
    border: 1px solid #e8e8e8;
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.location-card:active {
    transform: scale(0.99);
    box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.08);
}

.location-card-header {
    padding: 20rpx 24rpx;
    display: flex;
    align-items: center;
    background-color: #fafafa;
    border-bottom: 1px solid #f0f0f0;
}

.location-pin {
    font-size: 32rpx;
    margin-right: 12rpx;
}

.location-name {
    font-size: 30rpx;
    font-weight: 600;
    color: #333;
    flex: 1;
}

.location-map-wrapper {
    height: 360rpx;
    background-color: #f0f0f0;
}

.location-map {
    width: 100%;
    height: 100%;
}

/* ========== Input Area ========== */
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

/* ========== Upload Modal Styles ========== */
.upload-modal-mask {
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

.upload-modal {
    width: 100%;
    max-height: 85vh;
    background-color: #fff;
    border-radius: 32rpx 32rpx 0 0;
    padding: 32rpx 32rpx;
    padding-bottom: calc(60rpx + env(safe-area-inset-bottom));
    position: relative;
    overflow-y: auto;
    box-sizing: border-box;
}

.modal-close {
    position: absolute;
    top: 20rpx;
    right: 24rpx;
    width: 60rpx;
    height: 60rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f0f0f0;
    border-radius: 50%;
    z-index: 10;
}

.modal-close text {
    font-size: 40rpx;
    color: #666;
    line-height: 1;
}

.modal-image-preview {
    width: 100%;
    height: 320rpx;
    border-radius: 20rpx;
    overflow: hidden;
    position: relative;
    margin-bottom: 24rpx;
}

.preview-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.reupload-btn {
    position: absolute;
    bottom: 20rpx;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    padding: 12rpx 24rpx;
    background-color: rgba(0, 0, 0, 0.6);
    border-radius: 30rpx;
}

.reupload-icon {
    font-size: 28rpx;
    margin-right: 8rpx;
}

.reupload-text {
    font-size: 24rpx;
    color: #fff;
}

.preset-questions {
    display: flex;
    flex-wrap: nowrap;
    gap: 12rpx;
    margin-bottom: 20rpx;
}

.preset-btn {
    padding: 12rpx 18rpx;
    background-color: #f5f5f5;
    border-radius: 32rpx;
    border: 1px solid #e8e8e8;
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.preset-btn:active {
    background-color: #ebebeb;
    transform: scale(0.98);
}

.preset-btn text {
    font-size: 24rpx;
    color: #333;
    white-space: nowrap;
}

.modal-input-area {
    margin-bottom: 28rpx;
}

.modal-input {
    width: 100%;
    height: 88rpx;
    background-color: #f5f5f5;
    border-radius: 44rpx;
    padding: 0 32rpx;
    font-size: 28rpx;
    border: 1px solid #e8e8e8;
    box-sizing: border-box;
}

.modal-submit-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 88rpx;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 44rpx;
    box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.3);
}

.modal-submit-btn:active {
    transform: scale(0.98);
    opacity: 0.9;
}

.submit-icon {
    font-size: 32rpx;
    margin-right: 12rpx;
}

.submit-text {
    font-size: 32rpx;
    font-weight: 600;
    color: #fff;
}

/* ========== Timeline Step Styles ========== */
.thought-steps-timeline {
    position: relative;
    padding-left: 12rpx;
}

.timeline-step {
    position: relative;
    padding-left: 40rpx;
    padding-bottom: 32rpx;
}

.timeline-step:last-child {
    padding-bottom: 0;
}

/* 圆点样式 */
.timeline-dot {
    position: absolute;
    left: 0;
    top: 8rpx;
    width: 16rpx;
    height: 16rpx;
    background-color: #10b981;
    border-radius: 50%;
    z-index: 2;
}

/* 连接线样式 */
.timeline-line {
    position: absolute;
    left: 6rpx;
    top: 24rpx;
    width: 4rpx;
    bottom: 0;
    background-color: #d1d5db;
    z-index: 1;
}

.timeline-content {
    flex: 1;
}

.timeline-step-header {
    display: flex;
    align-items: center;
    margin-bottom: 12rpx;
}

.timeline-step-title {
    font-size: 28rpx;
    font-weight: 600;
    color: #333;
}

.timeline-step-body {
    text-align: left;
    font-size: 28rpx;
    line-height: 1.9;
    color: #555;
}

/* Timeline body mp-html styles */
.timeline-step-body :deep(.node) {
    font-size: 28rpx !important;
    line-height: 1.9 !important;
    color: #555 !important;
    text-align: left !important;
}

.timeline-step-body :deep(ul),
.timeline-step-body :deep(ol) {
    padding-left: 0;
    margin: 12rpx 0;
    margin-left: 0;
    text-align: left;
    list-style-position: inside;
}

.timeline-step-body :deep(li) {
    margin: 10rpx 0;
    font-size: 28rpx;
    line-height: 1.8;
    text-align: left;
    list-style-position: inside;
    padding-left: 0;
    margin-left: 0;
    text-indent: 0;
}

/* 嵌套列表保持左对齐 */
.timeline-step-body :deep(ul ul),
.timeline-step-body :deep(ul ol),
.timeline-step-body :deep(ol ul),
.timeline-step-body :deep(ol ol) {
    padding-left: 0;
    margin-left: 1em;
}

.timeline-step-body :deep(li li) {
    padding-left: 0;
    margin-left: 0;
}

.timeline-step-body :deep(p) {
    margin: 10rpx 0;
    text-align: left;
    line-height: 1.9;
}

.timeline-step-body :deep(strong) {
    font-weight: 600;
    color: #333;
}

/* ========== Bottom Action Area Styles ========== */
.bottom-action-area {
    background-color: #fff;
    padding: 16rpx 24rpx;
    padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
    border-top: 1px solid #eee;
}

/* 识别中状态 */
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
    background: linear-gradient(135deg, #667eea 0%, #5568e5 50%, #4361ee 100%);
    border-radius: 40rpx;
    gap: 12rpx;
    box-shadow: 0 4rpx 16rpx rgba(102, 126, 234, 0.3);
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
    background: linear-gradient(135deg, #667eea 0%, #5568e5 50%, #4361ee 100%);
    border-radius: 40rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4rpx 16rpx rgba(102, 126, 234, 0.3);
}

.stop-icon {
    width: 24rpx;
    height: 24rpx;
    background-color: #fff;
    border-radius: 4rpx;
}

/* 完成状态 */
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

/* 分享按钮样式 - 重置button默认样式 */
.share-btn {
    padding: 0;
    margin: 0;
    line-height: normal;
    background-color: #f8f8f8;
}

.share-btn::after {
    border: none;
}

/* 新对话按钮 */
.new-conversation-bar {
    display: flex;
    justify-content: center;
}

.new-conversation-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 88rpx;
    background-color: #1f2937;
    border-radius: 44rpx;
    gap: 12rpx;
}

.new-conv-icon {
    font-size: 32rpx;
}

.new-conv-text {
    font-size: 30rpx;
    color: #fff;
    font-weight: 500;
}

/* AI提示 */
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
</style>
