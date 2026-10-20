/**
 * Copyright (c) 2012 Partners In Health.  All rights reserved.
 * The use and distribution terms for this software are covered by the
 * Eclipse Public License 1.0 (http://opensource.org/licenses/eclipse-1.0.php)
 * which can be found in the file epl-v10.html at the root of this distribution.
 * By using this software in any fashion, you are agreeing to be bound by
 * the terms of this license.
 * You must not remove this notice, or any other, from this software.
 **/
package org.pih.warehouse.batch

import grails.core.GrailsApplication
import org.apache.poi.poifs.filesystem.OfficeXmlFileException
import org.pih.warehouse.api.GenericApiService
import org.pih.warehouse.core.DocumentService
import org.pih.warehouse.core.Location
import org.pih.warehouse.core.RoleType
import org.pih.warehouse.core.User
import org.pih.warehouse.core.UploadService
import org.pih.warehouse.data.DataService
import org.pih.warehouse.importer.CategoryExcelImporter
import org.pih.warehouse.importer.DataImporter
import org.pih.warehouse.importer.ImportDataCommand
import org.pih.warehouse.importer.ImportFileNormalizer
import org.pih.warehouse.importer.InventoryExcelImporter
import org.pih.warehouse.importer.InventoryLevelExcelImporter
import org.pih.warehouse.importer.LocationExcelImporter
import org.pih.warehouse.importer.OutboundStockMovementExcelImporter
import org.pih.warehouse.importer.PersonExcelImporter
import org.pih.warehouse.importer.ProductAttributeExcelImporter
import org.pih.warehouse.importer.ProductCatalogExcelImporter
import org.pih.warehouse.importer.ProductCatalogItemExcelImporter
import org.pih.warehouse.importer.ProductExcelImporter
import org.pih.warehouse.importer.ProductPackageExcelImporter
import org.pih.warehouse.importer.ProductSupplierAttributeExcelImporter
import org.pih.warehouse.importer.ProductSupplierExcelImporter
import org.pih.warehouse.importer.ProductSupplierPreferenceExcelImporter
import org.pih.warehouse.importer.ProductAssociationExcelImporter
import org.pih.warehouse.importer.ProductSynonymExcelImporter
import org.pih.warehouse.importer.PurchaseOrderActualReadyDateExcelImporter
import org.pih.warehouse.importer.TagExcelImporter
import org.pih.warehouse.importer.UserExcelImporter
import org.pih.warehouse.importer.UserLocationExcelImporter
import org.springframework.web.multipart.support.DefaultMultipartHttpServletRequest
import org.springframework.web.multipart.support.StandardMultipartHttpServletRequest

class BatchController {

    def userService

    DataService dataService
    DocumentService documentService
    GrailsApplication grailsApplication
    GenericApiService genericApiService
    UploadService uploadService

    def index() {}

    def uploadData(ImportDataCommand command) {
        if (request instanceof DefaultMultipartHttpServletRequest) {
            def uploadFile = request.getFile('xlsFile')
            if (!uploadFile.empty) {
                def localFile = uploadService.createLocalFile(uploadFile.originalFilename)
                uploadFile.transferTo(localFile)
            }
        }
    }

    def downloadExcel() {
        println "Download XLS template " + params

        def objects = genericApiService.getList(params.type, [:])
        def domainClass = genericApiService.getDomainClass(params.type)
        def data = dataService.transformObjects(objects, domainClass.PROPERTIES)

        response.contentType = "application/vnd.ms-excel"
        response.setHeader 'Content-disposition', "attachment; filename=\"${params.type}.xls\""
        documentService.generateExcel(response.outputStream, data)
        response.outputStream.flush()
    }

    def downloadTemplate() {
        println "Download XLS template " + params
        def filename = params.template
        try {
            def file = documentService.findFile("templates/" + filename)
            response.contentType = "application/vnd.ms-excel"
            response.setHeader 'Content-disposition', "attachment; filename=\"${filename}\""
            response.outputStream << file.bytes
            response.outputStream.flush()
        }
        catch (FileNotFoundException e) {
            response.status = 404
        }
    }

    def downloadCsvTemplate() {
        println "Download csv template " + params
        def filename = params.template
        try {
            def file = documentService.findFile("templates/" + filename)
            response.contentType = "text/csv"
            response.setHeader 'Content-disposition', "attachment; filename=\"${filename}\""
            response.outputStream << file.bytes
            response.outputStream.flush()
        }
        catch (FileNotFoundException e) {
            response.status = 404
        }
    }

    def importData(ImportDataCommand command) {

        // AERIS: storekeepers upload stock counts; the rest of this page stays with admins
        request.aerisAllowedTypes = aerisUploadTypes()

        if ("POST".equals(request.getMethod())) {
            String aerisType = command.importType ?: params.importType
            if (aerisType && !request.aerisAllowedTypes.contains(aerisType)) {
                redirect(controller: "errors", action: "handleForbidden")
                return
            }
            if (command.importNow && aerisType && !aerisMayImport(aerisType)) {
                // Checked but not imported: the logistics lead (Manager) imports, per separation of duties
                command.importNow = false
                request.aerisNotice = warehouse.message(code: 'aeris.import.managerOnly',
                        default: 'Only the logistics lead (Manager role) can import this file.')
            }
            request.aerisCanImport = aerisMayImport(aerisType)
            def localFile = session.localFile
            if (request instanceof StandardMultipartHttpServletRequest) {
                def uploadFile = command.importFile
                if (!uploadFile?.empty) {
                    try {
                        localFile = uploadService.createLocalFile(uploadFile.originalFilename)
                        uploadFile.transferTo(localFile)
                        // AERIS: .xlsx from French Excel ("Feuil1") and CSV files become readable workbooks
                        localFile = ImportFileNormalizer.normalize(localFile)
                        session.localFile = localFile

                    } catch (Exception e) {
                        log.error("Error uploading file" + e.message, e)
                        flash.message = "Unable to upload file due to exception: " + e.message
                        return
                    }
                } else {
                    flash.message = "${warehouse.message(code: 'inventoryItem.emptyFile.message')}"
                }
            }

            def dataImporter
            if (localFile) {
                log.info "Local xls file " + localFile.getAbsolutePath()
                command.filename = localFile.getAbsolutePath()
                command.location = Location.get(session.warehouse.id)
                try {
                    dataImporter = createExcelImporter(command)
                }
                catch (OfficeXmlFileException e) {
                    log.error("Error with import file " + e.message, e)
                    command.errors.reject("importFile", e.message)
                }

                if (dataImporter) {
                    // Get data from importer (should be done as a separate step 'processData' or within 'validateData')
                    command.data = dataImporter.data

                    // Validate data using importer (might change data)
                    dataImporter.validateData(command)

                    command.columnMap = dataImporter.columnMap
                }


                if (command?.data?.isEmpty()) {
                    command.errors.reject("importFile", "${warehouse.message(code: 'inventoryItem.pleaseEnsureDate.message', args: [dataImporter.columnMap?.sheet?:'Sheet1', localFile.getAbsolutePath()])}")
                }

                if (command.importType == 'inventory' && !command.date) {
                    command.errors.reject("date", "${warehouse.message(code: 'import.inventoryImportMustHaveDate.message', default: "Inventory import must specify the date of the stock count")}")
                }

                // If there are no errors and the user requests to import the data, we should execute the import
                if (command.importNow) {
                    try {
                        dataImporter.importData(command)
                    } catch(Exception e) {
                        log.error("Unable to import data: " + e.message, e)
                        command.errors.reject(e.message)
                    }
                    if (!command.hasErrors()) {
                        flash.message = "${warehouse.message(code: 'inventoryItem.importSuccess.message', args: [localFile.getAbsolutePath()])}"
                        // Remove once import has been completed
                        session.removeAttribute("localFile")
                        redirect(action: "importData")
                        return
                    }
                } else if (!command.hasErrors()) {
                    // AERIS: storekeepers have no "Import now" button, so don't tell them to click it
                    flash.message = request.aerisCanImport ?
                            "${warehouse.message(code: 'inventoryItem.dataReadyToBeImported.message')}" :
                            "${warehouse.message(code: 'aeris.import.checkedOk', default: 'File checked: no errors. Review the lines below.')}"
                }
            } else {
                flash.message = "${warehouse.message(code: 'inventoryItem.notValidXLSFile.message')}"
            }
            // Render data for user to review before proceeding
            render(view: "importData", model: [commandInstance:command])
        }
    }

    // AERIS: who may use which import type. Upload means "upload and check"; import means "Import now".
    private List<String> aerisUploadTypes() {
        if (aerisHasRole([RoleType.ROLE_SUPERUSER, RoleType.ROLE_ADMIN])) {
            return ['category', 'inventory', 'inventoryLevel', 'location', 'person', 'product', 'productAttribute',
                    'productCatalog', 'productCatalogItem', 'productPackage', 'productSupplier', 'productSupplierAttribute',
                    'productSupplierPreference', 'productSynonym', 'productAssociation', 'tag', 'user', 'userLocation',
                    'outboundStockMovement', 'purchaseOrderActualReadyDate', 'productGroup']
        }
        List<String> types = []
        if (userService.isUserManager(session.user)) {          // Assistant and above
            types << 'inventory'
        }
        if (aerisHasRole([RoleType.ROLE_MANAGER])) {
            types << 'inventoryLevel'
        }
        return types
    }

    private boolean aerisMayImport(String type) {
        if (type in ['inventory', 'inventoryLevel']) {
            return aerisHasRole([RoleType.ROLE_SUPERUSER, RoleType.ROLE_ADMIN, RoleType.ROLE_MANAGER])
        }
        return aerisHasRole([RoleType.ROLE_SUPERUSER, RoleType.ROLE_ADMIN])
    }

    private boolean aerisHasRole(List<RoleType> roles) {
        User user = session.user ? User.get(session.user.id) : null
        return user && userService.getEffectiveRoles(user).any { roles.contains(it.roleType) }
    }

    DataImporter createExcelImporter(ImportDataCommand command) {

        switch (command.importType) {
            case "category":
                return new CategoryExcelImporter(command?.filename)
            case "inventory":
                return new InventoryExcelImporter(command?.filename)
            case "inventoryLevel":
                return new InventoryLevelExcelImporter(command?.filename)
            case "location":
                return new LocationExcelImporter(command?.filename)
            case "person":
                return new PersonExcelImporter(command?.filename)
            case "product":
                return new ProductExcelImporter(command?.filename)
            case "productAttribute":
                return new ProductAttributeExcelImporter(command?.filename)
            case "productCatalog":
                return new ProductCatalogExcelImporter(command?.filename)
            case "productCatalogItem":
                return new ProductCatalogItemExcelImporter(command?.filename)
            case "productSupplier":
                return new ProductSupplierExcelImporter(command?.filename)
            case "productSupplierPreference":
                return new ProductSupplierPreferenceExcelImporter(command?.filename)
            case "productSupplierAttribute":
                return new ProductSupplierAttributeExcelImporter(command?.filename)
            case "productPackage":
                return new ProductPackageExcelImporter(command?.filename)
            case "outboundStockMovement":
                return new OutboundStockMovementExcelImporter(command?.filename)
            case "tag":
                return new TagExcelImporter(command?.filename)
            case "user":
                return new UserExcelImporter(command?.filename)
            case "userLocation":
                return new UserLocationExcelImporter(command?.filename)
            case "productAssociation":
                return new ProductAssociationExcelImporter(command?.filename)
            case "productSynonym":
                return new ProductSynonymExcelImporter(command?.filename)
            case "purchaseOrderActualReadyDate":
                return new PurchaseOrderActualReadyDateExcelImporter(command?.filename)
            default:
                command.errors.reject("importType", "${warehouse.message(code: 'import.invalidType.message', default: 'Please choose a valid import type')}")
        }
    }
}
