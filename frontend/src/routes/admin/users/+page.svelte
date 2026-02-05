<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { authService } from "$services/auth";
  import { toast } from "$stores/toast";
  import { tStore } from "$stores/language";
  import Pagination from "$components/Pagination.svelte";

  const t = $derived($tStore);

  interface User {
    id: number;
    email: string;
    name: string | null;
    is_admin: boolean;
    is_active: boolean;
    created_at: string;
    last_login_at: string | null;
  }

  let users = $state<User[]>([]);
  let loading = $state(true);
  let hasPermission = $state(true);
  let searchQuery = $state("");

  // Pagination
  let currentPage = $state(1);
  let pageSize = $state(10);
  let total = $state(0);
  let totalPages = $state(1);

  // Modal states
  let showModal = $state(false);
  let modalMode = $state<"add" | "edit">("add");
  let editingUser = $state<User | null>(null);
  let submitting = $state(false);

  // Form data
  let formEmail = $state("");
  let formName = $state("");
  let formPassword = $state("");
  let formConfirmPassword = $state("");
  let formIsAdmin = $state(false);
  let formIsActive = $state(true);

  // Delete confirmation
  let showDeleteConfirm = $state(false);
  let deletingUser = $state<User | null>(null);
  let deleting = $state(false);

  // Filtered users based on search
  let filteredUsers = $derived(
    users.filter(
      (user) =>
        user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (user.name && user.name.toLowerCase().includes(searchQuery.toLowerCase()))
    )
  );

  async function fetchUsers(page = 1) {
    loading = true;
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      const response = await fetch(`/api/admin/permissions/users?${params}`, {
        method: "GET",
        headers: authService.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch users");
      }

      const data = await response.json();
      users = data.users;
      total = data.total;
      totalPages = data.total_pages;
      currentPage = data.page;
    } catch (error) {
      console.error("Failed to fetch users:", error);
      toast.error(t("users.fetchFailed"));
    } finally {
      loading = false;
    }
  }

  function handlePageChange(page: number) {
    fetchUsers(page);
    // Scroll to top of table
    const tableContainer = document.querySelector(".table-wrapper");
    if (tableContainer) {
      tableContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function openAddModal() {
    modalMode = "add";
    editingUser = null;
    formEmail = "";
    formName = "";
    formPassword = "";
    formConfirmPassword = "";
    formIsAdmin = false;
    formIsActive = true;
    showModal = true;
  }

  function openEditModal(user: User) {
    modalMode = "edit";
    editingUser = user;
    formEmail = user.email;
    formName = user.name || "";
    formPassword = "";
    formConfirmPassword = "";
    formIsAdmin = user.is_admin;
    formIsActive = user.is_active;
    showModal = true;
  }

  function closeModal() {
    showModal = false;
    editingUser = null;
  }

  async function handleSubmit() {
    if (!formEmail) {
      toast.error(t("users.invalidEmail"));
      return;
    }

    if (modalMode === "add") {
      if (!formPassword) {
        toast.error(t("users.passwordTooShort"));
        return;
      }
      if (formPassword.length < 8) {
        toast.error(t("users.passwordTooShort"));
        return;
      }
      if (formPassword !== formConfirmPassword) {
        toast.error(t("users.passwordMismatch"));
        return;
      }
    } else if (modalMode === "edit") {
      // Validate new password if provided
      if (formPassword && formPassword.length > 0 && formPassword.length < 8) {
        toast.error(t("users.passwordTooShort"));
        return;
      }
      if (formPassword && formPassword !== formConfirmPassword) {
        toast.error(t("users.passwordMismatch"));
        return;
      }
    }

    submitting = true;
    try {
      const url = modalMode === "add"
        ? "/api/admin/permissions/users"
        : `/api/admin/permissions/users/${editingUser!.id}`;

      const method = modalMode === "add" ? "POST" : "PUT";

      const body: Record<string, any> = modalMode === "add"
        ? {
            email: formEmail,
            name: formName || null,
            password: formPassword,
            is_admin: formIsAdmin
          }
        : {
            email: formEmail,
            name: formName || null,
            is_admin: formIsAdmin,
            is_active: formIsActive
          };

      // Include new password if provided in edit mode
      if (modalMode === "edit" && formPassword) {
        body.password = formPassword;
      }

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...authService.getAuthHeaders(),
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Failed to save user");
      }

      toast.success(t("users.saveSuccess"));
      closeModal();
      fetchUsers(currentPage);
    } catch (error) {
      console.error("Failed to save user:", error);
      toast.error(t("users.saveFailed"));
    } finally {
      submitting = false;
    }
  }

  function confirmDelete(user: User) {
    deletingUser = user;
    showDeleteConfirm = true;
  }

  function closeDeleteConfirm() {
    showDeleteConfirm = false;
    deletingUser = null;
  }

  async function handleDelete() {
    if (!deletingUser) return;

    deleting = true;
    try {
      const response = await fetch(`/api/admin/permissions/users/${deletingUser.id}`, {
        method: "DELETE",
        headers: authService.getAuthHeaders(),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Failed to delete user");
      }

      toast.success(t("users.deleteSuccess"));
      closeDeleteConfirm();
      // Adjust page if needed
      const newTotal = total - 1;
      const newTotalPages = Math.ceil(newTotal / pageSize);
      const targetPage = currentPage > newTotalPages ? newTotalPages : currentPage;
      fetchUsers(targetPage || 1);
    } catch (error) {
      console.error("Failed to delete user:", error);
      toast.error(t("users.deleteFailed"));
    } finally {
      deleting = false;
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString();
  }

  onMount(() => {
    // Check permission
    if (!authService.hasPermission("providers")) {
      hasPermission = false;
      loading = false;
      toast.error(t("common.accessDenied"));
      setTimeout(() => goto("/chat"), 1000);
      return;
    }
    fetchUsers();
  });
</script>

<svelte:head>
  <title>{t("users.title")} - CC Switch</title>
</svelte:head>

<div class="container">
  {#if !hasPermission}
    <div class="access-denied">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
      </svg>
      <p>{t("common.accessDenied")}</p>
      <p class="redirect-hint">{t("common.redirecting")}</p>
    </div>
  {:else}
    <div class="page-header">
      <div class="header-title">
        <span class="total-badge">{t("pagination.page")} {currentPage} / {totalPages} ({total} {t("users.title")})</span>
      </div>
      <div class="header-actions">
        <div class="search-box">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            placeholder={t("users.searchPlaceholder")}
            bind:value={searchQuery}
          />
        </div>
        <button class="btn-primary" onclick={openAddModal}>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          {t("users.addUser")}
        </button>
      </div>
    </div>

    {#if loading}
      <div class="loading">
        <div class="spinner"></div>
        <p>{t("common.loading")}</p>
      </div>
    {:else}
      <div class="card">
        <div class="table-wrapper">
          <table class="users-table">
            <thead>
              <tr>
                <th class="th-id">ID</th>
                <th class="th-email">{t("users.email")}</th>
                <th class="th-name">{t("users.name")}</th>
                <th class="th-role">{t("users.role")}</th>
                <th class="th-status">{t("users.status")}</th>
                <th class="th-date">{t("users.createdAt")}</th>
                <th class="th-date">{t("users.lastLogin")}</th>
                <th class="th-actions">{t("users.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredUsers as user (user.id)}
                <tr>
                  <td class="td-id">{user.id}</td>
                  <td class="td-email">
                    <div class="email-cell">
                      <span class="email-text">{user.email}</span>
                    </div>
                  </td>
                  <td class="td-name">{user.name || "-"}</td>
                  <td class="td-role">
                    <span class="badge" class:admin={user.is_admin}>
                      {user.is_admin ? t("users.roles.admin") : t("users.roles.user")}
                    </span>
                  </td>
                  <td class="td-status">
                    <div class="status-wrapper">
                      <span class="status-dot" class:active={user.is_active}></span>
                      <span class="status-text">
                        {user.is_active ? t("users.statusActive") : t("users.statusInactive")}
                      </span>
                    </div>
                  </td>
                  <td class="td-date">{formatDate(user.created_at)}</td>
                  <td class="td-date">{formatDate(user.last_login_at)}</td>
                  <td class="td-actions">
                    <div class="action-buttons">
                      <button
                        class="btn-action"
                        title={t("users.editUser")}
                        onclick={() => openEditModal(user)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                      </button>
                      <button
                        class="btn-action"
                        title={t("users.managePermissions")}
                        onclick={() => goto(`/admin/users/${user.id}`)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                      </button>
                      <button
                        class="btn-action danger"
                        title={t("users.deleteUser")}
                        onclick={() => confirmDelete(user)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
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
        </div>

        <Pagination
          {currentPage}
          {totalPages}
          {total}
          pageSize={pageSize}
          onPageChange={handlePageChange}
        />
      </div>

      {#if filteredUsers.length === 0}
        <div class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
          <p>{t("users.noUsers")}</p>
          {#if total === 0}
            <button class="btn-primary" onclick={openAddModal}>
              {t("users.addFirstUser")}
            </button>
          {/if}
        </div>
      {/if}
    {/if}
  {/if}
</div>

<!-- Add/Edit User Modal -->
{#if showModal}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={closeModal} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1">
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
    <div class="modal" onclick={(e) => e.stopPropagation()} role="presentation">
      <div class="modal-header">
        <h2 id="modal-title">{modalMode === "add" ? t("users.addUser") : t("users.editUser")}</h2>
        <button class="btn-close" onclick={closeModal} aria-label={t("common.close")}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label for="email">{t("users.email")} *</label>
          <input
            type="email"
            id="email"
            bind:value={formEmail}
            placeholder={t("users.email")}
            disabled={modalMode === "edit"}
          />
        </div>
        <div class="form-group">
          <label for="name">{t("users.name")}</label>
          <input
            type="text"
            id="name"
            bind:value={formName}
            placeholder={t("users.name")}
          />
        </div>
        {#if modalMode === "add"}
          <div class="form-group">
            <label for="password">{t("users.password")} *</label>
            <input
              type="password"
              id="password"
              bind:value={formPassword}
              placeholder={t("users.password")}
            />
          </div>
          <div class="form-group">
            <label for="confirmPassword">{t("users.confirmPassword")} *</label>
            <input
              type="password"
              id="confirmPassword"
              bind:value={formConfirmPassword}
              placeholder={t("users.confirmPassword")}
            />
          </div>
        {:else}
          <div class="form-group">
            <label for="newPassword">{t("users.newPassword")}</label>
            <input
              type="password"
              id="newPassword"
              bind:value={formPassword}
              placeholder={t("users.newPasswordPlaceholder")}
            />
          </div>
          {#if formPassword}
            <div class="form-group">
              <label for="confirmNewPassword">{t("users.confirmPassword")}</label>
              <input
                type="password"
                id="confirmNewPassword"
                bind:value={formConfirmPassword}
                placeholder={t("users.confirmPassword")}
              />
            </div>
          {/if}
        {/if}
        <div class="form-row">
          <div class="form-group checkbox">
            <label>
              <input type="checkbox" bind:checked={formIsAdmin} />
              {t("users.isAdmin")}
            </label>
          </div>
          {#if modalMode === "edit"}
            <div class="form-group checkbox">
              <label>
                <input type="checkbox" bind:checked={formIsActive} />
                {t("users.isActive")}
              </label>
            </div>
          {/if}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick={closeModal}>
          {t("users.cancel")}
        </button>
        <button class="btn-primary" onclick={handleSubmit} disabled={submitting}>
          {#if submitting}
            <span class="spinner-sm"></span>
            {t("common.saving")}
          {:else}
            {t("users.save")}
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteConfirm && deletingUser}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={closeDeleteConfirm} role="alertdialog" aria-modal="true" aria-labelledby="delete-modal-title" tabindex="-1">
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
    <div class="modal confirm-modal" onclick={(e) => e.stopPropagation()} role="presentation">
      <div class="modal-header">
        <h2 id="delete-modal-title">{t("users.deleteConfirmTitle")}</h2>
        <button class="btn-close" onclick={closeDeleteConfirm} aria-label={t("common.close")}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <p>{t("users.deleteConfirm", { email: deletingUser.email })}</p>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick={closeDeleteConfirm}>
          {t("users.cancel")}
        </button>
        <button class="btn-danger" onclick={handleDelete} disabled={deleting}>
          {#if deleting}
            <span class="spinner-sm"></span>
            {t("common.deleting")}
          {:else}
            {t("users.deleteUser")}
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1.5rem 2rem;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    gap: 1rem;
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .total-badge {
    padding: 0.5rem 1rem;
    background: var(--bg-secondary, #f0f0f0);
    border-radius: 0.5rem;
    font-size: 0.9rem;
    color: var(--text-secondary, #666);
    font-weight: 500;
  }

  .header-actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
    margin-left: auto;
  }

  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-box svg {
    position: absolute;
    left: 0.75rem;
    color: var(--text-secondary, #999);
    pointer-events: none;
  }

  .search-box input {
    padding: 0.5rem 0.75rem 0.5rem 2.5rem;
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    width: 240px;
    background: var(--bg-primary, white);
    color: var(--text-primary, #333);
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .search-box input:focus {
    outline: none;
    border-color: var(--primary-color, #007bff);
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem;
    color: var(--text-secondary, #666);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border-color, #e0e0e0);
    border-top-color: var(--primary-color, #007bff);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .spinner-sm {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: inline-block;
    margin-right: 0.5rem;
  }

  .card {
    background: var(--bg-primary, white);
    border-radius: 0.75rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
    overflow: hidden;
  }

  .table-wrapper {
    overflow-x: auto;
  }

  .users-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 900px;
  }

  .users-table th,
  .users-table td {
    padding: 0.875rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border-color, #f0f0f0);
    vertical-align: middle;
  }

  .users-table th {
    background: var(--bg-secondary, #f8f9fa);
    font-weight: 600;
    font-size: 0.8rem;
    color: var(--text-secondary, #666);
    text-transform: uppercase;
    letter-spacing: 0.025em;
    white-space: nowrap;
  }

  .users-table tbody tr {
    transition: background 0.15s;
  }

  .users-table tbody tr:hover {
    background: var(--bg-hover, #f8f9fa);
  }

  .users-table tbody tr:last-child td {
    border-bottom: none;
  }

  .th-id { width: 60px; }
  .th-email { min-width: 200px; }
  .th-name { min-width: 120px; }
  .th-role { width: 100px; }
  .th-status { width: 110px; }
  .th-date { width: 160px; }
  .th-actions { width: 140px; text-align: center; }

  .td-id {
    font-family: monospace;
    color: var(--text-secondary, #888);
    font-size: 0.85rem;
  }

  .email-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .email-text {
    font-weight: 500;
  }

  .td-name {
    color: var(--text-primary, #333);
  }

  .badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.625rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    font-weight: 500;
    background: var(--bg-tertiary, #f0f0f0);
    color: var(--text-secondary, #666);
  }

  .badge.admin {
    background: rgba(0, 123, 255, 0.1);
    color: var(--primary-color, #007bff);
  }

  .status-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    height: 100%;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-secondary, #999);
    flex-shrink: 0;
  }

  .status-dot.active {
    background: var(--success-color, #28a745);
  }

  .status-text {
    font-size: 0.85rem;
    color: var(--text-primary, #333);
  }

  .td-date {
    font-size: 0.85rem;
    color: var(--text-secondary, #666);
    white-space: nowrap;
  }

  .td-actions {
    text-align: center;
  }

  .action-buttons {
    display: flex;
    justify-content: center;
    gap: 0.25rem;
  }

  .btn-action {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 0.375rem;
    background: transparent;
    color: var(--text-secondary, #666);
    cursor: pointer;
    transition: all 0.15s;
  }

  .btn-action:hover {
    background: var(--bg-hover, #f0f0f0);
    color: var(--primary-color, #007bff);
  }

  .btn-action.danger:hover {
    background: rgba(220, 53, 69, 0.1);
    color: var(--danger-color, #dc3545);
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    text-align: center;
    color: var(--text-secondary, #666);
  }

  .empty-state svg {
    margin-bottom: 1rem;
    color: var(--border-color, #e0e0e0);
  }

  .empty-state p {
    margin: 0 0 1rem;
    font-size: 1rem;
  }

  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--primary-color, #007bff);
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-primary:hover {
    background: var(--primary-color-dark, #0056b3);
    transform: translateY(-1px);
  }

  .btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--bg-secondary, #f5f5f5);
    color: var(--text-primary, #333);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    background: var(--bg-hover, #e8e8e8);
  }

  .btn-danger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--danger-color, #dc3545);
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-danger:hover:not(:disabled) {
    background: var(--danger-color-dark, #c82333);
    transform: translateY(-1px);
  }

  .btn-danger:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .btn-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 0.375rem;
    background: transparent;
    color: var(--text-secondary, #666);
    cursor: pointer;
    transition: all 0.15s;
  }

  .btn-close:hover {
    background: var(--bg-hover, #f0f0f0);
    color: var(--text-primary, #333);
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

  /* Modal styles */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
    backdrop-filter: blur(2px);
  }

  .modal {
    background: var(--bg-primary, white);
    border-radius: 0.75rem;
    width: 100%;
    max-width: 460px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
    animation: modalSlideIn 0.2s ease-out;
  }

  @keyframes modalSlideIn {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid var(--border-color, #f0f0f0);
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
  }

  .modal-body {
    padding: 1.5rem;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1.25rem 1.5rem;
    border-top: 1px solid var(--border-color, #f0f0f0);
    background: var(--bg-secondary, #f8f9fa);
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  .form-group:last-child {
    margin-bottom: 0;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary, #333);
  }

  .form-group input[type="text"],
  .form-group input[type="email"],
  .form-group input[type="password"] {
    width: 100%;
    padding: 0.625rem 0.875rem;
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 0.5rem;
    font-size: 0.9rem;
    background: var(--bg-primary, white);
    color: var(--text-primary, #333);
    transition: all 0.2s;
  }

  .form-group input:focus {
    outline: none;
    border-color: var(--primary-color, #007bff);
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
  }

  .form-group input:disabled {
    background: var(--bg-secondary, #f5f5f5);
    cursor: not-allowed;
  }

  .form-row {
    display: flex;
    gap: 1.5rem;
  }

  .form-group.checkbox {
    margin-bottom: 0;
  }

  .form-group.checkbox label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-weight: normal;
  }

  .form-group.checkbox input[type="checkbox"] {
    width: 1rem;
    height: 1rem;
    accent-color: var(--primary-color, #007bff);
  }

  .confirm-modal .modal-body {
    text-align: center;
    padding: 2rem 1.5rem;
  }

  .confirm-modal .modal-body p {
    margin: 0;
    font-size: 1rem;
    color: var(--text-primary, #333);
    line-height: 1.6;
  }
</style>
