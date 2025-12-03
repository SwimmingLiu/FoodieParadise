<template>
  <view class="container">
    <view class="banner">
      <image class="banner-img" src="/static/logo.png" mode="aspectFill"></image>
      <text class="banner-title">FoodieParadise</text>
    </view>

    <view class="feature-grid">
      <view class="feature-card" @click="navigateTo('/pages/where-to-eat/index')">
        <text class="card-icon">🗺️</text>
        <text class="card-title">Where to Eat</text>
        <text class="card-desc">Find location from food photos</text>
      </view>

      <view class="feature-card" @click="navigateTo('/pages/check-premade/index')">
        <text class="card-icon">🍱</text>
        <text class="card-title">Check Pre-made</text>
        <text class="card-desc">Analyze food freshness</text>
      </view>

      <view class="feature-card" @click="navigateTo('/pages/calories/index')">
        <text class="card-icon">🔥</text>
        <text class="card-title">How Much to Eat</text>
        <text class="card-desc">Estimate calories</text>
      </view>
    </view>
  </view>
</template>

<script setup>
const navigateTo = (url) => {
  uni.navigateTo({
    url: url
  });
};
</script>

<style>
.container {
  padding: 30rpx;
  background-color: #f5f5f5;
  min-height: 100vh;
}
.banner {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 50rpx;
  margin-top: 50rpx;
}
.banner-img {
  width: 150rpx;
  height: 150rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
  background-color: #ddd;
}
.banner-title {
  font-size: 40rpx;
  font-weight: bold;
  color: #333;
}
.feature-grid {
  display: flex;
  flex-direction: column;
  gap: 30rpx;
}
.feature-card {
  background-color: #fff;
  padding: 40rpx;
  border-radius: 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 4rpx 10rpx rgba(0,0,0,0.05);
}
.card-icon {
  font-size: 60rpx;
  margin-bottom: 20rpx;
}
.card-title {
  font-size: 32rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
}
.card-desc {
  font-size: 24rpx;
  color: #999;
}
</style>
