<template>
  <view class="container">
    <!-- Hero Section -->
    <view class="hero-section">
      <image class="hero-bg" src="/static/new_home_bg.png" mode="aspectFill"></image>
      <view class="hero-content">
        <text class="hero-title">好吃嘴儿天堂</text>
        <text class="hero-subtitle">发现 · 分析 · 享受</text>
      </view>
    </view>

    <!-- Main Features Grid -->
    <view class="feature-grid">
      <!-- Where to Eat -->
      <view class="feature-card large" @click="navigateTo('/pages/where-to-eat/index')">
        <image class="card-bg" src="/static/去哪儿背景图.png" mode="aspectFill"></image>
        <view class="card-overlay night-glass">
          <text class="card-title">去哪吃</text>
          <text class="card-desc">解决你的选择困难症</text>
        </view>
      </view>

      <view class="row">
        <!-- Check Pre-made -->
        <view class="feature-card medium" @click="navigateTo('/pages/check-premade/index')">
          <image class="card-bg" src="/static/预制菜背景图.png" mode="aspectFill"></image>
          <view class="card-overlay night-glass">
            <text class="card-title">查预制</text>
            <text class="card-desc">了解食品配料与来源</text>
          </view>
        </view>

        <!-- How Much to Eat -->
        <view class="feature-card medium" @click="navigateTo('/pages/calories/index')">
          <image class="card-bg" src="/static/体重秤.png" mode="aspectFill"></image>
          <view class="card-overlay night-glass">
            <text class="card-title">吃多少</text>
            <text class="card-desc">热量估算与建议</text>
          </view>
        </view>
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
  min-height: 100vh;
  background-color: #f8f9fa;
  padding-bottom: 50rpx;
}

/* Hero Section */
.hero-section {
  position: relative;
  width: 100%;
  height: 480rpx; /* Increased height to match design */
  border-bottom-left-radius: 40rpx;
  border-bottom-right-radius: 40rpx;
  overflow: hidden;
  box-shadow: 0 10rpx 30rpx rgba(0,0,0,0.1);
}
.hero-bg {
  width: 100%;
  height: 100%;
}
.hero-content {
  position: absolute;
  bottom: 80rpx;
  left: 40rpx;
  color: #fff;
  text-shadow: 0 2rpx 10rpx rgba(0,0,0,0.5);
}
.hero-title {
  font-size: 60rpx;
  font-weight: 800;
  display: block;
  margin-bottom: 10rpx;
}
.hero-subtitle {
  font-size: 30rpx;
  opacity: 0.95;
  font-weight: 500;
}

/* Feature Grid */
.feature-grid {
  padding: 40rpx;
  margin-top: -60rpx; /* Overlap with hero */
  position: relative;
  z-index: 10;
}

.feature-card {
  position: relative;
  border-radius: 30rpx;
  overflow: hidden;
  box-shadow: 0 8rpx 25rpx rgba(0,0,0,0.08);
  transition: transform 0.2s;
  background-color: #fff;
}
.feature-card:active {
  transform: scale(0.98);
}

.large {
  width: 100%;
  height: 340rpx;
  margin-bottom: 30rpx;
}

.row {
  display: flex;
  justify-content: space-between;
}

.medium {
  width: 48%;
  height: 380rpx;
}

.card-bg {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

/* Night Glassmorphism Style */
.card-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 30rpx;
  box-sizing: border-box;
}

.night-glass {
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0) 0%,
    rgba(0, 0, 0, 0.2) 50%,
    rgba(0, 0, 0, 0.7) 100%
  );
  backdrop-filter: blur(2px); /* Subtle blur */
}

.card-icon-wrapper {
  position: absolute;
  top: 30rpx;
  right: 30rpx;
  width: 80rpx;
  height: 80rpx;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.card-icon {
  width: 50rpx;
  height: 50rpx;
}

.card-icon.small {
  width: 80rpx;
  height: 80rpx;
  margin-bottom: auto; /* Push to top */
  align-self: center;
  /* Add a subtle glow or background for icons on complex backgrounds if needed */
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

.card-title {
  color: #fff;
  font-size: 38rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
  text-shadow: 0 2rpx 4rpx rgba(0,0,0,0.5);
}

.card-desc {
  color: rgba(255, 255, 255, 0.9);
  font-size: 26rpx;
  text-shadow: 0 1rpx 3rpx rgba(0,0,0,0.5);
}
</style>
