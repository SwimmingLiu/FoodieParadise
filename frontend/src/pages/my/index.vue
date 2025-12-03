<template>
  <view class="container">
    <!-- User Profile -->
    <view class="profile-section">
      <image class="avatar" src="/static/logo.png" mode="aspectFill"></image>
      <view class="info">
        <text class="nickname">Foodie User</text>
        <text class="uid">ID: 888888</text>
      </view>
    </view>

    <!-- History List -->
    <view class="history-section">
      <text class="section-title">History</text>
      <scroll-view scroll-y class="history-list">
        <view v-for="(item, index) in historyList" :key="index" class="history-item">
          <image :src="item.image_path" mode="aspectFill" class="history-thumb"></image>
          <view class="history-content">
            <view class="history-header">
              <text class="history-type">{{ formatType(item.type) }}</text>
              <text class="history-time">{{ formatDate(item.timestamp) }}</text>
            </view>
            <text class="history-summary">{{ item.summary }}</text>
          </view>
        </view>
        <view v-if="historyList.length === 0" class="empty-state">
          <text>No history yet.</text>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const historyList = ref([]);

const fetchHistory = () => {
  uni.request({
    url: 'http://localhost:8000/api/history',
    success: (res) => {
      historyList.value = res.data;
    }
  });
};

onMounted(() => {
  fetchHistory();
});

const formatType = (type) => {
  const map = {
    'where-to-eat': 'Where to Eat',
    'check-premade': 'Check Pre-made',
    'calories': 'Calories'
  };
  return map[type] || type;
};

const formatDate = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
};
</script>

<style>
.container {
  background-color: #f5f5f5;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.profile-section {
  background-color: #fff;
  padding: 40rpx;
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
}
.avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 60rpx;
  background-color: #eee;
  margin-right: 30rpx;
}
.info {
  display: flex;
  flex-direction: column;
}
.nickname {
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
}
.uid {
  font-size: 24rpx;
  color: #999;
}
.history-section {
  flex: 1;
  background-color: #fff;
  padding: 30rpx;
  display: flex;
  flex-direction: column;
}
.section-title {
  font-size: 32rpx;
  font-weight: bold;
  margin-bottom: 20rpx;
  display: block;
}
.history-list {
  flex: 1;
  height: 0; 
}
.history-item {
  display: flex;
  padding: 20rpx 0;
  border-bottom: 1px solid #eee;
}
.history-thumb {
  width: 120rpx;
  height: 120rpx;
  border-radius: 10rpx;
  margin-right: 20rpx;
  background-color: #eee;
}
.history-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10rpx;
}
.history-type {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
}
.history-time {
  font-size: 24rpx;
  color: #999;
}
.history-summary {
  font-size: 26rpx;
  color: #666;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
.empty-state {
  padding: 50rpx;
  text-align: center;
  color: #999;
}
</style>
