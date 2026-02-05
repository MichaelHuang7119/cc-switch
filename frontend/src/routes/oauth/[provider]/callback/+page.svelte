<script lang="ts">
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { authService } from '$lib/services/auth';

  // OAuth provider display names for error messages
  const providerNames: Record<string, string> = {
    github: 'GitHub',
    google: 'Google',
    feishu: 'Feishu',
    microsoft: 'Microsoft',
    oidc: 'OIDC'
  };

  function getProviderDisplayName(provider: string): string {
    return providerNames[provider] || provider;
  }

  async function handleOAuthCallback() {
    if (!browser) return;

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const idToken = urlParams.get('id_token');  // OIDC may return id_token
      const error = urlParams.get('error');
      const errorDescription = urlParams.get('error_description');
      const provider = $page.params.provider;

      // Handle OAuth errors from provider - only show error page for failures
      if (error || !code || !provider) {
        // Set page title before redirect
        document.title = 'Login Failed - CC Switch';
        // Invalid or failed OAuth, redirect to login with error
        const params = new URLSearchParams();
        if (error) params.set('error', error);
        if (errorDescription) params.set('error_description', errorDescription);
        if (!code) params.set('error', 'missing_code');
        await goto(`/login?${params.toString()}`, { replaceState: true });
        return;
      }

      // Process OAuth login - directly redirect to /auth with token
      const result = await authService.oauthCallback(provider, code, idToken || undefined);

      if (result.access_token) {
        // Set page title before redirect
        document.title = 'Logging in... - CC Switch';
        // Use goto instead of window.location.href to avoid "leave site" prompt
        const authUrl = `/auth?token=${encodeURIComponent(result.access_token)}`;
        await goto(authUrl, { replaceState: true, noScroll: true });
      } else {
        throw new Error('No access token in response');
      }

    } catch (err) {
      // On error, redirect to login page with error message
      document.title = 'Login Failed - CC Switch';
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      await goto(`/login?error=oauth_failed&error_description=${encodeURIComponent(errorMessage)}`, { replaceState: true });
    }
  }

  onMount(() => {
    handleOAuthCallback();
  });
</script>

<svelte:head>
  <title>Logging in... - CC Switch</title>
</svelte:head>

<!-- Minimal loading indicator - no success animation -->
<div class="oauth-callback">
  <div class="card">
    <div class="spinner"></div>
    <p>Logging in with {getProviderDisplayName($page.params.provider)}...</p>
  </div>
</div>

<style>
  .oauth-callback {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: var(--bg-secondary, #f5f5f5);
  }

  .card {
    background: var(--bg-primary, white);
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    max-width: 400px;
    width: 100%;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-color, #e0e0e0);
    border-top-color: var(--primary-color, #007bff);
    border-radius: 50%;
    margin: 0 auto 16px;
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
