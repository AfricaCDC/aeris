/**
 * AERIS: Excel exports for the Africa CDC logistics team.
 *
 *  - Stock cards in the MCM "Ebola Response Stock Card" layout: one card (sheet) per item and batch at a warehouse,
 *    with opening balance, chronological receipts/issues and running balance.
 *  - A consolidated workbook across warehouses: stock on hand by lot, product x warehouse totals, transactions.
 *
 * Ledger rules (same as OpenBoxes stock history): CREDIT adds, DEBIT removes, INVENTORY sets the listed lots,
 * PRODUCT_INVENTORY sets the listed lots and zeroes the product's other lots (a no-op for count baselines).
 **/
package org.pih.warehouse.report

import groovy.sql.GroovyRowResult
import groovy.sql.Sql
import org.apache.poi.ss.usermodel.BorderStyle
import org.apache.poi.ss.usermodel.Cell
import org.apache.poi.ss.usermodel.CellStyle
import org.apache.poi.ss.usermodel.FillPatternType
import org.apache.poi.ss.usermodel.Font
import org.apache.poi.ss.usermodel.HorizontalAlignment
import org.apache.poi.ss.usermodel.IndexedColors
import org.apache.poi.ss.usermodel.Row
import org.apache.poi.ss.usermodel.Sheet
import org.apache.poi.ss.usermodel.VerticalAlignment
import org.apache.poi.ss.util.CellRangeAddress
import org.apache.poi.xssf.usermodel.XSSFCellStyle
import org.apache.poi.xssf.usermodel.XSSFColor
import org.apache.poi.xssf.usermodel.XSSFWorkbook

import javax.sql.DataSource
import java.awt.Color

class AerisExportService {

    static transactional = false

    DataSource dataSource

    static final String RECEPTION = "Réception"
    static final String DISTRIBUTION = "Distribution"
    static final String TRANSFER_IN = "Transfert entrant"
    static final String TRANSFER_OUT = "Transfert sortant"
    static final String RETURN = "Retour"
    static final String ADJ_PLUS = "Ajustement +"
    static final String ADJ_MINUS = "Ajustement -"
    static final String LOSS = "Perte / destruction"
    static final List<String> LOSS_REASONS = ['DAMAGED', 'EXPIRED', 'STOLEN', 'LOST', 'DESTROYED', 'SCRAPPED', 'RECALLED', 'MISSING']

    static final int EXPIRY_WARNING_DAYS = 180

    // ------------------------------------------------------------------ data

    /** Depots (stock-managing warehouses) known to AERIS. */
    List<Map> listDepots() {
        sql().rows("""
            select l.id, l.name, l.location_number, l.inventory_id, lg.name as province,
                   trim(concat(coalesce(p.first_name, ''), ' ', coalesce(p.last_name, ''))) as custodian
            from location l
            join location_type lt on lt.id = l.location_type_id
            left join location_group lg on lg.id = l.location_group_id
            left join person p on p.id = l.manager_id
            where lt.location_type_code = 'DEPOT' and (l.active is null or l.active = 1)
            order by l.name""").collect { it as Map }
    }

    /**
     * Ledger rows for one warehouse, in date order, with running balances per lot.
     * @return [cards: [productId|lot -> [header..., opening, rows, closing]], rows: flat rows within the period]
     */
    Map ledger(Map depot, Date start, Date end, String productId = null, String lotNumber = null) {
        String query = """
            select t.id as tid, t.transaction_date, t.transaction_number, tt.name as type_name, tt.transaction_code as code,
                   src.name as src_name, slt.location_type_code as src_type, dst.name as dst_name, dlt.location_type_code as dst_type,
                   te.quantity, te.reason_code, coalesce(te.comments, t.comment) as remarks,
                   ii.lot_number, ii.expiration_date, bin.name as bin_name,
                   trim(concat(coalesce(u.first_name, ''), ' ', coalesce(u.last_name, ''))) as user_name,
                   coalesce(so.shipment_number, si.shipment_number, rq.request_number, t.transaction_number) as doc_ref,
                   pr.id as product_id, pr.product_code, pr.name as product_name, pr.unit_of_measure, pr.cold_chain,
                   c.name as category, syn.name as product_name_fr
            from transaction_entry te
            join transaction t on t.id = te.transaction_id
            join transaction_type tt on tt.id = t.transaction_type_id
            join inventory_item ii on ii.id = te.inventory_item_id
            join product pr on pr.id = ii.product_id
            left join category c on c.id = pr.category_id
            left join synonym syn on syn.product_id = pr.id and syn.locale = 'fr' and syn.synonym_type_code = 'DISPLAY_NAME'
            left join location src on src.id = t.source_id
            left join location_type slt on slt.id = src.location_type_id
            left join location dst on dst.id = t.destination_id
            left join location_type dlt on dlt.id = dst.location_type_id
            left join location bin on bin.id = te.bin_location_id
            left join person u on u.id = t.created_by_id
            left join shipment so on so.id = t.outgoing_shipment_id
            left join shipment si on si.id = t.incoming_shipment_id
            left join requisition rq on rq.id = t.requisition_id
            where t.inventory_id = :inventoryId and t.transaction_date < :endExclusive
              ${productId ? 'and pr.id = :productId' : ''}
            order by pr.product_code, t.transaction_date, t.date_created, t.id""".toString()
        Map params = [inventoryId: depot.inventory_id, endExclusive: end + 1]
        if (productId) {
            params.productId = productId
        }
        List<GroovyRowResult> entries = sql().rows(query, params)

        Map<String, Integer> levels = minLevels(depot.inventory_id as String)
        Map<String, Map> cards = [:]            // key product|lot
        List<Map> flat = []

        entries.groupBy { it.product_id }.each { String pid, List<GroovyRowResult> productEntries ->
            Map<String, Integer> balance = [:].withDefault { 0 }
            Map<String, GroovyRowResult> lotRow = [:]       // lot -> a row carrying its lot number and expiry
            // A count writes a baseline then adjustments a second later: tag those adjustments as count results
            List<Long> baselines = productEntries.findAll { it.code == 'PRODUCT_INVENTORY' }*.transaction_date*.time.unique()
            productEntries.groupBy { it.tid }.each { String tid, List<GroovyRowResult> txEntries ->
                txEntries.each { lotRow.putIfAbsent(lotKey(it), it) }
                GroovyRowResult t = txEntries.first()
                boolean inPeriod = !t.transaction_date.before(start)
                Map<String, Integer> delta = [:]
                String code = t.code
                if (code == 'CREDIT' || code == 'DEBIT') {
                    txEntries.each { e ->
                        int q = qty(e.quantity)
                        String lot = lotKey(e)
                        delta[lot] = (delta[lot] ?: 0) + (code == 'CREDIT' ? q : -q)
                    }
                } else {  // INVENTORY: listed lots; PRODUCT_INVENTORY: whole product
                    Map<String, Integer> counted = [:].withDefault { 0 }
                    txEntries.each { e -> String k = lotKey(e); counted.put(k, counted[k] + qty(e.quantity)) }
                    Set<String> lots = code == 'PRODUCT_INVENTORY' ? (balance.keySet() + counted.keySet()) : counted.keySet()
                    lots.each { lot -> delta[lot] = counted[lot] - balance[lot] }
                }
                delta.each { String lot, Integer d ->
                    GroovyRowResult e = txEntries.find { lotKey(it) == lot } ?: lotRow[lot]
                    Map card = cards.computeIfAbsent("${pid}|${lot}".toString()) { newCard(depot, e, lot, levels[pid]) }
                    if (!inPeriod) {
                        balance[lot] += d
                        card.opening = balance[lot]
                        return
                    }
                    balance[lot] += d
                    if (d == 0) {
                        return  // count that confirmed the balance (baseline): nothing moved
                    }
                    Map row = [
                            date       : t.transaction_date,
                            docRef     : t.doc_ref ?: t.transaction_number,
                            type       : label(t, e, d, code),
                            source     : d > 0 ? (code == 'CREDIT' ? t.src_name : null) : depot.name,
                            destination: d > 0 ? depot.name : (code == 'DEBIT' ? t.dst_name : null),
                            received   : d > 0 ? d : null,
                            issued     : d < 0 ? -d : null,
                            balance    : balance[lot],
                            lot        : e.lot_number,
                            expiry     : e.expiration_date,
                            bin        : e.bin_name,
                            user       : t.user_name,
                            remarks    : [e.reason_code, e.remarks ?: t.remarks,
                                          (code in ['INVENTORY', 'PRODUCT_INVENTORY'] || baselines.any { Math.abs((t.transaction_date as Date).time - it) <= 5000 }) ? 'Comptage / count' : null]
                                    .findAll { it }.join(' - '),
                            warehouse  : depot.name,
                            productCode: e.product_code,
                            productName: e.product_name,
                    ]
                    card.rows << row
                    card.received = qty(card.received) + qty(row.received)
                    card.issued = qty(card.issued) + qty(row.issued)
                    flat << row
                }
            }
            cards.findAll { it.key.startsWith(pid + '|') }.each { k, card -> card.closing = balance[card.lotKey] }
        }

        Map<String, Map> selected = lotNumber ? cards.findAll { it.value.lot == lotNumber } : cards
        // keep cards with stock or movement in the period
        selected = selected.findAll { k, c -> c.rows || c.opening || c.closing }
        return [cards: selected.values().sort { a, b -> a.productCode <=> b.productCode ?: (a.lot ?: '') <=> (b.lot ?: '') }, rows: flat]
    }

    /** Stock on hand by warehouse, product and lot (from the product availability table). */
    List<Map> stockOnHand(List<Map> depots) {
        if (!depots) {
            return []
        }
        Map<String, Map> byId = depots.collectEntries { [it.id, it] }
        String query = """
            select pa.location_id, pr.id as product_id, pr.product_code, pr.name as product_name, syn.name as product_name_fr,
                   c.name as category, pr.unit_of_measure, pr.cold_chain, pa.lot_number, ii.expiration_date,
                   sum(pa.quantity_on_hand) as qoh
            from product_availability pa
            join product pr on pr.id = pa.product_id
            left join inventory_item ii on ii.id = pa.inventory_item_id
            left join category c on c.id = pr.category_id
            left join synonym syn on syn.product_id = pr.id and syn.locale = 'fr' and syn.synonym_type_code = 'DISPLAY_NAME'
            where pa.location_id in (${depots.collect { '?' }.join(',')})
            group by pa.location_id, pr.id, pr.product_code, pr.name, syn.name, c.name, pr.unit_of_measure, pr.cold_chain,
                     pa.lot_number, ii.expiration_date
            having sum(pa.quantity_on_hand) <> 0
            order by pr.product_code, pa.lot_number""".toString()
        List<Map> rows = sql().rows(query, depots*.id as List<Object>).collect { it as Map }

        Map<String, Map<String, Map>> levels = [:]
        depots.each { d -> levels[d.id] = levelRows(d.inventory_id as String) }
        Date today = new Date().clearTime()
        rows.each { r ->
            Map d = byId[r.location_id]
            r.warehouse = d.name
            r.province = d.province
            Map lvl = levels[r.location_id][r.product_id]
            r.min = lvl?.min_quantity
            r.reorder = lvl?.reorder_quantity
            r.max = lvl?.max_quantity
            r.daysToExpiry = r.expiration_date ? ((r.expiration_date as Date) - today) : null
            r.expiryStatus = r.daysToExpiry == null ? 'No expiry' :
                    r.daysToExpiry < 0 ? 'Expired' : r.daysToExpiry <= EXPIRY_WARNING_DAYS ? 'Expires within 6 months' : 'OK'
        }
        // products at or below level per warehouse
        Map<String, Integer> totals = [:].withDefault { 0 }
        rows.each { String k = "${it.location_id}|${it.product_id}".toString(); totals.put(k, totals[k] + qty(it.qoh)) }
        rows.each { r ->
            int total = totals["${r.location_id}|${r.product_id}".toString()]
            r.productTotal = total
            r.levelStatus = levelStatus(total, r.min, r.reorder, r.max)
        }
        // products with a level set but no stock at all: stock-out lines
        depots.each { d ->
            levels[d.id].each { String pid, Map lvl ->
                if (!totals.containsKey("${d.id}|${pid}".toString()) && (lvl.min_quantity ?: 0) > 0) {
                    rows << [location_id: d.id, warehouse: d.name, province: d.province, product_id: pid, product_code: lvl.product_code,
                             product_name: lvl.product_name, product_name_fr: lvl.product_name_fr, category: lvl.category,
                             unit_of_measure: lvl.unit_of_measure, lot_number: null, expiration_date: null, qoh: 0, productTotal: 0,
                             min: lvl.min_quantity, reorder: lvl.reorder_quantity, max: lvl.max_quantity, daysToExpiry: null,
                             expiryStatus: '', levelStatus: 'Stock-out']
                }
            }
        }
        return rows.sort { a, b -> a.warehouse <=> b.warehouse ?: a.product_code <=> b.product_code ?: (a.lot_number ?: '') <=> (b.lot_number ?: '') }
    }

    // ------------------------------------------------------------------ workbooks

    /** MCM stock card workbook: an index sheet, then one card per item and batch. */
    byte[] stockCardWorkbook(Map depot, Date start, Date end, String productId, String lotNumber, String generatedBy) {
        Map ledger = ledger(depot, start, end, productId, lotNumber)
        XSSFWorkbook wb = new XSSFWorkbook()
        Styles s = new Styles(wb)

        Sheet index = wb.createSheet("Cards")
        title(index, s, "STOCK CARDS – ${depot.name}", 9)
        info(index, s, 1, "Period: ${fmt(start)} to ${fmt(end)}   ·   Generated by AERIS on ${fmt(new Date())} by ${generatedBy ?: ''}")
        header(index, s, 3, ["Card", "Item code", "Item description", "Batch / Lot No.", "Expiry date",
                              "Opening balance", "Quantity received", "Quantity issued", "Closing balance"])
        int r = 4
        Set<String> used = [] as Set
        ledger.cards.each { Map card ->
            String sheetName = uniqueSheetName("${card.productCode} ${card.lot ?: 'no lot'}", used)
            writeCard(wb.createSheet(sheetName), s, card, depot, start, end, generatedBy)
            Row row = index.createRow(r++)
            Cell link = row.createCell(0)
            link.setCellValue(sheetName)
            def hl = wb.creationHelper.createHyperlink(org.apache.poi.common.usermodel.HyperlinkType.DOCUMENT)
            hl.address = "'${sheetName}'!A1"
            link.hyperlink = hl
            link.cellStyle = s.link
            text(row, 1, card.productCode, s.cell); text(row, 2, card.productName, s.cell); text(row, 3, card.lot, s.cell)
            date(row, 4, card.expiry, s); num(row, 5, card.opening, s); num(row, 6, card.received, s)
            num(row, 7, card.issued, s); num(row, 8, card.closing, s)
        }
        if (!ledger.cards) {
            info(index, s, 4, "No stock or movement for this selection.")
        }
        widths(index, [14, 14, 44, 16, 12, 14, 14, 14, 14])
        index.createFreezePane(0, 4)
        return bytes(wb)
    }

    /** Consolidated workbook across warehouses. */
    byte[] consolidatedWorkbook(List<Map> depots, Date start, Date end, String generatedBy) {
        XSSFWorkbook wb = new XSSFWorkbook()
        Styles s = new Styles(wb)
        List<Map> soh = stockOnHand(depots)

        // 1. Stock on hand by lot
        Sheet sh = wb.createSheet("Stock on hand")
        title(sh, s, "STOCK ON HAND BY WAREHOUSE AND LOT – ${fmt(new Date())}", 18)
        List<String> cols = ["Warehouse", "Province", "Item code", "Item description", "Description (FR)", "Category", "Unit",
                             "Batch / Lot No.", "Expiry date", "Days to expiry", "Expiry status", "Quantity on hand",
                             "Total at warehouse", "Minimum", "Reorder point", "Maximum", "Stock level status", "Cold chain"]
        header(sh, s, 2, cols)
        int r = 3
        soh.each { m ->
            Row row = sh.createRow(r++)
            int c = 0
            text(row, c++, m.warehouse, s.cell); text(row, c++, m.province, s.cell); text(row, c++, m.product_code, s.cell)
            text(row, c++, m.product_name, s.cell); text(row, c++, m.product_name_fr, s.cell); text(row, c++, m.category, s.cell)
            text(row, c++, m.unit_of_measure, s.cell); text(row, c++, m.lot_number, s.cell); date(row, c++, m.expiration_date, s)
            num(row, c++, m.daysToExpiry, s)
            text(row, c++, m.expiryStatus, m.expiryStatus == 'Expired' ? s.bad : m.expiryStatus?.startsWith('Expires') ? s.warn : s.cell)
            num(row, c++, m.qoh, s); num(row, c++, m.productTotal, s); num(row, c++, m.min, s); num(row, c++, m.reorder, s)
            num(row, c++, m.max, s)
            text(row, c++, m.levelStatus, m.levelStatus in ['Stock-out', 'Below minimum'] ? s.bad : m.levelStatus == 'Below reorder point' ? s.warn : s.cell)
            text(row, c, (m.cold_chain as Boolean) ? 'Yes' : 'No', s.cell)
        }
        table(sh, 2, r - 1, cols.size())
        widths(sh, [26, 12, 14, 40, 40, 20, 10, 16, 12, 10, 20, 12, 12, 10, 10, 10, 18, 9])

        // 2. Product x warehouse totals
        Sheet pv = wb.createSheet("By product")
        List<String> names = depots*.name
        title(pv, s, "QUANTITY ON HAND – PRODUCT x WAREHOUSE", names.size() + 4)
        header(pv, s, 2, ["Item code", "Item description", "Unit"] + names + ["Total"])
        Map<String, Map> products = new TreeMap()
        soh.each { m ->
            Map p = products.computeIfAbsent(m.product_code as String) { [name: m.product_name, unit: m.unit_of_measure, q: [:].withDefault { 0 }] }
            p.q.put(m.warehouse, p.q[m.warehouse] + qty(m.qoh))
        }
        r = 3
        products.each { String code, Map p ->
            Row row = pv.createRow(r++)
            text(row, 0, code, s.cell); text(row, 1, p.name, s.cell); text(row, 2, p.unit, s.cell)
            names.eachWithIndex { String n, int i -> num(row, 3 + i, p.q[n], s) }
            num(row, 3 + names.size(), p.q.values().sum() ?: 0, s)
        }
        table(pv, 2, r - 1, names.size() + 4)
        widths(pv, [14, 44, 10] + names.collect { 18 } + [12])

        // 3. Transactions in the period
        Sheet tx = wb.createSheet("Transactions")
        title(tx, s, "TRANSACTIONS ${fmt(start)} – ${fmt(end)}", 15)
        List<String> tcols = ["Date", "Warehouse", "Source Document Reference", "Transaction Type", "Item code", "Item description",
                              "Batch / Lot No.", "Expiry Date", "Source / Supplier", "Destination / Receiving Unit",
                              "Quantity Received", "Quantity Issued", "Stock on Hand (lot)", "Handled By", "Remarks / Incident"]
        header(tx, s, 2, tcols)
        r = 3
        depots.each { d ->
            ledger(d, start, end).rows.sort { it.date }.each { m ->
                Row row = tx.createRow(r++)
                date(row, 0, m.date, s); text(row, 1, m.warehouse, s.cell); text(row, 2, m.docRef, s.cell); text(row, 3, m.type, s.cell)
                text(row, 4, m.productCode, s.cell); text(row, 5, m.productName, s.cell); text(row, 6, m.lot, s.cell); date(row, 7, m.expiry, s)
                text(row, 8, m.source, s.cell); text(row, 9, m.destination, s.cell); num(row, 10, m.received, s); num(row, 11, m.issued, s)
                num(row, 12, m.balance, s); text(row, 13, m.user, s.cell); text(row, 14, m.remarks, s.cell)
            }
        }
        table(tx, 2, r - 1, tcols.size())
        widths(tx, [12, 26, 18, 18, 14, 40, 16, 12, 28, 28, 12, 12, 12, 20, 30])

        // 4. About
        Sheet about = wb.createSheet("About")
        title(about, s, "AERIS – Africa CDC Emergency Response Inventory System", 2)
        [["Generated", "${fmt(new Date())} by ${generatedBy ?: ''}"],
         ["Warehouses", names.join(', ')],
         ["Transactions period", "${fmt(start)} to ${fmt(end)}"],
         ["Expiry status", "Expired; Expires within 6 months (${EXPIRY_WARNING_DAYS} days); OK; No expiry"],
         ["Stock level status", "Compares the product total at the warehouse with its minimum, reorder point and maximum"],
         ["Transaction types", "${RECEPTION}, ${DISTRIBUTION}, ${TRANSFER_IN}, ${TRANSFER_OUT}, ${RETURN}, ${ADJ_PLUS}, ${ADJ_MINUS}, ${LOSS} (MCM stock card vocabulary)"],
        ].eachWithIndex { List kv, int i ->
            Row row = about.createRow(2 + i)
            text(row, 0, kv[0], s.bold); text(row, 1, kv[1] as String, s.cell)
        }
        widths(about, [22, 110])
        wb.setSheetOrder("About", 3)
        return bytes(wb)
    }

    // ------------------------------------------------------------------ card sheet (MCM layout)

    private void writeCard(Sheet sh, Styles s, Map card, Map depot, Date start, Date end, String generatedBy) {
        title(sh, s, "STOCK CARD – MEDICAL COUNTERMEASURES | EBOLA RESPONSE", 14)
        field(sh, s, 2, 0, "Warehouse / Facility:", depot.name)
        field(sh, s, 2, 5, "Item Code:", card.productCode)
        field(sh, s, 2, 10, "Commodity Category:", card.category)
        field(sh, s, 3, 0, "Item Description:", card.productNameFr ? "${card.productName} / ${card.productNameFr}" : card.productName)
        field(sh, s, 3, 5, "Unit of Measure:", card.unit)
        field(sh, s, 3, 10, "Opening Stock Balance:", card.opening)
        field(sh, s, 4, 0, "Batch / Lot No.:", card.lot)
        field(sh, s, 4, 5, "Expiry Date:", card.expiry ? fmt(card.expiry as Date) : '')
        field(sh, s, 4, 10, "Minimum Stock Level:", card.min)
        field(sh, s, 5, 0, "Storage Conditions:", card.coldChain ? "Cold chain (2–8 °C)" : "Controlled ambient")
        field(sh, s, 5, 5, "Stock Custodian:", depot.custodian ?: '')
        field(sh, s, 5, 10, "Reporting Period:", "${fmt(start)} – ${fmt(end)}")

        header(sh, s, 7, ["No.", "Date", "Source Document Reference", "Transaction Type", "Source / Supplier",
                          "Destination / Receiving Unit", "Quantity Received", "Quantity Issued", "Stock on Hand",
                          "Batch / Lot No.", "Expiry Date", "Storage Location", "Handled By / Signature", "Remarks / Incident"])
        int r = 8
        card.rows.eachWithIndex { Map m, int i ->
            Row row = sh.createRow(r++)
            num(row, 0, i + 1, s); date(row, 1, m.date, s); text(row, 2, m.docRef, s.cell); text(row, 3, m.type, s.cell)
            text(row, 4, m.source, s.cell); text(row, 5, m.destination, s.cell); num(row, 6, m.received, s); num(row, 7, m.issued, s)
            num(row, 8, m.balance, s, s.boldNum); text(row, 9, m.lot, s.cell); date(row, 10, m.expiry, s); text(row, 11, m.bin, s.cell)
            text(row, 12, m.user, s.cell); text(row, 13, m.remarks, s.wrap)
        }
        Row total = sh.createRow(r + 1)
        text(total, 3, "Totals for the period / closing balance", s.boldRight)
        sh.addMergedRegion(new CellRangeAddress(r + 1, r + 1, 3, 5))
        num(total, 6, card.received, s, s.boldNum); num(total, 7, card.issued, s, s.boldNum); num(total, 8, card.closing, s, s.boldNum)
        Row foot = sh.createRow(r + 3)
        text(foot, 0, "Generated by AERIS on ${fmt(new Date())} by ${generatedBy ?: ''}. Physical count verified by: ____________________   Date: __________   Signature: __________", s.small)
        widths(sh, [6, 12, 20, 18, 26, 26, 12, 12, 12, 16, 12, 16, 22, 40])
        sh.createFreezePane(0, 8)
        sh.printSetup.landscape = true
        sh.fitToPage = true
        sh.printSetup.fitWidth = (short) 1
        sh.printSetup.fitHeight = (short) 0
    }

    // ------------------------------------------------------------------ helpers

    private Map newCard(Map depot, GroovyRowResult e, String lot, Integer min) {
        [productCode: e.product_code, productName: e.product_name, productNameFr: e.product_name_fr, category: e.category,
         unit: e.unit_of_measure, coldChain: e.cold_chain as Boolean, lot: e.lot_number, lotKey: lot, expiry: e.expiration_date,
         min: min, opening: 0, received: 0, issued: 0, closing: 0, rows: []]
    }

    /** SQL quantities arrive as BigDecimal/Long; never rely on 'as int' inside map arithmetic. */
    private static int qty(Object value) { value == null ? 0 : (value as Number).intValue() }

    private static String lotKey(GroovyRowResult e) { "${e.lot_number ?: ''}|${e.expiration_date ?: ''}" }

    private static String label(GroovyRowResult t, GroovyRowResult e, int delta, String code) {
        String reason = (e.reason_code ?: '').toString().toUpperCase()
        switch (t.type_name) {
            case 'Transfer In':
                return t.src_type == 'DEPOT' ? TRANSFER_IN : (t.src_type in [null, 'DONOR', 'SUPPLIER'] ? RECEPTION : RETURN)
            case 'Transfer Out':
                return t.dst_type == 'DEPOT' ? TRANSFER_OUT : DISTRIBUTION
            case 'Consumption':
                return DISTRIBUTION
            case 'Damaged':
            case 'Expired':
                return LOSS
            default:
                if (delta < 0 && LOSS_REASONS.any { reason.contains(it) }) {
                    return LOSS
                }
                return delta > 0 ? ADJ_PLUS : ADJ_MINUS
        }
    }

    private static String levelStatus(int total, Object min, Object reorder, Object max) {
        if (total <= 0) return 'Stock-out'
        if (min != null && total < qty(min)) return 'Below minimum'
        if (reorder != null && total < qty(reorder)) return 'Below reorder point'
        if (max != null && qty(max) > 0 && total > qty(max)) return 'Above maximum'
        return (min == null && reorder == null && max == null) ? 'No level set' : 'OK'
    }

    private Map<String, Integer> minLevels(String inventoryId) {
        levelRows(inventoryId).collectEntries { k, v -> [k, v.min_quantity as Integer] }
    }

    private Map<String, Map> levelRows(String inventoryId) {
        sql().rows("""
            select il.product_id, il.min_quantity, il.reorder_quantity, il.max_quantity, pr.product_code, pr.name as product_name,
                   syn.name as product_name_fr, c.name as category, pr.unit_of_measure
            from inventory_level il
            join product pr on pr.id = il.product_id
            left join category c on c.id = pr.category_id
            left join synonym syn on syn.product_id = pr.id and syn.locale = 'fr' and syn.synonym_type_code = 'DISPLAY_NAME'
            where il.inventory_id = :inv and il.internal_location_id is null""", [inv: inventoryId])
                .collectEntries { [it.product_id, it as Map] }
    }

    private Sql sql() { new Sql(dataSource) }

    private static String fmt(Date d) { d ? d.format('dd/MM/yyyy') : '' }

    private static String uniqueSheetName(String raw, Set<String> used) {
        String base = raw.replaceAll(/[\[\]\*\?\/\\:]/, '-').take(31)
        String name = base
        int n = 2
        while (used.contains(name.toLowerCase())) {
            String suffix = " (${n++})"
            name = base.take(31 - suffix.length()) + suffix
        }
        used << name.toLowerCase()
        return name
    }

    private static byte[] bytes(XSSFWorkbook wb) {
        ByteArrayOutputStream out = new ByteArrayOutputStream()
        wb.write(out)
        wb.close()
        return out.toByteArray()
    }

    private static void title(Sheet sh, Styles s, String value, int span) {
        Row row = sh.createRow(0)
        row.heightInPoints = 24
        Cell c = row.createCell(0)
        c.setCellValue(value)
        c.cellStyle = s.title
        (1..<Math.max(span, 2)).each { row.createCell(it).cellStyle = s.title }
        sh.addMergedRegion(new CellRangeAddress(0, 0, 0, Math.max(span, 2) - 1))
    }

    private static void info(Sheet sh, Styles s, int r, String value) {
        Row row = sh.getRow(r) ?: sh.createRow(r)
        text(row, 0, value, s.small)
    }

    private static void field(Sheet sh, Styles s, int r, int c, String label, Object value) {
        Row row = sh.getRow(r) ?: sh.createRow(r)
        text(row, c, label, s.label)
        Cell v = row.createCell(c + 2)
        if (value instanceof Number) {
            v.setCellValue((value as Number).doubleValue())
        } else {
            v.setCellValue(value != null ? value.toString() : '')
        }
        v.cellStyle = s.value
        row.createCell(c + 3).cellStyle = s.value
        row.createCell(c + 1).cellStyle = s.label
        sh.addMergedRegion(new CellRangeAddress(r, r, c + 2, c + 3))
    }

    private static void header(Sheet sh, Styles s, int r, List<String> names) {
        Row row = sh.createRow(r)
        row.heightInPoints = 30
        names.eachWithIndex { String n, int i -> text(row, i, n, s.header) }
    }

    private static void table(Sheet sh, int headerRow, int lastRow, int cols) {
        if (lastRow > headerRow) {
            sh.setAutoFilter(new CellRangeAddress(headerRow, lastRow, 0, cols - 1))
        }
        sh.createFreezePane(0, headerRow + 1)
    }

    private static void widths(Sheet sh, List<Integer> chars) {
        chars.eachWithIndex { int w, int i -> sh.setColumnWidth(i, w * 256) }
    }

    private static void text(Row row, int c, Object value, CellStyle style) {
        Cell cell = row.createCell(c)
        if (value != null && value != '') cell.setCellValue(value.toString())
        cell.cellStyle = style
    }

    private static void num(Row row, int c, Object value, Styles s, CellStyle style = null) {
        Cell cell = row.createCell(c)
        if (value != null) cell.setCellValue((value as Number).doubleValue())
        cell.cellStyle = style ?: s.num
    }

    private static void date(Row row, int c, Object value, Styles s) {
        Cell cell = row.createCell(c)
        if (value) cell.setCellValue(value as Date)
        cell.cellStyle = s.date
    }

    /** Africa CDC colours: green header band, gold accents. */
    private static class Styles {
        XSSFCellStyle title, header, label, value, cell, wrap, num, boldNum, date, bold, boldRight, small, warn, bad, link

        Styles(XSSFWorkbook wb) {
            XSSFColor green = new XSSFColor(new Color(0x23, 0x73, 0x48))
            XSSFColor gold = new XSSFColor(new Color(0xF5, 0xEE, 0xD6))
            Font white = wb.createFont(); white.bold = true; white.color = IndexedColors.WHITE.index; white.fontHeightInPoints = (short) 12
            Font whiteSmall = wb.createFont(); whiteSmall.bold = true; whiteSmall.color = IndexedColors.WHITE.index
            Font boldFont = wb.createFont(); boldFont.bold = true
            Font smallFont = wb.createFont(); smallFont.italic = true; smallFont.fontHeightInPoints = (short) 9
            Font linkFont = wb.createFont(); linkFont.underline = Font.U_SINGLE; linkFont.color = IndexedColors.BLUE.index

            title = filled(wb, green, white); title.alignment = HorizontalAlignment.LEFT; title.verticalAlignment = VerticalAlignment.CENTER
            header = filled(wb, green, whiteSmall); header.wrapText = true; header.verticalAlignment = VerticalAlignment.CENTER; bordered(header)
            label = wb.createCellStyle(); label.font = boldFont
            value = filled(wb, gold, null); bordered(value)
            cell = wb.createCellStyle(); bordered(cell)
            wrap = wb.createCellStyle(); bordered(wrap); wrap.wrapText = true; wrap.verticalAlignment = VerticalAlignment.TOP
            num = wb.createCellStyle(); bordered(num); num.dataFormat = wb.createDataFormat().getFormat("#,##0")
            boldNum = wb.createCellStyle(); boldNum.cloneStyleFrom(num); boldNum.font = boldFont
            date = wb.createCellStyle(); bordered(date); date.dataFormat = wb.createDataFormat().getFormat("dd/mm/yyyy")
            bold = wb.createCellStyle(); bold.font = boldFont
            boldRight = wb.createCellStyle(); boldRight.font = boldFont; boldRight.alignment = HorizontalAlignment.RIGHT
            small = wb.createCellStyle(); small.font = smallFont
            warn = filled(wb, new XSSFColor(new Color(0xFF, 0xF1, 0xC2)), null); bordered(warn)
            bad = filled(wb, new XSSFColor(new Color(0xF8, 0xD7, 0xDA)), null); bordered(bad)
            link = wb.createCellStyle(); link.font = linkFont; bordered(link)
        }

        private static XSSFCellStyle filled(XSSFWorkbook wb, XSSFColor color, Font font) {
            XSSFCellStyle st = wb.createCellStyle()
            st.setFillForegroundColor(color)
            st.fillPattern = FillPatternType.SOLID_FOREGROUND
            if (font) st.font = font
            return st
        }

        private static void bordered(CellStyle st) {
            st.borderBottom = BorderStyle.THIN; st.borderTop = BorderStyle.THIN
            st.borderLeft = BorderStyle.THIN; st.borderRight = BorderStyle.THIN
        }
    }
}
