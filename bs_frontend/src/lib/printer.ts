/**
 * printer.ts — Utilidades de impresión para el frontend de Blackshot POS
 *
 * Soporta tres estrategias de envío de bytes ESC/POS a una impresora térmica:
 *
 *  1. WebUSB    — Impresora USB conectada directamente a la PC de caja.
 *                 Solo Chrome/Edge en escritorio. Requiere HTTPS en producción.
 *
 *  2. Bluetooth — Impresora Bluetooth. El navegador del móvil usa Web Bluetooth API
 *                 para enviar los bytes. Compatible con Chrome Android.
 *
 *  3. Download  — Descarga el archivo binario .bin. El sistema operativo decide
 *                 cómo abrirlo. Funciona en CUALQUIER dispositivo y navegador
 *                 como fallback universal.
 */

// ── Declaraciones de tipos para WebUSB (no incluidas en lib.dom.d.ts por defecto) ──
declare global {
  interface Navigator {
    usb?: {
      requestDevice(options: { filters: object[] }): Promise<USBDeviceCompat>;
    };
    bluetooth?: {
      requestDevice(options: object): Promise<BluetoothDeviceCompat>;
    };
  }

  interface USBDeviceCompat {
    open(): Promise<void>;
    close(): Promise<void>;
    configuration: USBConfigurationCompat | null;
    selectConfiguration(value: number): Promise<void>;
    claimInterface(interfaceNumber: number): Promise<void>;
    releaseInterface(interfaceNumber: number): Promise<void>;
    // Uint8Array | ArrayBuffer para cubrir ambos casos sin problemas de tipo
    transferOut(endpointNumber: number, data: Uint8Array | ArrayBuffer): Promise<USBOutTransferResult>;
  }

  interface USBConfigurationCompat {
    interfaces: USBInterfaceCompat[];
  }

  interface USBInterfaceCompat {
    interfaceNumber: number;
    alternates: USBAlternateInterfaceCompat[];
  }

  interface USBAlternateInterfaceCompat {
    interfaceClass: number;
    endpoints: USBEndpointCompat[];
  }

  interface USBEndpointCompat {
    endpointNumber: number;
    direction: 'in' | 'out';
    type: 'bulk' | 'interrupt' | 'isochronous';
  }

  interface USBOutTransferResult {
    bytesWritten: number;
    status: 'ok' | 'stall' | 'babble';
  }

  interface BluetoothDeviceCompat {
    gatt: BluetoothRemoteGATTServerCompat;
  }

  interface BluetoothRemoteGATTServerCompat {
    connect(): Promise<BluetoothRemoteGATTServerCompat>;
    disconnect(): void;
    getPrimaryService(uuid: number | string): Promise<BluetoothRemoteGATTServiceCompat>;
  }

  interface BluetoothRemoteGATTServiceCompat {
    getCharacteristic(uuid: number | string): Promise<BluetoothRemoteGATTCharacteristicCompat>;
  }

  interface BluetoothRemoteGATTCharacteristicCompat {
    writeValueWithoutResponse(value: Uint8Array | ArrayBuffer): Promise<void>;
  }
}

// ── Tipos ───────────────────────────────────────────────────────────────────

export type PrintMethod = 'usb' | 'bluetooth' | 'download' | 'browser';

export interface PrintMethodInfo {
  id: PrintMethod;
  label: string;
  description: string;
  icon: string;
  /** true si el método es compatible con el dispositivo/navegador actual */
  available: boolean;
}

// ── Detección de capacidades ─────────────────────────────────────────────────

export function getAvailableMethods(): PrintMethodInfo[] {
  const isSecureContext = typeof window !== 'undefined' && window.isSecureContext;
  const hasUsb = typeof navigator !== 'undefined' && 'usb' in navigator;
  const hasBluetooth = typeof navigator !== 'undefined' && 'bluetooth' in navigator;
  const isMobile = typeof navigator !== 'undefined' && /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

  return [
    {
      id: 'usb',
      label: 'USB (WebUSB)',
      description: 'Impresora conectada por cable USB a esta PC.',
      icon: '🔌',
      available: hasUsb && isSecureContext && !isMobile,
    },
    {
      id: 'bluetooth',
      label: 'Bluetooth',
      description: 'Impresora Bluetooth. Ideal para móviles y tablets.',
      icon: '📶',
      available: hasBluetooth && isSecureContext,
    },
    {
      id: 'browser',
      label: 'Impresora del Sistema',
      description: 'Usa el diálogo de impresión de tu navegador (PDF/Windows).',
      icon: '🏛️',
      available: true,
    },
    {
      id: 'download',
      label: 'Descargar archivo',
      description: 'Descarga el archivo .bin. Compatible con cualquier dispositivo.',
      icon: '⬇️',
      available: true, // Siempre disponible
    },
  ];
}

/** Devuelve el método recomendado según el dispositivo actual. */
export function getRecommendedMethod(): PrintMethod {
  const preferred = getPreferredMethod();
  if (preferred) return preferred;

  const methods = getAvailableMethods();
  const isMobile = typeof navigator !== 'undefined' && /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

  if (isMobile && methods.find(m => m.id === 'bluetooth')?.available) return 'bluetooth';
  if (methods.find(m => m.id === 'usb')?.available) return 'usb';
  return 'browser';
}

/** Guarda el método favorito en este navegador. */
export function savePreferredMethod(method: PrintMethod): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('blackshot_preferred_print_method', method);
  }
}

/** Recupera el método favorito si existe. */
export function getPreferredMethod(): PrintMethod | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('blackshot_preferred_print_method') as PrintMethod | null;
  }
  return null;
}

// ── Obtener bytes del backend ─────────────────────────────────────────────────

const BASE_URL = '/api/v1/pos/system/printing';

async function fetchRawBytes(endpoint: string): Promise<Uint8Array> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    credentials: 'include'
  });
  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(err?.detail ?? `Error HTTP ${response.status}`);
  }
  const buffer = await response.arrayBuffer();
  return new Uint8Array(buffer);
}

// ── Estrategia 1: WebUSB ─────────────────────────────────────────────────────

/**
 * Envía bytes a una impresora térmica USB usando la WebUSB API.
 * El usuario debe autorizar el acceso la primera vez (dialog del browser).
 * La impresora se guarda en memoria para impresiones sucesivas sin re-selección.
 */
let _usbDevice: USBDeviceCompat | null = null;

async function printViaUsb(data: Uint8Array): Promise<void> {
  if (!navigator.usb) throw new Error('WebUSB no está disponible en este navegador.');

  if (!_usbDevice) {
    _usbDevice = await navigator.usb.requestDevice({ filters: [] });
  }

  const device = _usbDevice;
  await device.open();

  if (device.configuration === null) await device.selectConfiguration(1);

  const iface =
    device.configuration!.interfaces.find(
      (i: USBInterfaceCompat) => i.alternates[0]?.interfaceClass === 7
    ) ?? device.configuration!.interfaces[0];

  await device.claimInterface(iface.interfaceNumber);

  const endpoint = iface.alternates[0].endpoints.find(
    (e: USBEndpointCompat) => e.direction === 'out' && e.type === 'bulk'
  );

  if (!endpoint) {
    await device.releaseInterface(iface.interfaceNumber);
    await device.close();
    throw new Error('No se encontró endpoint de salida en la impresora USB.');
  }

  try {
    await device.transferOut(endpoint.endpointNumber, data);
  } finally {
    await device.releaseInterface(iface.interfaceNumber);
    await device.close();
  }
}

// ── Estrategia 2: Web Bluetooth ───────────────────────────────────────────────

/**
 * Envía bytes a una impresora Bluetooth térmica.
 * Usa el servicio estándar de impresión BT (0x1101 - Serial Port Profile).
 * Compatible con impresoras Bluetooth genéricas (Xprinter, EPSON TM, etc).
 */
const BT_PRINTER_SERVICE = 0x18f0;       // Servicio común en impresoras BT genéricas
const BT_PRINTER_CHARACTERISTIC = 0x2af1; // Característica de escritura

async function printViaBluetooth(data: Uint8Array): Promise<void> {
  if (!navigator.bluetooth) throw new Error('Web Bluetooth no está disponible en este navegador.');

  const device = await navigator.bluetooth.requestDevice({
    acceptAllDevices: true,
    optionalServices: [BT_PRINTER_SERVICE],
  });

  const server = await device.gatt.connect();
  let characteristic: BluetoothRemoteGATTCharacteristicCompat;

  try {
    const service = await server.getPrimaryService(BT_PRINTER_SERVICE);
    characteristic = await service.getCharacteristic(BT_PRINTER_CHARACTERISTIC);
  } catch {
    throw new Error(
      'No se pudo encontrar el servicio de impresión en el dispositivo Bluetooth. ' +
      'Asegúrese de que la impresora sea compatible con BLE SPP.'
    );
  }

  // Enviar en chunks de 512 bytes (límite común de BLE MTU)
  const CHUNK_SIZE = 512;
  for (let offset = 0; offset < data.byteLength; offset += CHUNK_SIZE) {
    // Extraer un ArrayBuffer limpio por cada chunk (requerido por writeValueWithoutResponse)
    const chunkBuffer = data.buffer.slice(
      data.byteOffset + offset,
      data.byteOffset + Math.min(offset + CHUNK_SIZE, data.byteLength)
    ) as ArrayBuffer;
    await characteristic.writeValueWithoutResponse(chunkBuffer);
    await new Promise(resolve => setTimeout(resolve, 20));
  }

  device.gatt.disconnect();
}

// ── Estrategia 3: Descarga de archivo ─────────────────────────────────────────

function printViaDownload(data: Uint8Array, filename: string): void {
  // Copiar a un ArrayBuffer limpio para compatibilidad con Blob
  const cleanBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) as ArrayBuffer;
  const blob = new Blob([cleanBuffer], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ── API pública ───────────────────────────────────────────────────────────────

/**
 * Imprime el ticket de venta de una orden.
 *
 * @param orderId  ID de la orden
 * @param method   Método de impresión ('usb' | 'bluetooth' | 'download')
 */
export async function printTicket(orderId: number, method: PrintMethod = 'browser'): Promise<void> {
  const data = await fetchRawBytes(`/ticket/${orderId}/raw`);
  await _dispatch(data, method, `ticket_${orderId}.bin`, orderId, 'ticket');
}

/**
 * Imprime la comanda de cocina de una orden.
 *
 * @param orderId  ID de la orden
 * @param method   Método de impresión ('usb' | 'bluetooth' | 'download' | 'browser')
 */
export async function printComanda(orderId: number, method: PrintMethod = 'browser'): Promise<void> {
  const data = await fetchRawBytes(`/comanda/${orderId}/raw`);
  await _dispatch(data, method, `comanda_${orderId}.bin`, orderId, 'comanda');
}

async function _dispatch(data: Uint8Array, method: PrintMethod, filename: string, orderId?: number, type?: 'ticket' | 'comanda'): Promise<void> {
  switch (method) {
    case 'usb':
      await printViaUsb(data);
      break;
    case 'bluetooth':
      await printViaBluetooth(data);
      break;
    case 'browser':
      if (orderId && type) {
        printViaBrowser(orderId, type);
      }
      break;
    case 'download':
    default:
      printViaDownload(data, filename);
      break;
  }
}

/** Abre una ventana nueva con el HTML del ticket para imprimir usando el diálogo del sistema. */
function printViaBrowser(orderId: number, type: 'ticket' | 'comanda'): void {
  const url = `${BASE_URL}/${type}/${orderId}/html`;
  
  // Abrir en una ventana pequeña o un popup
  const width = 400;
  const height = 600;
  const left = (window.screen.width / 2) - (width / 2);
  const top = (window.screen.height / 2) - (height / 2);
  
  window.open(url, `Imprimir ${type} #${orderId}`, `width=${width},height=${height},left=${left},top=${top},status=no,toolbar=no,menubar=no,location=no`);
}
