/**
 * 认证服务
 * 管理用户登录、登出和认证状态
 *
 * Features:
 * - OAuth2 登录支持 (GET/POST 模式)
 * - Token 自动存储和验证
 * - 认证状态监听
 * - 与 auth store 同步
 */
import { goto } from "$app/navigation";
import { browser } from "$app/environment";
import { toast } from "$stores/toast";
import {
  setAuthState,
  clearAuthState,
  initAuthState,
  updateUserState,
} from "$stores/auth.svelte";

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    name?: string;
    is_admin: boolean;
    avatar_url?: string;
  };
}

export interface OAuthLoginResponse {
  authorization_url: string;
  provider: string;
}

export interface OAuthCallbackResponse extends LoginResponse {
  provider: string;
  oauth_user_info: {
    email: string;
    name: string;
    avatar_url?: string;
  };
}

export interface OAuthProviderInfo {
  enabled: boolean;
  authorization_url?: string;
  name?: string;
}

export interface User {
  id: number;
  email: string;
  name?: string;
  is_admin: boolean;
  avatar_url?: string;
  permissions?: Record<string, boolean>;
}

class AuthService {
  // ============== Token Management ==============

  /**
   * 获取存储的 token
   */
  getToken(): string | null {
    if (!browser) return null;
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * 设置 token（用于 OAuth 重定向等场景）
   */
  setToken(token: string): void {
    if (!browser) return;
    localStorage.setItem(TOKEN_KEY, token);
    // 通知 auth store
    initAuthState();
  }

  /**
   * 清除 token
   */
  private clearToken(): void {
    if (!browser) return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    // 通知 auth store 清除状态（不重定向，因为 logout 会用 goto 重定向）
    clearAuthState(false);
  }

  // ============== User Management ==============

  /**
   * 获取存储的用户信息
   */
  getUser(): User | null {
    if (!browser) return null;
    const userStr = localStorage.getItem(USER_KEY);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  /**
   * 存储用户信息
   */
  setUser(user: User): void {
    if (!browser) return;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    // 同步到 auth store
    updateUserState(user);
  }

  // ============== Authentication Status ==============

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * 处理认证失败（401 错误）
   * 清除 token 并重定向到登录页
   */
  async handleAuthFailure(message?: string): Promise<void> {
    console.warn(
      "[Auth] Authentication failed:",
      message || "Token expired or invalid",
    );

    // 清除认证信息
    this.clearToken();

    // 通知用户
    if (browser) {
      toast.error("Session expired. Please login again.");

      // 重定向到登录页
      goto("/login");
    }
  }

  /**
   * 检查响应是否为 401 错误并处理
   * 返回 true 如果已处理 401 错误，false 否则
   */
  async checkUnauthorized(response: Response): Promise<boolean> {
    if (response.status === 401) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage =
        errorData.detail || errorData.message || "Unauthorized";
      await this.handleAuthFailure(errorMessage);
      return true;
    }
    return false;
  }

  /**
   * 获取认证头
   */
  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    if (!token) {
      if (browser) {
        console.warn("[Auth] No token found in localStorage");
      }
      return {};
    }
    if (browser) {
      console.debug("[Auth] Token found, creating Authorization header");
    }
    return {
      Authorization: `Bearer ${token}`,
    };
  }

  // ============== Login Methods ==============

  /**
   * 登录（邮箱密码）
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "登录失败" }));
      throw new Error(error.detail || error.message || "登录失败");
    }

    const data: LoginResponse = await response.json();

    // 存储 token
    this.setToken(data.access_token);

    // 获取完整的用户信息（包括权限）
    const fullUser = await this.getCurrentUser();
    if (fullUser) {
      this.setUser(fullUser);
      // 使用 auth store 设置认证状态（会触发响应式更新）
      setAuthState(fullUser, data.access_token);
    } else {
      // 如果获取失败，使用登录返回的基本用户信息
      this.setUser(data.user);
      setAuthState(data.user, data.access_token);
    }

    // 验证 token 已存储
    if (browser) {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (storedToken === data.access_token) {
        console.debug("[Auth] Token stored successfully");
      } else {
        console.error("[Auth] Token storage verification failed", {
          stored: storedToken?.substring(0, 20) + "...",
          expected: data.access_token.substring(0, 20) + "...",
        });
      }
    }

    return data;
  }

  /**
   * 登出
   */
  logout(): void {
    // 清除认证信息（会同时清除 localStorage 和 auth store）
    this.clearToken();

    // 清除欢迎弹窗标记
    if (browser) {
      localStorage.removeItem("welcome_shown");
      // Set page title before redirect
      document.title = "Login - CC Switch";
      goto("/login");
    }
  }

  /**
   * 获取当前用户信息（从 API）
   */
  async getCurrentUser(): Promise<User | null> {
    const token = this.getToken();
    if (!token) {
      return null;
    }

    try {
      const response = await fetch("/api/auth/me", {
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.logout();
        }
        return null;
      }

      const user: User = await response.json();
      this.setUser(user);
      return user;
    } catch (error) {
      console.error("Failed to get current user:", error);
      return null;
    }
  }

  /**
   * 修改密码
   */
  async changePassword(
    currentPassword: string,
    newPassword: string,
  ): Promise<void> {
    const response = await fetch("/api/auth/change-password", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Password change failed" }));
      throw new Error(
        error.detail || error.message || "Password change failed",
      );
    }
  }

  // ============== OAuth2 Methods ==============

  /**
   * OAuth2 登录 - 直接跳转到后端 OAuth 端点（推荐）
   *
   * 这种方式使用 GET 请求，OAuth 回调会直接重定向到前端
   */
  oauthLogin(provider: string): void {
    if (!browser) return;

    const url = `/oauth/${provider}/login`;
    console.debug(`[Auth] Redirecting to OAuth provider: ${provider}`);

    // 直接跳转到后端 OAuth 登录端点
    goto(url);
  }

  /**
   * OAuth2 登录 - 获取授权 URL（备用方法）
   */
  async getOAuthAuthorizationUrl(
    provider: string,
  ): Promise<OAuthLoginResponse> {
    const response = await fetch(`/oauth/${provider}/login`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "OAuth login failed" }));
      throw new Error(error.detail || error.message || "OAuth login failed");
    }

    // 后端返回的是重定向，我们解析 Location header
    const location =
      response.headers.get("Location") || response.headers.get("location");
    if (!location) {
      throw new Error("No authorization URL in response");
    }

    return {
      authorization_url: location,
      provider,
    };
  }

  /**
   * OAuth2 回调 - 使用授权码登录
   *
   * 这是 POST 方法，用于前端回调页面
   */
  async oauthCallback(
    provider: string,
    code: string,
    idToken?: string,
  ): Promise<OAuthCallbackResponse> {
    const body: { provider: string; code: string; id_token?: string } = {
      provider,
      code,
    };
    if (idToken) {
      body.id_token = idToken;
    }

    const response = await fetch(`/oauth/${provider}/callback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "OAuth callback failed" }));
      throw new Error(error.detail || error.message || "OAuth callback failed");
    }

    const data: OAuthCallbackResponse = await response.json();

    // 存储 token
    this.setToken(data.access_token);

    // 获取完整的用户信息（包括权限）
    const fullUser = await this.getCurrentUser();
    if (fullUser) {
      this.setUser(fullUser);
    } else {
      // 如果获取失败，使用回调返回的基本用户信息
      this.setUser(data.user);
    }

    console.debug(`[Auth] OAuth login successful for provider: ${provider}`);

    return data;
  }

  /**
   * OAuth2 回调 - 从 URL 参数解析并处理回调
   *
   * 用于处理 URL 中的 token（后端重定向方式）
   */
  async handleOAuthRedirect(): Promise<boolean> {
    if (!browser) return false;

    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");
    const error = urlParams.get("error");
    const errorDescription = urlParams.get("error_description");

    // 处理错误
    if (error) {
      console.warn(`[Auth] OAuth error: ${error}`, errorDescription);
      toast.error(errorDescription || `OAuth error: ${error}`);
      // 清除 URL 参数
      window.history.replaceState({}, document.title, window.location.pathname);
      return false;
    }

    // 处理 token
    if (token) {
      console.debug("[Auth] Processing OAuth redirect token");

      // 解码 token
      const decodedToken = decodeURIComponent(token);

      // 存储 token
      this.setToken(decodedToken);

      // 清除 URL 参数
      window.history.replaceState({}, document.title, window.location.pathname);

      // 获取完整的用户信息（包括权限）
      const user = await this.getCurrentUser();
      if (user) {
        // 确保权限信息被存储
        this.setUser(user);
        toast.success(`Welcome, ${user.name || user.email}!`);
        return true;
      }
    }

    return false;
  }

  /**
   * 获取可用的 OAuth2 提供商列表
   */
  async getOAuthProviders(): Promise<Record<string, OAuthProviderInfo>> {
    try {
      const response = await fetch("/oauth/providers");

      if (!response.ok) {
        return {};
      }

      const data = await response.json();
      return data.providers || {};
    } catch (error) {
      console.error("Failed to load OAuth providers:", error);
      return {};
    }
  }

  /**
   * 检查特定 OAuth 提供商是否可用
   */
  async isOAuthProviderEnabled(provider: string): Promise<boolean> {
    const providers = await this.getOAuthProviders();
    return providers[provider]?.enabled === true;
  }

  /**
   * 获取 OAuth 提供商列表（只返回已启用的）
   */
  async getEnabledOAuthProviders(): Promise<string[]> {
    const providers = await this.getOAuthProviders();
    return Object.entries(providers)
      .filter(([_, config]) => config.enabled)
      .map(([name, _]) => name);
  }

  // ============== Permission Methods ==============

  /**
   * Get user permissions from stored user data
   */
  getUserPermissions(): Record<string, boolean> | null {
    const user = this.getUser();
    if (!user) return null;

    // Check if user has permissions field (from API)
    if ("permissions" in user && user.permissions) {
      return user.permissions as Record<string, boolean>;
    }
    return null;
  }

  /**
   * Check if user has a specific permission
   */
  hasPermission(permission: string): boolean {
    const user = this.getUser();
    if (!user) {
      return false;
    }

    // Admins have all permissions
    if (user.is_admin) {
      return true;
    }

    // Check stored permissions
    const permissions = this.getUserPermissions();

    // Default permissions for regular users
    const defaultPermissions: Record<string, boolean> = {
      chat: true,
      conversations: true,
      preferences: true,
      providers: false,
      api_keys: false,
      stats: false,
      health: false,
      config: false,
    };

    // If no stored permissions, use defaults
    if (!permissions || Object.keys(permissions).length === 0) {
      return defaultPermissions[permission] ?? false;
    }

    // Use stored permissions
    return permissions[permission] ?? false;
  }

  /**
   * Check if user can access a specific route
   * 路由权限映射：只有明确列出的路由才能访问
   */
  canAccessRoute(route: string): boolean {
    // 公开路由，任何人都可以访问（包括所有 /api/ 路由）
    const publicRoutes = ["/login", "/oauth", "/auth", "/api/"];
    if (publicRoutes.some((r) => route.startsWith(r))) {
      console.info("[Auth] canAccessRoute: public route", route);
      return true;
    }

    // 路由权限映射表 - 只有明确配置了权限的路由才能访问
    // 注意：/chat 和 / 必须分开处理，因为 '/' 是所有路径的前缀
    const routePermissions: Record<string, string[]> = {
      // 聊天
      "/chat": ["chat"],

      // 对话管理
      "/conversations": ["conversations"],

      // 用户偏好设置
      "/preferences": ["preferences"],

      // 管理后台路由
      "/admin": ["providers"],
      "/admin/users": ["providers"],

      // 需要 admin 权限的路由
      "/providers": ["providers"],
      "/api-keys": ["api_keys"],
      "/stats": ["stats"],
      "/health": ["health"],
      "/config": ["config"],

      // 首页（需要 providers 权限，普通用户默认不可访问）- 放在最后
      "/": ["providers"],
    };

    // 先检查精确匹配（处理 /chat 等）
    if (routePermissions[route]) {
      const perms = routePermissions[route];
      console.info(
        "[Auth] canAccessRoute: exact match",
        route,
        "required perms",
        perms,
      );
      const result = perms.some((perm) => this.hasPermission(perm));
      console.info("[Auth] canAccessRoute: result for", route, ":", result);
      return result;
    }

    // 再检查带参数的路由（如 /admin/users/123）
    for (const [baseRoute, perms] of Object.entries(routePermissions)) {
      // 跳过根路由 '/'，它已经在上面精确匹配处理了
      if (baseRoute === "/") continue;
      if (route.startsWith(baseRoute)) {
        console.info(
          "[Auth] canAccessRoute: param route",
          route,
          "matched",
          baseRoute,
          "required perms",
          perms,
        );
        const result = perms.some((perm) => this.hasPermission(perm));
        console.info("[Auth] canAccessRoute: result for", route, ":", result);
        return result;
      }
    }

    // 最后检查根路由
    if (route === "/") {
      const perms = routePermissions["/"];
      console.info("[Auth] canAccessRoute: root route / required perms", perms);
      const result = perms.some((perm) => this.hasPermission(perm));
      console.info("[Auth] canAccessRoute: result for /:", result);
      return result;
    }

    // 未配置的路由不允许访问
    console.info(
      "[Auth] canAccessRoute: route not configured, denying access to",
      route,
    );
    return false;
  }

  /**
   * Get the default redirect URL after login based on user permissions
   * 登录后如果有首页访问权限跳转到首页，否则跳转到 chat 页面
   */
  getDefaultRedirectUrl(): string {
    // 首页需要 providers 权限
    if (this.canAccessRoute("/")) {
      return "/";
    }
    return "/chat";
  }
}

export const authService = new AuthService();
