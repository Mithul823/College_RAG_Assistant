const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    const envUrl = import.meta.env.VITE_API_URL.trim().replace(/\/+$/, '');
    return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`;
  }
  return '/api/v1';
};

const API_BASE_URL = getApiBaseUrl();

class ApiClient {
  static getToken() {
    return localStorage.getItem('token');
  }

  static setToken(token) {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }

  static async request(endpoint, options = {}) {
    const token = this.getToken();
    const isFormData = options.body instanceof FormData;

    const headers = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const url = `${API_BASE_URL}${endpoint}`;

    try {
      // 60-second timeout to allow Render Free Tier cold starts to complete
      const response = await fetch(url, {
        signal: options.signal || (typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(60000) : undefined),
        ...options,
        headers,
      });

      if (response.status === 401) {
        this.setToken(null);
      }

      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg =
          (data && data.detail) ||
          (data && data.message) ||
          `Request failed with status ${response.status}`;
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'TimeoutError' || err.message?.includes('timed out')) {
        throw new Error('Connection timed out. Render backend may be cold-starting; please try again in a moment.');
      }
      throw err;
    }
  }

  // Auth endpoints
  static async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  }

  static async register(name, email, password) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });
    return data;
  }

  static async getMe() {
    return this.request('/auth/me', {
      method: 'GET',
    });
  }

  // Chat endpoint
  static async sendChatMessage(message, conversationId = null) {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  }

  // Conversations endpoints
  static async getConversations(skip = 0, limit = 50) {
    return this.request(`/conversations?skip=${skip}&limit=${limit}`, {
      method: 'GET',
    });
  }

  static async getConversation(conversationId) {
    return this.request(`/conversations/${conversationId}`, {
      method: 'GET',
    });
  }

  static async deleteConversation(conversationId) {
    return this.request(`/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  }

  // Document Management (Admin)
  static async uploadDocument(formData) {
    return this.request('/documents', {
      method: 'POST',
      body: formData,
    });
  }

  static async listDocuments(skip = 0, limit = 100) {
    return this.request(`/documents?skip=${skip}&limit=${limit}`, {
      method: 'GET',
    });
  }

  static async getDocument(documentId) {
    return this.request(`/documents/${documentId}`, {
      method: 'GET',
    });
  }

  static async deleteDocument(documentId) {
    return this.request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  // Admin Metrics
  static async getAdminMetrics() {
    return this.request('/admin/metrics', {
      method: 'GET',
    });
  }

  // Student Feedback & Analytics
  static async submitMessageFeedback(messageId, rating, comment = null) {
    return this.request(`/chat/messages/${messageId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ rating, comment }),
    });
  }

  static async getFeedbackAnalytics() {
    return this.request('/admin/analytics/feedback', {
      method: 'GET',
    });
  }
}

export default ApiClient;
