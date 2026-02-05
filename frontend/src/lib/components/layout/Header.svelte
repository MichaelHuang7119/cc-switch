<script lang="ts">
  import { tStore } from '$stores/language';
  import { authService } from '$services/auth';
  import SettingsModal from '$components/SettingsModal.svelte';
  import { onMount } from 'svelte';

  let { title = 'CC Switch', subtitle = '', nav } = $props<{
    title?: string;
    subtitle?: string;
    nav?: () => any;
  }>();

  // 设置弹窗状态
  let showSettingsModal = $state(false);

  // 用户菜单状态
  let showUserMenu = $state(false);
  let userMenuRef = $state<HTMLDivElement | null>(null);

  // 移动端导航菜单状态
  let showMobileNav = $state(false);

  // 检测标题是否被截断
  let marqueeContainerRef = $state<HTMLElement | null>(null);
  let isTitleTruncated = $state(false);

  // 获取翻译函数（响应式）
  const t = $derived($tStore);

  // 检测文本是否被截断
  onMount(() => {
    const checkTruncation = () => {
      if (marqueeContainerRef) {
        // 检测h1元素本身是否被截断
        const h1Element = marqueeContainerRef.querySelector('h1') as HTMLElement;
        if (h1Element) {
          const scrollWidth = h1Element.scrollWidth;
          const clientWidth = h1Element.clientWidth;
          isTitleTruncated = scrollWidth > clientWidth;
        }
      }
    };

    // 初始检测
    checkTruncation();

    // 延迟检测，等待DOM渲染完成
    setTimeout(checkTruncation, 100);

    // 监听窗口大小变化
    window.addEventListener('resize', checkTruncation);

    return () => {
      window.removeEventListener('resize', checkTruncation);
    };
  });

  function handleLogout() {
    const message = t('common.logoutConfirm');
    if (confirm(message)) {
      authService.logout();
    }
  }

  function openSettings() {
    showSettingsModal = true;
    showUserMenu = false;
  }

  // 点击外部关闭用户菜单和移动端导航
  function handleClickOutside(event: MouseEvent) {
    if (showUserMenu && userMenuRef && !userMenuRef.contains(event.target as Node)) {
      showUserMenu = false;
    }

    // 点击导航项后关闭移动端导航
    if (showMobileNav) {
      const target = event.target as HTMLElement;
      if (target.closest('.mobile-nav a')) {
        showMobileNav = false;
      }
    }
  }

  // 添加和移除文档级点击监听器
  onMount(() => {
    document.addEventListener('click', handleClickOutside);

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<header class="header">
  <div class="container">
    <div class="brand">
      <img src="/favicon.svg" alt="CC Switch Logo" class="brand-icon" />
      <div class="brand-text" bind:this={marqueeContainerRef}>
        <h1>
          {#if isTitleTruncated}
            <span class="marquee-container">
              <span class="marquee-text">{title}</span>
              <span class="marquee-text">{title}</span>
            </span>
          {:else}
            <span class="title-text">{title}</span>
          {/if}
        </h1>
        {#if subtitle}
          <p class="subtitle">{subtitle}</p>
        {/if}
      </div>
    </div>

    <div class="header-actions">
      {#if nav}
        <nav class="nav desktop-nav">
          {@render nav()}
        </nav>
      {/if}

      <div class="mobile-actions">
        <!-- 移动端用户中心 -->
        <div class="user-menu" bind:this={userMenuRef}>
          <button
            class="user-menu-button"
            onclick={() => showUserMenu = !showUserMenu}
            aria-label={t('header.userCenter')}
            aria-expanded={showUserMenu}
            aria-haspopup="true"
          >
            <span class="user-avatar">👤</span>
          </button>

          {#if showUserMenu}
            <div class="user-menu-dropdown" role="menu">
              <button
                class="menu-item"
                onclick={openSettings}
                role="menuitem"
              >
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
                <span>{t('header.settings')}</span>
              </button>
              <div class="menu-separator"></div>
              <button
                class="menu-item logout-item"
                onclick={handleLogout}
                role="menuitem"
              >
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                <span>{t('header.logout')}</span>
              </button>
            </div>
          {/if}
        </div>

        <!-- 移动端汉堡菜单按钮 -->
        <button
          class="mobile-menu-button {showMobileNav ? 'is-open' : ''}"
          onclick={(e) => {
            e.stopPropagation();
            showMobileNav = !showMobileNav;
          }}
          aria-label={t('header.toggleMenu')}
          aria-expanded={showMobileNav}
        >
          <svg class="hamburger-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" class="line-1"></line>
            <line x1="3" y1="12" x2="21" y2="12" class="line-2"></line>
            <line x1="3" y1="18" x2="21" y2="18" class="line-3"></line>
          </svg>
        </button>
      </div>
    </div>
  </div>
</header>

<!-- 移动端导航菜单 -->
{#if showMobileNav && nav}
  <nav class="mobile-nav">
    {@render nav()}
  </nav>
{/if}

<!-- 设置弹窗 -->
<SettingsModal show={showSettingsModal} onClose={() => showSettingsModal = false} />

<style>
  .header {
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 0;
    box-shadow: 0 2px 4px var(--card-shadow);
    /* 确保Header始终可见 */
    position: sticky;
    top: 0;
    z-index: 100;
  }

  /* 聊天页面的Header需要更高的z-index */
  :global(.chat-layout) .header {
    z-index: 50;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .brand-icon {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .brand-text h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 350px;
  }

  /* 非截断状态的标题 */
  .title-text {
    display: inline-block;
    white-space: nowrap;
  }

  /* 滚动容器 - 只有在截断时使用 */
  .marquee-container {
    display: inline-flex;
    white-space: nowrap;
    /* 超慢滚动 - 让重置不可察觉 */
    animation: marquee-slide 6s linear infinite;
  }

  /* 滚动文本 */
  .marquee-text {
    display: inline-block;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* 第一个文本后添加间距 */
  .marquee-text:first-child {
    padding-right: 5rem;
  }

  /* 简单线性滚动 - 从0%到-50% */
  @keyframes marquee-slide {
    0% {
      transform: translateX(0);
    }
    100% {
      transform: translateX(-50%);
    }
  }

  @media (max-width: 1200px) {
    .brand-text h1 {
      max-width: 250px;
      font-size: 1.25rem;
    }
  }

  @media (max-width: 768px) {
    .brand-text h1 {
      max-width: 180px;
      font-size: 1.1rem;
    }
  }

  .subtitle {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .nav {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
    max-width: 600px;
  }

  /* 响应式调整 - 在较小屏幕上缩小间距 */
  @media (max-width: 1200px) {
    .nav {
      gap: 0.375rem;
      max-width: 500px;
    }
  }

  @media (max-width: 1024px) {
    .nav {
      gap: 0.25rem;
      max-width: 400px;
    }
  }

  .user-menu {
    position: relative;
  }

  .user-menu-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    background: var(--bg-primary);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .user-menu-button:hover {
    background: var(--bg-secondary);
    border-color: var(--primary-color);
  }

  .user-avatar {
    font-size: 1.25rem;
    line-height: 1;
  }

  .user-menu-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 0.5rem;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    box-shadow: 0 4px 12px var(--card-shadow);
    /* 宽度由内容决定，不再设置最小宽度 */
    width: max-content;
    min-width: max-content;
    z-index: 1000;
    /* 使用padding替代overflow裁剪，确保点击区域不被裁剪 */
    padding: 0.25rem;
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: background 0.15s;
    text-align: left;
    /* 确保点击区域足够大 */
    min-height: 44px;
    box-sizing: border-box;
  }

  .menu-item:hover {
    background: var(--bg-secondary);
  }

  .menu-item.logout-item {
    color: var(--danger-color);
  }

  .menu-item.logout-item:hover {
    background: var(--bg-secondary);
  }

  .menu-icon {
    flex-shrink: 0;
    color: var(--text-secondary);
  }

  .menu-item.logout-item .menu-icon {
    color: var(--danger-color);
  }

  .menu-separator {
    height: 1px;
    background: var(--border-color);
    margin: 0.25rem 0;
  }

  /* 移动端汉堡菜单按钮 */
  .mobile-menu-button {
    display: none;
    padding: 0.5rem;
    background: transparent;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }

  .mobile-menu-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(90, 156, 255, 0.1), transparent);
    transition: left 0.5s;
  }

  .mobile-menu-button:hover::before {
    left: 100%;
  }

  .mobile-menu-button:hover {
    background: var(--bg-secondary);
    border-color: var(--primary-color);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(90, 156, 255, 0.2);
  }

  .mobile-menu-button:active {
    transform: translateY(0) scale(0.95);
  }

  .hamburger-icon {
    display: block;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* 汉堡菜单动画 */
  .mobile-menu-button.is-open .hamburger-icon {
    transform: rotate(180deg);
  }

  .mobile-menu-button .line-1,
  .mobile-menu-button .line-2,
  .mobile-menu-button .line-3 {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    transform-origin: center;
  }

  /* 展开状态的线条动画 */
  .mobile-menu-button.is-open .line-1 {
    transform: translateY(6px) rotate(45deg);
  }

  .mobile-menu-button.is-open .line-2 {
    opacity: 0;
    transform: scale(0);
  }

  .mobile-menu-button.is-open .line-3 {
    transform: translateY(-6px) rotate(-45deg);
  }

  /* 移动端导航菜单 */
  .mobile-nav {
    position: fixed;
    top: 4.5rem; /* Header高度约4.5rem */
    right: 1rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 0.75rem;
    z-index: 9999;
    animation: slideDown 0.3s ease-out;
    /* 宽度由内容决定，但不超过屏幕宽度 */
    width: max-content;
    max-width: calc(100vw - 2rem);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  /* 移动端导航链接样式 */
  .mobile-nav :global(.nav-link) {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    color: var(--text-primary);
    text-decoration: none;
    border-radius: 0.5rem;
    transition: all 0.2s;
    background: transparent;
    text-align: left;
    font-weight: 500;
    /* 允许水平滚动长文本 */
    white-space: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
    /* 隐藏滚动条但保持可滚动 */
    -ms-overflow-style: none;
    mask-image: linear-gradient(to right, transparent 0, black 1rem, black calc(100% - 1rem), transparent 100%);
  }

  /* Webkit浏览器隐藏滚动条 */
  .mobile-nav :global(.nav-link)::-webkit-scrollbar {
    display: none;
  }

  .mobile-nav :global(.nav-link:hover) {
    background: var(--bg-tertiary);
    color: var(--primary-color);
  }

  .mobile-nav :global(.nav-link.active) {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    font-weight: 600;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 768px) {
    .container {
      padding: 0 1rem;
      flex-wrap: nowrap; /* 不换行，保持品牌和按钮在一行 */
    }

    .header-actions {
      gap: 0.5rem;
    }

    .mobile-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .user-menu-button {
      padding: 0.5rem;
    }

    .user-avatar {
      font-size: 1.125rem;
    }

    .mobile-menu-button {
      display: inline-flex;
    }

    .desktop-nav {
      display: none;
    }

    .brand-icon {
      width: 32px;
      height: 32px;
    }

    .brand-text h1 {
      font-size: 1.125rem;
      max-width: 160px;
    }

    .subtitle {
      font-size: 0.8125rem;
    }

    .user-menu-button {
      padding: 0.5rem;
      min-width: 2.5rem;
    }
  }

  @media (max-width: 480px) {
    .brand-icon {
      width: 28px;
      height: 28px;
    }

    .brand-text h1 {
      font-size: 1rem;
      max-width: 140px;
    }

    .mobile-menu-button svg {
      width: 20px;
      height: 20px;
    }

    .mobile-nav {
      padding: 0.75rem;
    }

    .mobile-nav :global(.nav-link) {
      padding: 0.75rem 0.875rem;
      font-size: 0.9375rem;
    }
  }
</style>