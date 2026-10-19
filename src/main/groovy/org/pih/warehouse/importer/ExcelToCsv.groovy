/**
 * AERIS: lets the CSV-based uploads (e.g. inbound stock movement "Import template") also take an Excel
 * workbook (.xlsx or .xls), as saved by staff. The first sheet is turned into the same CSV text the
 * upload already parses, so validation and behaviour are unchanged.
 **/
package org.pih.warehouse.importer

import org.apache.poi.ss.usermodel.Cell
import org.apache.poi.ss.usermodel.CellType
import org.apache.poi.ss.usermodel.DataFormatter
import org.apache.poi.ss.usermodel.DateUtil
import org.apache.poi.ss.usermodel.FormulaEvaluator
import org.apache.poi.ss.usermodel.Row
import org.apache.poi.ss.usermodel.Sheet
import org.apache.poi.ss.usermodel.Workbook
import org.apache.poi.ss.usermodel.WorkbookFactory

import java.math.RoundingMode

class ExcelToCsv {

    /** Dates in uploads use the same format as the CSV templates. */
    static final String DATE_FORMAT = "MM/dd/yyyy"

    /** True for .xlsx (zip) or .xls (OLE2) content, whatever the file is called. */
    static boolean isExcel(byte[] bytes) {
        if (!bytes || bytes.length < 4) {
            return false
        }
        boolean zip = bytes[0] == (byte) 0x50 && bytes[1] == (byte) 0x4B && bytes[2] == (byte) 0x03 && bytes[3] == (byte) 0x04
        boolean ole2 = bytes[0] == (byte) 0xD0 && bytes[1] == (byte) 0xCF && bytes[2] == (byte) 0x11 && bytes[3] == (byte) 0xE0
        return zip || ole2
    }

    /** First sheet as CSV text (comma separated, RFC 4180 quoting). Blank rows are skipped. */
    static String convert(byte[] bytes) {
        Workbook workbook = WorkbookFactory.create(new ByteArrayInputStream(bytes))
        try {
            Sheet sheet = workbook.getSheetAt(0)
            FormulaEvaluator evaluator = workbook.creationHelper.createFormulaEvaluator()
            DataFormatter formatter = new DataFormatter()
            int width = (sheet.getRow(sheet.firstRowNum)?.lastCellNum ?: 0) as int

            StringBuilder csv = new StringBuilder()
            for (int r = sheet.firstRowNum; r <= sheet.lastRowNum; r++) {
                Row row = sheet.getRow(r)
                int cells = Math.max(width, (row?.lastCellNum ?: 0) as int)
                List<String> values = (0..<Math.max(cells, 1)).collect { int c ->
                    cellText(row?.getCell(c), evaluator, formatter)
                }
                if (values.every { !it }) {
                    continue
                }
                csv.append(values.collect { quote(it) }.join(',')).append('\n')
            }
            return csv.toString()
        } finally {
            workbook.close()
        }
    }

    private static String cellText(Cell cell, FormulaEvaluator evaluator, DataFormatter formatter) {
        if (cell == null) {
            return ''
        }
        CellType type = cell.cellTypeEnum
        if (type == CellType.FORMULA) {
            type = evaluator.evaluateFormulaCellEnum(cell)
        }
        switch (type) {
            case CellType.NUMERIC:
                if (DateUtil.isCellDateFormatted(cell)) {
                    return cell.dateCellValue.format(DATE_FORMAT)
                }
                // Plain digits: 150326 stays 150326 (no ".0", no 1.5E5), 12.5 stays 12.5
                return new BigDecimal(cell.numericCellValue).setScale(6, RoundingMode.HALF_UP).stripTrailingZeros().toPlainString()
            case CellType.BOOLEAN:
                return cell.booleanCellValue ? 'true' : 'false'
            case CellType.BLANK:
            case CellType.ERROR:
                return ''
            default:
                return formatter.formatCellValue(cell)?.trim() ?: ''
        }
    }

    private static String quote(String value) {
        if (value == null) {
            return ''
        }
        if (value.contains(',') || value.contains('"') || value.contains('\n') || value.contains('\r')) {
            return '"' + value.replace('"', '""') + '"'
        }
        return value
    }
}
