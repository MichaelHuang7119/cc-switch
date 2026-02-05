<script lang="ts">
  import { onMount } from 'svelte';
  import { goto, beforeNavigate } from '$app/navigation';
  import { page } from '$app/stores';
  import Header from '$components/layout/Header.svelte';
  import Toast from '$components/ui/Toast.svelte';
  import { theme } from '$stores/theme';
  import { language, tStore } from '$stores/language';
  import { authService } from '$services/auth';
  import {
    initAuthState,
    subscribeAuth,
    checkPermission,
    getIsLoggingOut,
    type AuthState
  } from '$stores/auth.svelte';
  import { handleKeyboardEvent } from '$lib/config/keyboardShortcuts';
  import { toast } from '$stores/toast';
  import '../lib/styles/global.css';

  // 获取翻译函数（响应式）
  const t = $derived($tStore);

  // 使用响应式的 auth store（SSR 时为 null，onMount 后初始化）
  let authState = $state<AuthState | null>(null);

  // 获取初始认证状态（同步读取 localStorage，避免闪烁）
  function getInitialAuthState(): AuthState {
    const token = localStorage.getItem('auth_token');
    const userStr = localStorage.getItem('auth_user');

    if (!token) return { isAuthenticated: false, user: null };

    // token 存在，尝试从 localStorage 恢复用户信息
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        return { isAuthenticated: true, user };
      } catch {
        return { isAuthenticated: true, user: null };
      }
    }

    // token 存在但没有用户数据，先标记为已登录
    return { isAuthenticated: true, user: null };
  }

  // 初始化 auth store 并订阅状态变化
  $effect(() => {
    if (typeof window !== 'undefined') {
      // 初始化 auth 状态（同步读取 localStorage 避免闪烁）
      authState = getInitialAuthState();

      // 初始化 auth store（异步验证 token）
      initAuthState();

      // 订阅 auth 状态变化（登录/登出时自动更新导航栏）
      const unsubscribe = subscribeAuth((state) => {
        authState = state;
      });

      return unsubscribe;
    }
  });

  // 导航项配置（根据权限动态显示 - 使用响应式 authState）
  let navItems = $derived.by(() => {
    // SSR 或正在初始化时，不显示任何导航项
    if (!authState) {
      return [];
    }

    // 如果未登录且不在登出过程中，不在非登录页显示导航栏
    if (!authState.isAuthenticated && !getIsLoggingOut() && currentPathname !== '/login' && !currentPathname.startsWith('/oauth/')) {
      return [];
    }

    const items = [
      { href: '/', label: 'nav.home', permission: 'providers' },
      { href: '/chat', label: 'nav.chat', permission: 'chat' },
      { href: '/providers', label: 'nav.providers', permission: 'providers' },
      { href: '/admin/users', label: 'nav.users', permission: 'users' },
      { href: '/config', label: 'nav.config', permission: 'config' },
      { href: '/health', label: 'nav.health', permission: 'health' },
      { href: '/stats', label: 'nav.stats', permission: 'stats' },
      { href: '/api-keys', label: 'nav.apiKeys', permission: 'api_keys' }
    ];

    // 调试日志
    console.log('[Layout] Nav: user:', JSON.stringify(authState.user));

    // 根据权限过滤导航项
    return items.filter(item => {
      // chat 是默认权限，始终显示
      if (item.permission === 'chat') return true;
      // 其他权限需要检查
      const hasPerm = checkPermission(item.permission);
      console.log('[Layout] Nav filter:', item.href, item.permission, hasPerm);
      return hasPerm;
    });
  });

  // 获取当前路径名（增加空值检查）
  let currentPathname = $derived($page.url?.pathname || '');

  // 检查链接是否激活
  function isActive(href: string): boolean {
    if (href === '/') {
      return currentPathname === '/';
    }
    return currentPathname.startsWith(href);
  }

  // 在导航前检查权限
  beforeNavigate((nav) => {
    const pathname = nav.to?.url.pathname || '';
    console.log('[Layout] beforeNavigate to:', pathname);

    // 公开路由跳过检查
    if (pathname === '/login' || pathname.startsWith('/oauth/')) {
      console.log('[Layout] Skipping auth check for public route:', pathname);
      return;
    }

    // 未登录用户跳转到登录页（使用响应式 authState）
    console.log('[Layout] Auth check for', pathname, ':', authState?.isAuthenticated ? 'authenticated' : 'not authenticated');
    if (!authState?.isAuthenticated) {
      console.log('[Layout] Not authenticated, redirecting to /login');
      // 不使用 nav.cancel()，而是直接用 goto 重定向
      // 这样可以避免触发浏览器的导航拦截对话框
      goto('/login', { replaceState: true, keepFocus: true, noScroll: true });
      return;
    }

    // 权限检查
    const canAccess = authService.canAccessRoute(pathname);
    console.log('[Layout] Permission check for', pathname, ':', canAccess ? 'allowed' : 'denied');
    if (!canAccess) {
      console.log('[Layout] Permission denied for:', pathname);
      const defaultRedirect = authService.getDefaultRedirectUrl();
      if (pathname !== defaultRedirect) {
        console.log('[Layout] Redirecting to default:', defaultRedirect);
        toast.error(t('common.accessDenied'));
        // 不使用 nav.cancel()，直接用 goto 重定向
        goto(defaultRedirect, { replaceState: true, keepFocus: true, noScroll: true });
        return;
      }
    }
  });

  // 初始化主题和语言
  onMount(() => {
    // 主动注销任何已有的 Service Worker，避免刷新弹窗问题
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        for (const registration of registrations) {
          console.log('[Layout] Unregistering existing Service Worker');
          registration.unregister().catch(err => {
            console.warn('[Layout] Failed to unregister service worker:', err);
          });
        }
      }).catch(err => {
        console.warn('[Layout] Failed to check service workers:', err);
      });
    }

    // 初始化主题（使用浏览器本地存储，不依赖用户登录状态）
    theme.init();

    // 初始化语言设置（会尝试从后端获取，如果已登录的话）
    // 添加超时避免长时间等待
    const languagePromise = language.init();
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Language init timeout')), 5000)
    );
    Promise.race([languagePromise, timeoutPromise]).catch(console.error);

    // auth store 会在 $effect 中自动初始化，这里不需要额外处理
    // 轮询机制已经在 auth.svelte.ts 中实现

    // 未登录且不在登录页，重定向到登录页
    if (!authState?.isAuthenticated && currentPathname !== '/login' && !currentPathname.startsWith('/oauth/')) {
      console.log('[Layout] Not authenticated on load, redirecting to login');
      goto('/login', { replaceState: true, noScroll: true });
    }

    // 添加全局键盘快捷键监听
    const handleKeydown = (event: KeyboardEvent) => {
      handleKeyboardEvent(event);
    };

    window.addEventListener('keydown', handleKeydown);

    // 监听 OAuth 登录成功事件
    const handleAuthLogin = (event: CustomEvent) => {
      console.log('[Layout] Received auth:login event', event.detail);
      // 重新验证认证状态（使用响应式 authState）
      if (authState?.isAuthenticated) {
        console.log('[Layout] OAuth login successful, user is now authenticated');
        // 如果当前在登录页，自动跳转到默认页面（不要直接跳转到 /，避免权限问题）
        if (currentPathname === '/login') {
          const redirectUrl = authService.getDefaultRedirectUrl();
          console.log('[Layout] Redirecting to default page:', redirectUrl);
          goto(redirectUrl);
        }
      }
    };

    window.addEventListener('auth:login', handleAuthLogin as any);

    // 监听 storage 变化（用于多标签页同步）
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === 'auth_token' && event.newValue === null) {
        console.log('[Layout] Token cleared by another tab, logging out');
        if (currentPathname !== '/login' && !currentPathname.startsWith('/oauth/')) {
          goto('/login', { replaceState: true, noScroll: true });
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);

    // 返回清理函数
    return () => {
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('auth:login', handleAuthLogin as any);
      window.removeEventListener('storage', handleStorageChange);
    };
  });

  function _handleLogout() {
    authService.logout();
  }

  let { children } = $props();
</script>

<div class="app" class:chat-layout={currentPathname === '/chat'}>
  {#if currentPathname !== '/login' && !currentPathname.startsWith('/oauth/')}
    <Header title="CC Switch">
      {#snippet nav()}
        <nav>
          {#each navItems as item}
            <a
              href={item.href}
              class="nav-link"
              class:active={isActive(item.href)}
            >
              {t(item.label)}
            </a>
          {/each}
        </nav>
      {/snippet}
    </Header>
  {/if}
  <main class="main">
    {@render children()}
  </main>
  {#if currentPathname !== '/login' && currentPathname !== '/chat' && !currentPathname.startsWith('/oauth/')}
    <footer class="footer">
      <p>© 2025 CC Switch.</p>
    </footer>
  {/if}
  <Toast />
</div>

<style>
  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .main {
    flex: 1;
    background: var(--bg-secondary);
    padding: 2rem 0;
    min-height: 0;
  }

  :global(.app > .main:only-child) {
    /* 登录页无 Header/Footer 时移除顶部 padding，避免页面抖动 */
    padding-top: 0;
  }

  :global(.chat-layout) .main {
    padding: 0;
  }

  :global(.chat-layout) {
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* 移动端聊天布局优化 - 确保Header可见 */
  @media (max-width: 768px) {
    :global(.chat-layout) .app {
      height: 100dvh;
      overflow: auto; /* 允许页面滚动 */
    }

    :global(.chat-layout) .main {
      flex: 1;
      overflow: auto; /* 允许main区域滚动 */
      padding: 0;
      min-height: 0;
    }
  }

  @media (max-width: 768px) {
    .main {
      padding: 1rem 0 3rem; /* 增加底部padding为footer留出空间 */
    }
  }

  .footer {
    background: var(--bg-tertiary);
    border: none;
    padding: 0.5rem 0;
    text-align: center;
    color: var(--text-secondary);
    /* 确保footer始终可见 */
    position: relative;
    z-index: 5;
  }

  .footer p {
    margin: 0;
    font-size: 0.875rem;
    color: rgba(66, 153, 225, 0.6);
  }

  /* 移动端footer优化 */
  @media (max-width: 768px) {
    .footer {
      padding: 0.75rem 0;
      margin-bottom: env(safe-area-inset-bottom); /* 考虑安全区域 */
    }

    .footer p {
      font-size: 0.8125rem;
    }
  }

  .nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    padding: 0.5rem 0.375rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
    border-bottom: 2px solid transparent;
    font-size: 0.875rem;
    white-space: nowrap;
    max-width: 110px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @media (max-width: 1200px) {
    .nav-link {
      padding: 0.5rem 0.25rem;
      font-size: 0.8125rem;
      max-width: 95px;
    }
  }

  @media (max-width: 1024px) {
    .nav-link {
      padding: 0.5rem 0.1875rem;
      font-size: 0.78125rem;
      max-width: 85px;
    }
  }

  .nav-link:hover {
    background: var(--bg-tertiary);
    color: var(--primary-color);
  }

  .nav-link.active {
    color: var(--primary-color);
    font-weight: 600;
    background: var(--bg-tertiary);
    border-bottom-color: var(--primary-color);
  }

  @media (max-width: 768px) {
    .nav-link {
      padding: 0.5rem 0.375rem;
      font-size: 0.8125rem;
      max-width: 100px;
    }
  }

  @media (max-width: 480px) {
    .nav-link {
      padding: 0.5rem 0.25rem;
      font-size: 0.78125rem;
      max-width: 90px;
    }
  }
</style>