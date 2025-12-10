<template>
  <view class="container">
    <!-- 背景艺术字装饰 -->
    <text class="bg-art-text">Foodie</text>
    <text class="bg-art-text-2">Paradise</text>

    <!-- 顶部标题区域 -->
    <view class="header-section">
      <text class="main-title">好吃嘴儿天堂</text>
      <text class="sub-title">发现 · 分析 · 享受</text>
    </view>

    <!-- 卡片层叠区域 - 3D 效果 -->
    <swiper
      class="card-swiper"
      :current="currentIndex"
      :previous-margin="'120rpx'"
      :next-margin="'120rpx'"
      :circular="true"
      :autoplay="false"
      :duration="500"
      @change="onSwiperChange"
    >
      <!-- 去哪吃卡片 -->
      <swiper-item class="swiper-item">
        <view 
          class="elli-card"
          :class="{ 'active-card': currentIndex === 0 }"
          @click="navigateTo('/pages/where-to-eat/index')"
        >
          <!-- 顶部标题 -->
          <view class="card-top">
            <text class="card-title">去哪吃</text>
          </view>
          <!-- 中间图标区域 -->
          <view class="card-icon-wrapper">
            <image 
              class="card-icon" 
              src="https://oss.swimmingliu.cn/foodie_paradise/c050311f-f1f0-463a-8c4d-3a84ceb8a57a.png" 
              mode="aspectFit"
            ></image>
          </view>
          <!-- 底部描述 -->
          <view class="card-bottom">
            <text class="card-desc">看看他们在哪儿吃？</text>
          </view>
        </view>
      </swiper-item>

      <!-- 查预制卡片 -->
      <swiper-item class="swiper-item">
        <view 
          class="elli-card"
          :class="{ 'active-card': currentIndex === 1 }"
          @click="navigateTo('/pages/check-premade/index')"
        >
          <!-- 顶部标题 -->
          <view class="card-top">
            <text class="card-title">查预制</text>
          </view>
          <!-- 中间图标区域 -->
          <view class="card-icon-wrapper">
            <image 
              class="card-icon" 
              src="https://oss.swimmingliu.cn/foodie_paradise/a58b234f-ccdf-4041-b146-724e519a4f2f.png" 
              mode="aspectFit"
            ></image>
          </view>
          <!-- 底部描述 -->
          <view class="card-bottom">
            <text class="card-desc">辨别预制菜品</text>
          </view>
        </view>
      </swiper-item>

      <!-- 吃多少卡片 -->
      <swiper-item class="swiper-item">
        <view 
          class="elli-card"
          :class="{ 'active-card': currentIndex === 2 }"
          @click="navigateTo('/pages/calories/index')"
        >
          <!-- 顶部标题 -->
          <view class="card-top">
            <text class="card-title">吃多少</text>
          </view>
          <!-- 中间图标区域 -->
          <view class="card-icon-wrapper">
            <image 
              class="card-icon" 
              src="https://oss.swimmingliu.cn/foodie_paradise/84fb877f-7b8c-476e-bf4a-d0a1a8971414.png" 
              mode="aspectFit"
            ></image>
          </view>
          <!-- 底部描述 -->
          <view class="card-bottom">
            <text class="card-desc">科学管理饮食</text>
          </view>
        </view>
      </swiper-item>
    </swiper>

  </view>
</template>

<script setup>
import { ref } from 'vue';

const currentIndex = ref(0);

const onSwiperChange = (e) => {
  currentIndex.value = e.detail.current;
};

const navigateTo = (url) => {
  uni.navigateTo({
    url: url
  });
};
</script>

<style>
/* ============================================
   页面容器 - 紫蓝渐变背景
   ============================================ */
.container {
  min-height: 100vh;
  height: 100vh;
  background: linear-gradient(
    180deg,
    #8DA0E8 0%,
    #9BB0F0 40%,
    #AEC0F8 100%
  );
  position: relative;
  overflow: hidden;
  padding-bottom: env(safe-area-inset-bottom);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

/* ============================================
   背景艺术字 - "Foodie Paradise" 
   ============================================ */
.bg-art-text {
  position: absolute;
  bottom: 200rpx;
  right: 120rpx;
  left: auto;
  font-size: 100rpx;
  font-weight: 900;
  font-style: italic;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: -4rpx;
  font-family: 'Georgia', serif;
  transform: rotate(-5deg);
  pointer-events: none;
  white-space: nowrap;
  z-index: 0;
}

.bg-art-text-2 {
  position: absolute;
  bottom: 110rpx;
  right: 60rpx;
  left: auto;
  font-size: 110rpx;
  font-weight: 900;
  font-style: italic;
  color: rgba(255, 255, 255, 0.12);
  letter-spacing: -4rpx;
  font-family: 'Georgia', serif;
  transform: rotate(-5deg);
  pointer-events: none;
  white-space: nowrap;
  z-index: 0;
}

/* ============================================
   顶部标题区域
   ============================================ */
.header-section {
  padding: 20rpx 40rpx;
  padding-top: 50rpx; /* 顶部留白 */
  text-align: center;
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.main-title {
  font-size: 60rpx;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 4rpx;
  display: block;
  margin-bottom: 10rpx;
  text-shadow: 0 4rpx 12rpx rgba(0,0,0,0.1);
}

.sub-title {
  font-size: 30rpx;
  color: rgba(255, 255, 255, 0.95);
  font-weight: 600;
  letter-spacing: 8rpx;
  text-transform: uppercase;
}

/* ============================================
   Swiper 卡片区域
   解决卡片显示不全问题：大幅增加高度，确保放大后的卡片和阴影不被裁剪
   ============================================ */
.card-swiper {
  width: 100%;
  height: 1000rpx; /* 增加到 1000rpx，给 1.15 倍放大 + 阴影留足空间 */
  margin-top: auto;
  margin-bottom: auto;
  box-sizing: border-box;
  z-index: 20;
}

/* 底部占位调整 */
.container::after {
  content: "";
  display: block;
  height: 200rpx; 
  width: 100%;
  flex-shrink: 0;
}

.swiper-item {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible; 
  padding: 40rpx 0; /* 给上下增加内边距 */
}

/* ============================================
   3D 卡片 - 柔和高级感
   去除突兀的厚块阴影，使用多层柔和阴影模拟体积感
   ============================================ */
.elli-card {
  width: 480rpx;
  height: 680rpx;
  background: linear-gradient(165deg, #FFFFFF 0%, #F6F8FB 100%);
  border-radius: 60rpx;
  padding: 60rpx 40rpx;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  position: relative;
  
  /* 
     优化后的阴影组合:
     1. 环境光 (soft ambient)
     2. 底部投影 (drop shadow)
     3. 内部高光 (inset highlight) 增加精致感
  */
  box-shadow: 
    0 20rpx 50rpx rgba(28, 32, 66, 0.15),
    0 5rpx 15rpx rgba(0, 0, 0, 0.05),
    inset 0 0 0 2rpx rgba(255, 255, 255, 0.8),
    inset 0 4rpx 10rpx rgba(255, 255, 255, 1);

  transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  transform: scale(0.92);
  opacity: 0.85; /* 非激活态稍微不那么透明，避免看起来太远 */
}

/* 激活状态 */
.elli-card.active-card {
  opacity: 1;
  z-index: 100;
  
  /* 放大 */
  transform: scale(1.15); 
  
  /* 激活时增强投影和光泽 */
  background: linear-gradient(165deg, #FFFFFF 0%, #FFFFFF 100%);
  box-shadow: 
    0 40rpx 90rpx rgba(28, 32, 66, 0.25), /* 更深远的投影 */
    0 10rpx 30rpx rgba(28, 32, 66, 0.1),
    inset 0 0 0 2rpx rgba(255, 255, 255, 1),
    inset 0 4rpx 20rpx rgba(255, 255, 255, 1);
}

/* 按下效果 */
.elli-card:active {
  transform: scale(1.12);
}

.card-top {
  margin-bottom: 30rpx;
  width: 100%;
}

.card-title {
  font-size: 52rpx;
  font-weight: 800;
  color: #2D3142;
  letter-spacing: 2rpx;
}

.card-icon-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  margin: 10rpx 0;
}

.card-icon {
  width: 360rpx;
  height: 360rpx;
  /* 优化图标投影，使其浮在卡片之上 */
  filter: drop-shadow(0 20rpx 30rpx rgba(0,0,0,0.12));
  transition: transform 0.6s ease;
}

.active-card .card-icon {
  transform: scale(1.05) translateY(-5rpx);
}

.card-bottom {
  margin-top: auto;
}

.card-desc {
  font-size: 28rpx;
  color: #9093A8;
  font-weight: 600;
}
</style>
