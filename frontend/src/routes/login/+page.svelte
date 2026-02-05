<script lang="ts">
  import { browser } from '$app/environment';
  import { goto, replaceState } from '$app/navigation';
  import { onMount } from 'svelte';
  import OAuthIcon from '$components/ui/OAuthIcon.svelte';
  import { authService } from '$services/auth';
  import { toast } from '$stores/toast';
  import { tStore } from '$stores/language';
  import type { PageData } from './$types';
  import faviconSvg from '$lib/assets/favicon.svg?raw';

  // 获取翻译函数
  const t = $derived($tStore);

  let { data }: { data: PageData } = $props();

  let email = $state('');
  let password = $state('');
  let loading = $state(false);
  let showPassword = $state(false);

  // OAuth 配置从服务端加载，避免客户端闪烁
  let oauthProviders = $derived(data.oauthProviders || {});

  // 处理URL中的错误参数
  function handleErrorParams() {
    if (!browser) return;
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    const errorDescription = urlParams.get('error_description');
    if (error) {
      toast.error(errorDescription || `Authentication error: ${error}`);
      // 清除URL中的错误参数 - 延迟执行确保路由已初始化
      setTimeout(() => {
        replaceState(window.location.pathname, {});
      }, 0);
    }
  }

  // 页面加载时初始化
  onMount(() => {
    if (browser) {
      document.title = 'Login - CC Switch';
      handleErrorParams();
    }
  });

  // 普通（邮箱密码）登录
  async function handleSubmit() {
    if (!email || !password) {
      toast.error(t('login.enterEmailPassword'));
      return;
    }

    loading = true;
    try {
      await authService.login(email, password);
      console.log('[Login] Login successful, token stored');

      // 验证 token 已存储
      if (browser) {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          console.error('[Login] Token not found in localStorage after login!');
          toast.error(t('login.loginFailed'));
          return;
        }
        console.log('[Login] Token verified in localStorage');
      }

      toast.success(t('login.loginSuccess'));

      // 等待一小段时间确保 localStorage 写入完成
      await new Promise(resolve => setTimeout(resolve, 100));

      // 登录成功后跳转到用户有权限的默认页面
      console.log('[Login] Redirecting to default page based on permissions');
      const redirectUrl = authService.getDefaultRedirectUrl();
      setTimeout(() => {
        goto(redirectUrl, { replaceState: true });
      }, 50);
    } catch (error) {
      const message = error instanceof Error ? error.message : t('login.checkCredentials');
      toast.error(message);
    } finally {
      loading = false;
    }
  }

  // OAuth2 登录 - 使用 goto 导航到后端 OAuth 端点
  function handleOAuthLogin(provider: string) {
    // 使用 goto 避免触发 "leave site" 弹窗
    goto(`/oauth/${provider}/login`, { replaceState: true });
  }

  // OAuth 提供商显示名称映射
  const providerDisplayNames: Record<string, string> = {
    github: 'GitHub',
    google: 'Google',
    feishu: 'Feishu (飞书)',
    microsoft: 'Microsoft',
    oidc: 'OIDC (SSO)'
  };

  function getProviderDisplayName(provider: string): string {
    return providerDisplayNames[provider] || provider;
  }

  // 计算启用的 OAuth 提供商
  let enabledProviders = $derived(
    (Object.entries(oauthProviders) as [string, { enabled: boolean }][]).filter(([_, config]) => config.enabled)
  );
</script>

<div class="login-container">
  <div class="login-card">
    <div class="login-title-wrapper">
      <span class="login-logo-inline">{@html faviconSvg}</span>
      <div class="login-title-group">
        <h1 class="login-title">CC Switch</h1>
      </div>
    </div>
    <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="login-form">
        <!-- 邮箱输入框 - 浮动标签设计 -->
        <div class="floating-input-group">
          <input
            id="email"
            type="email"
            bind:value={email}
            placeholder=" "
            required
            disabled={loading}
            class="floating-input"
            autocomplete="off"
          />
          <label for="email" class="floating-label">{t('login.email')}</label>
        </div>

        <!-- 密码输入框 -->
        <div class="floating-input-group password-group">
          <input
            id="password"
            type={showPassword ? 'text' : 'password'}
            bind:value={password}
            placeholder=" "
            required
            disabled={loading}
            class="floating-input"
            autocomplete="off"
          />
          <label for="password" class="floating-label">{t('login.password')}</label>
          {#if password.length > 0}
            <button
              type="button"
              class="toggle-password"
              onclick={() => showPassword = !showPassword}
              disabled={loading}
              aria-label={showPassword ? t('login.togglePasswordHide') : t('login.togglePasswordShow')}
            >
              {#if showPassword}
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="eye-icon">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="eye-icon">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              {/if}
            </button>
          {/if}
        </div>

        <button
          type="submit"
          class="full-width-button primary-button"
          disabled={loading}
        >
          {loading ? t('login.loggingIn') : t('login.login')}
        </button>
      </form>

      <!-- OAuth2 登录选项 -->
      {#if enabledProviders.length > 0}
        <div class="oauth-section">
          <div class="divider">
            <span class="divider-text">or continue with</span>
          </div>
          <div class="oauth-buttons">
            {#each enabledProviders as [provider, _]}
              <button
                type="button"
                class="oauth-button oauth-button-{provider}"
                onclick={() => handleOAuthLogin(provider)}
                disabled={loading}
              >
                <div class="oauth-icon">
                  <OAuthIcon provider={provider} size={20} />
                </div>
                <span class="oauth-button-text">
                  {getProviderDisplayName(provider)}
                </span>
              </button>
            {/each}
          </div>
        </div>
      {/if}

      <div class="login-info">
        <p class="info-title">{t('login.defaultAdminTitle')}</p>
        <div class="info-content">
          <p><strong>{t('login.defaultEmail')}</strong>admin@example.com</p>
          <p><strong>{t('login.defaultPassword')}</strong>admin123</p>
        </div>
        <p class="info-note">{t('login.warnChangePassword')}</p>
      </div>
    </div>
  </div>

<style>
  .login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background: var(--bg-secondary, #f5f5f5);
  }

  .login-card {
    width: 100%;
    max-width: 450px;
    background: var(--bg-primary, white);
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: 0.75rem;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  /* 覆盖 Card 头部样式 */
  :global(.login-card .card-header) {
    background: transparent !important;
    border-bottom: none !important;
    padding: 0 0 1rem !important;
  }

  /* 覆盖 Card 内容区域 */
  :global(.login-card .card-body) {
    padding: 0 !important;
  }

  .login-title-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
  }

  .login-title-group {
    text-align: left;
  }

  .login-logo-inline {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    flex-shrink: 0;
  }

  .login-logo-inline :global(svg) {
    width: 100%;
    height: 100%;
  }

  .login-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
    line-height: 1.2;
  }

  .login-subtitle {
    margin: 0.25rem 0 0;
    font-size: 0.8125rem;
    color: var(--text-secondary, #666);
    text-align: left;
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-top: 2rem;
  }

  /* 浮动标签输入框组 */
  .floating-input-group {
    position: relative;
    width: 100%;
  }

  .floating-input {
    width: 100%;
    padding: 1rem 0.75rem 0.5rem;
    border: 1px solid var(--input-border, #ced4da);
    border-radius: 0.375rem;
    font-size: 1rem;
    font-family: inherit;
    background: var(--input-bg, white);
    color: var(--text-primary, #333);
    transition: border-color 0.2s ease;
    box-sizing: border-box;
  }

  .floating-input:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  .floating-input:disabled {
    background-color: #e9ecef;
    cursor: not-allowed;
  }

  .floating-label {
    position: absolute;
    left: 0.75rem;
    top: 0;
    transform: translateY(-50%);
    font-size: 0.75rem;
    color: #999;
    pointer-events: none;
    transition: color 0.2s ease;
    background: var(--input-bg, white);
    padding: 0 0.25rem;
    border-radius: 0.25rem;
  }

  /* 焦点时颜色变化 */
  .floating-input:focus ~ .floating-label {
    color: #007bff;
  }

  /* 密码输入框组的切换按钮 */
  .password-group {
    position: relative;
  }

  .password-group .floating-input {
    padding-right: 2.5rem;
  }

  .toggle-password {
    position: absolute;
    right: 0.5rem;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.375rem;
    color: var(--text-secondary, #6c757d);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.375rem;
    transition: all 0.2s;
    opacity: 0;
    visibility: hidden;
  }

  /* 只在输入框获得焦点时显示眼睛按钮 */
  .password-group:focus-within .toggle-password {
    opacity: 1;
    visibility: visible;
  }

  .toggle-password:hover:not(:disabled) {
    color: var(--text-primary, #495057);
    background: rgba(0, 0, 0, 0.05);
  }

  .toggle-password:disabled {
    cursor: not-allowed;
  }

  .toggle-password .eye-icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  /* 全宽按钮统一样式 */
  .full-width-button {
    width: 100%;
    padding: 0.875rem 1rem;
    border: none;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .primary-button {
    background: var(--primary-color, #007bff);
    color: white;
  }

  .primary-button:hover:not(:disabled) {
    background: var(--primary-color-hover, #0056b3);
  }

  .primary-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .login-info {
    margin-top: 2rem;
    padding: 1.5rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
  }

  .info-title {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .info-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .info-content p {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  }

  .info-content strong {
    color: var(--text-primary, #1a1a1a);
  }

  .info-note {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--warning-color, #856404);
    font-weight: 500;
  }

  :global([data-theme="dark"]) .info-note {
    color: #d29922;
  }

  @media (max-width: 480px) {
    .login-container {
      padding: 1rem;
    }

    .login-title {
      font-size: 1.5rem;
    }
  }

  .oauth-section {
    margin-top: 2rem;
  }

  .divider {
    display: flex;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .divider::before,
  .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e0e0e0;
  }

  .divider-text {
    padding: 0 1rem;
    font-size: 0.875rem;
    color: #666;
  }

  .oauth-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .oauth-button {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    padding: 0.75rem 1rem;
    border: 1px solid #d0d7de;
    border-radius: 0.5rem;
    background: #fff;
    color: #24292f;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    justify-content: center;
  }

  .oauth-button:hover:not(:disabled) {
    background: #f7f9ff;
    border-color: #9333ea;
  }

  .oauth-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .oauth-button-twitter {
    border-color: #1da1f2;
  }

  .oauth-button-twitter:hover:not(:disabled) {
    background: #e8f5fd;
  }

  .oauth-button-github {
    border-color: #333;
  }

  .oauth-button-github:hover:not(:disabled) {
    background: #f5f5f5;
  }

  .oauth-button-google {
    border-color: #4285f4;
  }

  .oauth-button-google:hover:not(:disabled) {
    background: #f8f9fa;
  }

  .oauth-button-feishu {
    border-color: #3370ff;
  }

  .oauth-button-feishu:hover:not(:disabled) {
    background: #e6effe;
  }

  .oauth-button-microsoft {
    border-color: #00a4ef;
  }

  .oauth-button-microsoft:hover:not(:disabled) {
    background: #e6f7ff;
  }

  .oauth-icon {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .oauth-button-text {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .loading-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #666;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
