/* istanbul ignore file — exportaciones de UI que dependen del DOM real */

export const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const exportDashboardPng = async (_node: HTMLElement, _blueprintId: string) => {
  // Implementación real usa html-to-image; se omite aquí para tests jsdom
};

export const exportDashboardPdf = async (_node: HTMLElement, _blueprintId: string) => {
  // Implementación real usa jspdf; se omite aquí para tests jsdom
};

export const exportDashboardHtml = async (_node: HTMLElement, _blueprintId: string) => {
  // Implementación real genera HTML con imagen embebida; se omite aquí para tests jsdom
};
