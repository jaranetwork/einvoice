# Módulo en desarrollo ERPNEXT para el sistema FEPY

Envía datos de facturación de ERPNext al sistema FEPY para la generación de XML, KUDE y el envío de datos al sistema SIFEN Paraguay.

---

## Características

- ✅ Campos reequeridos para facturación electrónica con SIFEN Paraguay
- ✅ Generación automática de XML y KUDE en el sistema FEPY
- ✅ Validación de campos requeridos antes del envío
- ✅ Soporte para todos los tipos de operación (B2B, B2C, B2G, B2F)
- ✅ Descarga de documentos desde Sales Invoice

---

## Requisitos
- Frappe Framework v15 docker
- ERPNext v15
- Timbrado habilitado en SET

---

## Instalación

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO
bench install-app einvoice
bench clear-cache
```

## Inicio Rápido

1. **Configurar E-Invoice Setting**: Habilitar y configurar API Endpoint + API Key del sistema FEPY
2. **Configurar Company**: RUC, Timbrado, Actividades Económicas, Responsable SIFEN
3. **Configurar Customer**: sifen_tipo_documento, sifen_tipo_impuesto
4. **Configurar Items**: Item Tax Template con sifen_tipo_iva

Ver [Documentación Completa](einvoice/docs/00_index.md) para más detalles.

---

## Uso

1. Crear Sales Invoice
2. Validar factura (Submit)
3. Menú E-Invoice → Send to FEPY
4. Descargar XML/KUDE

---

## Documentación

La documentación completa está disponible en:
- [docs/00_index.md](einvoice/docs/00_index.md) - Índice y guía completa
- [docs/01_quick_start.md](einvoice/docs/01_quick_start.md) - Inicio rápido
- [docs/09_troubleshooting.md](einvoice/docs/09_troubleshooting.md) - Solución de problemas

---

## Proyectos

Este módulo trabaja con el sistema FEPY:
- [FEPY backend](https://github.com/jaranetwork/fepy-backend)
- [FEPY frontend - Interfaz web](https://github.com/jaranetwork/fepy-frontend)

---

**Soporte**: Para reportar errores o solicitar funcionalidades, por favor crear un issue en el repositorio.
