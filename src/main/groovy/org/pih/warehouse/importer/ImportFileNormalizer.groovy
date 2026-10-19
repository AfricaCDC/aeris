/**
 * AERIS: makes uploaded files readable by the Excel importers (Configuration/Inventory > Import data).
 *
 *  - Excel (.xlsx/.xls) whose first sheet is not called "Sheet1" (a French Excel calls it "Feuil1"):
 *    the first sheet is renamed "Sheet1", because the importers look the sheet up by that name.
 *  - CSV: converted to an .xlsx workbook with one "Sheet1": dates as date cells, everything else as text.
 *    Dates: yyyy-MM-dd, or d/m/yyyy day-first (DRC convention); month-first only when it cannot be a day-first
 *    date (e.g. 04/30/2028). "," or ";" separated (Excel in French saves ";").
 **/
package org.pih.warehouse.importer

import org.apache.poi.ss.usermodel.Cell
import org.apache.poi.ss.usermodel.CellStyle
import org.apache.poi.ss.usermodel.Row
import org.apache.poi.ss.usermodel.Sheet
import org.apache.poi.ss.usermodel.Workbook
import org.apache.poi.ss.usermodel.WorkbookFactory
import org.apache.poi.xssf.usermodel.XSSFWorkbook

import java.nio.charset.Charset
import java.nio.charset.CharacterCodingException
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import java.nio.ByteBuffer

class ImportFileNormalizer {

    static final String SHEET = "Sheet1"

    /** @return the file to hand to the importer (the same file, or a new .xlsx next to it for CSV input) */
    static File normalize(File file) {
        byte[] bytes = file.bytes
        if (ExcelToCsv.isExcel(bytes)) {
            renameFirstSheet(file)
            return file
        }
        File xlsx = new File(file.parentFile, file.name.replaceAll(/\.[^.]*$/, '') + "-aeris.xlsx")
        csvToXlsx(decode(bytes), xlsx)
        return xlsx
    }

    private static void renameFirstSheet(File file) {
        Workbook workbook = new FileInputStream(file).withStream { WorkbookFactory.create(it) }
        try {
            if (workbook.getSheet(SHEET) != null || workbook.numberOfSheets == 0) {
                return
            }
            workbook.setSheetName(0, SHEET)
            new FileOutputStream(file).withStream { workbook.write(it) }
        } finally {
            workbook.close()
        }
    }

    private static void csvToXlsx(String text, File target) {
        List<String> lines = text.readLines().findAll { it.trim() }
        char separator = lines && lines[0].count(';') > lines[0].count(',') ? (char) ';' : (char) ','
        Workbook workbook = new XSSFWorkbook()
        try {
            Sheet sheet = workbook.createSheet(SHEET)
            CellStyle dateStyle = workbook.createCellStyle()
            dateStyle.dataFormat = workbook.creationHelper.createDataFormat().getFormat("yyyy-mm-dd")
            lines.eachWithIndex { String line, int r ->
                Row row = sheet.createRow(r)
                splitCsv(line, separator).eachWithIndex { String value, int c ->
                    Cell cell = row.createCell(c)
                    if (r == 0) {             // header row stays text
                        cell.setCellValue(value)
                        return
                    }
                    Date date = parseDate(value)
                    if (date) {
                        cell.setCellValue(date)
                        cell.cellStyle = dateStyle
                    } else {
                        // Text, including numbers: lot numbers like 150326 must not become 150326.0,
                        // and the importers read codes, lots and quantities as text.
                        cell.setCellValue(value)
                    }
                }
            }
            new FileOutputStream(target).withStream { workbook.write(it) }
        } finally {
            workbook.close()
        }
    }

    static Date parseDate(String value) {
        def iso = value =~ /^(\d{4})-(\d{1,2})-(\d{1,2})$/
        if (iso.matches()) {
            return date(iso.group(1) as int, iso.group(2) as int, iso.group(3) as int)
        }
        def dmy = value =~ /^(\d{1,2})[\/.](\d{1,2})[\/.](\d{4})$/
        if (dmy.matches()) {
            int a = dmy.group(1) as int, b = dmy.group(2) as int, y = dmy.group(3) as int
            return b > 12 ? date(y, a, b) : date(y, b, a)   // day-first unless that is impossible
        }
        return null
    }

    private static Date date(int year, int month, int day) {
        if (month < 1 || month > 12 || day < 1 || day > 31) {
            return null
        }
        Calendar cal = Calendar.getInstance()
        cal.lenient = false
        cal.clear()
        cal.set(year, month - 1, day)
        try {
            return cal.time
        } catch (IllegalArgumentException ignored) {
            return null     // e.g. 31/02
        }
    }

    /** UTF-8 (with or without BOM), else Windows-1252 as saved by Excel's plain "CSV". */
    private static String decode(byte[] bytes) {
        int start = (bytes.length >= 3 && bytes[0] == (byte) 0xEF && bytes[1] == (byte) 0xBB && bytes[2] == (byte) 0xBF) ? 3 : 0
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(bytes, start, bytes.length - start)).toString()
        } catch (CharacterCodingException ignored) {
            return new String(bytes, Charset.forName("windows-1252"))
        }
    }

    private static List<String> splitCsv(String line, char separator) {
        List<String> out = []
        StringBuilder cur = new StringBuilder()
        boolean quoted = false
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i)
            if (quoted) {
                if (ch == '"' as char) {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"' as char) { cur.append('"'); i++ } else { quoted = false }
                } else {
                    cur.append(ch)
                }
            } else if (ch == '"' as char) {
                quoted = true
            } else if (ch == separator) {
                out << cur.toString().trim(); cur.setLength(0)
            } else {
                cur.append(ch)
            }
        }
        out << cur.toString().trim()
        return out
    }
}
