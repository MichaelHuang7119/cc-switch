<script lang="ts">
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import Card from '$components/ui/Card.svelte';
  import Badge from '$lib/components/ui/Badge.svelte';
  import Button from '$components/ui/Button.svelte';
  import WelcomeModal from '$lib/components/WelcomeModal.svelte';
  import StatCard from '$lib/components/ui/StatCard.svelte';
  import RealTimeIndicator from '$lib/components/ui/RealTimeIndicator.svelte';
  import { providers, providerStats } from '$stores/providers';
  import { healthStatus } from '$stores/health';
  import { providerService } from '$services/providers';
  import { authService } from '$services/auth';
  import { toast } from '$stores/toast';
  import Input from '$components/ui/Input.svelte';
  import { tStore } from '$stores/language';

  // Set page title
  if (browser) {
    document.title = 'CC Switch';
  }

  let loading = $state(true);
  let currentUrl = $state('');
  let copySuccess = $state(false);
  let showWelcome = $state(false);

  // 检查是否需要显示欢迎弹窗 - 立即检查，不等待onMount
  if (browser) {
    const hasShownWelcome = localStorage.getItem('welcome_shown');
    const token = localStorage.getItem('auth_token');

    console.log('[Home] Initial check - hasShownWelcome:', hasShownWelcome, 'hasToken:', !!token);

    if (!hasShownWelcome && token) {
      console.log('[Home] Setting showWelcome to true (initial)');
      showWelcome = true;
    }
  }

  // 检查是否需要显示欢迎弹窗 - 在 effect 中再次检查
  $effect(() => {
    if (!browser) return;

    const hasShownWelcome = localStorage.getItem('welcome_shown');
    const token = localStorage.getItem('auth_token');

    console.log('[Home] Effect check - hasShownWelcome:', hasShownWelcome, 'hasToken:', !!token, 'showWelcome:', showWelcome);

    if (!hasShownWelcome && token && !showWelcome) {
      console.log('[Home] Setting showWelcome to true (effect)');
      showWelcome = true;
    } else {
      console.log('[Home] Not showing welcome modal - hasShownWelcome:', hasShownWelcome, 'token exists:', !!token);
    }
  });

  // 获取翻译函数和当前语言
  const t = $derived($tStore);

  // 翻译函数，支持参数替换
  function translateWithParams(key: string, params: Record<string, string | number> = {}): string {
    let text = t(key);
    Object.keys(params).forEach((paramKey) => {
      text = text.replace(new RegExp(`{${paramKey}}`, 'g'), String(params[paramKey]));
    });
    return text;
  }

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  // 供应商概览搜索和筛选
  let providerSearchQuery = $state('');
  let providerFilterEnabled: 'all' | 'enabled' | 'disabled' = $state('all');
  const maxDisplayProviders = 5; // 首页最多显示5个
  
  // 客户端过滤
  const filteredProvidersForPreview = $derived(
    $providers.filter(p => {
      // 搜索过滤
      if (providerSearchQuery.trim()) {
        const query = providerSearchQuery.toLowerCase();
        if (!p.name.toLowerCase().includes(query) &&
            !p.base_url.toLowerCase().includes(query)) {
          return false;
        }
      }

      // 状态过滤
      if (providerFilterEnabled === 'enabled' && !p.enabled) return false;
      if (providerFilterEnabled === 'disabled' && p.enabled) return false;

      return true;
    }).slice(0, maxDisplayProviders)
  );
  
  // 计算是否有更多供应商（优化：复用过滤逻辑）
  const allFilteredProviders = $derived(
    $providers.filter(p => {
      if (providerSearchQuery.trim()) {
        const query = providerSearchQuery.toLowerCase();
        if (!p.name.toLowerCase().includes(query) &&
            !p.base_url.toLowerCase().includes(query)) {
          return false;
        }
      }
      if (providerFilterEnabled === 'enabled' && !p.enabled) return false;
      if (providerFilterEnabled === 'disabled' && p.enabled) return false;
      return true;
    })
  );

  const hasMoreProviders = $derived(filteredProvidersForPreview.length < allFilteredProviders.length);

  onMount(async () => {
    // 确保已认证后再加载数据
    if (!authService.isAuthenticated()) {
      return;
    }

    // 如果没有 providers 权限，跳过数据加载（路由级别会重定向，但保留这里作为安全网）
    if (!authService.hasPermission('providers')) {
      console.log('[Home] User does not have providers permission');
      loading = false;
      return;
    }

    abortController = new AbortController();
    try {
      // 获取当前 URL
      if (browser) {
        currentUrl = window.location.origin;
      }

      // 加载供应商
      const providersData = await providerService.getAll({ signal: abortController.signal });

      // 检查是否已被取消
      if (abortController.signal.aborted) return;

      providers.set(providersData);

      // 不自动加载健康状态 - 仅在用户手动刷新时加载
      // 健康状态检查会消耗API调用和token
      // 但如果store中已有健康数据，则显示
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load dashboard data:', error);
      toast.error(t('home.messages.loadingFailed'));
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
    }
  });

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  });

  async function copyToClipboard(text: string) {
    if (!browser) return;

    // 优先使用现代 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        copySuccess = true;
        toast.success(t('home.messages.copiedToClipboard'));
        setTimeout(() => {
          copySuccess = false;
        }, 2000);
        return;
      } catch (error) {
        console.error('Clipboard API failed:', error);
        // 继续尝试降级方案
      }
    }

    // 降级方案：使用传统的 execCommand
    try {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);

      if (successful) {
        copySuccess = true;
        toast.success(t('home.messages.copiedToClipboard'));
        setTimeout(() => {
          copySuccess = false;
        }, 2000);
      } else {
        throw new Error('execCommand failed');
      }
    } catch (error) {
      console.error('Failed to copy:', error);
      toast.error(t('home.messages.copyFailed'));
    }
  }

  // 计算健康状态统计（基于store中的数据）
  const healthyCount = $derived($healthStatus.providers.filter(p => p.healthy === true).length);
  const unhealthyCount = $derived($healthStatus.providers.filter(p => p.healthy === false).length);
  const hasHealthData = $derived($healthStatus.providers.length > 0 && healthyCount + unhealthyCount > 0);

  // 使用后端返回的总体状态，而不是自己计算
  const overallStatus = $derived($healthStatus.status);
  const statusBadgeType = $derived(
    overallStatus === 'healthy' ? 'success' as const :
    overallStatus === 'partial' ? 'warning' as const :
    overallStatus === 'unhealthy' ? 'danger' as const :
    'info' as const
  );
  const statusBadgeText = $derived(
    overallStatus === 'healthy' ? t('health.healthy') :
    overallStatus === 'partial' ? t('health.partialHealthy') :
    overallStatus === 'unhealthy' ? t('health.unhealthy') :
    t('health.notChecked')
  );

  const anthropicBaseUrl = $derived(currentUrl || 'http://localhost:5175');
  const configCommand = $derived(`export ANTHROPIC_BASE_URL=${anthropicBaseUrl}\nexport ANTHROPIC_API_KEY="any-value"`);

  // 最近活动时间线数据（模拟数据，实际可从API获取）
  const _recentActivities = $derived([
    {
      id: 1,
      type: 'health_check',
      message: t('home.recentActivities.healthCheckCompleted'),
      timestamp: new Date(),
      status: 'success'
    },
    {
      id: 2,
      type: 'provider_added',
      message: t('home.recentActivities.providerAdded'),
      timestamp: new Date(Date.now() - 3600000),
      status: 'info'
    },
    {
      id: 3,
      type: 'config_updated',
      message: t('home.recentActivities.configUpdated'),
      timestamp: new Date(Date.now() - 7200000),
      status: 'warning'
    }
  ]);
</script>

<div class="container">

{#if loading}
    <div class="loading">
      <div class="loading-spinner"></div>
      <p>{t('common.loading')}</p>
    </div>
  {:else}
    <!-- 欢迎区块 -->
    <div class="welcome-section">
      <div class="welcome-content">
        <div class="welcome-text">
          <h1 class="welcome-title">
            <span class="welcome-emoji">👋</span>
            {t('home.welcome.title')}
          </h1>
        </div>
        <div class="welcome-actions">
          <Button variant="primary" onclick={() => goto('/providers', { replaceState: true })}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            {t('home.welcomeActions.addProvider')}
          </Button>
          <Button variant="secondary" onclick={() => goto('/health', { replaceState: true })}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            {t('home.welcomeActions.viewHealthStatus')}
          </Button>
        </div>
      </div>
    </div>

    <!-- 关键指标卡片 -->
    <div class="stats-grid">
      <StatCard
        title={t('home.providerStats.total')}
        value={$providerStats.total}
        subtitle={t('home.providerStats.totalProvidersConfigured')}
        icon="<circle cx='12' cy='12' r='10'></circle><path d='M12 6v6l4 2'></path>"
        type="info"
        size="lg"
      >
        {#snippet children()}
          <div class="stat-detail">
            <Badge type="success">{$providerStats.enabled} {t("providers.enabled")}</Badge>
            <Badge type="secondary">{$providerStats.disabled} {t("providers.disabled")}</Badge>
          </div>
        {/snippet}
      </StatCard>

      <StatCard
        title={t('health.overallStatus')}
        value={hasHealthData ? statusBadgeText : t('health.notChecked')}
        subtitle={hasHealthData ? t('health.systemHealth') : t('health.noData')}
        icon={hasHealthData ? (statusBadgeType === 'success' ? "<path d='M22 11.08V12a10 10 0 1 1-5.93-9.14'></path><polyline points='22 4 12 14.01 9 11.01'></polyline>" : "<path d='M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'></path><line x1='12' y1='9' x2='12' y2='13'></line><line x1='12' y1='17' x2='12.01' y2='17'></line>") : "<circle cx='12' cy='12' r='10'></circle><line x1='12' y1='8' x2='12' y2='12'></line><line x1='12' y1='16' x2='12.01' y2='16'></line>"}
        type={hasHealthData ? (statusBadgeType === 'success' ? 'success' : statusBadgeType === 'warning' ? 'warning' : 'danger') : 'default'}
        size="lg"
        trend={hasHealthData ? (statusBadgeType === 'success' ? 'up' : statusBadgeType === 'warning' ? 'neutral' : 'down') : 'neutral'}
        trendValue={hasHealthData ? `${healthyCount}/${healthyCount + unhealthyCount} ${t("health.healthy")}` : t("health.notChecked")}
      >
        {#snippet children()}
          <div class="stat-detail">
            <span class="detail-item">
              <Badge type="success">{healthyCount} {t("health.healthy")}</Badge>
            </span>
            <span class="detail-item">
              <Badge type="danger">{unhealthyCount} {t("health.unhealthy")}</Badge>
            </span>
          </div>
        {/snippet}
      </StatCard>

      <StatCard
        title={t('home.systemStatus.title')}
        value={t('home.systemStatus.running')}
        subtitle={t('home.systemStatus.subtitle')}
        icon="<circle cx='12' cy='12' r='10'></circle><path d='M12 6v6l4 2'></path>"
        type="success"
        size="lg"
      >
        {#snippet children()}
          <RealTimeIndicator status="online" text={t('home.systemStatus.normal')} size="sm" animated={true} />
        {/snippet}
      </StatCard>
    </div>

    <div class="config-section">
      <Card title={t('home.config.title')} subtitle={t('home.config.subtitle')}>
        <div class="config-content">
          <p class="config-description">
            {t('home.config.description')}
          </p>
          <div class="config-code">
            <div class="code-header">
              <span class="code-label">{t('home.config.envVarsConfig')}</span>
              <Button variant="secondary" size="sm" onclick={() => copyToClipboard(configCommand)} title={copySuccess ? t('home.config.copied') : t('home.config.copy')} class="icon-button">
                {#if copySuccess}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                {/if}
              </Button>
            </div>
            <pre class="code-block"><code>export ANTHROPIC_BASE_URL={anthropicBaseUrl}
export ANTHROPIC_API_KEY="any-value"</code></pre>
          </div>
          <div class="config-note">
            <p><strong>{t('home.config.method1')}</strong></p>
            <p><strong>{t('home.config.method2')}</strong></p>
            <p class="note-text">{translateWithParams('home.config.tip', { url: anthropicBaseUrl })}</p>
            <div class="api-key-note">
              <p><strong>{t('home.config.aboutApiKey')}</strong></p>
              <ul>
                <li><strong>{t('home.config.devMode')}</strong>{t('home.config.devModeDesc')}</li>
                <li><strong>{t('home.config.prodMode')}</strong>{t('home.config.prodModeDesc')}</li>
                <li><strong>{t('home.config.checkMode')}</strong>{t('home.config.checkModeDesc')}</li>
              </ul>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <div class="providers-preview">
      <Card title={t('home.providersPreview.title')} subtitle={$providers.length > 0 ? translateWithParams('home.providersPreview.subtitle', { count: $providers.length }) : t('home.providersPreview.subtitleEmpty')}>
        {#snippet titleActionsSlot()}
          {#if $providers.length > 0}
            <a href="/providers" class="view-all">{t('home.providersPreview.viewAll')}</a>
          {/if}
        {/snippet}

        {#if $providers.length === 0}
          <div class="empty-state">
            <p>{t('home.providersPreview.noProviders')}</p>
            <a href="/providers" class="add-link">{t('home.providersPreview.addNow')}</a>
          </div>
        {:else}
          <!-- 搜索和筛选 -->
          <div class="filters">
            <div class="filter-row">
              <div class="filter-group search-group">
                <Input
                  type="text"
                  bind:value={providerSearchQuery}
                  placeholder={t('home.providersPreview.searchPlaceholder')}
                />
              </div>

              <div class="filter-group">
                <label for="provider-filter-status">{t('home.providersPreview.statusFilter')}</label>
                <select id="provider-filter-status" class="filter-select" bind:value={providerFilterEnabled}>
                  <option value="all">{t('home.providersPreview.all')}</option>
                  <option value="enabled">{t('home.providersPreview.enabled')}</option>
                  <option value="disabled">{t('home.providersPreview.disabled')}</option>
                </select>
              </div>
            </div>
          </div>
          
          {#if filteredProvidersForPreview.length > 0}
            <div class="table-container">
              <table class="providers-table">
                <thead>
                  <tr>
                    <th>{t('home.providersPreview.table.name')}</th>
                    <th>{t('home.providersPreview.table.apiFormat')}</th>
                    <th>{t('home.providersPreview.table.status')}</th>
                    <th>{t('home.providersPreview.table.baseUrl')}</th>
                    <th>{t('home.providersPreview.table.modelCount')}</th>
                  </tr>
                </thead>
                <tbody>
                  {#each filteredProvidersForPreview as provider}
                    <tr class={!provider.enabled ? 'disabled-row' : ''}>
                      <td class="name-cell">
                        <span class="provider-name">{provider.name}</span>
                      </td>
                      <td class="format-cell">
                        <Badge type={provider.api_format === 'anthropic' ? 'warning' : 'info'}>
                          {provider.api_format === 'anthropic' ? 'Anthropic' : 'OpenAI'}
                        </Badge>
                      </td>
                      <td>
                        <Badge type={provider.enabled ? 'success' : 'secondary'}>
                          {provider.enabled ? t('home.providerStats.enabled') : t('home.providerStats.disabled')}
                        </Badge>
                      </td>
                      <td class="url-cell">
                        <span class="url-text" title={provider.base_url}>{provider.base_url}</span>
                      </td>
                      <td class="models-cell">
                        <div class="models-badge">
                          <Badge type="info">{t('home.providersPreview.bigModels')} {provider.models.big?.length || 0}</Badge>
                          <Badge type="info">{t('home.providersPreview.middleModels')} {provider.models.middle?.length || 0}</Badge>
                          <Badge type="info">{t('home.providersPreview.smallModels')} {provider.models.small?.length || 0}</Badge>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>

            {#if hasMoreProviders}
              <div class="view-more">
                <a href="/providers" class="btn-link">{translateWithParams('home.providersPreview.viewMore', { count: $providers.length })}</a>
              </div>
            {/if}
          {:else}
            <div class="empty-state">
              <p>{t('home.providersPreview.noMatch')}</p>
            </div>
          {/if}
        {/if}
      </Card>
    </div>
  {/if}
</div>

<!-- 欢迎弹窗 -->
<WelcomeModal show={showWelcome} />

<style>
  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary, #666);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
  }

  .providers-preview {
    margin-top: 2rem;
  }

  .filters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }

  .filter-row {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
    width: 100%;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .filter-group.search-group {
    min-width: 250px;
    flex: 1;
  }
  
  .filter-group.search-group :global(input) {
    width: 100%;
    height: 2.5rem;
  }

  .filter-group label {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
    white-space: nowrap;
    font-weight: 500;
    margin: 0;
  }

  .filter-select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.375rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    cursor: pointer;
    min-width: 150px;
    height: 2.5rem;
  }

  .filter-select:focus {
    outline: 2px solid var(--primary-color, #007bff);
    outline-offset: 2px;
  }

  .view-all {
    color: var(--link-color, var(--primary-color, #007bff));
    text-decoration: none;
    font-weight: 500;
    font-size: 0.875rem;
    transition: color 0.2s;
  }

  .view-all:hover {
    color: var(--link-hover-color, var(--primary-color, #0056b3));
    text-decoration: underline;
  }

  :global([data-theme="dark"]) .view-all {
    color: #58a6ff;
  }

  :global([data-theme="dark"]) .view-all:hover {
    color: #79c0ff;
  }

  .empty-state {
    text-align: center;
    padding: 3rem;
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
  }

  .empty-state p {
    color: var(--text-secondary, #666);
    margin-bottom: 1rem;
  }

  .add-link {
    color: var(--link-color, var(--primary-color, #007bff));
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
  }

  .add-link:hover {
    color: var(--link-hover-color, var(--primary-color, #0056b3));
    text-decoration: underline;
  }

  :global([data-theme="dark"]) .add-link {
    color: #58a6ff;
  }

  :global([data-theme="dark"]) .add-link:hover {
    color: #79c0ff;
  }

  .table-container {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow-x: auto;
  }

  :global([data-theme="dark"]) .table-container {
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }

  .providers-table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .providers-table thead {
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 2px solid var(--border-color, #dee2e6);
  }

  .providers-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary, #495057);
    white-space: nowrap;
  }

  .providers-table th:first-child {
    width: 150px;
  }

  .providers-table th:nth-child(2) {
    width: 100px;
  }

  .providers-table th:nth-child(3) {
    width: 100px;
  }

  .providers-table th:nth-child(4) {
    width: 250px;
  }

  .providers-table th:last-child {
    width: 180px;
  }

  .providers-table tbody tr {
    border-bottom: 1px solid var(--border-color, #dee2e6);
    transition: background-color 0.2s;
  }

  .providers-table tbody tr:hover {
    background: var(--bg-tertiary, #f8f9fa);
  }

  .providers-table tbody tr.disabled-row {
    opacity: 0.6;
  }

  .providers-table td {
    padding: 1rem;
    vertical-align: middle;
    white-space: nowrap;
  }

  .name-cell {
    padding: 1rem 0.75rem;
  }

  .provider-name {
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .url-cell {
    max-width: 250px;
  }

  .url-text {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-secondary, #6c757d);
    font-size: 0.8125rem;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  }

  .models-cell {
    padding: 0.75rem 1rem;
  }

  .models-badge {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }

  .models-badge :global(.badge) {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }

  .btn-link {
    color: #007bff;
    text-decoration: none;
    font-weight: 500;
  }

  .btn-link:hover {
    text-decoration: underline;
  }

  .config-section {
    margin-bottom: 3rem;
  }

  .config-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .config-description {
    margin: 0;
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
    line-height: 1.6;
  }

  .config-code {
    background: var(--bg-tertiary, #f8f9fa);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--bg-tertiary, #e9ecef);
    border-bottom: 1px solid var(--border-color, #e0e0e0);
  }

  .code-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary, #495057);
  }

  .code-block {
    margin: 0;
    padding: 1rem;
    background: var(--code-bg, var(--bg-primary, #fff));
    overflow-x: auto;
  }

  .code-block code {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    font-size: 0.875rem;
    color: var(--text-primary, #1a1a1a);
    white-space: pre;
  }

  .config-note {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1rem;
    background: #e7f3ff;
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
  }

  :global([data-theme="dark"]) .config-note {
    background: rgba(88, 166, 255, 0.1);
    border-left-color: #58a6ff;
  }

  .config-note p {
    margin: 0;
    font-size: 0.875rem;
    color: #004085;
    line-height: 1.6;
  }

  :global([data-theme="dark"]) .config-note p {
    color: var(--text-primary);
  }

  .note-text {
    margin-top: 0.5rem;
    font-weight: 500;
  }

  .api-key-note {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #b3d9ff;
  }

  :global([data-theme="dark"]) .api-key-note {
    border-top-color: rgba(88, 166, 255, 0.3);
  }

  .api-key-note p {
    margin-bottom: 0.5rem;
    font-weight: 600;
  }

  .api-key-note ul {
    margin: 0.5rem 0 0 0;
    padding-left: 1.5rem;
    list-style-type: disc;
  }

  .api-key-note li {
    margin: 0.5rem 0;
    font-size: 0.875rem;
    color: #004085;
    line-height: 1.6;
  }

  :global([data-theme="dark"]) .api-key-note li {
    color: var(--text-primary);
  }

  .api-key-note li strong {
    color: #002752;
  }

  :global([data-theme="dark"]) .api-key-note li strong {
    color: var(--text-primary);
  }
</style>
