<template>
  <div class="layout">
    <header class="nav">
      <nav>
        <RouterLink to="/current" class="tab" active-class="active">当期家债</RouterLink>
        <RouterLink to="/past" class="tab" active-class="active">往期家债</RouterLink>
      </nav>
    </header>
    <main class="content" @touchstart="handleTouchStart" @touchmove="handleTouchMove" @touchend="handleTouchEnd">
      <Transition name="view" mode="out-in">
        <RouterView />
      </Transition>
    </main>
    <footer class="footer">© 2025 郑涵 版权所有</footer>
  </div>
  
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { useRouter } from 'vue-router'
import { ref } from 'vue'

const router = useRouter()

// 触摸事件处理相关变量
const touchStartX = ref(0)
const touchEndX = ref(0)
const minSwipeDistance = 50 // 最小滑动距离

// 处理触摸开始事件
const handleTouchStart = (event) => {
  touchStartX.value = event.touches[0].clientX
}

// 处理触摸移动事件
const handleTouchMove = (event) => {
  touchEndX.value = event.touches[0].clientX
}

// 处理触摸结束事件
const handleTouchEnd = () => {
  const diffX = touchStartX.value - touchEndX.value
  
  // 判断是否为有效的滑动
  if (Math.abs(diffX) > minSwipeDistance) {
    // 向左滑动 - 切换到下一个标签
    if (diffX > 0) {
      if (router.currentRoute.value.path === '/current') {
        router.push('/past')
      }
    } 
    // 向右滑动 - 切换到上一个标签
    else {
      if (router.currentRoute.value.path === '/past') {
        router.push('/current')
      }
    }
  }
}
</script>

<style>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.nav {
  border-bottom: 1px solid #eee;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 10;
}
.nav nav {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 10px 12px;
}
.tab {
  text-decoration: none;
  color: #333;
  padding: 8px 12px;
  border-radius: 8px;
}
.active {
  color: #1677ff;
  font-weight: 600;
}
.content {
  flex: 1;
  display: block;
  padding: 24px;
}
.footer {
  text-align: center;
  padding: 16px 0;
  border-top: 1px solid #eee;
}

@media (max-width: 640px) {
  .content { padding: 12px; }
  .tab { padding: 10px 14px; }
}

@media (min-width: 641px) {
  .content { display: grid; place-items: center; }
}

.view-enter-active, .view-leave-active {
  transition: transform 360ms ease-in-out, opacity 360ms ease-in-out;
  will-change: transform, opacity;
  backface-visibility: hidden;
}
.view-enter-from, .view-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
.view-enter-to, .view-leave-from {
  opacity: 1;
  transform: translateX(0);
}

@media (prefers-reduced-motion: reduce) {
  .view-enter-active, .view-leave-active { transition: none; }
}
</style>
