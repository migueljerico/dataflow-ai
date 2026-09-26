import React from 'react';
import { ListChecks, BookOpen, Palette, Calculator, Square, TrendingUp, Info, BarChart3, Filter, CheckCircle2 } from 'lucide-react';
import { DashboardBlueprint, VisualType, VisualRecommendation } from '../types';
import { useLanguage } from '../context/LanguageContext';
import type { PowerBiGuideStep, PowerBiVisualRecipe } from '../i18n';

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
  srcOverviewLabel: 'Información general de visualizaciones',
  srcSlicersLabel: 'Introducción a las segmentaciones',
  srcShareLabel: 'Compartir y colaborar en informes y paneles',
  visualsLabel: 'Tus visuales del Blueprint (pestaña Visuales)',
  visualFieldsLabel: 'Campos',
  kpisLabel: 'Tus KPIs del Blueprint',
  filtersLabel: 'Tus filtros del Blueprint (pestaña Resumen)',
  filterValuesLabel: 'Valores recomendados',
  questionsLabel: 'Preguntas de negocio que debe responder',
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
  step6: {
    title: 'Crea los visuales de la pestaña Visuales',
    intro: 'Visuales propone un tipo concreto para cada pregunta de negocio. Para cada tipo presente en tu Blueprint tienes abajo su receta: nombre real del icono, ruta en la interfaz, campos que hay que arrastrar y su artículo oficial de Microsoft Learn.',
    route: 'Panel Visualizaciones → icono del tipo de visual',
    items: [
      'Pulsa el icono del tipo de visual indicado en la receta (panel Visualizaciones) y arrastra desde el panel Datos los campos del visual a los pozos de campo: dimensión en el eje de categorías, medida en Valores y campo de leyenda si la receta lo indica.',
      'Crea un visual por cada título de la pestaña Visuales: así el informe cubre exactamente las mismas preguntas que la pestaña Resumen.',
      'Ordena antes de formatear: Más opciones (...) → Ordenar → Ordenar por valor → Orden descendente; si el visual es un ranking, aplica un filtro de nivel superior (Top N) desde el panel Filtros.',
      'Aplica la paleta del Blueprint en Formato visual → General (Título y propiedades) y en Colores de datos para mantener el contraste WCAG validado en la pestaña Diseño.',
    ],
    note: 'No renombres campos ni medidas del Blueprint: los visuales se construyen con los mismos nombres para que todo el Dashboard sea coherente.',
  },
  step7: {
    title: 'Añade las segmentaciones (slicers) de tus filtros',
    intro: 'Los filtros del Blueprint se materializan como segmentaciones visibles en el lienzo y como filtros de página o de objeto visual en el panel Filtros.',
    route: 'Panel Visualizaciones → icono Segmentación de datos (Slicer)',
    items: [
      'Crea una segmentación por cada filtro de la lista inferior: selecciona el icono Segmentación de datos (Slicer) del panel Visualizaciones y arrastra el campo indicado (tabla y columna del Blueprint).',
      'Elige el estilo en Formato visual → Visual: lista vertical, lista desplegable o selección de fechas según el tipo de campo.',
      'Aplica los valores recomendados del Blueprint como valores iniciales y activa Selección única cuando el filtro no admita varios valores.',
      'Los filtros que no deben verse en el lienzo van al panel Filtros (filtros de página y de objeto visual): están ocultos hasta que el autor los abre, mientras que las segmentaciones siempre son visibles e interactivas.',
    ],
    note: 'Segmentaciones y panel Filtros se complementan: segmentaciones para los filtros frecuentes que verá el usuario y panel Filtros para el filtrado complejo del autor.',
  },
  step8: {
    title: 'Verifica las preguntas de negocio y comparte el informe',
    intro: 'Antes de publicar, comprueba que cada pregunta de negocio del Blueprint tiene su visual y su medida en el informe.',
    route: 'Inicio → Publicar',
    items: [
      'Recorre la lista inferior de preguntas de negocio (pestaña Resumen) y confirma que cada una tiene un visual de la pestaña Visuales que la responde con la medida indicada.',
      'Revisa las comprobaciones de validación del Blueprint antes de compartir: si hay avisos, explicalos en el informe o corrige los datos en el origen.',
      'Publica el informe: Inicio → Publicar y elige tu espacio de trabajo en el servicio Power BI; después comparte el enlace con permisos de lectura.',
      'Si cambian los datos, vuelve a generar el Blueprint en DataFlow AI en lugar de editar el modelo a mano: la IA propone, tú apruebas y Power BI ejecuta.',
    ],
    note: 'Guarda junto al informe publicado el .pbip descargado de la pestaña Power BI: es la fuente determinista del modelo y de las medidas.',
  },
  visualTypes: {
    bar: {
      name: 'Gráfico de columnas (barras verticales)',
      route: 'Panel Visualizaciones → icono Gráfico de columnas agrupadas',
      items: [
        'Eje X (categorías) = la dimensión del visual; Valores = la medida. Cada columna es una categoría y su altura, el valor.',
        'Ordena por valor: Más opciones (...) → Ordenar → Ordenar por valor → Orden descendente para leer la comparación de un vistazo.',
        'Si los nombres de categoría son largos, cambia al icono Gráfico de barras agrupadas (barras horizontales): Microsoft recomienda las barras cuando las etiquetas de categoría son largas.',
      ],
      srcLabel: 'Gráficos de columnas en Power BI',
    },
    horizontal_bar: {
      name: 'Gráfico de barras horizontales (ranking)',
      route: 'Panel Visualizaciones → icono Gráfico de barras agrupadas',
      items: [
        'Eje Y = la dimensión del ranking; Valores = la medida. Las barras horizontales dejan leer con calma etiquetas largas.',
        'Ordena por valor descendente (Más opciones (...) → Ordenar → Ordenar por valor) y limita las categorías con un filtro de nivel superior (Top N) del panel Filtros.',
        'Añade etiquetas de datos: Formato visual → Etiquetas de datos → activar, para leer cada valor sin seguir la escala del eje.',
      ],
      srcLabel: 'Gráficos de columnas en Power BI',
    },
    line: {
      name: 'Gráfico de líneas',
      route: 'Panel Visualizaciones → icono Gráfico de líneas',
      items: [
        'Eje X = la dimensión temporal (columna de fecha del Blueprint); Valores = la medida de la tendencia.',
        'Ordena la fecha de forma ascendente antes de leer la tendencia (Más opciones (...) → Ordenar → Orden ascendente).',
        'Las líneas enfatizan la forma general de los valores a lo largo del tiempo: úsalas para evolución y estacionalidad, no para comparar magnitudes puntuales.',
      ],
      srcLabel: 'Gráficos de líneas en Power BI',
    },
    area: {
      name: 'Gráfico de áreas',
      route: 'Panel Visualizaciones → icono Gráfico de áreas',
      items: [
        'El gráfico de áreas parte del gráfico de líneas y rellena el área entre la línea y el eje: comunica volumen además de tendencia.',
        'Campos igual que en líneas: eje X temporal y Valores con la medida; usa áreas apiladas solo si las series no se solapan.',
      ],
      srcLabel: 'Gráficos de áreas básicos en Power BI',
    },
    stacked_bar: {
      name: 'Gráfico apilado (columnas o barras)',
      route: 'Panel Visualizaciones → icono Gráfico de columnas apiladas',
      items: [
        'Eje de categorías = dimensión, Valores = medida y Leyenda = campo de serie para descomponer cada barra en sus partes.',
        'Elige Gráfico de columnas apiladas (vertical) o Gráfico de barras apiladas (horizontal) según la longitud de las etiquetas; existe también la variante 100 % apilada para comparar proporciones.',
      ],
      srcLabel: 'Gráficos de columnas en Power BI',
    },
    pie: {
      name: 'Gráfico circular',
      route: 'Panel Visualizaciones → icono Gráfico circular',
      items: [
        'Leyenda = la dimensión; Valores = la medida. Cada sector es la proporción de una categoría sobre el total.',
        'Muestra los porcentajes en las etiquetas: Formato visual → Etiquetas de datos → detalles de la etiqueta → porcentaje.',
      ],
      srcLabel: 'Gráficos circulares y de anillos',
    },
    donut: {
      name: 'Gráfico de anillos',
      route: 'Panel Visualizaciones → icono Gráfico de anillos',
      items: [
        'Mismos pozos que el circular: Leyenda = dimensión y Valores = medida; el agujero central deja espacio para el total.',
        'Mantén pocas categorías: con muchas series los sectores son difíciles de comparar; en ese caso usa un gráfico de barras.',
      ],
      srcLabel: 'Gráficos circulares y de anillos',
    },
    scatter: {
      name: 'Diagrama de dispersión (dispersión y burbujas)',
      route: 'Panel Visualizaciones → icono Gráfico de dispersión',
      items: [
        'Arrastra los campos a los pozos de campo: eje X = primera columna numérica, eje Y = segunda y Leyenda = la dimensión que colorea los puntos.',
        'Con Detalle y Tamaño conviertes el gráfico en burbujas: el tamaño de la burbuja pasa a ser una tercera medida.',
        'Añade una línea de tendencia desde el panel Análisis para leer la correlación entre ambos ejes.',
      ],
      srcLabel: 'Gráficos de dispersión y burbujas',
    },
    histogram: {
      name: 'Histograma (discretización + columnas)',
      route: 'Panel Datos → clic derecho en la columna → Nuevo grupo',
      items: [
        'Power BI no incluye un visual de histograma: se construye con discretización (binning). En el panel Datos, haz clic derecho en la columna numérica y elige Nuevo grupo.',
        'En el cuadro de diálogo Grupos, establece el tamaño del intervalo y pulsa Aceptar: aparece un campo nuevo en el panel Datos con «(discretizaciones)» añadido.',
        'Crea un Gráfico de columnas agrupadas con la columna de intervalos en el eje X y el recuento (o la medida) en Valores, y ordena los intervalos de menor a mayor.',
      ],
      srcLabel: 'Agrupación y discretización en Power BI Desktop',
    },
    table: {
      name: 'Tabla',
      route: 'Panel Visualizaciones → icono Tabla',
      items: [
        'Arrastra las dimensiones y las medidas a la sección de campos: cada campo se convierte en una columna de la tabla.',
        'Da formato numérico desde el menú desplegable del campo (formato de número) y resalta condiciones con formato condicional (barra de datos o iconos).',
      ],
      srcLabel: 'Visualizaciones de tabla en Power BI',
    },
    kpi_card: {
      name: 'Indicador (KPI)',
      route: 'Panel Visualizaciones → icono KPI',
      items: [
        'Sigue el Paso 5 de esta guía: Valor = la medida del Blueprint, Eje de tendencia = columna de fecha y Destino = la meta.',
        'Usa el mismo título que aparece en la pestaña Resumen para que el KPI del informe se identifique con el del Blueprint.',
      ],
      srcLabel: 'Visuales KPI',
    },
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

const STEP_ICONS = [Calculator, Calculator, Square, Palette, TrendingUp, BarChart3, Filter, CheckCircle2];

const blockStyle: React.CSSProperties = {
  marginTop: '10px',
  padding: '10px 12px',
  backgroundColor: 'var(--bg-input)',
  borderRadius: '8px',
};

const blockLabelStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 700,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const chipStyle: React.CSSProperties = {
  fontSize: '11px',
  fontFamily: 'var(--font-mono)',
  color: 'var(--text-main)',
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  padding: '3px 8px',
};

/** Artículo verificado de Microsoft Learn para cada tipo de visual del Blueprint. */
const VISUAL_DOC: Record<VisualType, string> = {
  bar: 'visuals/power-bi-visualization-column-charts',
  horizontal_bar: 'visuals/power-bi-visualization-column-charts',
  stacked_bar: 'visuals/power-bi-visualization-column-charts',
  line: 'visuals/power-bi-line-chart',
  area: 'visuals/power-bi-visualization-basic-area-chart',
  pie: 'visuals/power-bi-visualization-pie-donut-chart',
  donut: 'visuals/power-bi-visualization-pie-donut-chart',
  scatter: 'visuals/power-bi-visualization-scatter',
  histogram: 'create-reports/desktop-grouping-and-binning',
  table: 'visuals/power-bi-visualization-tables',
  kpi_card: 'visuals/power-bi-visualization-kpi',
};

const stepNumbered = (label: string, value: string): string => label.replace('{n}', value);

/**
 * Guía paso a paso (Paso 5) para construir el Dashboard en Power BI Desktop.
 * Todo el contenido procede de la documentación oficial de Microsoft Learn y
 * se personaliza con datos reales del Blueprint (medidas DAX, KPIs, paleta,
 * visuales por tipo, filtros y preguntas de negocio), de modo que la guía
 * explica exactamente las mismas propuestas del resto de pestañas.
 */
export const PowerBiBuildGuide: React.FC<Props> = ({ blueprint }) => {
  const { t, language } = useLanguage();
  const g = { ...DEFAULT_GUIDE, ...(t.powerBiGuide ?? {}) };
  const locale = language === 'en' ? 'en-us' : 'es-es';
  const doc = (path: string): string => `https://learn.microsoft.com/${locale}/power-bi/${path}`;

  const steps: PowerBiGuideStep[] = [g.step1, g.step2, g.step3, g.step4, g.step5, g.step6, g.step7, g.step8];
  const measures = (blueprint.dax_measures ?? []).slice(0, 6);
  const palette = blueprint.design?.palette;
  const kpis = (blueprint.kpis ?? []).filter((kpi) => !kpi.hidden).slice(0, 6);
  const filters = (blueprint.filters ?? []).filter((filter) => !filter.hidden).slice(0, 6);
  const questions = (blueprint.business_questions ?? []).slice(0, 6);
  const recipes: Partial<Record<VisualType, PowerBiVisualRecipe>> = g.visualTypes ?? {};
  /** Tipos de visual propuestos agrupados en el mismo orden en que aparecen. */
  const visualGroups: Array<{ type: VisualType; items: VisualRecommendation[] }> = [];
  for (const visual of blueprint.visuals ?? []) {
    if (visual.hidden) continue;
    const group = visualGroups.find((entry) => entry.type === visual.visual_type);
    if (group) group.items.push(visual);
    else visualGroups.push({ type: visual.visual_type, items: [visual] });
  }

  const sources: GuideSource[] = [
    { href: doc('transform-model/desktop-measures'), label: g.srcMeasuresLabel },
    { href: doc('create-reports/power-bi-reports-add-text-and-shapes'), label: g.srcShapesLabel },
    { href: doc('visuals/power-bi-visualization-format-pane-overview'), label: g.srcFormatLabel },
    { href: doc('visuals/power-bi-visualization-kpi'), label: g.srcKpiLabel },
    { href: doc('visuals/power-bi-visualizations-overview'), label: g.srcOverviewLabel },
    { href: doc('visuals/power-bi-visualization-slicers'), label: g.srcSlicersLabel },
    { href: doc('collaborate-share/service-share-dashboards'), label: g.srcShareLabel },
  ];
  // Fuentes dinámicas: solo los artículos de los tipos de visual presentes en el Blueprint.
  const seenSources = new Set(sources.map((source) => source.href));
  for (const group of visualGroups) {
    const href = doc(VISUAL_DOC[group.type]);
    if (seenSources.has(href)) continue;
    seenSources.add(href);
    sources.push({ href, label: recipes[group.type]?.srcLabel ?? g.srcOverviewLabel });
  }

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

      {/* Pasos 1-8 */}
      {steps.map((step, index) => {
        const Icon = STEP_ICONS[index] ?? ListChecks;
        const stepNo = index + 1;
        const isDaxStep = stepNo === 2;
        const isPaletteStep = stepNo === 4;
        const isKpiStep = stepNo === 5;
        const isVisualsStep = stepNo === 6;
        const isFiltersStep = stepNo === 7;
        const isQuestionsStep = stepNo === 8;
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

                {/* Personalización con los KPIs reales del Blueprint (pestaña Resumen) */}
                {isKpiStep && kpis.length > 0 && (
                  <div style={blockStyle}>
                    <div style={blockLabelStyle}>{g.kpisLabel}</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }} data-testid="powerbi-guide-kpis">
                      {kpis.map((kpi) => (
                        <code key={kpi.kpi_id} style={chipStyle}>
                          {kpi.title} · {kpi.dax_measure_name}
                        </code>
                      ))}
                    </div>
                  </div>
                )}

                {/* Receta por cada tipo de visual propuesto en la pestaña Visuales */}
                {isVisualsStep && visualGroups.length > 0 && (
                  <div style={blockStyle}>
                    <div style={blockLabelStyle}>{g.visualsLabel}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }} data-testid="powerbi-guide-visuals">
                      {visualGroups.map((group) => {
                        const recipe = recipes[group.type];
                        return (
                          <div
                            key={group.type}
                            style={{ padding: '10px 12px', backgroundColor: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                            data-testid={`powerbi-guide-visual-recipe-${group.type}`}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>{recipe?.name ?? group.type}</span>
                              {recipe && (
                                <code style={routeStyle} data-testid={`powerbi-guide-visual-recipe-${group.type}-route`}>
                                  {recipe.route}
                                </code>
                              )}
                            </div>
                            <ol style={{ margin: '8px 0 0 0', paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {(recipe?.items ?? []).map((item, i) => (
                                <li key={i} style={{ fontSize: '12.5px', color: 'var(--text-main)', lineHeight: 1.5 }}>
                                  {item}
                                </li>
                              ))}
                            </ol>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px' }}>
                              {group.items.map((visual) => (
                                <div key={visual.visual_id} style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.45 }}>
                                  <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{visual.title}</span>
                                  {(visual.fields ?? []).length > 0 && (
                                    <span>
                                      {' '}
                                      · {g.visualFieldsLabel}: {(visual.fields ?? []).join(', ')}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                            {recipe && (
                              <a
                                href={doc(VISUAL_DOC[group.type])}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ display: 'inline-block', marginTop: '8px', fontSize: '12px', color: 'var(--primary)', textDecoration: 'none' }}
                                data-testid={`powerbi-guide-visual-recipe-${group.type}-src`}
                              >
                                {recipe.srcLabel} ↗
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Filtros del Blueprint convertidos en segmentaciones (pestaña Resumen) */}
                {isFiltersStep && filters.length > 0 && (
                  <div style={blockStyle}>
                    <div style={blockLabelStyle}>{g.filtersLabel}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }} data-testid="powerbi-guide-filters">
                      {filters.map((filter) => (
                        <div key={filter.filter_id} style={{ padding: '8px 10px', backgroundColor: 'var(--bg-card)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{filter.label}</div>
                          <code style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>
                            {filter.table_ref}.{filter.column}
                          </code>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                            {g.filterValuesLabel}: {filter.recommended_values.slice(0, 3).join(', ')}
                            {filter.recommended_values.length > 3 && ` +${filter.recommended_values.length - 3}`}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Preguntas de negocio que el informe debe responder (pestaña Resumen) */}
                {isQuestionsStep && questions.length > 0 && (
                  <div style={blockStyle}>
                    <div style={blockLabelStyle}>{g.questionsLabel}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }} data-testid="powerbi-guide-questions">
                      {questions.map((question) => (
                        <div
                          key={question.question_id}
                          style={{ fontSize: '12.5px', color: 'var(--text-main)', lineHeight: 1.45, padding: '6px 8px', backgroundColor: 'var(--bg-card)', borderRadius: '6px' }}
                        >
                          {question.text}
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
