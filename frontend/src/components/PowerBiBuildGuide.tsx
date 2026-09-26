import React from 'react';
import { ListChecks, BookOpen, Palette, Calculator, Square, TrendingUp, Info } from 'lucide-react';
import { DashboardBlueprint } from '../types';
import { useLanguage } from '../context/LanguageContext';
import type { PowerBiGuideStep } from '../i18n';

interface Props {
  blueprint: DashboardBlueprint;
}

interface GuideSource {
  href: string;
  label: string;
}

/** Etiquetas en castellano (fallback para idiomas sin clave `powerBiGuide`). */
const DEFAULT_GUIDE = {
  title: 'Guía paso a paso: construye tu Dashboard en Power BI',
  subtitle:
    'Sigue estos pasos en Power BI Desktop o en el servicio Power BI para reproducir el diseño propuesto en el Blueprint, con los nombres reales de la interfaz de Microsoft.',
  governance: 'La IA propone, el usuario decide, Python ejecuta: aquí solo tienes instrucciones deterministas y verificables.',
  sourceNote:
    'Cada paso está verificado contra la documentación oficial de Microsoft Learn (consulta las fuentes al pie de la guía).',
  sourcesLabel: 'Fuentes oficiales',
  stepTag: 'Paso {n}',
  routeLabel: 'Ruta en Power BI',
  noteLabel: 'Importante',
  measuresLabel: 'Tus medidas DAX del Blueprint',
  paletteLabel: 'Colores de tu paleta',
  primaryColorLabel: 'Color del título',
  backgroundColorLabel: 'Color de fondo',
  srcMeasuresLabel: 'Medidas en Power BI Desktop',
  srcShapesLabel: 'Cuadros de texto y formas en informes',
  srcFormatLabel: 'Panel Formato: pestaña General',
  srcKpiLabel: 'Visuales KPI',
  step1: {
    title: 'Carga el modelo en Power BI',
    intro: 'Abre Power BI Desktop y trae el modelo que DataFlow AI ha preparado para ti antes de diseñar.',
    items: [
      'Opción A: Inicio → Obtener datos → Texto/CSV y selecciona el dataset limpio descargado en el Paso 4.',
      'Opción B: descarga el proyecto .pbip desde la pestaña Power BI de esta vista previa y ábrelo en Power BI Desktop.',
      'Comprueba en el panel Datos que las tablas del esquema estrella (hechos y dimensiones) aparecen con sus relaciones.',
    ],
  },
  step2: {
    title: 'Crea las fórmulas DAX: dónde y en qué tabla',
    intro: 'Las medidas son cálculos DAX que se guardan en el modelo y se usan en cualquier visualización.',
    route: 'Modeling → New measure',
    items: [
      'Con una tabla seleccionada en el panel Datos, pulsa Modeling → New measure (Nueva medida) y escribe la fórmula en la barra de fórmulas que se abre arriba.',
      'Las medidas aparecen en el panel Datos con un icono de calculadora; arrástralas a cualquier visualización como cualquier otro campo.',
      'Cada medida tiene una tabla principal (home table) que define en qué tabla de la lista Datos aparece; puedes cambiarla eligiendo otra tabla del modelo.',
      'Para organizarlas, crea una tabla especial solo de medidas: Entrar datos → tabla con una sola columna → traslada allí las medidas → oculta la columna (la tabla queda arriba en el panel Datos).',
    ],
    note: 'Pega aquí las medidas del Blueprint (pestaña Power BI): respeta sus nombres para que los visuales coincidan con la guía.',
  },
  step3: {
    title: 'Añade el rectángulo del título',
    intro: 'Un rectángulo con el título encabeza el layout del Blueprint (cabecera ejecutiva + franja de acento).',
    route: 'Insertar → Elementos → Formas',
    items: [
      'En la pestaña Insertar, sección Elementos, selecciona Formas y elige la forma de rectángulo en el menú desplegable.',
      'Escribe el título en un Cuadro de texto (Inicio → Insertar → Cuadro de texto) y colócalo sobre el rectángulo.',
      'Para colocarlo: arrastra el área gris de la parte superior; para redimensionarlo, arrastra los tiradores de tamaño.',
      'Para tamaño y posición exactos: con el objeto visual seleccionado, Formato visual → General → Propiedades → Tamaño (alto y ancho en píxeles) y Posición (horizontal y vertical en píxeles desde la esquina superior izquierda).',
    ],
  },
  step4: {
    title: 'Fondo de un color y bordes redondeados',
    intro: 'El panel Formato visual tiene dos pestañas: Visual (opciones del tipo de objeto visual) y General (comunes a casi todos los visuales).',
    route: 'Formato visual → General → Efectos',
    items: [
      'Fondo de un color: General → Efectos → Fondo → Color (usa el color de fondo de tu paleta) y pon la Transparencia al 0 %.',
      'Bordes redondeados: General → Efectos → Borde visual → actívalo y ajusta Color, radio de esquinas redondeadas y Ancho.',
      'El relleno propio de la forma se configura en la pestaña Visual del panel Formato visual, donde están las opciones específicas de cada tipo de objeto visual.',
      'Si quieres el título dentro del propio visual, también puedes usar General → Título (texto, fuente, color de texto y color de fondo).',
    ],
    note: 'Usa los colores de tu paleta para mantener el contraste WCAG validado en el Blueprint.',
  },
  step5: {
    title: 'Añade un KPI: dónde y de qué tipo',
    intro: 'El visual KPI comunica el progreso hacia un objetivo cuantificable: mide el avance y la distancia hasta la meta.',
    route: 'Panel Visualizaciones → icono KPI',
    items: [
      'Tipo de visual: KPI (icono KPI del panel Visualizaciones). Requiere una medida base que devuelva un valor, un valor objetivo y un umbral o meta.',
      'Campos: Valor = tu medida base (el indicador), Eje de tendencia = una columna de fecha (la tendencia) y Destino = la medida o valor objetivo.',
      'Ordena antes de convertir: Más opciones (...) → Ordenar eje → columna de fecha y Ordenar por eje → Orden ascendente; una vez convertido en KPI ya no hay opción de ordenación.',
      'Formato: icono del pincel (Dar formato al objeto visual) → Valor de llamada (unidades y decimales), Iconos (✓ verde / ! rojo), Eje de tendencia (Dirección → Más alto es mejor) y Etiqueta de destino.',
    ],
    note: 'Si el KPI no muestra el eje de tendencia, comprueba que la columna de Valor sea continua y no contenga valores NULL.',
  },
};

const cardStyle: React.CSSProperties = {
  padding: '16px',
  backgroundColor: 'var(--bg-card)',
  borderRadius: '10px',
  border: '1px solid var(--border-color)',
};

const routeStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '4px 10px',
  fontSize: '11.5px',
  fontWeight: 600,
  fontFamily: 'var(--font-mono)',
  color: 'var(--primary)',
  backgroundColor: 'rgba(14, 165, 233, 0.10)',
  border: '1px solid rgba(14, 165, 233, 0.30)',
  borderRadius: '6px',
  wordBreak: 'break-word',
};

const STEP_ICONS = [Calculator, Calculator, Square, Palette, TrendingUp];

const stepNumbered = (label: string, value: string): string => label.replace('{n}', value);

/**
 * Guía paso a paso (Paso 5) para construir el Dashboard en Power BI Desktop.
 * Todo el contenido procede de la documentación oficial de Microsoft Learn y
 * se personaliza con datos reales del Blueprint (medidas DAX y paleta).
 */
export const PowerBiBuildGuide: React.FC<Props> = ({ blueprint }) => {
  const { t, language } = useLanguage();
  const g = { ...DEFAULT_GUIDE, ...(t.powerBiGuide ?? {}) };
  const locale = language === 'en' ? 'en-us' : 'es-es';
  const doc = (path: string): string => `https://learn.microsoft.com/${locale}/power-bi/${path}`;

  const steps: PowerBiGuideStep[] = [g.step1, g.step2, g.step3, g.step4, g.step5];
  const measures = (blueprint.dax_measures ?? []).slice(0, 6);
  const palette = blueprint.design?.palette;
  const sources: GuideSource[] = [
    { href: doc('transform-model/desktop-measures'), label: g.srcMeasuresLabel },
    { href: doc('create-reports/power-bi-reports-add-text-and-shapes'), label: g.srcShapesLabel },
    { href: doc('visuals/power-bi-visualization-format-pane-overview'), label: g.srcFormatLabel },
    { href: doc('visuals/power-bi-visualization-kpi'), label: g.srcKpiLabel },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} data-testid="powerbi-guide">
      {/* Cabecera de la guía */}
      <div className="card" style={{ ...cardStyle, display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            backgroundColor: 'rgba(14, 165, 233, 0.10)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <ListChecks size={22} color="var(--primary)" />
        </div>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }} data-testid="powerbi-guide-title">
            {g.title}
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.55, margin: '8px 0 0 0' }}>{g.subtitle}</p>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, margin: '8px 0 0 0' }} data-testid="powerbi-guide-governance">
            {g.governance}
          </p>
          <p
            style={{
              fontSize: '12px',
              color: 'var(--accent-emerald)',
              lineHeight: 1.5,
              margin: '6px 0 0 0',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '6px',
            }}
            data-testid="powerbi-guide-source-note"
          >
            <Info size={13} style={{ marginTop: '2px', flexShrink: 0 }} />
            <span>{g.sourceNote}</span>
          </p>
        </div>
      </div>

      {/* Pasos 1-5 */}
      {steps.map((step, index) => {
        const Icon = STEP_ICONS[index] ?? ListChecks;
        const stepNo = index + 1;
        const isDaxStep = stepNo === 2;
        const isPaletteStep = stepNo === 4;
        return (
          <div key={step.title} className="card" style={cardStyle} data-testid={`powerbi-guide-step-${stepNo}`}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <div
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--primary)',
                  color: '#ffffff',
                  fontSize: '14px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
                data-testid={`powerbi-guide-step-${stepNo}-badge`}
              >
                {stepNo}
              </div>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <Icon size={16} color="var(--primary)" />
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {stepNumbered(g.stepTag, String(stepNo))}
                  </span>
                </div>
                <h4 style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-main)', margin: '6px 0 0 0' }}>{step.title}</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5, margin: '6px 0 0 0' }}>{step.intro}</p>

                {step.route && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '10px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>{g.routeLabel}:</span>
                    <code style={routeStyle} data-testid={`powerbi-guide-step-${stepNo}-route`}>
                      {step.route}
                    </code>
                  </div>
                )}

                <ol style={{ margin: '10px 0 0 0', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {step.items.map((item, i) => (
                    <li key={i} style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.55 }}>
                      {item}
                    </li>
                  ))}
                </ol>

                {/* Personalización con datos reales del Blueprint */}
                {isDaxStep && measures.length > 0 && (
                  <div style={{ marginTop: '10px', padding: '10px 12px', backgroundColor: 'var(--bg-input)', borderRadius: '8px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      {g.measuresLabel}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }} data-testid="powerbi-guide-measures">
                      {measures.map((measure) => (
                        <code
                          key={measure.name}
                          style={{
                            fontSize: '11px',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-main)',
                            backgroundColor: 'var(--bg-card)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            padding: '3px 8px',
                          }}
                        >
                          {measure.name}
                        </code>
                      ))}
                    </div>
                  </div>
                )}

                {isPaletteStep && (
                  <div style={{ marginTop: '10px', padding: '10px 12px', backgroundColor: 'var(--bg-input)', borderRadius: '8px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      {g.paletteLabel}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '8px' }} data-testid="powerbi-guide-palette">
                      {[
                        { label: g.primaryColorLabel, color: palette?.primary_color },
                        { label: g.backgroundColorLabel, color: palette?.background_color },
                      ].map((swatch) => (
                        <div key={swatch.label} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span
                            style={{
                              width: '22px',
                              height: '22px',
                              borderRadius: '6px',
                              backgroundColor: swatch.color || 'var(--bg-card)',
                              border: '1px solid var(--border-color)',
                              display: 'inline-block',
                            }}
                          />
                          <span style={{ fontSize: '12px', color: 'var(--text-main)' }}>{swatch.label}</span>
                          <code style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{swatch.color}</code>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {step.note && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '8px',
                      marginTop: '10px',
                      padding: '8px 12px',
                      fontSize: '12px',
                      lineHeight: 1.5,
                      color: 'var(--accent-amber)',
                      backgroundColor: 'rgba(245, 158, 11, 0.07)',
                      border: '1px solid rgba(245, 158, 11, 0.25)',
                      borderRadius: '8px',
                    }}
                    data-testid={`powerbi-guide-step-${stepNo}-note`}
                  >
                    <Info size={13} style={{ marginTop: '2px', flexShrink: 0 }} />
                    <span>
                      <strong>{g.noteLabel}:</strong> {step.note}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Fuentes oficiales de Microsoft Learn */}
      <div className="card" style={cardStyle} data-testid="powerbi-guide-sources">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BookOpen size={16} color="var(--primary)" />
          <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>{g.sourcesLabel}</h4>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
          {sources.map((source) => (
            <a
              key={source.href}
              href={source.href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: '12.5px', color: 'var(--primary)', textDecoration: 'none' }}
            >
              {source.label} ↗
            </a>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PowerBiBuildGuide;
