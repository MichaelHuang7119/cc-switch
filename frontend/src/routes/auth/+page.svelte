<script lang="ts">
  import { browser } from '$app/environment';
  import { goto, replaceState } from '$app/navigation';
  import { onMount } from 'svelte';
  import { authService } from '$lib/services/auth';
  import { toast } from '$stores/toast';
  import { tStore } from '$stores/language';

  const t = $derived($tStore);

  async function handleAuthCallback() {
    if (!browser) return;

    try {
      // Check for token in URL
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const error = urlParams.get('error');
      const errorDescription = urlParams.get('error_description');

      // Handle errors - redirect to login with error
      if (error || !token) {
        document.title = t('common.error');
        const params = new URLSearchParams();
        if (error) params.set('error', error);
        if (errorDescription) params.set('error_description', errorDescription);
        if (!token) {
          params.set('error', 'missing_token');
          params.set('error_description', 'No authentication token found');
        }
        await goto(`/login?${params.toString()}`, { replaceState: true });
        return;
      }

      // Store token first
      authService.setToken(token);

      // CRITICAL: Fetch and store user info BEFORE any navigation
      // This ensures permissions are available during beforeNavigate
      console.log('[Auth] Fetching user info before navigation...');
      const user = await authService.getCurrentUser();
      if (user) {
        console.log('[Auth] Raw user from API:', JSON.stringify(user));
        authService.setUser(user);
        const storedUser = authService.getUser();
        console.log('[Auth] User info stored:', JSON.stringify(storedUser));
        toast.success(t('loginSuccess') + ' ' + (user.name || user.email));
        // Dispatch login event for other components
        window.dispatchEvent(new CustomEvent('auth:login', {
          detail: { token, user }
        }));
      } else {
        console.warn('[Auth] Failed to fetch user info');
      }

      // Clear URL using SvelteKit's replaceState (not window.history.replaceState)
      replaceState(window.location.pathname, {});

      // Now navigate to the target page
      const redirectUrl = authService.getDefaultRedirectUrl();
      console.log('[Auth] Redirecting to:', redirectUrl);

      // Navigate to the target page
      await goto(redirectUrl, { replaceState: true, noScroll: true });
      console.log('[Auth] Navigation completed successfully');

    } catch (err) {
      // On error, redirect to login page
      document.title = t('common.error');
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
      await goto(`/login?error=auth_failed&error_description=${encodeURIComponent(errorMessage)}`, { replaceState: true });
    }
  }

  onMount(() => {
    handleAuthCallback();
  });
</script>

<svelte:head>
  <title>Logging in... - CC Switch</title>
</svelte:head>

<!-- Minimal loading indicator - no success animation -->
<div class="auth-page">
  <div class="spinner"></div>
  <p>Completing login...</p>
</div>

<style>
  .auth-page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: var(--bg-secondary, #f5f5f5);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-color, #e0e0e0);
    border-top-color: var(--primary-color, #007bff);
    border-radius: 50%;
    margin-bottom: 16px;
    animation: spin 0.8s linear infinite;
  }

  p {
    margin: 0;
    color: var(--text-secondary, #666);
    font-size: 0.95rem;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
