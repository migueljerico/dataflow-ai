/* Exportaciones ejecutivas del dashboard (PNG 3x, PDF apaisado, HTML autocontenido).
 * Patrón SVG → canvas ya probado en BusinessInsights / StarSchema.
 * Diseñado para no romper en jsdom: si faltan APIs de navegador, resuelve sin lanzar.
 */

export interface DashboardExportMeta {
  name: string;
  objective: string;
  businessQuestions: string[];
  filtersLabel: string;
  checksLabel: string;
  paletteName: string;
  governance: string;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

export const serializeDashboardSvg = (svg: SVGSVGElement): string | null => {
  try {
    if (typeof XMLSerializer === 'undefined') return null;
    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute('xmlns', SVG_NS);
    clone.setAttribute('font-family', 'Arial, Helvetica, sans-serif');
    return new XMLSerializer().serializeToString(clone);
  } catch {
    return null;
  }
};

const loadImage = (src: string, timeoutMs = 900): Promise<HTMLImageElement | null> =>
  new Promise((resolve) => {
    let settled = false;
    const done = (img: HTMLImageElement | null) => {
      if (!settled) {
        settled = true;
        resolve(img);
      }
    };
    try {
      const timer = setTimeout(() => done(null), timeoutMs);
      const img = new Image();
      img.onload = () => {
        clearTimeout(timer);
        done(img);
      };
      img.onerror = () => {
        clearTimeout(timer);
        done(null);
      };
      img.src = src;
    } catch {
      done(null);
    }
  });

export const svgToPngDataUrl = async (svg: SVGSVGElement, scale = 3): Promise<string | null> => {
  try {
    const xml = serializeDashboardSvg(svg);
    if (!xml) return null;
    if (typeof Blob === 'undefined' || typeof URL === 'undefined' || typeof URL.createObjectURL === 'undefined') {
      return null;
    }
    const blob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    try {
      const img = await loadImage(url);
      if (!img) return null;
      const vb = svg.viewBox?.baseVal;
      const w = vb && vb.width > 0 ? vb.width : 1600;
      const h = vb && vb.height > 0 ? vb.height : 1240;
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(w * scale);
      canvas.height = Math.round(h * scale);
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('image/png');
    } finally {
      URL.revokeObjectURL(url);
    }
  } catch {
    return null;
  }
};

export const downloadBlob = (blob: Blob, filename: string): void => {
  try {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    /* jsdom o navegador sin soporte: no rompe la app */
  }
};

export const downloadDataUrl = (dataUrl: string, filename: string): void => {
  try {
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch {
    /* no-op */
  }
};

const safeBlueprintId = (id: string): string => id.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 48) || 'dashboard';

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

export const exportDashboardPng = async (svg: SVGSVGElement | null, blueprintId: string): Promise<boolean> => {
  if (!svg) return false;
  const dataUrl = await svgToPngDataUrl(svg, 3);
  if (!dataUrl) return false;
  downloadDataUrl(dataUrl, `dashboard_${safeBlueprintId(blueprintId)}.png`);
  return true;
};

export const exportDashboardPdf = async (
  svg: SVGSVGElement | null,
  blueprintId: string,
  meta?: DashboardExportMeta,
): Promise<boolean> => {
  if (!svg) return false;
  const dataUrl = await svgToPngDataUrl(svg, 3);
  if (!dataUrl) return false;
  try {
    const { jsPDF } = await import('jspdf');
    const pdf = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = 28;
    const titleH = meta ? 44 : 12;
    if (meta) {
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(14);
      pdf.setTextColor(15, 23, 42);
      pdf.text(meta.name.slice(0, 90), margin, 30);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(9);
      pdf.setTextColor(71, 85, 105);
      pdf.text(meta.objective.slice(0, 140), margin, 44);
    }
    const img = await loadImage(dataUrl);
    const iw = img?.naturalWidth || 1600;
    const ih = img?.naturalHeight || 1240;
    const availW = pageW - margin * 2;
    const availH = pageH - margin - titleH - 18;
    const ratio = Math.min(availW / iw, availH / ih);
    const dw = iw * ratio;
    const dh = ih * ratio;
    const dx = margin + (availW - dw) / 2;
    const dy = titleH + margin / 2;
    pdf.addImage(dataUrl, 'PNG', dx, dy, dw, dh);
    pdf.setFontSize(8);
    pdf.setTextColor(100, 116, 139);
    const footer = meta
      ? `${meta.governance} · ${meta.checksLabel} · dashboard_${safeBlueprintId(blueprintId)}`
      : `dashboard_${safeBlueprintId(blueprintId)}`;
    pdf.text(footer.slice(0, 160), margin, pageH - 12);
    pdf.save(`dashboard_${safeBlueprintId(blueprintId)}.pdf`);
    return true;
  } catch {
    return false;
  }
};

export const exportDashboardHtml = async (
  svg: SVGSVGElement | null,
  blueprintId: string,
  meta?: DashboardExportMeta,
): Promise<boolean> => {
  if (!svg) return false;
  const xml = serializeDashboardSvg(svg);
  if (!xml) return false;
  try {
    const title = meta ? escapeHtml(meta.name) : `Dashboard ${escapeHtml(blueprintId)}`;
    const objective = meta ? escapeHtml(meta.objective) : '';
    const questions = (meta?.businessQuestions ?? []).slice(0, 5);
    const questionsHtml =
      questions.length > 0
        ? `<ol>${questions.map((q) => `<li>${escapeHtml(q)}</li>`).join('')}</ol>`
        : '';
    const html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${title} — DataFlow AI</title>
<style>
  body{margin:0;background:#f1f5f9;color:#0f172a;font-family:Arial,Helvetica,sans-serif;padding:24px;}
  .wrap{max-width:1280px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;}
  h1{font-size:22px;margin:0 0 6px 0;}
  p.obj{font-size:13px;color:#475569;margin:0 0 12px 0;}
  .meta{font-size:11px;color:#64748b;margin-bottom:12px;}
  ol{font-size:13px;color:#334155;}
  svg{width:100%;height:auto;display:block;border:1px solid #e2e8f0;border-radius:8px;}
  .foot{font-size:11px;color:#64748b;margin-top:12px;}
</style>
</head>
<body>
<div class="wrap">
<h1>${title}</h1>
${objective ? `<p class="obj">${objective}</p>` : ''}
${meta ? `<div class="meta">${escapeHtml(meta.checksLabel)} · ${escapeHtml(meta.paletteName)}</div>` : ''}
${xml}
${questionsHtml ? `<h2 style="font-size:14px;margin:16px 0 8px 0;">Preguntas de negocio</h2>${questionsHtml}` : ''}
${meta ? `<div class="foot">${escapeHtml(meta.governance)} · DataFlow AI · dashboard_${escapeHtml(safeBlueprintId(blueprintId))}</div>` : ''}
</div>
</body>
</html>`;
    downloadBlob(new Blob([html], { type: 'text/html;charset=utf-8' }), `dashboard_${safeBlueprintId(blueprintId)}.html`);
    return true;
  } catch {
    return false;
  }
};
