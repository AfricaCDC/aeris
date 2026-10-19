/**
 * AERIS: Excel exports for the logistics team (see AerisExportService).
 *   /aerisExport/index         form page
 *   /aerisExport/stockCard     MCM stock cards (.xlsx) for one warehouse
 *   /aerisExport/consolidated  stock on hand + transactions across warehouses (.xlsx)
 **/
package org.pih.warehouse.report

import org.pih.warehouse.core.Location
import org.pih.warehouse.product.Product

import java.text.SimpleDateFormat

class AerisExportController {

    static final String XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    AerisExportService aerisExportService

    def index() {
        List<Map> depots = aerisExportService.listDepots()
        String current = session.warehouse?.id
        [depots      : depots,
         currentDepot: depots.find { it.id == current }?.id ?: depots ? depots.first().id : null,
         products    : Product.findAllByActive(true, [sort: 'productCode']),
         startDate   : firstDayOfYear().format('yyyy-MM-dd'),
         endDate     : new Date().format('yyyy-MM-dd')]
    }

    def stockCard() {
        Map depot = aerisExportService.listDepots().find { it.id == (params.locationId ?: session.warehouse?.id) }
        if (!depot) {
            flash.message = "Choose a warehouse"
            redirect(action: 'index')
            return
        }
        Date start = parseDate(params.startDate) ?: firstDayOfYear()
        Date end = parseDate(params.endDate) ?: new Date().clearTime()
        String productId = params.productId ?: null
        String lot = params.lotNumber?.trim() ?: null
        byte[] xlsx = aerisExportService.stockCardWorkbook(depot, start, end, productId, lot, session.user?.name)
        String product = productId ? (Product.get(productId)?.productCode ?: '') + ' ' : ''
        send(xlsx, "Stock cards - ${depot.name} - ${product}${end.format('yyyy-MM-dd')}.xlsx")
    }

    def consolidated() {
        List<Map> all = aerisExportService.listDepots()
        List<String> chosen = (params.list('locationIds') ?: []) as List<String>
        List<Map> depots = chosen ? all.findAll { chosen.contains(it.id) } : all
        Date start = parseDate(params.startDate) ?: firstDayOfYear()
        Date end = parseDate(params.endDate) ?: new Date().clearTime()
        byte[] xlsx = aerisExportService.consolidatedWorkbook(depots, start, end, session.user?.name)
        send(xlsx, "AERIS stock - all warehouses - ${end.format('yyyy-MM-dd')}.xlsx")
    }

    private void send(byte[] xlsx, String filename) {
        String safe = filename.replaceAll(/[\\\/:*?"<>|]/, '-')
        response.contentType = XLSX
        response.setHeader("Content-Disposition",
                "attachment; filename=\"${safe.replaceAll(/[^\x20-\x7E]/, '_')}\"; filename*=UTF-8''${URLEncoder.encode(safe, 'UTF-8').replace('+', '%20')}")
        response.contentLength = xlsx.length
        response.outputStream << xlsx
        response.outputStream.flush()
    }

    private static Date parseDate(String value) {
        if (!value) {
            return null
        }
        try {
            SimpleDateFormat f = new SimpleDateFormat('yyyy-MM-dd')
            f.lenient = false
            return f.parse(value)
        } catch (Exception ignored) {
            return null
        }
    }

    private static Date firstDayOfYear() {
        Calendar c = Calendar.getInstance()
        c.clearTime()
        c.set(Calendar.DAY_OF_YEAR, 1)
        return c.time
    }
}
