<%-- AERIS: Excel exports for the logistics team --%>
<html>
<head>
    <meta name="layout" content="custom"/>
    <title>${warehouse.message(code: 'aeris.export.title', default: 'Excel exports')}</title>
    <style>
        .aeris-exports { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 16px; margin: 10px 0 20px; }
        .aeris-exports .box { padding: 16px 20px 18px; }
        .aeris-exports h2 { margin: 0 0 4px; font-size: 16px; }
        .aeris-exports p.hint { color: #555; margin: 0 0 14px; line-height: 1.45; }
        .aeris-exports label { display: block; font-weight: bold; margin: 10px 0 4px; }
        .aeris-exports select, .aeris-exports input[type=text], .aeris-exports input[type=date] { width: 100%; max-width: 420px; padding: 4px; }
        .aeris-exports .dates { display: flex; gap: 12px; flex-wrap: wrap; }
        .aeris-exports .dates > div { flex: 1; min-width: 150px; }
        .aeris-exports .checks label { font-weight: normal; display: flex; gap: 6px; align-items: center; margin: 4px 0; }
        .aeris-exports .actions { margin-top: 16px; }
        .aeris-exports button { padding: 6px 14px; font-weight: bold; }
    </style>
</head>
<body>
<div class="body">
    <g:if test="${flash.message}"><div class="message">${flash.message}</div></g:if>
    <h1>${warehouse.message(code: 'aeris.export.title', default: 'Excel exports')}</h1>

    <div class="aeris-exports">
        <div class="box" id="cards">
            <h2>${warehouse.message(code: 'aeris.export.stockCard.title', default: 'Stock cards (MCM format)')}</h2>
            <p class="hint">${warehouse.message(code: 'aeris.export.stockCard.hint', default: 'One card per item and batch at a warehouse, in the MCM Ebola response stock card layout: opening balance, each receipt and issue, running balance. Leave the item empty for all items.')}</p>
            <g:form action="stockCard" method="GET">
                <label for="cardLocation">${warehouse.message(code: 'aeris.export.warehouse', default: 'Warehouse')}</label>
                <select id="cardLocation" name="locationId">
                    <g:each in="${depots}" var="d">
                        <option value="${d.id}" ${d.id == currentDepot ? 'selected' : ''}>${d.name}</option>
                    </g:each>
                </select>
                <label for="cardProduct">${warehouse.message(code: 'aeris.export.item', default: 'Item')}</label>
                <select id="cardProduct" name="productId">
                    <option value="">${warehouse.message(code: 'aeris.export.allItems', default: 'All items')}</option>
                    <g:each in="${products}" var="p">
                        <option value="${p.id}">${p.productCode} – ${p.name}</option>
                    </g:each>
                </select>
                <label for="cardLot">${warehouse.message(code: 'aeris.export.lot', default: 'Batch / lot (optional)')}</label>
                <input type="text" id="cardLot" name="lotNumber" autocomplete="off"/>
                <div class="dates">
                    <div><label for="cardStart">${warehouse.message(code: 'aeris.export.from', default: 'From')}</label>
                        <input type="date" id="cardStart" name="startDate" value="${startDate}"/></div>
                    <div><label for="cardEnd">${warehouse.message(code: 'aeris.export.to', default: 'To')}</label>
                        <input type="date" id="cardEnd" name="endDate" value="${endDate}"/></div>
                </div>
                <div class="actions">
                    <button type="submit" class="button">${warehouse.message(code: 'aeris.export.download', default: 'Download Excel')}</button>
                </div>
            </g:form>
        </div>

        <div class="box" id="all">
            <h2>${warehouse.message(code: 'aeris.export.consolidated.title', default: 'Stock across warehouses')}</h2>
            <p class="hint">${warehouse.message(code: 'aeris.export.consolidated.hint', default: 'One workbook for analysis: stock on hand by warehouse, item and lot with expiry and minimum-level status, item × warehouse totals, and every transaction in the period.')}</p>
            <g:form action="consolidated" method="GET">
                <label>${warehouse.message(code: 'aeris.export.warehouses', default: 'Warehouses')}</label>
                <div class="checks">
                    <g:each in="${depots}" var="d">
                        <label><input type="checkbox" name="locationIds" value="${d.id}" checked/> ${d.name}<g:if test="${d.province}"> (${d.province})</g:if></label>
                    </g:each>
                </div>
                <div class="dates">
                    <div><label for="allStart">${warehouse.message(code: 'aeris.export.txFrom', default: 'Transactions from')}</label>
                        <input type="date" id="allStart" name="startDate" value="${startDate}"/></div>
                    <div><label for="allEnd">${warehouse.message(code: 'aeris.export.to', default: 'To')}</label>
                        <input type="date" id="allEnd" name="endDate" value="${endDate}"/></div>
                </div>
                <div class="actions">
                    <button type="submit" class="button">${warehouse.message(code: 'aeris.export.download', default: 'Download Excel')}</button>
                </div>
            </g:form>
        </div>
    </div>
</div>
</body>
</html>
