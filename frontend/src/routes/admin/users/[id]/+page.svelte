<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { permissionsService } from "$services/permissions";
  import { authService } from "$services/auth";
  import { toast } from "$stores/toast";
  import { tStore } from "$stores/language";
  import type { PermissionCategory, PermissionInfo, PermissionCategoryGroup } from "$types/permission";

  const t = $derived($tStore);

  const userId = $derived(parseInt($page.params.id));

  interface UserInfo {
    id: number;
    email: string;
    name: string | null;
    is_admin: boolean;
  }

  let loading = $state(true);
  let saving = $state(false);
  let user = $state<UserInfo | null>(null);
  let permissions = $state<Record<PermissionCategory, boolean>>({} as Record<PermissionCategory, boolean>);
  let originalPermissions = $state<Record<string, boolean>>({});
  let allPermissions = $state<PermissionInfo[]>([]);

  // Group permissions by category (excluding feature which is basic for all users)
  let permissionGroups = $derived.by((): PermissionCategoryGroup[] => {
    const groups: Record<string, PermissionCategoryGroup> = {
      admin: { name: t("permissions.categories.admin"), permissions: [] },
    };

    for (const perm of allPermissions) {
      // Skip feature permissions as they are basic for all users
      if (perm.category === "feature") continue;
      // Skip users permission - it's controlled by is_admin flag, not editable
      if (perm.code === "users") continue;
      if (groups[perm.category]) {
        groups[perm.category].permissions.push(perm);
      }
    }

    return Object.values(groups).filter((g) => g.permissions.length > 0);
  });

    // Check if user is editable (only non-admin users can have their permissions edited)
  let isEditable = $derived(user !== null && !user.is_admin);

  // 检查所有数据是否加载完成，避免页面渲染时状态闪跳
  let allDataLoaded = $derived(!loading && user !== null && Object.keys(permissions).length > 0);

  async function fetchData() {
    try {
      const [permsData, userPermsData] = await Promise.all([
        permissionsService.getAllPermissions(),
        permissionsService.getUserPermissions(userId),
      ]);

      allPermissions = permsData;
      permissions = userPermsData.permissions as Record<PermissionCategory, boolean>;
      originalPermissions = { ...permissions };

      // Fetch user info
      const userResponse = await fetch(`/api/admin/permissions/users/${userId}`, {
        method: "GET",
        headers: authService.getAuthHeaders(),
      });

      if (userResponse.ok) {
        user = await userResponse.json();
      }
    } catch (error) {
      console.error("Failed to load data:", error);
      toast.error(t("permissions.loadFailed"));
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      await permissionsService.updateUserPermissions(userId, permissions);
      toast.success(t("permissions.saved"));
      originalPermissions = { ...permissions };
    } catch (error) {
      console.error("Failed to save permissions:", error);
      toast.error(t("permissions.saveFailed"));
    } finally {
      saving = false;
    }
  }

  async function handleReset() {
    if (!confirm(t("permissions.resetConfirm"))) return;

    saving = true;
    try {
      const result = await permissionsService.resetUserPermissions(userId);
      permissions = result.permissions as Record<PermissionCategory, boolean>;
      toast.success(t("permissions.resetSuccess"));
    } catch (error) {
      console.error("Failed to reset permissions:", error);
      toast.error(t("permissions.resetFailed"));
    } finally {
      saving = false;
    }
  }

  function hasChanges(): boolean {
    return JSON.stringify(permissions) !== JSON.stringify(originalPermissions);
  }

  onMount(() => {
    fetchData();
  });
</script>

<svelte:head>
  <title>
    {t("permissions.title")} - {user?.email || ""} - CC Switch
  </title>
</svelte:head>

<div class="container">
  {#if !allDataLoaded}
    <div class="loading">
      <p>{t("common.loading")}</p>
    </div>
  {:else}
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" onclick={() => goto("/admin/users")}>
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
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          {t("common.back")}
        </button>
        <div class="user-info">
          <h1>{t("permissions.title")}</h1>
          {#if user}
            <p class="user-email">{user.email}</p>
          {/if}
        </div>
      </div>
      <div class="actions">
        {#if !isEditable}
          <span class="admin-badge">{t("permissions.adminUser")}</span>
        {:else}
          <button
            class="btn secondary"
            onclick={handleReset}
            disabled={saving}
          >
            {t("permissions.reset")}
          </button>
          <button
            class="btn primary"
            onclick={handleSave}
            disabled={!hasChanges() || saving}
          >
            {saving ? t("common.saving") : t("common.save")}
          </button>
        {/if}
      </div>
    </div>

    {#each permissionGroups as group}
      <div class="permission-group">
        <h2>{group.name}</h2>
        <div class="permission-grid">
          {#each group.permissions as perm}
            <div class="permission-item" class:disabled={!isEditable}>
              <div class="permission-info">
                <span class="permission-name">{perm.name}</span>
                <span class="permission-description">{perm.description}</span>
              </div>
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  bind:checked={permissions[perm.code as PermissionCategory]}
                  disabled={!isEditable || (user?.is_admin && perm.code === "config")}
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>

<style>
  .container {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: none;
    border: none;
    color: var(--text-secondary, #666);
    cursor: pointer;
    padding: 0;
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
  }

  .back-btn:hover {
    color: var(--primary-color, #007bff);
  }

  .user-info h1 {
    margin: 0;
    font-size: 1.5rem;
  }

  .user-email {
    margin: 0.25rem 0 0;
    color: var(--text-secondary, #666);
    font-size: 0.875rem;
  }

  .actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }

  .admin-badge {
    padding: 0.5rem 1rem;
    background: rgba(0, 123, 255, 0.1);
    color: var(--primary-color, #007bff);
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn.primary {
    background: var(--primary-color, #007bff);
    color: white;
  }

  .btn.primary:hover:not(:disabled) {
    background: var(--primary-color-hover, #0056b3);
  }

  .btn.secondary {
    background: var(--bg-tertiary, #e0e0e0);
    color: var(--text-primary, #333);
  }

  .btn.secondary:hover:not(:disabled) {
    background: var(--border-color, #ccc);
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary, #666);
  }

  .permission-group {
    margin-bottom: 2rem;
  }

  .permission-group h2 {
    font-size: 1.125rem;
    margin: 0 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-color, #e0e0e0);
  }

  .permission-grid {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .permission-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: var(--bg-primary, white);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    transition: all 0.2s;
  }

  .permission-item.disabled {
    opacity: 0.7;
    background: var(--bg-secondary, #f8f9fa);
  }

  .permission-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .permission-name {
    font-weight: 500;
  }

  .permission-description {
    font-size: 0.875rem;
    color: var(--text-secondary, #666);
  }

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
  }

  .toggle-switch input:checked + .toggle-slider {
    background-color: var(--success-color, #28a745);
  }

  .toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(20px);
  }

  .toggle-switch input:disabled + .toggle-slider {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
