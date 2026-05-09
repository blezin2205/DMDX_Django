export {}

declare global {
  interface Window {
    desktop?: {
      platform: string
      isElectron: boolean
      apiRequest?: (options: {
        method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
        url: string
        data?: unknown
        headers?: Record<string, string>
      }) => Promise<{
        ok: boolean
        status?: number
        data?: unknown
        error?: string
      }>
    }
  }
}
