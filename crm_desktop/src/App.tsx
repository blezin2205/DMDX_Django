import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, MouseEvent } from 'react'
import axios from 'axios'
import './App.css'

type ApiResponse = {
  ok: boolean
  status?: number
  data?: unknown
  error?: string
}

type CrmModule = 'dashboard' | 'clients' | 'orders' | 'delivery' | 'cart' | 'deals' | 'tasks'
type SupplyRow = {
  id: number
  general_supply_id: number | null
  name: string
  package_and_tests: string | null
  category: string | null
  ref: string | null
  smn_code: string | null
  supplyLot: string | null
  count: number | null
  expiredDate: string | null
  countOnHold?: number | null
}

type CartItem = {
  id: number
  supply_id: number
  general_supply_id: number | null
  name: string
  lot: string | null
  count: number
  expiredDate: string | null
  available: number | null
  on_hold: number | null
}

type OrderListItem = {
  id: number
  dateCreated: string | null
  dateSent: string | null
  isComplete: boolean
  isPinned?: boolean
  isMerged?: boolean
  dateToSend?: string | null
  date_send_is_today?: boolean
  date_send_is_expired?: boolean
  comment?: string | null
  userCreated?: {
    id?: number | null
    full_name?: string | null
  } | null
  userSent?: {
    id?: number | null
    full_name?: string | null
  } | null
  place?: {
    id?: number
    name?: string | null
    city?: string | null
  } | null
  np?: {
    has_documents?: boolean
    documents_count?: number
    status_code?: string | null
    status_desc?: string | null
    statuses_count?: number
  } | null
}

type OrderSupplyItem = {
  name: string | null
  ref: string | null
  lot: string | null
  dateCreated: string | null
  expiredDate: string | null
  countInOrder: number | null
}

type OrderMeta = {
  id: number
  isComplete: boolean
  isPinned: boolean
  dateCreated: string | null
  dateSent: string | null
  dateToSend: string | null
  comment: string | null
  place: {
    id: number | null
    name: string | null
    city: string | null
  }
  np: {
    documents: Array<{
      id: number
      document_id: string
      estimated_time_delivery: string | null
      cost_on_site: number | null
    }>
    statuses: Array<{
      id: number
      status_code: string | null
      status_desc: string | null
      doc_number: string | null
      recipient: string | null
      scheduled_delivery: string | null
      actual_delivery: string | null
      recipient_datetime: string | null
    }>
  }
}

type OrderStatusFilter = 'all' | 'open' | 'completed'

type DeliveryBarcodeType = 'Data Matrix' | 'Siemens'

type DeliveryCatalogItem = {
  id: number
  name: string | null
  ref: string | null
  SMN_code: string | null
  category?: {
    name?: string | null
  } | null
}

type LocalScannedItem = {
  id: string
  raw: string
  barcode_type: DeliveryBarcodeType
  smn: string
  lot: string
  date_expired: string
  recognized: boolean
  matched_general_supply_id: number | null
  matched_name: string | null
  matched_ref: string | null
}

type SupplyHistoryPayload = {
  general_supply: { id: number; name: string; ref: string | null; smn_code: string | null }
  orders: Array<{ id: number; order_id: number | null; place: string | null; count: number | null; lot: string | null; date_expired: string | null; date_created: string | null }>
  preorders: Array<{ id: number; preorder_id: number | null; place: string | null; count: number | null; state: string | null }>
  deliveries: Array<{ id: number; delivery_id: number | null; count: number | null; lot: string | null; date_expired: string | null; date_created: string | null }>
  booked: Array<{ id: number; place: string | null; count: number | null; lot: string | null; date_expired: string | null; date_created: string | null }>
  totals: { orders_count: number; preorders_count: number; deliveries_count: number; booked_count: number }
}

type ProductGroup = {
  id: number
  key: string
  name: string
  packageAndTests: string
  category: string
  ref: string
  smn: string
  lots: SupplyRow[]
  totalCount: number
  totalOnHold: number
  nearestExpiry: string | null
}

type GroupSort =
  | 'name_asc'
  | 'name_desc'
  | 'count_desc'
  | 'count_asc'
  | 'expiry_asc'
  | 'expiry_desc'

type ColumnKey =
  | 'name'
  | 'package'
  | 'category'
  | 'ref'
  | 'smn'
  | 'lots'
  | 'count'
  | 'onhold'
  | 'expiry'
  | 'actions'

type ColumnConfig = Record<
  ColumnKey,
  {
    visible: boolean
    width: number
    label: string
  }
>

type SuppliesPreferences = {
  supplySearch?: string
  categoryFilter?: string
  stockFilter?: 'all' | 'with_children' | 'without_children'
  expiredOnly?: boolean
  groupSort?: GroupSort
  columns?: Partial<Record<ColumnKey, Partial<ColumnConfig[ColumnKey]>>>
}

type UserPreferences = {
  activeModule?: CrmModule
  supplies?: SuppliesPreferences
  orders?: {
    search?: string
    statusFilter?: OrderStatusFilter
  }
}

type ProfileIdentity = {
  username?: string | null
  full_name?: string | null
  first_name?: string | null
  last_name?: string | null
}

const STORAGE_KEYS = {
  profileName: 'crm_profile_name',
  authToken: 'crm_token',
  jwtToken: 'crm_jwt_token',
  cartTotalItems: 'crm_cart_total_items',
  cartTotalRows: 'crm_cart_total_rows',
  userKey: 'crm_user_key',
  userPreferences: 'crm_user_preferences_v1',
}

const DEFAULT_COLUMNS: ColumnConfig = {
  name: { visible: true, width: 260, label: 'Назва товару' },
  package: { visible: true, width: 180, label: 'Пакування / Тести' },
  category: { visible: true, width: 150, label: 'Категорія' },
  ref: { visible: true, width: 130, label: 'REF' },
  smn: { visible: true, width: 130, label: 'SMN' },
  lots: { visible: true, width: 90, label: 'Партій' },
  count: { visible: true, width: 110, label: 'К-сть' },
  onhold: { visible: true, width: 110, label: 'On Hold' },
  expiry: { visible: true, width: 130, label: 'Найближчий термін' },
  actions: { visible: true, width: 220, label: 'Дії' },
}

const ORDERS_PAGE_SIZE = 12
const SUPPLIES_PAGE_SIZE = 20

const isCrmModule = (value: string | undefined): value is CrmModule => {
  return (
    value === 'dashboard' ||
    value === 'clients' ||
    value === 'orders' ||
    value === 'delivery' ||
    value === 'cart' ||
    value === 'deals' ||
    value === 'tasks'
  )
}

const isSupplyStockFilter = (
  value: string | undefined,
): value is 'all' | 'with_children' | 'without_children' => {
  return value === 'all' || value === 'with_children' || value === 'without_children'
}

const buildProfileLabel = (profile?: ProfileIdentity | null, fallback?: string) => {
  const fullName = profile?.full_name?.trim()
  if (fullName) {
    return fullName
  }

  const firstName = profile?.first_name?.trim() ?? ''
  const lastName = profile?.last_name?.trim() ?? ''
  const fullNameByParts = `${firstName} ${lastName}`.trim()
  if (fullNameByParts) {
    return fullNameByParts
  }

  const fallbackLabel = fallback?.trim()
  if (fallbackLabel) {
    return fallbackLabel
  }

  const username = profile?.username?.trim()
  return username || 'Користувач'
}

const readJsonFromStorage = <T,>(key: string, fallback: T): T => {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) {
      return fallback
    }
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

const writeJsonToStorage = (key: string, value: unknown) => {
  localStorage.setItem(key, JSON.stringify(value))
}

const getStoredUserKey = () => localStorage.getItem(STORAGE_KEYS.userKey) ?? ''

const getUserPreferencesMap = () =>
  readJsonFromStorage<Record<string, UserPreferences>>(STORAGE_KEYS.userPreferences, {})

const getStoredUserPreferences = (): UserPreferences => {
  const userKey = getStoredUserKey()
  if (!userKey) {
    return {}
  }
  return getUserPreferencesMap()[userKey] ?? {}
}

const updateStoredUserPreferences = (
  userKey: string,
  updater: (prev: UserPreferences) => UserPreferences,
) => {
  if (!userKey) {
    return
  }
  const map = getUserPreferencesMap()
  const current = map[userKey] ?? {}
  map[userKey] = updater(current)
  writeJsonToStorage(STORAGE_KEYS.userPreferences, map)
}

const mergeColumns = (
  override?: Partial<Record<ColumnKey, Partial<ColumnConfig[ColumnKey]>>>,
): ColumnConfig => {
  const merged = { ...DEFAULT_COLUMNS }
  if (!override) {
    return merged
  }
  for (const key of Object.keys(DEFAULT_COLUMNS) as ColumnKey[]) {
    const fromStorage = override[key]
    if (!fromStorage) {
      continue
    }
    merged[key] = {
      ...DEFAULT_COLUMNS[key],
      ...fromStorage,
    }
  }
  return merged
}

function App() {
  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL ??
    (import.meta.env.DEV ? '' : 'http://127.0.0.1:8000')
  const normalizedBase = useMemo(() => apiBaseUrl.replace(/\/$/, ''), [apiBaseUrl])
  const authUrl = useMemo(() => `${normalizedBase}/api/login`, [normalizedBase])
  const healthUrl = useMemo(
    () => `${normalizedBase}/api/csrf-token/`,
    [normalizedBase],
  )
  const userProfileUrl = useMemo(
    () => `${normalizedBase}/api/profile`,
    [normalizedBase],
  )
  const cartAddUrl = useMemo(
    () => `${normalizedBase}/api/desktop/cart/add`,
    [normalizedBase],
  )
  const precartAddGeneralUrl = useMemo(
    () => `${normalizedBase}/api/desktop/precart/add-general`,
    [normalizedBase],
  )
  const lotAddUrl = useMemo(
    () => `${normalizedBase}/api/desktop/lots/add`,
    [normalizedBase],
  )
  const cartUrl = useMemo(
    () => `${normalizedBase}/api/desktop/cart`,
    [normalizedBase],
  )
  const cartCheckoutUrl = useMemo(
    () => `${normalizedBase}/api/desktop/cart/checkout`,
    [normalizedBase],
  )
  const placesUrl = useMemo(
    () => `${normalizedBase}/api/places`,
    [normalizedBase],
  )
  const desktopOrdersUrl = useMemo(
    () => `${normalizedBase}/api/desktop/orders`,
    [normalizedBase],
  )
  const desktopDeliveryUploadUrl = useMemo(
    () => `${normalizedBase}/api/desktop/deliveries/upload`,
    [normalizedBase],
  )
  const generalSuppliesUrl = useMemo(
    () => `${normalizedBase}/api/general-supplies`,
    [normalizedBase],
  )
  const ordersUrl = useMemo(
    () => `${normalizedBase}/api/orders`,
    [normalizedBase],
  )
  const supplyHistoryUrl = useMemo(
    () => `${normalizedBase}/api/desktop/supplies`,
    [normalizedBase],
  )
  const desktopSuppliesUrl = useMemo(
    () => `${normalizedBase}/api/desktop/supplies`,
    [normalizedBase],
  )
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('Готово до входу')
  const [loading, setLoading] = useState(false)
  const [currentUserKey, setCurrentUserKey] = useState(() => getStoredUserKey())
  const [activeModule, setActiveModule] = useState<CrmModule>(() => {
    const value = getStoredUserPreferences().activeModule
    return isCrmModule(value) ? value : 'dashboard'
  })
  const [profileName, setProfileName] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.profileName) ?? 'Користувач'
  })
  const [authToken, setAuthToken] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.authToken) ?? ''
  })
  const [jwtToken, setJwtToken] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.jwtToken) ?? ''
  })
  const [supplyGroups, setSupplyGroups] = useState<ProductGroup[]>([])
  const [suppliesLoading, setSuppliesLoading] = useState(false)
  const [suppliesLoaded, setSuppliesLoaded] = useState(false)
  const [suppliesTotalCount, setSuppliesTotalCount] = useState(0)
  const [suppliesTotalPages, setSuppliesTotalPages] = useState(1)
  const [suppliesPageSize, setSuppliesPageSize] = useState(SUPPLIES_PAGE_SIZE)
  const [suppliesPage, setSuppliesPage] = useState(1)
  const [categoryOptions, setCategoryOptions] = useState<string[]>([])
  const [supplySearch, setSupplySearch] = useState(
    () => getStoredUserPreferences().supplies?.supplySearch ?? '',
  )
  const [categoryFilter, setCategoryFilter] = useState(
    () => getStoredUserPreferences().supplies?.categoryFilter ?? 'all',
  )
  const [stockFilter, setStockFilter] = useState<'all' | 'with_children' | 'without_children'>(
    () => {
      const value = getStoredUserPreferences().supplies?.stockFilter
      return isSupplyStockFilter(value) ? value : 'with_children'
    },
  )
  const [expiredOnly, setExpiredOnly] = useState(
    () => getStoredUserPreferences().supplies?.expiredOnly ?? false,
  )
  const [groupSort, setGroupSort] = useState<GroupSort>(
    () => getStoredUserPreferences().supplies?.groupSort ?? 'name_asc',
  )
  const [columns, setColumns] = useState<ColumnConfig>(() =>
    mergeColumns(getStoredUserPreferences().supplies?.columns),
  )
  const [lotDraft, setLotDraft] = useState({
    mode: 'add' as 'add' | 'edit',
    supplyId: 0,
    generalSupplyId: 0,
    supplyLot: '',
    count: 0,
    expiredDate: '',
  })
  const [lotModalOpen, setLotModalOpen] = useState(false)
  const [generalDraft, setGeneralDraft] = useState({
    generalSupplyId: 0,
    name: '',
    ref: '',
    smn_code: '',
    package_and_tests: '',
  })
  const [generalModalOpen, setGeneralModalOpen] = useState(false)
  const [rowActionBusy, setRowActionBusy] = useState(false)
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [cartLoading, setCartLoading] = useState(false)
  const [cartTotals, setCartTotals] = useState(() => ({
    total_items: Number(localStorage.getItem(STORAGE_KEYS.cartTotalItems) ?? '0'),
    total_rows: Number(localStorage.getItem(STORAGE_KEYS.cartTotalRows) ?? '0'),
  }))
  const [places, setPlaces] = useState<Array<{ id: number; name: string }>>([])
  const [checkoutDraft, setCheckoutDraft] = useState({
    place_id: '',
    comment: '',
    isComplete: false,
    isPinned: false,
    dateToSend: '',
  })
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean
    x: number
    y: number
    group: ProductGroup | null
  }>({ visible: false, x: 0, y: 0, group: null })
  const [lotContextMenu, setLotContextMenu] = useState<{
    visible: boolean
    x: number
    y: number
    group: ProductGroup | null
    lot: SupplyRow | null
  }>({ visible: false, x: 0, y: 0, group: null, lot: null })
  const [historyModalOpen, setHistoryModalOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyData, setHistoryData] = useState<SupplyHistoryPayload | null>(null)
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [ordersLoading, setOrdersLoading] = useState(false)
  const [ordersLoaded, setOrdersLoaded] = useState(false)
  const [ordersTotalCount, setOrdersTotalCount] = useState(0)
  const [ordersOpenCount, setOrdersOpenCount] = useState(0)
  const [ordersCompletedCount, setOrdersCompletedCount] = useState(0)
  const [ordersTotalPages, setOrdersTotalPages] = useState(1)
  const [ordersPageSize, setOrdersPageSize] = useState(ORDERS_PAGE_SIZE)
  const [ordersSearch, setOrdersSearch] = useState(
    () => getStoredUserPreferences().orders?.search ?? '',
  )
  const [ordersStatusFilter, setOrdersStatusFilter] = useState<OrderStatusFilter>(
    () => getStoredUserPreferences().orders?.statusFilter ?? 'all',
  )
  const [openOrderTabs, setOpenOrderTabs] = useState<number[]>([])
  const [activeOrderTabId, setActiveOrderTabId] = useState<number | null>(null)
  const [ordersPage, setOrdersPage] = useState(1)
  const [orderSuppliesMap, setOrderSuppliesMap] = useState<Record<number, OrderSupplyItem[]>>({})
  const [orderSuppliesLoading, setOrderSuppliesLoading] = useState<Record<number, boolean>>({})
  const [orderTabsCache, setOrderTabsCache] = useState<Record<number, OrderListItem>>({})
  const [orderMetaMap, setOrderMetaMap] = useState<Record<number, OrderMeta>>({})
  const [orderMetaLoading, setOrderMetaLoading] = useState<Record<number, boolean>>({})
  const [orderActionLoading, setOrderActionLoading] = useState<Record<number, boolean>>({})
  const [deliveryBarcodeType, setDeliveryBarcodeType] =
    useState<DeliveryBarcodeType>('Data Matrix')
  const [deliveryScanInput, setDeliveryScanInput] = useState('')
  const [deliveryCatalog, setDeliveryCatalog] = useState<DeliveryCatalogItem[]>([])
  const [deliveryCatalogLoaded, setDeliveryCatalogLoaded] = useState(false)
  const [deliveryCatalogLoading, setDeliveryCatalogLoading] = useState(false)
  const [deliveryScannedItems, setDeliveryScannedItems] = useState<LocalScannedItem[]>([])
  const [deliveryUploadLoading, setDeliveryUploadLoading] = useState(false)

  const sidebarUserInitial = useMemo(() => {
    const normalized = profileName.trim()
    if (!normalized) {
      return 'U'
    }
    return normalized[0].toUpperCase()
  }, [profileName])
  const deliveryScanSequenceRef = useRef(0)
  const deliveryLiveBufferRef = useRef('')
  const deliveryAudioContextRef = useRef<AudioContext | null>(null)

  const isLoggedIn = Boolean(authToken || jwtToken)
  const getAuthHeaderCandidates = () => {
    const candidates: string[] = []
    if (authToken) {
      candidates.push(`Token ${authToken}`)
    }
    if (jwtToken) {
      candidates.push(`Bearer ${jwtToken}`)
    }
    return candidates
  }

  const formatResponseError = (response: ApiResponse) => {
    if (typeof response.data === 'string') {
      return response.data
    }
    if (response.data && typeof response.data === 'object') {
      return JSON.stringify(response.data)
    }
    return response.error ?? 'Unknown error'
  }

  const requestWithAuth = async (
    method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
    url: string,
    data?: unknown,
  ) => {
    const authCandidates = getAuthHeaderCandidates()
    if (!authCandidates.length) {
      return { ok: false, error: 'No auth credentials' } as ApiResponse
    }

    let response: ApiResponse = { ok: false, error: 'Auth request failed' }
    for (const candidate of authCandidates) {
      response = await requestApi(method, url, data, {
        Authorization: candidate,
      })
      if (response.ok) {
        break
      }
    }
    return response
  }

  const filteredGroups = supplyGroups
  const totalSuppliesPagesSafe = Math.max(1, suppliesTotalPages)
  const safeSuppliesPage = Math.min(Math.max(suppliesPage, 1), totalSuppliesPagesSafe)

  const totalOrdersPagesSafe = Math.max(1, ordersTotalPages)
  const safeOrdersPage = Math.min(Math.max(ordersPage, 1), totalOrdersPagesSafe)
  const pagedOrders = orders

  const selectedOrder = useMemo(() => {
    if (activeOrderTabId === null) {
      return null
    }
    return orders.find((item) => item.id === activeOrderTabId) ?? orderTabsCache[activeOrderTabId] ?? null
  }, [orders, activeOrderTabId, orderTabsCache])
  const truncateTabLabel = (value: string, maxLength = 50) => {
    if (value.length <= maxLength) {
      return value
    }
    return `${value.slice(0, maxLength - 1)}…`
  }

  const deliveryCatalogBySmn = useMemo(() => {
    const map = new Map<string, DeliveryCatalogItem>()
    for (const item of deliveryCatalog) {
      const smn = (item.SMN_code ?? '').trim()
      if (smn) {
        map.set(smn, item)
      }
    }
    return map
  }, [deliveryCatalog])

  const deliveryCatalogByRef = useMemo(() => {
    const map = new Map<string, DeliveryCatalogItem>()
    for (const item of deliveryCatalog) {
      const ref = (item.ref ?? '').trim()
      if (ref) {
        map.set(ref, item)
      }
    }
    return map
  }, [deliveryCatalog])

  const parseScannedBarcode = (
    rawValue: string,
    barcodeType: DeliveryBarcodeType,
  ): { smn: string; lot: string; date_expired: string } => {
    const raw = rawValue.trim()
    if (!raw) {
      return { smn: '', lot: '', date_expired: '' }
    }
    if (barcodeType === 'Siemens') {
      const byComma = raw.split(',')
      if (byComma.length === 3) {
        return {
          smn: byComma[0]?.trim() ?? '',
          lot: byComma[1]?.trim() ?? '',
          date_expired: byComma[2]?.trim() ?? '',
        }
      }
      const smn = raw.slice(32, -6).slice(-8)
      const lot = raw.slice(18, -25)
      const date_expired = raw.slice(23, -17).slice(-6)
      return { smn, lot, date_expired }
    }

    let work = raw
    let gtin = ''
    let date_expired = ''
    let lot = ''
    let smnFound = ''

    if (work.startsWith('01')) {
      gtin = work.slice(2, 16)
      work = work.slice(16)
    } else {
      const m01 = work.match(/(?:^|[^0-9])01(\d{14})/)
      if (m01?.[1]) {
        gtin = m01[1]
        work = work.replace(m01[0], '|')
      }
    }

    const m17 = work.match(/17(\d{6})/)
    if (m17?.[1]) {
      date_expired = m17[1]
      work = work.replace(m17[0], '|')
    }

    const m11 = work.match(/11(\d{6})/)
    if (m11?.[1]) {
      work = work.replace(m11[0], '|')
    }

    const m240 = work.match(/240([A-Za-z0-9]+?)(?:\||422|$)/)
    if (m240?.[1]) {
      smnFound = m240[1]
      work = work.replace(m240[0], '|')
    }

    const m10 = work.match(/10([A-Za-z0-9]+?)(?:\||$)/)
    if (m10?.[1]) {
      lot = m10[1]
    }

    return { smn: smnFound || gtin, lot, date_expired }
  }

  const requestApi = async (
    method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
    url: string,
    data?: unknown,
    headers?: Record<string, string>,
  ): Promise<ApiResponse> => {
    const isAbsoluteHttpUrl = /^https?:\/\//i.test(url)
    const electronApiRequest = window.desktop?.apiRequest
    const shouldUseElectronIpc =
      window.desktop?.isElectron &&
      electronApiRequest &&
      (!import.meta.env.DEV || isAbsoluteHttpUrl)

    if (shouldUseElectronIpc && electronApiRequest) {
      return electronApiRequest({ method, url, data, headers })
    }

    try {
      const response = await axios({
        method,
        url,
        data,
        headers,
        timeout: 10000,
      })
      return { ok: true, status: response.status, data: response.data }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        return {
          ok: false,
          status: error.response.status,
          data: error.response.data,
        }
      }
      return { ok: false, error: 'Network error' }
    }
  }

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    try {
      setLoading(true)
      setMessage('Виконується вхід...')
      const response = await requestApi('POST', authUrl, { username, password })

      if (!response.ok) {
        if (response.status) {
          const backendMessage =
            typeof response.data === 'string'
              ? response.data
              : JSON.stringify(response.data ?? {})
          setMessage(`Помилка входу (${response.status}): ${backendMessage}`)
        } else {
          setMessage(
            'Не вдалося підключитися до Django API. Перевірте запуск сервера та адресу API.',
          )
        }
        return
      }

      const payload =
        typeof response.data === 'object' && response.data !== null ? response.data : {}
      const token = (payload as { token?: string }).token
      const jwtToken = (payload as { jwt_token?: string }).jwt_token
      const profile = (payload as { user?: ProfileIdentity }).user

      if (token || jwtToken) {
        const profileLabel = buildProfileLabel(profile, username)
        setProfileName(profileLabel)
        const userKey = (profile?.username || username).trim().toLowerCase()
        const userPreferences = getUserPreferencesMap()[userKey] ?? {}
        applyUserPreferences(userPreferences)
        setCurrentUserKey(userKey)
        localStorage.setItem(STORAGE_KEYS.userKey, userKey)
        localStorage.setItem(STORAGE_KEYS.profileName, profileLabel)

        if (token) {
          setAuthToken(token)
          localStorage.setItem(STORAGE_KEYS.authToken, token)
        }

        if (jwtToken) {
          setJwtToken(jwtToken)
          localStorage.setItem(STORAGE_KEYS.jwtToken, jwtToken)
        }

        setMessage('Успішний вхід. Токен отримано, CRM готова до інтеграції.')
        void loadCart()
        void loadPlaces()
      } else {
        setMessage(
          'Вхід пройшов, але токен не знайдено. Перевірте формат відповіді API.',
        )
      }
    } catch {
      setMessage('Невідома помилка при вході.')
    } finally {
      setLoading(false)
    }
  }

  const checkConnection = async () => {
    try {
      setLoading(true)
      setMessage('Перевіряю з’єднання з сервером...')
      const response = await requestApi('GET', healthUrl)
      if (response.ok) {
        setMessage('Сервер доступний. Онлайн-режим працює.')
      } else if (response.status) {
        setMessage(
          `Сервер відповів з помилкою (${response.status}). Перевірте URL: ${healthUrl}`,
        )
      } else {
        setMessage(
          'Сервер недоступний. Перевірте запуск Django: python3 manage.py runserver',
        )
      }
    } catch {
      setMessage('Сервер недоступний. Перевірте URL API або запуск Django.')
    } finally {
      setLoading(false)
    }
  }

  const fetchProfile = async () => {
    if (!getAuthHeaderCandidates().length) {
      setMessage('Немає токена для завантаження профілю.')
      return
    }

    setLoading(true)
    setMessage('Оновлюю профіль...')
    const response = await requestWithAuth('GET', userProfileUrl)
    setLoading(false)

    if (!response.ok) {
      if (response.status) {
        setMessage(`Не вдалося отримати профіль (${response.status}): ${formatResponseError(response)}`)
      } else {
        setMessage('Не вдалося отримати профіль користувача.')
      }
      return
    }

    const payload =
      typeof response.data === 'object' && response.data !== null ? response.data : {}
    const label = buildProfileLabel(payload as ProfileIdentity, profileName)
    setProfileName(label)
    localStorage.setItem(STORAGE_KEYS.profileName, label)
    setMessage('Профіль оновлено.')
  }

  const loadSupplies = async (params?: {
    page?: number
    search?: string
    category?: string
    stock?: 'all' | 'with_children' | 'without_children'
    expiredOnly?: boolean
    sort?: GroupSort
  }) => {
    if (!getAuthHeaderCandidates().length) {
      setMessage('Немає токена для завантаження товарів.')
      return
    }

    const targetPage = params?.page ?? suppliesPage
    const targetSearch = (params?.search ?? supplySearch).trim()
    const targetCategory = params?.category ?? categoryFilter
    const targetStock = params?.stock ?? stockFilter
    const targetExpiredOnly = params?.expiredOnly ?? expiredOnly
    const targetSort = params?.sort ?? groupSort
    const query = new URLSearchParams()
    query.set('page', String(targetPage))
    query.set('page_size', String(SUPPLIES_PAGE_SIZE))
    query.set('sort', targetSort)
    if (targetSearch) {
      query.set('q', targetSearch)
    }
    if (targetCategory !== 'all') {
      query.set('category', targetCategory)
    }
    if (targetStock !== 'all') {
      query.set('availability', targetStock)
    }
    if (targetExpiredOnly) {
      query.set('expired_only', '1')
    }

    setSuppliesLoading(true)
    const response = await requestWithAuth('GET', `${desktopSuppliesUrl}?${query.toString()}`)
    setSuppliesLoading(false)

    if (!response.ok) {
      if (response.status) {
        setMessage(`Не вдалося завантажити список товарів (${response.status}): ${formatResponseError(response)}`)
      } else {
        setMessage('Не вдалося завантажити список товарів.')
      }
      return
    }

    const payload = (response.data ?? {}) as {
      count?: number
      page?: number
      page_size?: number
      total_pages?: number
      results?: ProductGroup[]
      category_options?: string[]
    }

    if (!Array.isArray(payload.results)) {
      setMessage('Отримано неочікуваний формат списку товарів.')
      return
    }

    const results = payload.results
    setSupplyGroups(results)
    setSuppliesTotalCount(payload.count ?? results.length)
    setSuppliesTotalPages(Math.max(1, payload.total_pages ?? 1))
    setSuppliesPageSize(payload.page_size ?? SUPPLIES_PAGE_SIZE)
    setSuppliesPage(payload.page ?? targetPage)
    setCategoryOptions(
      Array.isArray(payload.category_options)
        ? payload.category_options.filter((item): item is string => Boolean(item))
        : [],
    )
    setSuppliesLoaded(true)
    setMessage(`Завантажено груп товарів: ${results.length}`)
  }

  const loadPlaces = async () => {
    const response = await requestWithAuth('GET', placesUrl)
    if (!response.ok || !Array.isArray(response.data)) {
      return
    }
    const options = (response.data as Array<{ id: number; name: string }>).map((item) => ({
      id: item.id,
      name: item.name,
    }))
    setPlaces(options)
    if (!checkoutDraft.place_id && options.length > 0) {
      setCheckoutDraft((prev) => ({ ...prev, place_id: String(options[0].id) }))
    }
  }

  const loadCart = async () => {
    if (!getAuthHeaderCandidates().length) {
      setMessage('Немає токена для завантаження корзини.')
      return
    }
    setCartLoading(true)
    const response = await requestWithAuth('GET', cartUrl)
    setCartLoading(false)
    if (!response.ok) {
      setMessage(`Не вдалося завантажити корзину: ${formatResponseError(response)}`)
      return
    }

    const payload = (response.data ?? {}) as {
      items?: CartItem[]
      total_items?: number
      total_rows?: number
    }
    setCartItems(Array.isArray(payload.items) ? payload.items : [])
    const nextTotals = {
      total_items: payload.total_items ?? 0,
      total_rows: payload.total_rows ?? 0,
    }
    setCartTotals(nextTotals)
    localStorage.setItem(STORAGE_KEYS.cartTotalItems, String(nextTotals.total_items))
    localStorage.setItem(STORAGE_KEYS.cartTotalRows, String(nextTotals.total_rows))
  }

  const loadOrders = async (params?: {
    page?: number
    search?: string
    status?: OrderStatusFilter
  }) => {
    if (!getAuthHeaderCandidates().length) {
      setMessage('Немає токена для завантаження замовлень.')
      return
    }
    const targetPage = params?.page ?? ordersPage
    const targetSearch = (params?.search ?? ordersSearch).trim()
    const targetStatus = params?.status ?? ordersStatusFilter
    const query = new URLSearchParams()
    query.set('page', String(targetPage))
    query.set('page_size', String(ORDERS_PAGE_SIZE))
    if (targetSearch) {
      query.set('q', targetSearch)
    }
    if (targetStatus !== 'all') {
      query.set('status', targetStatus)
    }

    setOrdersLoading(true)
    const response = await requestWithAuth('GET', `${ordersUrl}?${query.toString()}`)
    setOrdersLoading(false)
    if (!response.ok) {
      setMessage(`Не вдалося завантажити замовлення: ${formatResponseError(response)}`)
      return
    }
    const payload = (response.data ?? {}) as {
      count?: number
      open_count?: number
      completed_count?: number
      page?: number
      page_size?: number
      total_pages?: number
      results?: OrderListItem[]
    }
    if (!Array.isArray(payload.results)) {
      setMessage('Отримано неочікуваний формат списку замовлень.')
      return
    }
    const results = payload.results
    setOrders(results)
    setOrderTabsCache((prev) => {
      const next = { ...prev }
      for (const order of results) {
        next[order.id] = order
      }
      return next
    })
    setOrdersTotalCount(payload.count ?? results.length)
    setOrdersOpenCount(payload.open_count ?? results.filter((item) => !item.isComplete).length)
    setOrdersCompletedCount(
      payload.completed_count ?? results.filter((item) => item.isComplete).length,
    )
    setOrdersTotalPages(Math.max(1, payload.total_pages ?? 1))
    setOrdersPageSize(payload.page_size ?? ORDERS_PAGE_SIZE)
    if (payload.page && payload.page !== ordersPage) {
      setOrdersPage(payload.page)
    }
    setOrdersLoaded(true)
  }

  const loadOrderSupplies = async (orderId: number, force = false) => {
    if (!force && orderSuppliesMap[orderId]) {
      return
    }
    setOrderSuppliesLoading((prev) => ({ ...prev, [orderId]: true }))
    const response = await requestWithAuth('GET', `${ordersUrl}/${orderId}`)
    setOrderSuppliesLoading((prev) => ({ ...prev, [orderId]: false }))
    if (!response.ok) {
      setMessage(`Не вдалося завантажити позиції замовлення №${orderId}: ${formatResponseError(response)}`)
      return
    }
    if (!Array.isArray(response.data)) {
      setMessage(`Некоректний формат позицій замовлення №${orderId}.`)
      return
    }
    setOrderSuppliesMap((prev) => ({
      ...prev,
      [orderId]: response.data as OrderSupplyItem[],
    }))
  }

  const loadOrderMeta = async (orderId: number, force = false) => {
    if (!force && orderMetaMap[orderId]) {
      return
    }
    setOrderMetaLoading((prev) => ({ ...prev, [orderId]: true }))
    const response = await requestWithAuth('GET', `${desktopOrdersUrl}/${orderId}/meta`)
    setOrderMetaLoading((prev) => ({ ...prev, [orderId]: false }))
    if (!response.ok) {
      setMessage(`Не вдалося завантажити мета-дані замовлення №${orderId}: ${formatResponseError(response)}`)
      return
    }
    setOrderMetaMap((prev) => ({
      ...prev,
      [orderId]: response.data as OrderMeta,
    }))
    const meta = response.data as OrderMeta
    setOrderTabsCache((prev) => ({
      ...prev,
      [orderId]: {
        ...(prev[orderId] ?? {
          id: meta.id,
          dateCreated: meta.dateCreated,
          dateSent: meta.dateSent,
          isComplete: meta.isComplete,
        }),
        isComplete: meta.isComplete,
        isPinned: meta.isPinned,
        dateCreated: meta.dateCreated,
        dateSent: meta.dateSent,
        dateToSend: meta.dateToSend,
        comment: meta.comment,
        place: {
          id: meta.place.id ?? undefined,
          name: meta.place.name,
          city: meta.place.city,
        },
      },
    }))
  }

  const loadDeliveryCatalog = async () => {
    if (deliveryCatalogLoading) {
      return
    }
    setDeliveryCatalogLoading(true)
    const aggregated: DeliveryCatalogItem[] = []
    let page = 1
    const pageSize = 1000

    while (true) {
      const response = await requestWithAuth(
        'GET',
        `${generalSuppliesUrl}?page=${page}&page_size=${pageSize}`,
      )
      if (!response.ok) {
        setDeliveryCatalogLoading(false)
        setMessage(`Не вдалося завантажити каталог для сканування: ${formatResponseError(response)}`)
        return
      }
      const payload = (response.data ?? {}) as {
        results?: DeliveryCatalogItem[]
        next?: string | null
      }
      if (!Array.isArray(payload.results)) {
        setDeliveryCatalogLoading(false)
        setMessage('Некоректний формат каталогу для сканування.')
        return
      }
      aggregated.push(...payload.results)
      if (!payload.next) {
        break
      }
      page += 1
    }

    setDeliveryCatalog(aggregated)
    setDeliveryCatalogLoaded(true)
    setDeliveryCatalogLoading(false)
    setMessage(`Каталог для сканування завантажено: ${aggregated.length} позицій.`)
  }

  const playScanFeedback = useCallback((recognized: boolean) => {
    try {
      const AudioCtx = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!AudioCtx) {
        return
      }
      if (!deliveryAudioContextRef.current) {
        deliveryAudioContextRef.current = new AudioCtx()
      }
      const ctx = deliveryAudioContextRef.current
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()

      oscillator.type = 'sine'
      oscillator.frequency.value = recognized ? 1080 : 320
      gain.gain.value = 0.001

      oscillator.connect(gain)
      gain.connect(ctx.destination)

      const now = ctx.currentTime
      gain.gain.exponentialRampToValueAtTime(0.08, now + 0.01)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + (recognized ? 0.09 : 0.14))

      oscillator.start(now)
      oscillator.stop(now + (recognized ? 0.1 : 0.16))
    } catch {
      // Audio feedback is optional; ignore errors on unsupported platforms.
    }
  }, [])

  const registerScannedValue = useCallback((rawValue: string) => {
    const raw = rawValue.trim()
    if (!raw) {
      return
    }
    const parsed = parseScannedBarcode(raw, deliveryBarcodeType)
    const match =
      deliveryCatalogBySmn.get(parsed.smn) ??
      deliveryCatalogByRef.get(parsed.smn) ??
      null

    deliveryScanSequenceRef.current += 1
    const sequenceId = deliveryScanSequenceRef.current
    const entry: LocalScannedItem = {
      id: `scan-${sequenceId}`,
      raw,
      barcode_type: deliveryBarcodeType,
      smn: parsed.smn,
      lot: parsed.lot,
      date_expired: parsed.date_expired,
      recognized: Boolean(match),
      matched_general_supply_id: match?.id ?? null,
      matched_name: match?.name ?? null,
      matched_ref: match?.ref ?? null,
    }
    setDeliveryScannedItems((prev) => [entry, ...prev])
    playScanFeedback(Boolean(match))
  }, [deliveryBarcodeType, deliveryCatalogBySmn, deliveryCatalogByRef, playScanFeedback])

  const uploadDeliveryFromLocalScan = async () => {
    if (!deliveryScannedItems.length) {
      setMessage('Список сканувань порожній.')
      return
    }
    setDeliveryUploadLoading(true)
    const response = await requestWithAuth('POST', desktopDeliveryUploadUrl, {
      barcode_type: deliveryBarcodeType,
      scans: deliveryScannedItems.map((item) => item.raw),
    })
    setDeliveryUploadLoading(false)
    if (!response.ok) {
      setMessage(`Не вдалося завантажити поставку: ${formatResponseError(response)}`)
      return
    }
    const payload = (response.data ?? {}) as {
      delivery_order_id?: number
      recognized_count?: number
      unrecognized_count?: number
      total_requests?: number
    }
    setMessage(
      `Поставка №${payload.delivery_order_id ?? '-'} створена. Розпізнано: ${payload.recognized_count ?? 0}, не розпізнано: ${payload.unrecognized_count ?? 0}, сканів: ${payload.total_requests ?? deliveryScannedItems.length}.`,
    )
    setDeliveryScannedItems([])
  }

  const toggleOrderPinned = async (orderId: number, nextPinned: boolean) => {
    setOrderActionLoading((prev) => ({ ...prev, [orderId]: true }))
    const response = await requestWithAuth('POST', `${desktopOrdersUrl}/${orderId}/pin`, {
      isPinned: nextPinned,
    })
    setOrderActionLoading((prev) => ({ ...prev, [orderId]: false }))
    if (!response.ok) {
      setMessage(`Не вдалося оновити закріплення: ${formatResponseError(response)}`)
      return
    }
    await loadOrders()
    await loadOrderMeta(orderId, true)
  }

  const completeOrder = async (orderId: number) => {
    setOrderActionLoading((prev) => ({ ...prev, [orderId]: true }))
    const response = await requestWithAuth('POST', `${desktopOrdersUrl}/${orderId}/complete`)
    setOrderActionLoading((prev) => ({ ...prev, [orderId]: false }))
    if (!response.ok) {
      setMessage(`Не вдалося завершити замовлення: ${formatResponseError(response)}`)
      return
    }
    setMessage(`Замовлення №${orderId} завершено.`)
    await loadOrders()
    await loadOrderMeta(orderId, true)
  }

  const refreshOrderNpStatus = async (orderId: number) => {
    setOrderActionLoading((prev) => ({ ...prev, [orderId]: true }))
    const response = await requestWithAuth('POST', `${desktopOrdersUrl}/${orderId}/np-refresh`)
    setOrderActionLoading((prev) => ({ ...prev, [orderId]: false }))
    if (!response.ok) {
      setMessage(`Не вдалося оновити статус НП: ${formatResponseError(response)}`)
      return
    }
    const statuses = ((response.data as { statuses?: OrderMeta['np']['statuses'] }).statuses ?? [])
    setOrderMetaMap((prev) => {
      const current = prev[orderId]
      if (!current) {
        return prev
      }
      return {
        ...prev,
        [orderId]: {
          ...current,
          np: {
            ...current.np,
            statuses,
          },
        },
      }
    })
    await loadOrders()
  }

  const updateCartItem = async (itemId: number, action: 'plus' | 'minus') => {
    setCartLoading(true)
    const response = await requestWithAuth(
      'PATCH',
      `${normalizedBase}/api/desktop/cart/items/${itemId}`,
      { action },
    )
    setCartLoading(false)
    if (!response.ok) {
      setMessage(`Не вдалося оновити позицію: ${formatResponseError(response)}`)
      return
    }
    await loadCart()
  }

  const removeCartItem = async (itemId: number) => {
    setCartLoading(true)
    const response = await requestWithAuth(
      'DELETE',
      `${normalizedBase}/api/desktop/cart/items/${itemId}`,
    )
    setCartLoading(false)
    if (!response.ok) {
      setMessage(`Не вдалося видалити позицію: ${formatResponseError(response)}`)
      return
    }
    await loadCart()
  }

  const checkoutCart = async () => {
    if (!checkoutDraft.place_id) {
      setMessage('Оберіть організацію перед оформленням.')
      return
    }
    setCartLoading(true)
    const response = await requestWithAuth('POST', cartCheckoutUrl, {
      place_id: Number(checkoutDraft.place_id),
      comment: checkoutDraft.comment,
      isComplete: checkoutDraft.isComplete,
      isPinned: checkoutDraft.isPinned,
      dateToSend: checkoutDraft.dateToSend || null,
    })
    setCartLoading(false)
    if (!response.ok) {
      setMessage(`Не вдалося оформити корзину: ${formatResponseError(response)}`)
      return
    }
    const orderId = (response.data as { order_id?: number }).order_id
    setMessage(`Корзину оформлено. Замовлення №${orderId ?? '-'}.`)
    setCartItems([])
    setCartTotals({ total_items: 0, total_rows: 0 })
    localStorage.setItem(STORAGE_KEYS.cartTotalItems, '0')
    localStorage.setItem(STORAGE_KEYS.cartTotalRows, '0')
  }

  const addLotToCart = async (supplyId: number) => {
    setRowActionBusy(true)
    const response = await requestWithAuth('POST', cartAddUrl, { supply_id: supplyId, quantity: 1 })
    setRowActionBusy(false)
    if (!response.ok) {
      setMessage(`Не вдалося додати в кошик: ${formatResponseError(response)}`)
      return
    }
    const count = (response.data as { in_cart_count?: number })?.in_cart_count
    setMessage(`Додано в кошик. Кількість у кошику: ${count ?? 0}`)
    await loadCart()
  }

  const addGeneralToPrecart = async (generalSupplyId: number) => {
    setRowActionBusy(true)
    const response = await requestWithAuth('POST', precartAddGeneralUrl, {
      general_supply_id: generalSupplyId,
      quantity: 1,
    })
    setRowActionBusy(false)
    if (!response.ok) {
      setMessage(`Не вдалося додати в передзамовлення: ${formatResponseError(response)}`)
      return
    }
    const count = (response.data as { in_precart_count?: number })?.in_precart_count
    setMessage(`Додано в передзамовлення. Позицій: ${count ?? 0}`)
  }

  const openAddLotModal = (generalSupplyId: number) => {
    setLotDraft({
      mode: 'add',
      supplyId: 0,
      generalSupplyId,
      supplyLot: '',
      count: 1,
      expiredDate: '',
    })
    setLotModalOpen(true)
  }

  const openEditLotModal = (lot: SupplyRow) => {
    setLotDraft({
      mode: 'edit',
      supplyId: lot.id,
      generalSupplyId: lot.general_supply_id ?? 0,
      supplyLot: lot.supplyLot ?? '',
      count: lot.count ?? 0,
      expiredDate: lot.expiredDate ?? '',
    })
    setLotModalOpen(true)
  }

  const saveLotDraft = async () => {
    setRowActionBusy(true)
    const payload = {
      general_supply_id: lotDraft.generalSupplyId,
      supplyLot: lotDraft.supplyLot,
      count: lotDraft.count,
      expiredDate: lotDraft.expiredDate || null,
    }

    const response =
      lotDraft.mode === 'add'
        ? await requestWithAuth('POST', lotAddUrl, payload)
        : await requestWithAuth('PATCH', `${normalizedBase}/api/desktop/lots/${lotDraft.supplyId}`, payload)
    setRowActionBusy(false)

    if (!response.ok) {
      setMessage(`Не вдалося зберегти LOT: ${formatResponseError(response)}`)
      return
    }

    setLotModalOpen(false)
    setMessage(lotDraft.mode === 'add' ? 'LOT додано.' : 'LOT оновлено.')
    await loadSupplies()
  }

  const deleteLot = async (supplyId: number) => {
    setRowActionBusy(true)
    const response = await requestWithAuth('DELETE', `${normalizedBase}/api/desktop/lots/${supplyId}`)
    setRowActionBusy(false)
    if (!response.ok) {
      setMessage(`Не вдалося видалити LOT: ${formatResponseError(response)}`)
      return
    }
    setMessage('LOT видалено.')
    await loadSupplies()
  }

  const openEditGeneralModal = (group: ProductGroup) => {
    const generalSupplyId = group.id
    if (!generalSupplyId) {
      setMessage('Не вдалося визначити ID товару для редагування.')
      return
    }
    setGeneralDraft({
      generalSupplyId,
      name: group.name === '-' ? '' : group.name,
      ref: group.ref === '-' ? '' : group.ref,
      smn_code: group.smn === '-' ? '' : group.smn,
      package_and_tests: group.packageAndTests === '-' ? '' : group.packageAndTests,
    })
    setGeneralModalOpen(true)
  }

  const saveGeneralDraft = async () => {
    setRowActionBusy(true)
    const response = await requestWithAuth(
      'PATCH',
      `${normalizedBase}/api/desktop/general-supplies/${generalDraft.generalSupplyId}`,
      {
        name: generalDraft.name,
        ref: generalDraft.ref,
        smn_code: generalDraft.smn_code,
        package_and_tests: generalDraft.package_and_tests,
      },
    )
    setRowActionBusy(false)

    if (!response.ok) {
      setMessage(`Не вдалося оновити товар: ${formatResponseError(response)}`)
      return
    }
    setGeneralModalOpen(false)
    setMessage('Товар оновлено.')
    await loadSupplies()
  }

  const logout = () => {
    setAuthToken('')
    setJwtToken('')
    setProfileName('Користувач')
    setCurrentUserKey('')
    localStorage.removeItem(STORAGE_KEYS.authToken)
    localStorage.removeItem(STORAGE_KEYS.jwtToken)
    localStorage.removeItem(STORAGE_KEYS.profileName)
    localStorage.removeItem(STORAGE_KEYS.cartTotalItems)
    localStorage.removeItem(STORAGE_KEYS.cartTotalRows)
    localStorage.removeItem(STORAGE_KEYS.userKey)
    setActiveModule('dashboard')
    setSupplyGroups([])
    setSuppliesLoaded(false)
    setSuppliesTotalCount(0)
    setSuppliesTotalPages(1)
    setSuppliesPageSize(SUPPLIES_PAGE_SIZE)
    setSuppliesPage(1)
    setCategoryOptions([])
    setOrders([])
    setOrdersLoaded(false)
    setOrdersTotalCount(0)
    setOrdersOpenCount(0)
    setOrdersCompletedCount(0)
    setOrdersTotalPages(1)
    setOrdersPageSize(ORDERS_PAGE_SIZE)
    setOpenOrderTabs([])
    setActiveOrderTabId(null)
    setOrdersPage(1)
    setOrderSuppliesMap({})
    setOrderTabsCache({})
    setOrderMetaMap({})
    setDeliveryCatalog([])
    setDeliveryCatalogLoaded(false)
    setDeliveryCatalogLoading(false)
    setDeliveryScanInput('')
    setDeliveryScannedItems([])
    setCartItems([])
    setCartTotals({ total_items: 0, total_rows: 0 })
    setMessage('Вихід виконано.')
  }

  const openSuppliesModule = () => {
    setActiveModule('clients')
    if (!suppliesLoaded && !suppliesLoading) {
      void loadSupplies()
    }
  }

  const openOrdersModule = () => {
    setActiveModule('orders')
    if (!ordersLoaded && !ordersLoading) {
      void loadOrders({ page: ordersPage })
    }
  }

  const openDeliveryModule = () => {
    setActiveModule('delivery')
    if (!deliveryCatalogLoaded && !deliveryCatalogLoading) {
      void loadDeliveryCatalog()
    }
  }

  const openOrderDetails = (orderId: number) => {
    const orderFromPage = orders.find((item) => item.id === orderId)
    if (orderFromPage) {
      setOrderTabsCache((prev) => ({ ...prev, [orderId]: orderFromPage }))
    }
    setOpenOrderTabs((prev) => (prev.includes(orderId) ? prev : [...prev, orderId]))
    setActiveOrderTabId(orderId)
    void loadOrderSupplies(orderId)
    void loadOrderMeta(orderId)
  }

  const backToOrdersList = () => {
    setActiveOrderTabId(null)
  }

  const closeOrderTab = (orderId: number) => {
    const currentTabs = [...openOrderTabs]
    const tabIndex = currentTabs.indexOf(orderId)
    const nextTabs = currentTabs.filter((id) => id !== orderId)
    setOpenOrderTabs(nextTabs)
    setOrderTabsCache((prev) => {
      const next = { ...prev }
      delete next[orderId]
      return next
    })

    if (activeOrderTabId !== orderId) {
      return
    }
    if (!nextTabs.length) {
      setActiveOrderTabId(null)
      return
    }
    const fallbackIndex = Math.max(0, Math.min(tabIndex, nextTabs.length - 1))
    setActiveOrderTabId(nextTabs[fallbackIndex] ?? null)
  }

  const closeAllOrderTabs = () => {
    setOpenOrderTabs([])
    setActiveOrderTabId(null)
    setOrderTabsCache({})
  }

  const openCartModule = () => {
    setActiveModule('cart')
    void loadCart()
    if (places.length === 0) {
      void loadPlaces()
    }
  }

  const openGroupContextMenu = (event: MouseEvent<HTMLTableRowElement>, group: ProductGroup) => {
    event.preventDefault()
    setLotContextMenu({ visible: false, x: 0, y: 0, group: null, lot: null })
    setContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      group,
    })
  }

  const openLotContextMenu = (
    event: MouseEvent<HTMLTableRowElement>,
    group: ProductGroup,
    lot: SupplyRow,
  ) => {
    event.preventDefault()
    setContextMenu({ visible: false, x: 0, y: 0, group: null })
    setLotContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      group,
      lot,
    })
  }

  const closeContextMenu = () => {
    setContextMenu({ visible: false, x: 0, y: 0, group: null })
  }

  const closeLotContextMenu = () => {
    setLotContextMenu({ visible: false, x: 0, y: 0, group: null, lot: null })
  }

  const openSupplyHistory = async (group: ProductGroup) => {
    const generalSupplyId = group.id
    if (!generalSupplyId) {
      setMessage('Не вдалося визначити товар для історії.')
      return
    }

    closeContextMenu()
    setHistoryModalOpen(true)
    setHistoryLoading(true)
    const response = await requestWithAuth(
      'GET',
      `${supplyHistoryUrl}/${generalSupplyId}/history`,
    )
    setHistoryLoading(false)

    if (!response.ok) {
      setMessage(`Не вдалося завантажити історію: ${formatResponseError(response)}`)
      setHistoryData(null)
      return
    }

    setHistoryData(response.data as SupplyHistoryPayload)
  }

  const toggleColumnVisibility = (column: ColumnKey) => {
    setColumns((prev) => ({
      ...prev,
      [column]: {
        ...prev[column],
        visible: !prev[column].visible,
      },
    }))
  }

  const changeColumnWidth = (column: ColumnKey, width: number) => {
    setColumns((prev) => ({
      ...prev,
      [column]: {
        ...prev[column],
        width,
      },
    }))
  }

  const applyUserPreferences = (preferences: UserPreferences) => {
    setActiveModule(
      isCrmModule(preferences.activeModule) ? preferences.activeModule : 'dashboard',
    )
    setSupplySearch(preferences.supplies?.supplySearch ?? '')
    setCategoryFilter(preferences.supplies?.categoryFilter ?? 'all')
    setStockFilter(
      isSupplyStockFilter(preferences.supplies?.stockFilter)
        ? preferences.supplies?.stockFilter
        : 'with_children',
    )
    setExpiredOnly(preferences.supplies?.expiredOnly ?? false)
    setGroupSort(preferences.supplies?.groupSort ?? 'name_asc')
    setSuppliesPage(1)
    setColumns(mergeColumns(preferences.supplies?.columns))
    setOrdersSearch(preferences.orders?.search ?? '')
    setOrdersStatusFilter(preferences.orders?.statusFilter ?? 'all')
    setOrdersPage(1)
    setOpenOrderTabs([])
    setActiveOrderTabId(null)
  }

  useEffect(() => {
    if (!contextMenu.visible && !lotContextMenu.visible) {
      return
    }

    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeContextMenu()
        closeLotContextMenu()
      }
    }

    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
    }
  }, [contextMenu.visible, lotContextMenu.visible])

  useEffect(() => {
    if (activeModule !== 'delivery') {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return
      }
      if (event.key === 'Escape') {
        deliveryLiveBufferRef.current = ''
        setDeliveryScanInput('')
        return
      }
      if (event.key === 'Enter') {
        const value = deliveryLiveBufferRef.current.trim()
        if (value) {
          registerScannedValue(value)
          deliveryLiveBufferRef.current = ''
          setDeliveryScanInput('')
          event.preventDefault()
        }
        return
      }
      if (event.key.length === 1) {
        deliveryLiveBufferRef.current += event.key
        setDeliveryScanInput(deliveryLiveBufferRef.current)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [
    activeModule,
    deliveryBarcodeType,
    deliveryCatalogBySmn,
    deliveryCatalogByRef,
    registerScannedValue,
  ])

  useEffect(() => {
    if (!currentUserKey) {
      return
    }
    updateStoredUserPreferences(currentUserKey, (prev) => ({
      ...prev,
      activeModule,
    }))
  }, [currentUserKey, activeModule])

  useEffect(() => {
    if (!currentUserKey) {
      return
    }
    updateStoredUserPreferences(currentUserKey, (prev) => ({
      ...prev,
      supplies: {
        ...(prev.supplies ?? {}),
        supplySearch,
        categoryFilter,
        stockFilter,
        expiredOnly,
        groupSort,
        columns,
      },
      orders: {
        ...(prev.orders ?? {}),
        search: ordersSearch,
        statusFilter: ordersStatusFilter,
      },
    }))
  }, [
    currentUserKey,
    supplySearch,
    categoryFilter,
    stockFilter,
    expiredOnly,
    groupSort,
    columns,
    ordersSearch,
    ordersStatusFilter,
  ])

  const renderModuleContent = () => {
    if (activeModule === 'dashboard') {
      return (
        <>
          <div className="dashboard-user-actions">
            <button type="button" onClick={fetchProfile} disabled={loading}>
              Оновити профіль
            </button>
            <button type="button" className="danger-btn" onClick={logout}>
              Вийти
            </button>
          </div>
          <div className="module-grid">
            <article className="metric-card">
              <p className="metric-title">Клієнти</p>
              <p className="metric-value">0</p>
              <p className="metric-hint">Підключимо реальні дані на наступному кроці</p>
            </article>
            <article className="metric-card">
              <p className="metric-title">Активні угоди</p>
              <p className="metric-value">0</p>
              <p className="metric-hint">Синхронізується з Django API</p>
            </article>
            <article className="metric-card">
              <p className="metric-title">Задачі на сьогодні</p>
              <p className="metric-value">0</p>
              <p className="metric-hint">Додамо фільтри і пріоритети</p>
            </article>
          </div>
        </>
      )
    }

    if (activeModule === 'clients') {
      return (
        <section className="module-card supplies-module-flat">
          <div className="module-toolbar">
            <div>
              <h3>Список товарів</h3>
              <p className="module-toolbar-hint">
                General supplies + дочірні LOT, серверні фільтри та пагінація.
              </p>
            </div>
            <div className="module-toolbar-actions">
              <button type="button" onClick={() => void loadSupplies({ page: safeSuppliesPage })} disabled={suppliesLoading}>
                {suppliesLoading ? 'Оновлення...' : 'Оновити'}
              </button>
            </div>
          </div>

          <div className="supplies-controls-grid">
            <input
              type="text"
              value={supplySearch}
              onChange={(event) => {
                const nextValue = event.target.value
                setSupplySearch(nextValue)
                void loadSupplies({
                  page: 1,
                  search: nextValue,
                  category: categoryFilter,
                  stock: stockFilter,
                  expiredOnly,
                  sort: groupSort,
                })
              }}
              placeholder="Пошук: назва, REF, SMN, LOT"
            />
            <select
              value={categoryFilter}
              onChange={(event) => {
                const nextValue = event.target.value
                setCategoryFilter(nextValue)
                void loadSupplies({
                  page: 1,
                  search: supplySearch,
                  category: nextValue,
                  stock: stockFilter,
                  expiredOnly,
                  sort: groupSort,
                })
              }}
            >
              <option value="all">Усі категорії</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            <select
              value={stockFilter}
              onChange={(event) =>
                {
                  const nextValue = event.target.value as 'all' | 'with_children' | 'without_children'
                  setStockFilter(nextValue)
                  void loadSupplies({
                    page: 1,
                    search: supplySearch,
                    category: categoryFilter,
                    stock: nextValue,
                    expiredOnly,
                    sort: groupSort,
                  })
                }
              }
            >
              <option value="all">Усі general supplies</option>
              <option value="with_children">Лише з дочірніми</option>
              <option value="without_children">Лише без дочірніх</option>
            </select>
            <select
              value={groupSort}
              onChange={(event) => {
                const nextValue = event.target.value as GroupSort
                setGroupSort(nextValue)
                void loadSupplies({
                  page: 1,
                  search: supplySearch,
                  category: categoryFilter,
                  stock: stockFilter,
                  expiredOnly,
                  sort: nextValue,
                })
              }}
            >
              <option value="name_asc">Назва A-Z</option>
              <option value="name_desc">Назва Z-A</option>
              <option value="count_desc">Кількість за спаданням</option>
              <option value="count_asc">Кількість за зростанням</option>
              <option value="expiry_asc">Термін (найближчий спочатку)</option>
              <option value="expiry_desc">Термін (найпізніший спочатку)</option>
            </select>
            <label className="checkbox-inline">
              <input
                type="checkbox"
                checked={expiredOnly}
                onChange={(event) => {
                  const nextValue = event.target.checked
                  setExpiredOnly(nextValue)
                  void loadSupplies({
                    page: 1,
                    search: supplySearch,
                    category: categoryFilter,
                    stock: stockFilter,
                    expiredOnly: nextValue,
                    sort: groupSort,
                  })
                }}
              />
              Лише прострочені
            </label>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => {
                setSupplySearch('')
                setCategoryFilter('all')
                setStockFilter('with_children')
                setExpiredOnly(false)
                setGroupSort('name_asc')
                void loadSupplies({
                  page: 1,
                  search: '',
                  category: 'all',
                  stock: 'with_children',
                  expiredOnly: false,
                  sort: 'name_asc',
                })
              }}
            >
              Скинути фільтри
            </button>
          </div>

          <details className="column-settings">
            <summary>Налаштування колонок</summary>
            <div className="column-settings-grid">
              {(Object.keys(columns) as ColumnKey[]).map((column) => (
                <div key={column} className="column-setting-item">
                  <label>
                    <input
                      type="checkbox"
                      checked={columns[column].visible}
                      onChange={() => toggleColumnVisibility(column)}
                    />
                    {columns[column].label}
                  </label>
                  <input
                    type="range"
                    min={80}
                    max={420}
                    value={columns[column].width}
                    onChange={(event) =>
                      changeColumnWidth(column, Number(event.target.value))
                    }
                  />
                </div>
              ))}
            </div>
          </details>

          <div className="supplies-stats-row">
            <span>General supplies: {suppliesTotalCount}</span>
            <span>На сторінці: {filteredGroups.length}</span>
            <span>Розмір сторінки: {suppliesPageSize}</span>
            <span>Партій на сторінці: {filteredGroups.reduce((acc, item) => acc + item.lots.length, 0)}</span>
          </div>

          <div className="supplies-table-wrapper">
            <table className="supplies-table">
              <thead>
                <tr>
                  <th>Назва товару</th>
                  <th>Товар</th>
                </tr>
              </thead>
              <tbody>
                {filteredGroups.map((group) => {
                  return (
                    <Fragment key={group.key}>
                      <tr className="group-combined-row" onContextMenu={(event) => openGroupContextMenu(event, group)}>
                        <td colSpan={2}>
                          <div className="group-item-card">
                            <div className="group-split-layout">
                              <div className="group-general-panel">
                                {columns.name.visible && <p className="group-main-name">{group.name}</p>}
                                <div className="group-meta-grid">
                                {columns.package.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="Пакування / Тести">🧪 Пакування</span>
                                    <span className="meta-value">{group.packageAndTests}</span>
                                  </div>
                                )}
                                {columns.category.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="Категорія">🏷 Категорія</span>
                                    <span className="meta-value">{group.category}</span>
                                  </div>
                                )}
                                {columns.ref.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="REF">🔖 REF</span>
                                    <span className="meta-value">{group.ref}</span>
                                  </div>
                                )}
                                {columns.smn.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="SMN">🧬 SMN</span>
                                    <span className="meta-value">{group.smn}</span>
                                  </div>
                                )}
                                {columns.lots.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="Партій">📦 Партій</span>
                                    <span className="meta-value">{group.lots.length}</span>
                                  </div>
                                )}
                                {columns.count.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="Кількість">🔢 К-сть</span>
                                    <span className="meta-value">{group.totalCount}</span>
                                  </div>
                                )}
                                {columns.onhold.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="On Hold">🟧 Hold</span>
                                    <span className="meta-value">{group.totalOnHold}</span>
                                  </div>
                                )}
                                {columns.expiry.visible && (
                                  <div className="group-meta-item">
                                    <span className="meta-badge" title="Найближчий термін">⏰ Термін</span>
                                    <span className="meta-value">{group.nearestExpiry ?? '-'}</span>
                                  </div>
                                )}
                                </div>
                              </div>
                              <div className="nested-row-panel">
                                <div className="nested-table-wrap">
                                  <table className="nested-table">
                                  <thead>
                                    <tr>
                                      <th><span className="col-badge">🏷 LOT</span></th>
                                      <th><span className="col-badge">🔢 К-сть</span></th>
                                      <th><span className="col-badge">🟧 Hold</span></th>
                                      <th><span className="col-badge">⏰ Термін</span></th>
                                      <th><span className="col-badge">🛒</span></th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                      {group.lots.length === 0 ? (
                                        <tr>
                                          <td colSpan={5}>
                                            Немає дочірніх LOT для цього товару.
                                          </td>
                                        </tr>
                                      ) : (
                                        group.lots.map((lot) => (
                                          <tr
                                            key={lot.id}
                                            onContextMenu={(event) => openLotContextMenu(event, group, lot)}
                                          >
                                            <td>{lot.supplyLot || '-'}</td>
                                            <td>{lot.count ?? '-'}</td>
                                            <td>{lot.countOnHold ?? 0}</td>
                                            <td>{lot.expiredDate || '-'}</td>
                                            <td>
                                              <div className="row-actions">
                                                <button
                                                  type="button"
                                                  className="action-btn action-cart"
                                                  title="Додати в кошик"
                                                  onClick={() => void addLotToCart(lot.id)}
                                                  disabled={rowActionBusy}
                                                >
                                                  🛒
                                                </button>
                                              </div>
                                            </td>
                                          </tr>
                                        ))
                                      )}
                                  </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="pagination-bar">
            <span>
              Сторінка {safeSuppliesPage} з {totalSuppliesPagesSafe}
            </span>
            <div className="pagination-actions">
              <button
                type="button"
                disabled={safeSuppliesPage <= 1 || suppliesLoading}
                onClick={() => void loadSupplies({ page: safeSuppliesPage - 1 })}
              >
                ← Назад
              </button>
              <button
                type="button"
                disabled={safeSuppliesPage >= totalSuppliesPagesSafe || suppliesLoading}
                onClick={() => void loadSupplies({ page: safeSuppliesPage + 1 })}
              >
                Далі →
              </button>
            </div>
          </div>

          {lotModalOpen && (
            <div className="desktop-modal-backdrop">
              <div className="desktop-modal">
                <h4>{lotDraft.mode === 'add' ? 'Додати LOT' : 'Редагувати LOT'}</h4>
                <div className="modal-form-grid">
                  <label>
                    LOT
                    <input
                      type="text"
                      value={lotDraft.supplyLot}
                      onChange={(event) =>
                        setLotDraft((prev) => ({ ...prev, supplyLot: event.target.value }))
                      }
                    />
                  </label>
                  <label>
                    Кількість
                    <input
                      type="number"
                      min={0}
                      value={lotDraft.count}
                      onChange={(event) =>
                        setLotDraft((prev) => ({ ...prev, count: Number(event.target.value) }))
                      }
                    />
                  </label>
                  <label>
                    Термін (YYYY-MM-DD)
                    <input
                      type="date"
                      value={lotDraft.expiredDate}
                      onChange={(event) =>
                        setLotDraft((prev) => ({ ...prev, expiredDate: event.target.value }))
                      }
                    />
                  </label>
                </div>
                <div className="desktop-modal-actions">
                  <button type="button" onClick={() => setLotModalOpen(false)}>
                    Скасувати
                  </button>
                  <button type="button" onClick={() => void saveLotDraft()} disabled={rowActionBusy}>
                    Зберегти
                  </button>
                </div>
              </div>
            </div>
          )}

          {generalModalOpen && (
            <div className="desktop-modal-backdrop">
              <div className="desktop-modal">
                <h4>Редагувати товар</h4>
                <div className="modal-form-grid">
                  <label>
                    Назва
                    <input
                      type="text"
                      value={generalDraft.name}
                      onChange={(event) =>
                        setGeneralDraft((prev) => ({ ...prev, name: event.target.value }))
                      }
                    />
                  </label>
                  <label>
                    REF
                    <input
                      type="text"
                      value={generalDraft.ref}
                      onChange={(event) =>
                        setGeneralDraft((prev) => ({ ...prev, ref: event.target.value }))
                      }
                    />
                  </label>
                  <label>
                    SMN
                    <input
                      type="text"
                      value={generalDraft.smn_code}
                      onChange={(event) =>
                        setGeneralDraft((prev) => ({ ...prev, smn_code: event.target.value }))
                      }
                    />
                  </label>
                  <label>
                    Пакування / Тести
                    <input
                      type="text"
                      value={generalDraft.package_and_tests}
                      onChange={(event) =>
                        setGeneralDraft((prev) => ({
                          ...prev,
                          package_and_tests: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>
                <div className="desktop-modal-actions">
                  <button type="button" onClick={() => setGeneralModalOpen(false)}>
                    Скасувати
                  </button>
                  <button type="button" onClick={() => void saveGeneralDraft()} disabled={rowActionBusy}>
                    Зберегти
                  </button>
                </div>
              </div>
            </div>
          )}

          {contextMenu.visible && contextMenu.group && (
            <div
              className="context-menu-overlay"
              onClick={closeContextMenu}
              onContextMenu={(event) => event.preventDefault()}
            >
              <div
                className="context-menu"
                style={{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }}
                onClick={(event) => event.stopPropagation()}
              >
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => void openSupplyHistory(contextMenu.group!)}
                >
                  🕘 Історія товару
                </button>
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => {
                    const generalId = contextMenu.group?.id ?? 0
                    if (generalId) {
                      void addGeneralToPrecart(generalId)
                    }
                    closeContextMenu()
                  }}
                >
                  ⏳ Додати в передзамовлення
                </button>
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => {
                    const generalId = contextMenu.group?.id ?? 0
                    if (generalId) {
                      openAddLotModal(generalId)
                    }
                    closeContextMenu()
                  }}
                >
                  ＋ Додати LOT
                </button>
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => {
                    if (contextMenu.group) {
                      openEditGeneralModal(contextMenu.group)
                    }
                    closeContextMenu()
                  }}
                >
                  ✎ Редагувати товар
                </button>
              </div>
            </div>
          )}

          {lotContextMenu.visible && lotContextMenu.group && lotContextMenu.lot && (
            <div
              className="context-menu-overlay"
              onClick={closeLotContextMenu}
              onContextMenu={(event) => event.preventDefault()}
            >
              <div
                className="context-menu"
                style={{ top: `${lotContextMenu.y}px`, left: `${lotContextMenu.x}px` }}
                onClick={(event) => event.stopPropagation()}
              >
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => {
                    openEditLotModal(lotContextMenu.lot!)
                    closeLotContextMenu()
                  }}
                >
                  ✎ Редагувати LOT
                </button>
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => {
                    void deleteLot(lotContextMenu.lot!.id)
                    closeLotContextMenu()
                  }}
                >
                  🗑 Видалити LOT
                </button>
                <button
                  type="button"
                  className="context-menu-item"
                  onClick={() => {
                    openAddLotModal(lotContextMenu.group!.id)
                    closeLotContextMenu()
                  }}
                >
                  ＋ Додати LOT
                </button>
              </div>
            </div>
          )}

          {historyModalOpen && (
            <div className="desktop-modal-backdrop">
              <div className="desktop-modal history-modal">
                <div className="history-modal-header">
                  <h4>Історія товару</h4>
                  <button type="button" onClick={() => setHistoryModalOpen(false)}>
                    Закрити
                  </button>
                </div>
                {historyLoading ? (
                  <p>Завантаження...</p>
                ) : !historyData ? (
                  <p>Дані історії недоступні.</p>
                ) : (
                  <div className="history-content">
                    <p>
                      <strong>{historyData.general_supply.name}</strong> | REF:{' '}
                      {historyData.general_supply.ref || '-'} | SMN:{' '}
                      {historyData.general_supply.smn_code || '-'}
                    </p>
                    <p className="module-toolbar-hint">
                      Замовлення: {historyData.totals.orders_count} | Передзамовлення:{' '}
                      {historyData.totals.preorders_count} | Поставки:{' '}
                      {historyData.totals.deliveries_count} | Бронь:{' '}
                      {historyData.totals.booked_count}
                    </p>

                    <div className="history-section">
                      <h5>Останні рухи в замовленнях</h5>
                      <div className="supplies-table-wrapper">
                        <table className="supplies-table">
                          <thead>
                            <tr>
                              <th>Order ID</th>
                              <th>Організація</th>
                              <th>LOT</th>
                              <th>К-сть</th>
                              <th>Термін</th>
                              <th>Дата</th>
                            </tr>
                          </thead>
                          <tbody>
                            {historyData.orders.map((item) => (
                              <tr key={`h-order-${item.id}`}>
                                <td>{item.order_id ?? '-'}</td>
                                <td>{item.place ?? '-'}</td>
                                <td>{item.lot ?? '-'}</td>
                                <td>{item.count ?? '-'}</td>
                                <td>{item.date_expired ?? '-'}</td>
                                <td>{item.date_created ?? '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      )
    }

    if (activeModule === 'orders') {
      return (
        <section className="module-card">
          <div className="module-toolbar">
            <div>
              <h3>Замовлення</h3>
              <p className="module-toolbar-hint">
                Компактний список як у вебі + перехід на деталі замовлення.
              </p>
            </div>
            <div className="module-toolbar-actions">
              <button
                type="button"
                onClick={() => void loadOrders({ page: safeOrdersPage })}
                disabled={ordersLoading}
              >
                {ordersLoading ? 'Оновлення...' : 'Оновити'}
              </button>
            </div>
          </div>

          <div className="module-nav-tabs">
            <button
              type="button"
              className={activeOrderTabId === null ? 'module-tab active' : 'module-tab'}
              onClick={backToOrdersList}
            >
              Список
            </button>
            {openOrderTabs.map((orderId) => (
              <div
                key={`order-tab-${orderId}`}
                className={
                  activeOrderTabId === orderId
                    ? 'order-tab-item order-tab-frame active'
                    : 'order-tab-item order-tab-frame'
                }
              >
                <button
                  type="button"
                  className="order-tab-open-btn order-tab-label"
                  onClick={() => setActiveOrderTabId(orderId)}
                >
                  {truncateTabLabel(
                    `№${orderId} ${
                      orderTabsCache[orderId]?.place?.name ??
                      orders.find((item) => item.id === orderId)?.place?.name ??
                      '-'
                    }`,
                  )}
                </button>
                <button
                  type="button"
                  className="order-tab-close-btn"
                  aria-label={`Закрити вкладку ${orderId}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    closeOrderTab(orderId)
                  }}
                >
                  ×
                </button>
              </div>
            ))}
            {openOrderTabs.length > 0 && (
              <button
                type="button"
                className="module-tab order-close-all-btn"
                onClick={closeAllOrderTabs}
              >
                Закрити всі вкладки
              </button>
            )}
          </div>

          <div className="supplies-controls-grid orders-controls-grid">
            <input
              type="text"
              value={ordersSearch}
              onChange={(event) => {
                const nextSearch = event.target.value
                setOrdersSearch(nextSearch)
                setOrdersPage(1)
                if (activeModule === 'orders') {
                  void loadOrders({ page: 1, search: nextSearch, status: ordersStatusFilter })
                }
              }}
              placeholder="Пошук: № замовлення, організація, дата"
            />
            <select
              value={ordersStatusFilter}
              onChange={(event) => {
                const nextStatus = event.target.value as OrderStatusFilter
                setOrdersStatusFilter(nextStatus)
                setOrdersPage(1)
                if (activeModule === 'orders') {
                  void loadOrders({ page: 1, search: ordersSearch, status: nextStatus })
                }
              }}
            >
              <option value="all">Усі статуси</option>
              <option value="open">В очікуванні</option>
              <option value="completed">Завершені</option>
            </select>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => {
                setOrdersSearch('')
                setOrdersStatusFilter('all')
                setOrdersPage(1)
                if (activeModule === 'orders') {
                  void loadOrders({ page: 1, search: '', status: 'all' })
                }
              }}
            >
              Скинути
            </button>
          </div>

          {activeOrderTabId === null ? (
            <>
              <div className="supplies-stats-row">
                <span>Замовлень: {ordersTotalCount}</span>
                <span>
                  Активних: {ordersOpenCount}
                </span>
                <span>
                  Завершених: {ordersCompletedCount}
                </span>
                <span>
                  Сторінка: {safeOrdersPage} / {totalOrdersPagesSafe}
                </span>
              </div>

              <div className="orders-web-list">
                {pagedOrders.map((order) => (
                  <article
                    key={`order-row-${order.id}`}
                    className={order.isPinned ? 'orders-web-row pinned' : 'orders-web-row'}
                    onClick={() => openOrderDetails(order.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        openOrderDetails(order.id)
                      }
                    }}
                  >
                    <div className="orders-web-left">
                      <span className="orders-web-badge">📅 {order.dateCreated ?? '-'}</span>
                      <span className="orders-web-badge muted">
                        👤 {order.userCreated?.full_name || 'Користувач'}
                      </span>
                    </div>

                    <div className="orders-web-center">
                      <div className="orders-web-title-line">
                        <strong>№{order.id}</strong>
                        {order.isMerged && <span className="orders-web-merged">Merged</span>}
                        <button
                          type="button"
                          className={
                            order.isPinned
                              ? 'order-pin-toggle active'
                              : 'order-pin-toggle'
                          }
                          title={order.isPinned ? 'Відкріпити замовлення' : 'Закріпити замовлення'}
                          onClick={(event) => {
                            event.stopPropagation()
                            void toggleOrderPinned(order.id, !(order.isPinned ?? false))
                          }}
                          disabled={Boolean(orderActionLoading[order.id])}
                        >
                          📌
                        </button>
                      </div>
                      <p className="orders-web-place">
                        {order.place?.name ?? '-'}
                        {order.place?.city ? `, ${order.place.city}` : ''}
                      </p>
                      {order.comment && <p className="orders-web-comment">💬 {order.comment}</p>}
                      {order.np?.status_desc && (
                        <p className="orders-web-np">
                          🚚 {order.np.status_desc}
                          {order.np.status_code ? ` (код ${order.np.status_code})` : ''}
                        </p>
                      )}
                    </div>

                    <div className="orders-web-right">
                      {!order.isComplete && order.dateToSend && (
                        <span
                          className={
                            order.date_send_is_today
                              ? 'orders-web-badge warn'
                              : order.date_send_is_expired
                                ? 'orders-web-badge danger'
                                : 'orders-web-badge'
                          }
                        >
                          🚚 {order.dateToSend}
                        </span>
                      )}
                      <span
                        className={
                          order.isComplete
                            ? 'order-status order-status-done'
                            : 'order-status order-status-open'
                        }
                      >
                        {order.isComplete
                          ? `Завершено ${order.dateSent ? `(${order.dateSent})` : ''}`
                          : 'В очікуванні'}
                      </span>
                    </div>
                  </article>
                ))}
                {pagedOrders.length === 0 && (
                  <div className="order-empty-state">Замовлення не знайдено.</div>
                )}
              </div>

              <div className="orders-pagination">
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => {
                    const nextPage = Math.max(safeOrdersPage - 1, 1)
                    setOrdersPage(nextPage)
                    void loadOrders({ page: nextPage })
                  }}
                  disabled={safeOrdersPage <= 1}
                >
                  Назад
                </button>
                <span className="orders-pagination-label">
                  {safeOrdersPage} / {totalOrdersPagesSafe} • по {ordersPageSize}
                </span>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => {
                    const nextPage = Math.min(safeOrdersPage + 1, totalOrdersPagesSafe)
                    setOrdersPage(nextPage)
                    void loadOrders({ page: nextPage })
                  }}
                  disabled={safeOrdersPage >= totalOrdersPagesSafe}
                >
                  Далі
                </button>
              </div>
            </>
          ) : (
            <div className="order-details-panel">
              {!selectedOrder ? (
                <p className="module-toolbar-hint">Оберіть замовлення зі списку.</p>
              ) : (
                <>
                  <div className="order-details-head">
                    <div>
                      <h4>Замовлення #{selectedOrder.id}</h4>
                      <p className="module-toolbar-hint">
                        {selectedOrder.place?.name ?? '-'} | Створено: {selectedOrder.dateCreated ?? '-'}
                      </p>
                    </div>
                    <div className="module-toolbar-actions">
                      <button
                        type="button"
                        className="ghost-btn"
                        onClick={backToOrdersList}
                      >
                        До списку
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          void loadOrderSupplies(selectedOrder.id, true)
                          void loadOrderMeta(selectedOrder.id, true)
                        }}
                        disabled={Boolean(orderSuppliesLoading[selectedOrder.id])}
                      >
                        {orderSuppliesLoading[selectedOrder.id] ? 'Оновлення...' : 'Оновити позиції'}
                      </button>
                    </div>
                  </div>

                  <div className="order-meta-panel">
                    {orderMetaLoading[selectedOrder.id] ? (
                      <p className="module-toolbar-hint">Завантаження деталей замовлення...</p>
                    ) : (
                      <>
                        <div className="order-meta-top">
                          <span>
                            Статус:{' '}
                            <strong>
                              {orderMetaMap[selectedOrder.id]?.isComplete
                                ? 'Завершено'
                                : 'В очікуванні'}
                            </strong>
                          </span>
                          <span>
                            DateToSend: {orderMetaMap[selectedOrder.id]?.dateToSend ?? '-'}
                          </span>
                          <span>
                            Коментар: {orderMetaMap[selectedOrder.id]?.comment || '-'}
                          </span>
                        </div>
                        <div className="module-toolbar-actions">
                          <button
                            type="button"
                            onClick={() =>
                              void toggleOrderPinned(
                                selectedOrder.id,
                                !(orderMetaMap[selectedOrder.id]?.isPinned ?? false),
                              )
                            }
                            disabled={Boolean(orderActionLoading[selectedOrder.id])}
                          >
                            {(orderMetaMap[selectedOrder.id]?.isPinned ?? false)
                              ? 'Відкріпити'
                              : 'Закріпити'}
                          </button>
                          <button
                            type="button"
                            onClick={() => void refreshOrderNpStatus(selectedOrder.id)}
                            disabled={Boolean(orderActionLoading[selectedOrder.id])}
                          >
                            Оновити статус НП
                          </button>
                          <button
                            type="button"
                            className="danger-btn"
                            onClick={() => void completeOrder(selectedOrder.id)}
                            disabled={
                              Boolean(orderActionLoading[selectedOrder.id]) ||
                              Boolean(orderMetaMap[selectedOrder.id]?.isComplete)
                            }
                          >
                            Завершити замовлення
                          </button>
                        </div>
                        <div className="order-np-list">
                          <h5>Статуси Нової Пошти</h5>
                          {(orderMetaMap[selectedOrder.id]?.np.statuses ?? []).length === 0 ? (
                            <p className="module-toolbar-hint">Немає даних по НП.</p>
                          ) : (
                            <div className="supplies-table-wrapper">
                              <table className="supplies-table">
                                <thead>
                                  <tr>
                                    <th>Документ</th>
                                    <th>Код</th>
                                    <th>Статус</th>
                                    <th>Отримувач</th>
                                    <th>План</th>
                                    <th>Факт</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {(orderMetaMap[selectedOrder.id]?.np.statuses ?? []).map((np) => (
                                    <tr key={`np-status-${np.id}`}>
                                      <td>{np.doc_number || '-'}</td>
                                      <td>{np.status_code || '-'}</td>
                                      <td>{np.status_desc || '-'}</td>
                                      <td>{np.recipient || '-'}</td>
                                      <td>{np.scheduled_delivery || '-'}</td>
                                      <td>{np.actual_delivery || np.recipient_datetime || '-'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  <div className="supplies-table-wrapper">
                    {orderSuppliesLoading[selectedOrder.id] ? (
                      <p className="module-toolbar-hint order-details-loading">Завантаження позицій...</p>
                    ) : (
                      <table className="supplies-table">
                        <thead>
                          <tr>
                            <th>Назва</th>
                            <th>REF</th>
                            <th>LOT</th>
                            <th>Кількість</th>
                            <th>Створено</th>
                            <th>Термін</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(orderSuppliesMap[selectedOrder.id] ?? []).map((item, index) => (
                            <tr key={`order-item-${selectedOrder.id}-${index}`}>
                              <td>{item.name || '-'}</td>
                              <td>{item.ref || '-'}</td>
                              <td>{item.lot || '-'}</td>
                              <td>{item.countInOrder ?? '-'}</td>
                              <td>{item.dateCreated || '-'}</td>
                              <td>{item.expiredDate || '-'}</td>
                            </tr>
                          ))}
                          {(orderSuppliesMap[selectedOrder.id] ?? []).length === 0 && (
                            <tr>
                              <td colSpan={6}>Позиції відсутні.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </section>
      )
    }

    if (activeModule === 'delivery') {
      const lastScanned = deliveryScannedItems[0] ?? null
      const recognizedCount = deliveryScannedItems.filter((item) => item.recognized).length
      const unrecognizedCount = deliveryScannedItems.length - recognizedCount

      return (
        <section className="module-card">
          <div className="module-toolbar">
            <div>
              <h3>Поставка (сканер)</h3>
              <p className="module-toolbar-hint">
                Офлайн-розпізнавання по кожному скану і фінальне завантаження поставки.
              </p>
            </div>
            <div className="module-toolbar-actions">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => void loadDeliveryCatalog()}
                disabled={deliveryCatalogLoading}
              >
                {deliveryCatalogLoading ? 'Оновлення каталогу...' : 'Оновити каталог'}
              </button>
            </div>
          </div>

          <div className="supplies-controls-grid orders-controls-grid">
            <select
              value={deliveryBarcodeType}
              onChange={(event) => setDeliveryBarcodeType(event.target.value as DeliveryBarcodeType)}
            >
              <option value="Data Matrix">Data Matrix</option>
              <option value="Siemens">Siemens</option>
            </select>
            <input
              type="text"
              value={deliveryScanInput}
              onChange={(event) => setDeliveryScanInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  registerScannedValue(deliveryScanInput)
                  setDeliveryScanInput('')
                }
              }}
              placeholder="Скануйте код (Enter після кожного піку)"
            />
            <button
              type="button"
              className="ghost-btn"
              onClick={() => {
                registerScannedValue(deliveryScanInput)
                setDeliveryScanInput('')
              }}
            >
              Додати
            </button>
          </div>

          <div className="supplies-stats-row">
            <span>Каталог: {deliveryCatalogLoaded ? deliveryCatalog.length : 'не завантажено'}</span>
            <span>Сканів: {deliveryScannedItems.length}</span>
            <span>Розпізнано: {recognizedCount}</span>
            <span>Не розпізнано: {unrecognizedCount}</span>
          </div>

          <div className="order-meta-panel">
            <h4>Останній скан</h4>
            {!lastScanned ? (
              <p className="module-toolbar-hint">Ще немає сканованих кодів.</p>
            ) : (
              <div className="order-meta-top">
                <span>
                  Raw: <strong>{lastScanned.raw}</strong>
                </span>
                <span>
                  SMN/REF: <strong>{lastScanned.smn || '-'}</strong>
                </span>
                <span>
                  LOT: <strong>{lastScanned.lot || '-'}</strong>
                </span>
                <span>
                  Exp: <strong>{lastScanned.date_expired || '-'}</strong>
                </span>
                <span>
                  Статус:{' '}
                  <strong>{lastScanned.recognized ? 'Знайдено' : 'Не знайдено'}</strong>
                </span>
                <span>
                  Товар: <strong>{lastScanned.matched_name || '-'}</strong>
                </span>
              </div>
            )}
          </div>

          <div className="supplies-table-wrapper">
            <table className="supplies-table">
              <thead>
                <tr>
                  <th>Raw</th>
                  <th>SMN/REF</th>
                  <th>LOT</th>
                  <th>Exp</th>
                  <th>Знайдено</th>
                  <th>Товар</th>
                </tr>
              </thead>
              <tbody>
                {deliveryScannedItems.map((item) => (
                  <tr key={item.id}>
                    <td>{item.raw}</td>
                    <td>{item.smn || '-'}</td>
                    <td>{item.lot || '-'}</td>
                    <td>{item.date_expired || '-'}</td>
                    <td>{item.recognized ? 'Так' : 'Ні'}</td>
                    <td>{item.matched_name || '-'}</td>
                  </tr>
                ))}
                {deliveryScannedItems.length === 0 && (
                  <tr>
                    <td colSpan={6}>Список сканувань порожній.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="desktop-modal-actions">
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setDeliveryScannedItems([])}
              disabled={deliveryUploadLoading || deliveryScannedItems.length === 0}
            >
              Очистити список
            </button>
            <button
              type="button"
              onClick={() => void uploadDeliveryFromLocalScan()}
              disabled={deliveryUploadLoading || deliveryScannedItems.length === 0}
            >
              {deliveryUploadLoading ? 'Завантаження...' : 'Завантажити поставку'}
            </button>
          </div>
        </section>
      )
    }

    if (activeModule === 'deals') {
      return (
        <section className="module-card">
          <h3>Угоди</h3>
          <p>Тут буде канбан/воронка продажів і статуси угод.</p>
        </section>
      )
    }

    if (activeModule === 'cart') {
      return (
        <section className="module-card">
          <div className="module-toolbar">
            <div>
              <h3>Корзина</h3>
              <p className="module-toolbar-hint">
                Повний desktop flow: редагування позицій і оформлення замовлення.
              </p>
            </div>
            <div className="module-toolbar-actions">
              <button type="button" onClick={() => void loadCart()} disabled={cartLoading}>
                Оновити
              </button>
            </div>
          </div>

          <div className="supplies-stats-row">
            <span>Рядків: {cartTotals.total_rows}</span>
            <span>Одиниць: {cartTotals.total_items}</span>
          </div>

          <div className="supplies-table-wrapper">
            <table className="supplies-table">
              <thead>
                <tr>
                  <th>Назва</th>
                  <th>LOT</th>
                  <th>Термін</th>
                  <th>Кількість</th>
                  <th>Дії</th>
                </tr>
              </thead>
              <tbody>
                {cartItems.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.lot || '-'}</td>
                    <td>{item.expiredDate || '-'}</td>
                    <td>{item.count}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="action-btn action-edit"
                          title="Зменшити"
                          onClick={() => void updateCartItem(item.id, 'minus')}
                          disabled={cartLoading}
                        >
                          −
                        </button>
                        <button
                          type="button"
                          className="action-btn action-add-lot"
                          title="Збільшити"
                          onClick={() => void updateCartItem(item.id, 'plus')}
                          disabled={cartLoading}
                        >
                          +
                        </button>
                        <button
                          type="button"
                          className="action-btn action-delete"
                          title="Видалити позицію"
                          onClick={() => void removeCartItem(item.id)}
                          disabled={cartLoading}
                        >
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="checkout-panel">
            <h4>Оформлення</h4>
            <div className="checkout-grid">
              <label>
                Організація
                <select
                  value={checkoutDraft.place_id}
                  onChange={(event) =>
                    setCheckoutDraft((prev) => ({ ...prev, place_id: event.target.value }))
                  }
                >
                  <option value="">Оберіть організацію</option>
                  {places.map((place) => (
                    <option key={place.id} value={place.id}>
                      {place.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Коментар
                <input
                  type="text"
                  value={checkoutDraft.comment}
                  onChange={(event) =>
                    setCheckoutDraft((prev) => ({ ...prev, comment: event.target.value }))
                  }
                />
              </label>
              <label>
                Дата відправки
                <input
                  type="date"
                  value={checkoutDraft.dateToSend}
                  onChange={(event) =>
                    setCheckoutDraft((prev) => ({ ...prev, dateToSend: event.target.value }))
                  }
                />
              </label>
            </div>
            <div className="checkout-options">
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={checkoutDraft.isPinned}
                  onChange={(event) =>
                    setCheckoutDraft((prev) => ({ ...prev, isPinned: event.target.checked }))
                  }
                />
                Закріпити
              </label>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={checkoutDraft.isComplete}
                  onChange={(event) =>
                    setCheckoutDraft((prev) => ({ ...prev, isComplete: event.target.checked }))
                  }
                />
                Одразу завершити
              </label>
            </div>
            <div className="desktop-modal-actions">
              <button type="button" onClick={() => void checkoutCart()} disabled={cartLoading || cartItems.length === 0}>
                Оформити замовлення
              </button>
            </div>
          </div>
        </section>
      )
    }

    return (
      <section className="module-card">
        <h3>Задачі</h3>
        <p>Підготуємо список задач з дедлайнами та нагадуваннями.</p>
      </section>
    )
  }

  return (
    <>
      {!isLoggedIn ? (
        <main className="container">
          <header>
            <h1>DMDX CRM Desktop</h1>
            <p className="subtitle">
              Онлайн-MVP для Windows. Наступним кроком можна додати офлайн-режим.
            </p>
          </header>

          <section className="card">
            <h2>Вхід у систему</h2>
            <form className="form" onSubmit={handleLogin}>
              <label htmlFor="username">Логін</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Введіть логін"
                required
              />

              <label htmlFor="password">Пароль</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Введіть пароль"
                required
              />

              <button type="submit" disabled={loading}>
                {loading ? 'Зачекайте...' : 'Увійти'}
              </button>
            </form>
          </section>

          <section className="card">
            <h2>Підключення до Django API</h2>
            <p className="api-url">{apiBaseUrl || '/api (через Vite proxy)'}</p>
            <button type="button" onClick={checkConnection} disabled={loading}>
              Перевірити з’єднання
            </button>
            <p className="status">{message}</p>
            <p className="hint">
              Для зміни API адресу вкажіть `VITE_API_BASE_URL` у файлі `.env`.
            </p>
          </section>

          <footer>
            <span>Платформа: {window.desktop?.platform ?? 'web'}</span>
          </footer>
        </main>
      ) : (
        <main className="crm-layout">
          <aside className="sidebar">
            <div className="sidebar-user-chip">
              <span className="sidebar-user-icon" aria-hidden="true">
                {sidebarUserInitial}
              </span>
              <span className="sidebar-user-name">{profileName}</span>
            </div>
            <div className="sidebar-main-tabs">
              <button
                className={activeModule === 'dashboard' ? 'menu-btn active' : 'menu-btn'}
                type="button"
                onClick={() => setActiveModule('dashboard')}
              >
                Dashboard
              </button>
              <button
                className={activeModule === 'clients' ? 'menu-btn active' : 'menu-btn'}
                type="button"
                onClick={openSuppliesModule}
              >
                Товари
              </button>
              <button
                className={activeModule === 'orders' ? 'menu-btn active' : 'menu-btn'}
                type="button"
                onClick={openOrdersModule}
              >
                Замовлення
              </button>
              <button
                className={activeModule === 'delivery' ? 'menu-btn active' : 'menu-btn'}
                type="button"
                onClick={openDeliveryModule}
              >
                Поставка
              </button>
              <button
                className={activeModule === 'deals' ? 'menu-btn active' : 'menu-btn'}
                type="button"
                onClick={() => setActiveModule('deals')}
              >
                Угоди
              </button>
              <button
                className={activeModule === 'tasks' ? 'menu-btn active' : 'menu-btn'}
                type="button"
                onClick={() => setActiveModule('tasks')}
              >
                Задачі
              </button>
            </div>
            {cartTotals.total_rows > 0 && (
              <div className="sidebar-cart-shortcut">
                <button
                  className={activeModule === 'cart' ? 'menu-btn active cart-btn' : 'menu-btn cart-btn'}
                  type="button"
                  onClick={openCartModule}
                >
                  Корзина ({cartTotals.total_items})
                </button>
              </div>
            )}
          </aside>

          <section className="content">
            <section className="content-body">
              {renderModuleContent()}
              <p className="status">{message}</p>
            </section>
          </section>
        </main>
      )}
    </>
  )
}

export default App
