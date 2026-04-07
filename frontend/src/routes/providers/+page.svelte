<script lang="ts">
  import { onMount } from "svelte";
  import { onDestroy } from "svelte";
  import { goto } from "$app/navigation";
  import Button from "$components/ui/Button.svelte";
  import Card from "$components/ui/Card.svelte";
  import Badge from "$components/ui/Badge.svelte";
  import StatCard from "$lib/components/ui/StatCard.svelte";
  import ProviderForm from "$components/ProviderForm.svelte";
  import ErrorMessageModal from "$components/ErrorMessageModal.svelte";
  import { providers } from "$stores/providers";
  import { providerService } from "$services/providers";
  import { toast } from "$stores/toast";
  import type { Provider } from "$types/provider";
  import Input from "$components/ui/Input.svelte";
  import { tStore } from "$stores/language";
  import { authService } from "$services/auth";

  let showForm = $state(false);
  let hasPermission = $state(true);
  let editingProvider: Provider | null = $state(null);
  let loading = $state(true);
  let saving = $state(false);
  let providersForEdit: Provider[] = $state([]); // 包含真实API key的完整数据
  let showTestResult = $state(false);
  let testResult: any = $state(null);
  let testingProvider: string | null = $state(null);

  // 获取翻译函数
  const t = $derived($tStore);

  // 模型类别翻译
  function getCategoryLabel(category: string): string {
    const labels: Record<string, string> = {
      big: t("providers.bigModels"),
      middle: t("providers.middleModels"),
      small: t("providers.smallModels"),
    };
    return labels[category] || category;
  }

  // 获取带参数的翻译
  function tWithParams(key: string, params: Record<string, string>): string {
    let result = t(key);
    for (const [k, v] of Object.entries(params)) {
      result = result.replace(`{${k}}`, v);
    }
    return result;
  }

  // 优先级编辑相关
  let editingPriorityKey: string | null = $state(null); // 格式: "name||api_format"
  let editingPriorityValue: number = $state(0);

  // 搜索和筛选相关
  let searchQuery = $state("");
  let filterEnabled: "all" | "enabled" | "disabled" = $state("all");

  // 视图模式切换
  let viewMode: "card" | "table" = $state("card");

  // 分页相关 - 卡片视图
  let currentPage = $state(1);
  const pageSize = 10;

  // 分页相关 - 表格视图（仅用于状态跟踪）
  let tableCurrentPage = $state(1);

  // 请求取消控制器（用于组件卸载时取消请求）
  let abortController: AbortController | null = null;

  // 在组件顶层订阅providers store
  let currentProviders = $state<Provider[]>([]);

  // 客户端过滤和排序
  let allFilteredProviders = $derived(() => {
    // 使用currentProviders进行过滤
    const providers = Array.isArray(currentProviders) ? currentProviders : [];

    return providers
      .filter((p) => {
        // 搜索过滤
        if (searchQuery.trim()) {
          const query = searchQuery.toLowerCase();
          if (
            !p.name.toLowerCase().includes(query) &&
            !p.base_url.toLowerCase().includes(query)
          ) {
            return false;
          }
        }

        // 状态过滤
        if (filterEnabled === "enabled" && !p.enabled) return false;
        if (filterEnabled === "disabled" && p.enabled) return false;

        return true;
      })
      .sort((a, b) => {
        // 按名称排序（不区分大小写）
        const nameCompare = a.name
          .toLowerCase()
          .localeCompare(b.name.toLowerCase());
        if (nameCompare !== 0) return nameCompare;

        // 如果名称相同，按 API 格式排序
        return (a.api_format || '').localeCompare(b.api_format || '');
      });
  });

  // 表格视图专用：重置到第1页（当视图切换时）
  $effect(() => {
    if (viewMode === "table") {
      tableCurrentPage = 1;
    }
  });

  // 表格视图排序和分页
  let tableSortColumn = $state<string>('');
  let tableSortDirection = $state<'asc' | 'desc'>('asc');

  // 表格排序后的数据
  let tableSortedProviders = $derived(() => {
    const data = Array.isArray(allFilteredProviders()) ? allFilteredProviders() : [];
    if (!tableSortColumn) return data;

    return [...data].sort((a, b) => {
      let aVal: any = a[tableSortColumn as keyof Provider];
      let bVal: any = b[tableSortColumn as keyof Provider];

      // 特殊处理布尔值
      if (typeof aVal === 'boolean' && typeof bVal === 'boolean') {
        return tableSortDirection === 'asc'
          ? (aVal === bVal ? 0 : aVal ? 1 : -1)
          : (aVal === bVal ? 0 : aVal ? -1 : 1);
      }

      // 字符串排序
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        const comparison = aVal.localeCompare(bVal);
        return tableSortDirection === 'asc' ? comparison : -comparison;
      }

      // 数字排序
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        const comparison = aVal - bVal;
        return tableSortDirection === 'asc' ? comparison : -comparison;
      }

      return 0;
    });
  });

  // 表格分页计算
  let tableTotalCount = $derived(() => {
    const data = tableSortedProviders();
    return Array.isArray(data) ? data.length : 0;
  });
  let tableTotalPages = $derived(() => Math.ceil(tableTotalCount() / pageSize));

  // 确保表格当前页在有效范围内
  $effect(() => {
    const pages = tableTotalPages();
    if (pages === 0) {
      tableCurrentPage = 1;
    } else if (pages > 0 && tableCurrentPage > pages) {
      tableCurrentPage = pages;
    } else if (tableCurrentPage < 1) {
      tableCurrentPage = 1;
    }
  });

  // 表格当前页显示的数据
  let tableFilteredProviders = $derived(() => {
    const data = tableSortedProviders();
    const arrayData = Array.isArray(data) ? data : [];
    return arrayData.slice(
      (tableCurrentPage - 1) * pageSize,
      tableCurrentPage * pageSize
    );
  });

  // 表格排序处理
  function handleTableSort(column: string) {
    if (tableSortColumn === column) {
      tableSortDirection = tableSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      tableSortColumn = column;
      tableSortDirection = 'asc';
    }
  }

  // 表格分页处理
  function handleTablePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= tableTotalPages() && newPage !== tableCurrentPage) {
      tableCurrentPage = newPage;
    }
  }

  // 分页计算（卡片视图）
  let totalCount = $derived(() => {
    const data = allFilteredProviders();
    return data.length;
  });
  let enabledCount = $derived(() => {
    const data = allFilteredProviders();
    return data.filter(p => p.enabled).length;
  });
  let disabledCount = $derived(() => {
    const data = allFilteredProviders();
    return data.filter(p => !p.enabled).length;
  });
  let openaiCount = $derived(() => {
    const data = allFilteredProviders();
    return data.filter(p => p.api_format === 'openai').length;
  });
  let totalPages = $derived(() => Math.ceil(totalCount() / pageSize));

  // 确保当前页在有效范围内
  $effect(() => {
    const pages = totalPages();
    if (pages === 0) {
      currentPage = 1;
    } else if (pages > 0 && currentPage > pages) {
      currentPage = pages;
    } else if (currentPage < 1) {
      currentPage = 1;
    }
  });

  // 当前页显示的数据
  let filteredProviders = $derived(() => {
    const data = allFilteredProviders();
    return data.slice(
      (currentPage - 1) * pageSize,
      currentPage * pageSize
    );
  });

  onMount(async () => {
    // 检查权限
    if (!authService.hasPermission('providers')) {
      hasPermission = false;
      loading = false;
      toast.error(t('common.accessDenied'));
      setTimeout(() => goto('/chat'), 1000);
      return;
    }

    abortController = new AbortController();
    try {
      await loadProviders();
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      throw error;
    }
  });

  onDestroy(() => {
    // 取消所有进行中的请求
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  });

  async function loadProviders() {
    if (!abortController) return;
    loading = true;
    try {
      const data = await providerService.getAll({
        signal: abortController.signal,
      });

      // 检查是否已被取消
      if (abortController.signal.aborted) {
        return;
      }

      // 更新store和本地状态
      providers.set(data);
      currentProviders = data;
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      console.error("Failed to load providers:", error);
      const errorMessage = (error as Error).message;

      // 检查是否是未认证错误
      if (errorMessage.includes("Unauthorized") || errorMessage.includes("401")) {
        toast.error("未登录或权限不足。请使用管理员账户登录后再试。");
      } else {
        toast.error(t("providers.loadFailed") + ": " + errorMessage);
      }
    } finally {
      if (!abortController?.signal.aborted) {
        loading = false;
      }
    }
  }

  function handleAdd() {
    editingProvider = null;
    showForm = true;
  }

  async function handleEdit(provider: Provider) {
    if (!abortController) return;
    try {
      // 每次编辑都重新获取最新的完整数据，确保显示最新的配置
      const editData = await providerService.getAllForEdit({
        signal: abortController.signal,
      });

      // 检查是否已被取消
      if (abortController.signal.aborted) return;

      // 更新缓存
      providersForEdit = editData;

      // 从最新数据中找到对应的供应商 (包含格式匹配)
      const fullProvider = providersForEdit.find(
        (p) => p.name === provider.name && p.api_format === provider.api_format,
      );
      if (!fullProvider) {
        toast.error(t("providers.providerNotFound"));
        return;
      }

      editingProvider = fullProvider;
      showForm = true;
    } catch (error) {
      // 忽略取消错误
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      console.error("Failed to load provider data for editing:", error);
      toast.error(t("providers.loadEditDataFailed") + ": " + (error as Error).message);
    }
  }

  async function handleToggleEnabled(provider: Provider) {
    const newEnabled = !provider.enabled;
    try {
      await providerService.toggleEnabled(
        provider.name,
        newEnabled,
        provider.api_format,
      );
      await loadProviders();
      toast.success(newEnabled ? t("providers.providerEnabled") : t("providers.providerDisabled"));
    } catch (error) {
      console.error("Failed to toggle provider status:", error);
      toast.error(t("providers.operationFailed") + ": " + (error as Error).message);
    }
  }

  async function handleDelete(provider: Provider) {
    if (!confirm(t("providers.confirmDeleteProvider").replace("{name}", provider.name))) {
      return;
    }

    try {
      await providerService.delete(provider.name, provider.api_format);
      // 清空编辑数据缓存
      providersForEdit = [];
      await loadProviders();
      toast.success(t("providers.deleteSuccess"));
    } catch (error) {
      console.error("Failed to delete provider:", error);
      toast.error(t("providers.deleteFailed") + ": " + (error as Error).message);
    }
  }

  async function handleTest(provider: Provider) {
    testingProvider = provider.name;
    try {
      const result = await providerService.test(provider.name);
      testResult = result;
      showTestResult = true;

      // Also show a summary toast
      if (result.healthy) {
        toast.success(t("providers.testCompleted") + "\n" + t("providers.healthyStatus"));
      } else {
        toast.error(t("providers.testCompleted") + "\n" + t("providers.unhealthyStatus"));
      }
    } catch (error) {
      console.error("Failed to test provider:", error);
      toast.error(t("providers.testFailed") + ": " + (error as Error).message);
      testingProvider = null;
    }
  }

  function closeTestResult() {
    showTestResult = false;
    testResult = null;
    testingProvider = null;
  }

  function handleOverlayClick(event: Event) {
    // Only close if clicking directly on the overlay (not on modal content)
    if (event.target === event.currentTarget) {
      closeTestResult();
    }
  }

  function handleFormOverlayClick(_event: MouseEvent) {
    // 禁用点击遮罩层关闭弹窗，只能通过关闭按钮关闭
    // Do nothing - modal can only be closed via close/cancel buttons
  }

  async function copyToClipboard(text: string) {
    if (typeof window === "undefined") return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        toast.success(t("providers.copiedToClipboard"));
      } else {
        // Fallback for older browsers
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
        toast.success(t("providers.copiedToClipboard"));
      }
    } catch (error) {
      console.error("Failed to copy:", error);
      toast.error(t("providers.copyFailed"));
    }
  }

  function copyTestResult() {
    if (!testResult) return;

    const lines: string[] = [];
    lines.push(`${t("providers.testResult")} ${testingProvider}`);
    lines.push(`${t("providers.overallStatus")} ${testResult.healthy ? t("providers.healthyStatus") : t("providers.unhealthyStatus")}`);
    if (testResult.responseTime !== null) {
      lines.push(tWithParams("providers.responseTimeMs", { time: String(testResult.responseTime) }));
    }
    lines.push("");
    lines.push(t("providers.categoryHealthStatus").replace(":", ""));

    if (testResult.categories) {
      for (const [category, status] of Object.entries(testResult.categories)) {
        const catStatus = status as any;
        lines.push(
          `  ${getCategoryLabel(category)}: ${catStatus.healthy ? t("providers.healthyStatus") : t("providers.unhealthyStatus")}`,
        );
        if (catStatus.responseTime !== null) {
          lines.push(`    ${t("providers.responseTime")} ${catStatus.responseTime}ms`);
        }
        if (catStatus.workingModel) {
          lines.push(`    ${t("providers.availableModels")} ${catStatus.workingModel}`);
        }
        if (catStatus.error) {
          lines.push(`    ${t("providers.categoryError")} ${catStatus.error}`);
        }
      }
    }

    copyToClipboard(lines.join("\n"));
  }

  function truncateError(errorMessage: string, maxLength: number = 50): string {
    if (!errorMessage) return "";
    if (errorMessage.length <= maxLength) return errorMessage;
    return errorMessage.substring(0, maxLength) + "...";
  }

  // 错误信息模态框相关
  let showErrorModal = $state(false);
  let selectedError: string = $state("");
  let selectedErrorTitle: string = $state("");

  function showErrorMessage(category: string, error: string) {
    selectedErrorTitle = `${t("health.errorMessage")} - ${testingProvider} - ${getCategoryLabel(category)}`;
    selectedError = error;
    showErrorModal = true;
  }

  function closeErrorModal() {
    showErrorModal = false;
    selectedError = "";
    selectedErrorTitle = "";
  }

  async function handleSave(saveData: {
    provider: Provider;
    api_format?: string;
  }) {
    try {
      saving = true;

      // Extract provider data and api_format
      const { provider: providerData, api_format } = saveData;

      if (editingProvider) {
        // Pass original api_format for precise provider identification
        // Pass new api_format in providerData for update
        await providerService.update(
          editingProvider.name,
          providerData,
          editingProvider.api_format,
        );
      } else {
        await providerService.create(providerData);
      }
      showForm = false;
      editingProvider = null;
      // 清空编辑数据缓存，强制下次编辑时重新加载最新数据
      providersForEdit = [];
      // 刷新供应商列表
      await loadProviders();
      toast.success(t("providers.saveSuccess"));
    } catch (error) {
      console.error("Failed to save provider:", error);
      toast.error(tWithParams("providers.saveFailed", { error: (error as Error).message }));
    } finally {
      saving = false;
    }
  }

  function handleCancel() {
    showForm = false;
    editingProvider = null;
  }

  function clearFilters() {
    searchQuery = "";
    filterEnabled = "all";
    currentPage = 1;
  }

  function handlePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= totalPages() && newPage !== currentPage) {
      currentPage = newPage;
    }
  }

  function handleEditPriority(provider: Provider) {
    const key = `${provider.name}||${provider.api_format}`;
    editingPriorityKey = key;
    editingPriorityValue = provider.priority;
  }

  function handleCancelEditPriority() {
    editingPriorityKey = null;
    editingPriorityValue = 0;
  }

  async function handleSavePriority(provider: Provider) {
    const key = `${provider.name}||${provider.api_format}`;
    if (editingPriorityKey !== key) return;

    // 验证优先级值
    if (editingPriorityValue < 0) {
      toast.error(t("providers.priorityValidation"));
      return;
    }

    try {
      saving = true;

      // 获取包含完整 API Key 的供应商数据
      const editData = await providerService.getAllForEdit({
        signal: abortController?.signal,
      });

      // 找到对应的供应商
      const fullProvider = editData.find(
        (p) => p.name === provider.name && p.api_format === provider.api_format,
      );

      if (!fullProvider) {
        toast.error(t("providers.providerNotFound"));
        return;
      }

      // 更新优先级，使用完整的供应商数据
      const updatedData = {
        ...fullProvider,
        priority: editingPriorityValue,
      };

      await providerService.update(
        provider.name,
        updatedData,
        provider.api_format,
      );
      toast.success(t("providers.priorityUpdateSuccess"));
      await loadProviders();
      handleCancelEditPriority();
    } catch (error) {
      console.error("Failed to update priority:", error);
      toast.error(tWithParams("providers.priorityUpdateFailed", { error: (error as Error).message }));
    } finally {
      saving = false;
    }
  }
</script>

<div class="container">
  <div class="page-header">
    <div class="header-right">
      <!-- 视图切换按钮 -->
      <div class="view-toggle">
        <Button
          variant={viewMode === "card" ? "primary" : "secondary"}
          size="sm"
          onclick={() => viewMode = "card"}
          title={t("providers.cardView")}
          class="toggle-btn"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
        </Button>
        <Button
          variant={viewMode === "table" ? "primary" : "secondary"}
          size="sm"
          onclick={() => viewMode = "table"}
          title={t("providers.tableView")}
          class="toggle-btn"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
          </svg>
        </Button>
      </div>
      <Button onclick={handleAdd} title={t("providers.addProvider")} class="icon-button">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </Button>
    </div>
  </div>

  {#if !hasPermission}
    <div class="access-denied">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
      </svg>
      <p>{t('common.accessDenied')}</p>
      <p class="redirect-hint">{t('common.redirecting')}</p>
    </div>
  {:else if loading}
    <div class="loading">
      <p>{t("providers.loading")}</p>
    </div>
  {:else if $providers.length === 0}
    <div class="empty">
      <p>{t("providers.noProviders")}</p>
      <Button onclick={handleAdd} title={t("providers.addFirstProvider")} class="icon-button">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </Button>
    </div>
  {:else}
    <!-- 搜索和筛选 -->
    <Card>
      <div class="filters">
        <div class="filter-row">
          <div class="filter-group search-group">
            <Input
              type="text"
              bind:value={searchQuery}
              placeholder={t("providers.searchPlaceholder")}
            />
          </div>

          <div class="filter-group">
            <label for="provider-filter-status">{t("providers.status")}:</label>
            <select
              id="provider-filter-status"
              class="filter-select"
              bind:value={filterEnabled}
            >
              <option value="all">{t("providers.all")}</option>
              <option value="enabled">{t("providers.enabled")}</option>
              <option value="disabled">{t("providers.disabled")}</option>
            </select>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onclick={clearFilters}
            title={t("providers.clearFilters")}
            class="clear-button"
          >
            {t("providers.clearFilter")}
          </Button>
        </div>
      </div>
    </Card>

    <!-- 统计卡片行 -->
    <div class="stats-row">
      <StatCard
        title={t("providers.totalProviders")}
        value={totalCount()}
        type="info"
        icon="server"
      />
      <StatCard
        title={t("providers.enabled")}
        value={enabledCount()}
        type="success"
        icon="check-circle"
      />
      <StatCard
        title={t("providers.disabled")}
        value={disabledCount()}
        type="danger"
        icon="x-circle"
      />
      <StatCard
        title={t("providers.openaiApi")}
        value={openaiCount()}
        type="default"
        icon="cpu"
      />
    </div>

    {#if filteredProviders().length === 0}
      <div class="empty">
        <p>{t("providers.noMatch")}</p>
      </div>
    {:else}
      {#if viewMode === "card"}
        <!-- 卡片视图 -->
        <div class="providers-grid">
          {#each filteredProviders() as provider}
            <Card variant="elevated" class="provider-card">
              <!-- Card Header -->
              <div class="card-header">
                <div class="provider-info">
                  <h3 class="provider-name" title={provider.name}>
                    {provider.name}
                  </h3>
                  <Badge
                    type={provider.api_format === "anthropic"
                      ? "warning"
                      : "info"}
                  >
                    {provider.api_format === "anthropic"
                      ? t("providers.anthropicApi")
                      : t("providers.openaiApi")}
                  </Badge>
                </div>
                <label class="toggle-switch">
                  <input
                    type="checkbox"
                    checked={provider.enabled}
                    onchange={() => handleToggleEnabled(provider)}
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>

              <!-- Card Body -->
              <div class="card-body">
                <div class="info-row">
                  <div class="info-item">
                    <span class="info-label">{t("providers.baseUrl")}:</span>
                    <span class="info-value url" title={provider.base_url}>
                      {provider.base_url}
                    </span>
                  </div>
                </div>

                <div class="info-row">
                  <div class="info-item">
                    <span class="info-label">{t("health.priority")}:</span>
                    {#if editingPriorityKey === `${provider.name}||${provider.api_format}`}
                      <div class="priority-edit-wrapper">
                        <input
                          type="number"
                          class="priority-input"
                          bind:value={editingPriorityValue}
                          min="0"
                          step="1"
                        />
                        <div class="priority-actions">
                          <button
                            class="priority-btn save-btn"
                            onclick={() => handleSavePriority(provider)}
                            disabled={saving}
                            title={t("providers.save")}
                          >
                            ✓
                          </button>
                          <button
                            class="priority-btn cancel-btn"
                            onclick={handleCancelEditPriority}
                            disabled={saving}
                            title={t("providers.cancel")}
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    {:else}
                      <div class="priority-display">
                        <span class="priority-value">{provider.priority}</span>
                        <button
                          class="priority-edit-icon"
                          onclick={() => handleEditPriority(provider)}
                          title={t("providers.editPriority")}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <path
                              d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                            ></path>
                            <path
                              d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                            ></path>
                          </svg>
                        </button>
                      </div>
                    {/if}
                  </div>
                </div>

                <div class="info-row">
                  <div class="info-item">
                    <span class="info-label">{t("health.models")}:</span>
                    <div class="models-grid">
                      <Badge type="info" class="model-badge">
                        {t("providers.bigModels")} {provider.models.big?.length || 0}
                      </Badge>
                      <Badge type="info" class="model-badge">
                        {t("providers.middleModels")} {provider.models.middle?.length || 0}
                      </Badge>
                      <Badge type="info" class="model-badge">
                        {t("providers.smallModels")} {provider.models.small?.length || 0}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Card Actions -->
              <div class="card-actions">
                <Button
                  variant="secondary"
                  size="sm"
                  onclick={() => handleTest(provider)}
                  title={t("providers.testConnection")}
                  class="action-button"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                  </svg>
                  {t("providers.test")}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onclick={() => handleEdit(provider)}
                  title={t("providers.editProvider")}
                  class="action-button"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path
                      d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                    ></path>
                    <path
                      d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                    ></path>
                  </svg>
                  {t("providers.edit")}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onclick={() => handleDelete(provider)}
                  title={t("providers.deleteProvider")}
                  class="action-button"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path
                      d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                    ></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                  {t("providers.delete")}
                </Button>
              </div>
            </Card>
          {/each}
        </div>
      {:else}
        <!-- 表格视图 -->
        <div class="table-view">
          <Card variant="elevated" class="table-card">
            <div class="table-wrapper">
              <table class="providers-table">
                <thead>
                  <tr>
                    <th class="name-column" onclick={() => handleTableSort('name')}>
                      <div class="th-content">
                        <span>{t("providers.name")}</span>
                        {#if tableSortColumn === 'name'}
                          <span class="sort-indicator">{tableSortDirection === 'asc' ? '↑' : '↓'}</span>
                        {/if}
                      </div>
                    </th>
                    <th class="status-column" onclick={() => handleTableSort('enabled')}>
                      <div class="th-content">
                        <span>{t("providers.status")}</span>
                        {#if tableSortColumn === 'enabled'}
                          <span class="sort-indicator">{tableSortDirection === 'asc' ? '↑' : '↓'}</span>
                        {/if}
                      </div>
                    </th>
                    <th class="url-column" onclick={() => handleTableSort('base_url')}>
                      <div class="th-content">
                        <span>{t("providers.baseUrl")}</span>
                        {#if tableSortColumn === 'base_url'}
                          <span class="sort-indicator">{tableSortDirection === 'asc' ? '↑' : '↓'}</span>
                        {/if}
                      </div>
                    </th>
                    <th class="api-format-column" onclick={() => handleTableSort('api_format')}>
                      <div class="th-content">
                        <span>{t("providers.apiFormat")}</span>
                        {#if tableSortColumn === 'api_format'}
                          <span class="sort-indicator">{tableSortDirection === 'asc' ? '↑' : '↓'}</span>
                        {/if}
                      </div>
                    </th>
                    <th class="priority-column" onclick={() => handleTableSort('priority')}>
                      <div class="th-content">
                        <span>{t("health.priority")}</span>
                        {#if tableSortColumn === 'priority'}
                          <span class="sort-indicator">{tableSortDirection === 'asc' ? '↑' : '↓'}</span>
                        {/if}
                      </div>
                    </th>
                    <th class="models-column">
                      <div class="th-content">
                        <span>{t("health.models")}</span>
                      </div>
                    </th>
                    <th class="actions-column">{t("providers.actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {#each tableFilteredProviders() as provider, index}
                    {@const _rowNumber = (tableCurrentPage - 1) * pageSize + index + 1}
                    {@const isEditingPriority = editingPriorityKey === `${provider.name}||${provider.api_format}`}
                    <tr class="table-row">
                      <td class="name-cell">
                        <div class="provider-name-cell">
                          <span class="provider-title" title={provider.name}>{provider.name}</span>
                        </div>
                      </td>
                      <td class="status-cell">
                        <div class="toggle-wrapper" role="switch" aria-label={t("providers.toggleEnabled")} aria-checked={provider.enabled} tabindex="0" onkeydown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleToggleEnabled(provider);
                          }
                        }}>
                          <label class="toggle-switch small">
                            <input
                              type="checkbox"
                              checked={provider.enabled}
                              onchange={() => handleToggleEnabled(provider)}
                            />
                            <span class="toggle-slider"></span>
                          </label>
                        </div>
                      </td>
                      <td class="url-cell">
                        <span class="url-text" title={provider.base_url}>{provider.base_url}</span>
                      </td>
                      <td class="api-format-cell">
                        <Badge
                          type={provider.api_format === "anthropic"
                            ? "warning"
                            : "info"}
                          class="api-badge"
                        >
                          {provider.api_format === "anthropic"
                            ? t("providers.anthropicApi")
                            : t("providers.openaiApi")}
                        </Badge>
                      </td>
                      <td class="priority-cell">
                        {#if isEditingPriority}
                          <div class="priority-edit-wrapper" role="group" aria-label={t("providers.editPriority")}>
                            <input
                              type="number"
                              class="priority-input"
                              bind:value={editingPriorityValue}
                              min="0"
                              step="1"
                              onclick={(e) => e.stopPropagation()}
                            />
                            <div class="priority-actions">
                              <button
                                class="priority-btn save-btn"
                                onclick={(e) => {
                                  e.stopPropagation();
                                  handleSavePriority(provider);
                                }}
                                disabled={saving}
                                title={t("providers.save")}
                              >
                                ✓
                              </button>
                              <button
                                class="priority-btn cancel-btn"
                                onclick={(e) => {
                                  e.stopPropagation();
                                  handleCancelEditPriority();
                                }}
                                disabled={saving}
                                title={t("providers.cancel")}
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        {:else}
                          <div class="priority-display">
                            <span class="priority-value">{provider.priority}</span>
                            <button
                              class="priority-edit-icon"
                              onclick={(e) => {
                                e.stopPropagation();
                                handleEditPriority(provider);
                              }}
                              title={t("providers.editPriority")}
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                              >
                                <path
                                  d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                                ></path>
                                <path
                                  d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                                ></path>
                              </svg>
                            </button>
                          </div>
                        {/if}
                      </td>
                      <td class="models-cell">
                        <div class="models-list">
                          <Badge type="info" class="model-badge">
                            {t("providers.bigModels")} {provider.models.big?.length || 0}
                          </Badge>
                          <Badge type="info" class="model-badge">
                            {t("providers.middleModels")} {provider.models.middle?.length || 0}
                          </Badge>
                          <Badge type="info" class="model-badge">
                            {t("providers.smallModels")} {provider.models.small?.length || 0}
                          </Badge>
                        </div>
                      </td>
                      <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
                        <div class="action-buttons">
                          <button
                            class="action-icon-btn test-btn"
                            onclick={() => handleTest(provider)}
                            title={t("providers.testConnection")}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="16"
                              height="16"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                            >
                              <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                            </svg>
                          </button>
                          <button
                            class="action-icon-btn edit-btn"
                            onclick={() => handleEdit(provider)}
                            title={t("providers.editProvider")}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="16"
                              height="16"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                            >
                              <path
                                d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                              ></path>
                              <path
                                d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                              ></path>
                            </svg>
                          </button>
                          <button
                            class="action-icon-btn delete-btn"
                            onclick={() => handleDelete(provider)}
                            title={t("providers.deleteProvider")}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="16"
                              height="16"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                            >
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path
                                d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                              ></path>
                              <line x1="10" y1="11" x2="10" y2="17"></line>
                              <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>

              {#if tableFilteredProviders().length === 0}
                <div class="empty-table">
                  <p>{t("providers.noMatch")}</p>
                </div>
              {/if}
            </div>

            <!-- 表格分页控件 -->
            {#if tableTotalPages() > 1}
              <div class="table-pagination">
                <div class="pagination-info">
                  {tWithParams("health.paginationInfo", {
                    totalCount: String(tableTotalCount()),
                    currentPage: String(tableCurrentPage),
                    totalPages: String(tableTotalPages())
                  })}
                </div>
                <div class="pagination-controls">
                  <button
                    class="page-btn"
                    disabled={tableCurrentPage === 1}
                    onclick={() => handleTablePageChange(tableCurrentPage - 1)}
                    title={t("common.previousPage")}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                  </button>
                  <span class="page-info">{tableCurrentPage} / {tableTotalPages()}</span>
                  <button
                    class="page-btn"
                    disabled={tableCurrentPage === tableTotalPages()}
                    onclick={() => handleTablePageChange(tableCurrentPage + 1)}
                    title={t("common.nextPage")}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                </div>
              </div>
            {/if}
          </Card>
        </div>
      {/if}

      <!-- 分页控件 - 仅卡片视图显示 -->
      {#if viewMode === "card" && totalPages() > 1}
        <div class="pagination">
          <div class="pagination-info">
            {tWithParams("health.paginationInfo", {
              totalCount: String(totalCount()),
              currentPage: String(currentPage),
              totalPages: String(totalPages())
            })}
          </div>
          <div class="pagination-controls">
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === 1}
              onclick={() => handlePageChange(currentPage - 1)}
              title={t("common.previousPage")}
              class="icon-button"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </Button>
            <span class="page-info">{currentPage} / {totalPages()}</span>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === totalPages()}
              onclick={() => handlePageChange(currentPage + 1)}
              title={t("common.nextPage")}
              class="icon-button"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Button>
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>

<!-- Provider Form Modal -->
{#if showForm}
  <div
    class="modal-overlay"
    role="button"
    tabindex="0"
    onclick={handleFormOverlayClick}
    onkeydown={() => {}}
  >
    <div
      class="modal-content"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <h2>{editingProvider ? t("providers.editProvider") : t("providers.addProvider")}</h2>
      <ProviderForm
        provider={editingProvider}
        apiFormat={editingProvider?.api_format}
        loading={saving}
        on:save={(e) => handleSave(e.detail)}
        on:cancel={handleCancel}
      />
    </div>
  </div>
{/if}

<!-- Test Result Modal -->
{#if showTestResult && testResult}
  <div
    class="modal-overlay"
    role="button"
    tabindex="0"
    onclick={handleOverlayClick}
    onkeydown={(e) => e.key === "Escape" && handleOverlayClick(e)}
  >
    <div
      class="modal-content test-result-modal"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="test-result-header">
        <h2>{tWithParams("providers.testResultTitle", { name: testingProvider || "" })}</h2>
        <div class="header-actions">
          <Button
            variant="secondary"
            size="sm"
            onclick={copyTestResult}
            title={t("providers.copyResult")}
            class="icon-button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
              ></path>
            </svg>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onclick={closeTestResult}
            title={t("providers.close")}
            class="icon-button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </Button>
        </div>
      </div>

      <div class="test-summary">
        <div class="summary-item">
          <span class="summary-label">{t("providers.overallStatus")}</span>
          <Badge type={testResult.healthy ? "success" : "danger"}>
            {testResult.healthy ? t("providers.healthyStatus") : t("providers.unhealthyStatus")}
          </Badge>
        </div>
        {#if testResult.responseTime !== null}
          <div class="summary-item">
            <span class="summary-label">{t("providers.responseTime")}</span>
            <span class="summary-value">{testResult.responseTime}ms</span>
          </div>
        {/if}
      </div>

      <div class="categories-section">
        <h3>{t("providers.categoryHealthStatus").replace(":", "")}</h3>
        <div class="categories-list">
          {#each Object.entries(testResult.categories || {}) as [category, status]}
            {@const catStatus = status as any}
            <div class="category-item">
              <div class="category-header">
                <span class="category-name">{getCategoryLabel(category)}</span>
                <Badge type={catStatus.healthy ? "success" : "danger"}>
                  {catStatus.healthy ? t("providers.healthyStatus") : t("providers.unhealthyStatus")}
                </Badge>
              </div>

              {#if catStatus.healthy}
                <div class="category-details">
                  {#if catStatus.responseTime !== null}
                    <div class="detail-item">
                      <span class="detail-label">{t("providers.responseTime")}</span>
                      <span class="detail-value"
                        >{catStatus.responseTime}ms</span
                      >
                    </div>
                  {/if}
                  {#if catStatus.workingModel}
                    <div class="detail-item">
                      <span class="detail-label">{t("providers.availableModels")}</span>
                      <span class="detail-value code"
                        >{catStatus.workingModel}</span
                      >
                    </div>
                  {/if}
                  {#if catStatus.testedModels && catStatus.testedModels.length > 0}
                    <div class="detail-item">
                      <span class="detail-label">{t("providers.testedModels")}</span>
                      <span class="detail-value"
                        >{tWithParams("providers.testedModelsCount", { count: String(catStatus.testedModels.length) })}</span
                      >
                    </div>
                  {/if}
                </div>
              {:else}
                <div class="category-details">
                  {#if catStatus.error}
                    {@const truncated = truncateError(catStatus.error)}
                    {@const isTruncated = catStatus.error.length > 50}
                    <div class="detail-item error">
                      <span class="detail-label">{t("providers.categoryError")}</span>
                      <span
                        class="detail-value error-value clickable"
                        role="button"
                        tabindex="0"
                        onclick={() =>
                          showErrorMessage(category, catStatus.error)}
                        onkeydown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            showErrorMessage(category, catStatus.error);
                          }
                        }}
                        title={isTruncated ? t("providers.viewFullError") : ""}
                      >
                        {truncated}
                      </span>
                    </div>
                  {/if}
                  {#if catStatus.testedModels && catStatus.testedModels.length > 0}
                    <div class="detail-item">
                      <span class="detail-label">{t("providers.testedModels")}</span>
                      <span class="detail-value"
                        >{tWithParams("providers.testedModelsCount", { count: String(catStatus.testedModels.length) })}</span
                      >
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      </div>

      <div class="test-result-actions">
        <Button variant="primary" onclick={closeTestResult}>{t("providers.close")}</Button>
      </div>
    </div>
  </div>
{/if}

<!-- Error Message Modal -->
<ErrorMessageModal
  show={showErrorModal}
  errorMessage={selectedError}
  title={selectedErrorTitle}
  on:close={closeErrorModal}
/>

<style>
  .page-header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: 2rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .view-toggle {
    display: flex;
    gap: 0.375rem;
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.25rem;
    border-radius: 0.375rem;
  }

  :global([data-theme="dark"]) .view-toggle {
    background: var(--bg-tertiary, #1f2937);
  }

  :global([data-theme="dark"]) .info-value.url {
    background: var(--bg-tertiary, #1f2937);
    color: var(--text-secondary, #9ca3af);
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary, #666);
  }

  .empty {
    text-align: center;
    padding: 4rem;
    background: var(--card-bg, white);
    border-radius: 0.5rem;
  }

  .empty p {
    color: var(--text-secondary, #666);
    margin-bottom: 1rem;
  }

  .filters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0;
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

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
  }

  .pagination-info {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .page-info {
    font-size: 0.875rem;
    color: var(--text-primary, #495057);
    min-width: 60px;
    text-align: center;
  }

  /* Statistics Row Layout */
  .stats-row {
    display: flex;
    gap: 1rem;
    margin-top: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .stats-row :global(.stat-card) {
    flex: 1;
  }

  /* Provider Grid Layout */
  .providers-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 1.5rem;
    margin-top: 1.5rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-color, #dee2e6);
  }

  .provider-info {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex: 1;
    min-width: 0;
  }

  .provider-name {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Toggle Switch Styles */
  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
    flex-shrink: 0;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--bg-tertiary, #ccc);
    transition: 0.3s;
    border-radius: 24px;
    border: 1px solid var(--border-color, transparent);
  }

  :global([data-theme="dark"]) .toggle-slider {
    background-color: #21262d;
    border-color: #30363d;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  :global([data-theme="dark"]) .toggle-slider:before {
    background-color: #c9d1d9;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  }

  .toggle-switch input:checked + .toggle-slider {
    background-color: var(--success-color, #28a745);
    border-color: var(--success-color, #28a745);
  }

  :global([data-theme="dark"]) .toggle-switch input:checked + .toggle-slider {
    background-color: #238636;
    border-color: #238636;
  }

  .toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(20px);
  }

  .toggle-switch:hover .toggle-slider {
    opacity: 0.9;
  }

  .toggle-switch input:disabled + .toggle-slider {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .card-body {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    flex: 1;
  }

  .info-row {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .info-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary, #666);
  }

  .info-value {
    font-size: 0.875rem;
    color: var(--text-primary, #1a1a1a);
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .info-value.url {
    font-family: monospace;
    font-size: 0.8125rem;
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.375rem 0.5rem;
    border-radius: 0.25rem;
    color: var(--text-secondary, #6c757d);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .priority-display {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .priority-value {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: var(--bg-tertiary, #e9ecef);
    border-radius: 0.25rem;
    font-weight: 500;
    color: var(--text-primary, #495057);
  }

  .priority-edit-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    background: transparent;
    border: none;
    color: var(--text-secondary, #6c757d);
    cursor: pointer;
    border-radius: 0.25rem;
    transition: all 0.2s;
    opacity: 0.6;
  }

  .priority-edit-icon:hover {
    opacity: 1;
    background: var(--bg-tertiary, #e9ecef);
    color: var(--primary-color, #007bff);
  }

  .priority-edit-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .priority-input {
    width: 70px;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--primary-color, #007bff);
    border-radius: 0.25rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.875rem;
    text-align: center;
    font-weight: 500;
  }

  .priority-input:focus {
    outline: none;
    border-color: var(--primary-color, #007bff);
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
  }

  .priority-actions {
    display: flex;
    gap: 0.25rem;
  }

  .priority-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: bold;
    transition: all 0.2s;
  }

  .priority-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .save-btn {
    background: var(--success-color, #28a745);
    color: white;
  }

  .save-btn:hover:not(:disabled) {
    background: #218838;
    transform: scale(1.05);
  }

  .cancel-btn {
    background: var(--danger-color, #dc3545);
    color: white;
  }

  .cancel-btn:hover:not(:disabled) {
    background: #c82333;
    transform: scale(1.05);
  }

  .models-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
  }

  .card-actions {
    display: flex;
    gap: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border-color, #dee2e6);
    flex-wrap: wrap;
  }

  /* Responsive Design */
  @media (max-width: 1200px) {
    .providers-grid {
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    }
  }

  @media (max-width: 1024px) {
    .stats-row {
      flex-wrap: wrap;
    }

    .stats-row :global(.stat-card) {
      flex: 1 1 calc(50% - 0.5rem);
      min-width: 200px;
    }
  }

  @media (max-width: 768px) {
    .providers-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .stats-row {
      flex-direction: column;
    }

    .stats-row :global(.stat-card) {
      width: 100%;
    }

    .page-header {
      flex-direction: column;
      align-items: stretch;
      gap: 1rem;
    }

    .header-right {
      width: 100%;
      justify-content: flex-end;
    }

    .view-toggle {
      width: 100%;
      max-width: 200px;
    }

    .card-header {
      flex-direction: column;
      gap: 0.75rem;
    }

    .card-actions {
      flex-direction: column;
    }
  }

  @media (max-width: 480px) {
    .info-value.url {
      font-size: 0.75rem;
    }
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--card-bg, white);
    border-radius: 0.5rem;
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    padding: 2rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }

  .modal-content h2 {
    margin: 0 0 1rem 0;
    font-size: 1.5rem;
    color: var(--text-primary, #1a1a1a);
  }

  /* Test Result Modal Styles */
  .test-result-modal {
    max-width: 700px;
  }

  .test-result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .test-result-header h2 {
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .test-summary {
    display: flex;
    gap: 2rem;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .summary-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .summary-label {
    font-weight: 500;
    color: var(--text-secondary, #666);
  }

  .summary-value {
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
  }

  .categories-section {
    margin-bottom: 1.5rem;
  }

  .categories-section h3 {
    margin: 0 0 1rem 0;
    font-size: 1.125rem;
    color: var(--text-primary, #1a1a1a);
  }

  .categories-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .category-item {
    padding: 1rem;
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 0.5rem;
  }

  .category-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .category-name {
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
    font-size: 1rem;
  }

  .category-details {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.875rem;
  }

  .detail-item {
    display: flex;
    gap: 0.5rem;
  }

  .detail-item.error {
    color: var(--danger-color, #dc3545);
  }

  .detail-label {
    font-weight: 500;
    color: var(--text-secondary, #666);
    min-width: 80px;
  }

  .detail-value {
    color: var(--text-primary, #1a1a1a);
    white-space: nowrap;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .detail-item.error .detail-value {
    color: var(--danger-color, #dc3545);
  }

  .error-value {
    display: block;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-value.clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .error-value.clickable:hover {
    color: var(--danger-color, #dc3545);
    opacity: 0.8;
  }

  .detail-value.code {
    font-family: monospace;
    font-size: 0.8125rem;
    background: var(--bg-tertiary, #f8f9fa);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .category-details {
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .detail-value {
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
  }

  .test-result-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color, #dee2e6);
  }

  /* 表格视图样式 */
  .table-view {
    margin-top: 1.5rem;
  }

  .table-wrapper {
    overflow-x: auto;
  }

  .providers-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .providers-table thead {
    background: var(--bg-tertiary, #f8f9fa);
    border-bottom: 2px solid var(--border-color, #dee2e6);
  }

  .providers-table th {
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary, #1a1a1a);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    transition: background 0.2s;
  }

  .providers-table th:hover {
    background: var(--bg-tertiary, #e9ecef);
  }

  .th-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .sort-indicator {
    font-size: 0.75rem;
    color: var(--primary-color, #007bff);
  }

  .providers-table tbody tr {
    border-bottom: 1px solid var(--border-color, #dee2e6);
    transition: background 0.2s;
  }

  .providers-table tbody tr:hover {
    background: var(--bg-tertiary, #f8f9fa);
  }

  .providers-table td {
    padding: 0.75rem 0.75rem;
    color: var(--text-secondary, #6c757d);
    vertical-align: middle;
    text-align: left;
  }

  /* 列宽控制 */
  .name-column {
    min-width: 150px;
  }

  .status-column {
    min-width: 100px;
    text-align: left;
  }

  .url-column {
    min-width: 250px;
  }

  .api-format-column {
    min-width: 100px;
    text-align: left;
  }

  .priority-column {
    min-width: 80px;
    text-align: left;
  }

  .models-column {
    min-width: 200px;
  }

  .actions-column {
    min-width: 80px;
    text-align: left;
  }

  /* 单元格内容样式 */
  .provider-name-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .provider-title {
    font-weight: 500;
    color: var(--text-primary, #1a1a1a);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .url-text {
    font-family: monospace;
    font-size: 0.8125rem;
    color: var(--text-secondary, #6c757d);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: block;
    text-align: left;
  }

  .priority-display {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.5rem;
  }

  .priority-value {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: var(--bg-tertiary, #e9ecef);
    border-radius: 0.25rem;
    font-weight: 500;
    color: var(--text-primary, #495057);
    font-size: 0.8125rem;
    text-align: left;
  }

  .priority-edit-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    background: transparent;
    border: none;
    color: var(--text-secondary, #6c757d);
    cursor: pointer;
    border-radius: 0.25rem;
    transition: all 0.2s;
    opacity: 0.6;
  }

  .priority-edit-icon:hover {
    opacity: 1;
    background: var(--bg-tertiary, #e9ecef);
    color: var(--primary-color, #007bff);
  }

  .priority-edit-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: center;
  }

  .priority-input {
    width: 60px;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--primary-color, #007bff);
    border-radius: 0.25rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    font-size: 0.8125rem;
    text-align: center;
    font-weight: 500;
  }

  .priority-input:focus {
    outline: none;
    border-color: var(--primary-color, #007bff);
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
  }

  .priority-actions {
    display: flex;
    gap: 0.25rem;
  }

  .priority-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: bold;
    transition: all 0.2s;
  }

  .priority-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .save-btn {
    background: var(--success-color, #28a745);
    color: white;
  }

  .save-btn:hover:not(:disabled) {
    background: #218838;
    transform: scale(1.05);
  }

  .cancel-btn {
    background: var(--danger-color, #dc3545);
    color: white;
  }

  .cancel-btn:hover:not(:disabled) {
    background: #c82333;
    transform: scale(1.05);
  }

  .models-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    justify-content: flex-start;
  }

  .action-buttons {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.125rem;
  }

  .action-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    border: none;
    background: transparent;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s;
    opacity: 0.7;
  }

  .action-icon-btn:hover {
    opacity: 1;
    transform: scale(1.1);
  }

  .test-btn {
    color: var(--primary-color, #007bff);
  }

  .test-btn:hover {
    background: rgba(0, 123, 255, 0.1);
  }

  .edit-btn {
    color: var(--info-color, #17a2b8);
  }

  .edit-btn:hover {
    background: rgba(23, 162, 184, 0.1);
  }

  .delete-btn {
    color: var(--danger-color, #dc3545);
  }

  .delete-btn:hover {
    background: rgba(220, 53, 69, 0.1);
  }

  .empty-table {
    padding: 3rem;
    text-align: center;
    color: var(--text-secondary, #6c757d);
  }

  .table-pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: var(--bg-tertiary, #f8f9fa);
    border-top: 1px solid var(--border-color, #dee2e6);
  }

  .pagination-info {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .page-info {
    font-size: 0.875rem;
    color: var(--text-primary, #495057);
    min-width: 60px;
    text-align: center;
  }

  .page-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem;
    border: 1px solid var(--border-color, #dee2e6);
    background: var(--bg-primary, white);
    color: var(--text-primary, #495057);
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .page-btn:hover:not(:disabled) {
    background: var(--bg-tertiary, #e9ecef);
  }

  .page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* 小尺寸开关 */
  .toggle-switch.small {
    width: 36px;
    height: 20px;
  }

  .toggle-switch.small .toggle-slider:before {
    height: 14px;
    width: 14px;
    left: 3px;
    bottom: 3px;
  }

  .toggle-switch.small input:checked + .toggle-slider:before {
    transform: translateX(16px);
  }

  /* 暗黑主题 */
  :global([data-theme="dark"]) .providers-table thead {
    background: var(--bg-tertiary, #1f2937);
  }

  :global([data-theme="dark"]) .providers-table th {
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .providers-table th:hover {
    background: var(--bg-tertiary, #374151);
  }

  :global([data-theme="dark"]) .providers-table tbody tr:hover {
    background: var(--bg-tertiary, #1f2937);
  }

  :global([data-theme="dark"]) .priority-value {
    background: var(--bg-tertiary, #374151);
    color: var(--text-secondary, #d1d5db);
  }

  :global([data-theme="dark"]) .priority-edit-icon:hover {
    background: var(--bg-tertiary, #374151);
  }

  :global([data-theme="dark"]) .table-pagination {
    background: var(--bg-tertiary, #1f2937);
    border-top-color: var(--border-color, #374151);
  }

  :global([data-theme="dark"]) .page-btn {
    background: var(--bg-primary, #1f2937);
    border-color: var(--border-color, #374151);
    color: var(--text-primary, #f9fafb);
  }

  :global([data-theme="dark"]) .page-btn:hover:not(:disabled) {
    background: var(--bg-tertiary, #374151);
  }

  /* 响应式设计 */
  @media (max-width: 1200px) {
    .api-format-column,
    .priority-column {
      min-width: 80px;
    }

    .actions-column {
      min-width: 160px;
    }
  }

  @media (max-width: 1024px) {
    .models-column {
      min-width: 200px;
    }

    .url-column {
      min-width: 200px;
    }
  }

  @media (max-width: 768px) {
    .providers-table th,
    .providers-table td {
      padding: 0.75rem 0.5rem;
      font-size: 0.8125rem;
    }

    .name-column {
      min-width: 120px;
    }

    .status-column {
      min-width: 80px;
    }

    .url-column {
      min-width: 180px;
    }

    .api-format-column,
    .priority-column {
      min-width: 70px;
    }

    .models-column {
      min-width: 180px;
    }

    .actions-column {
      min-width: 140px;
    }

    .action-buttons {
      flex-direction: column;
      gap: 0.25rem;
    }

    .table-pagination {
      flex-direction: column;
      gap: 0.75rem;
      align-items: stretch;
    }

    .pagination-controls {
      justify-content: center;
    }
  }

  @media (max-width: 480px) {
    .providers-table th,
    .providers-table td {
      padding: 0.5rem 0.375rem;
      font-size: 0.75rem;
    }

    .name-column {
      min-width: 100px;
    }

    .url-column {
      min-width: 150px;
    }

    .models-column {
      min-width: 160px;
    }

    .actions-column {
      min-width: 120px;
    }
  }

  .access-denied {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    text-align: center;
    color: var(--text-secondary);
  }

  .access-denied svg {
    color: var(--danger-color, #dc3545);
    margin-bottom: 1rem;
  }

  .access-denied p {
    margin: 0;
    font-size: 1.25rem;
  }

  .access-denied .redirect-hint {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
  }
</style>
