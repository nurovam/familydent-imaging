import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';

export function TotpQr({ uri }: { uri: string }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    const element = canvas.current;
    if (!element) return;
    setFailed(false);
    void QRCode.toCanvas(element, uri, {
      width: 240, margin: 4, errorCorrectionLevel: 'M',
      color: { dark: '#000000', light: '#ffffff' },
    }).catch(() => { if (active) setFailed(true); });
    return () => {
      active = false;
      element.getContext('2d')?.clearRect(0, 0, element.width, element.height);
    };
  }, [uri]);
  return <div className="totp-qr">{failed ? <p role="status">Не удалось создать QR-код. Добавьте ключ вручную.</p> : <canvas ref={canvas} role="img" aria-label="QR-код для настройки TOTP" />}</div>;
}
