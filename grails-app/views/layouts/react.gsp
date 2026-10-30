<%@ page import="com.newrelic.api.agent.NewRelic" %>
<%@ page contentType="text/html;charset=UTF-8" %>
<html>
<head>
    <%= NewRelic.getBrowserTimingHeader() %>
    <title><g:layoutTitle default="AERIS" /></title>
    <link rel="stylesheet" href="${request.contextPath}/static/vendor/netdna.bootstrapcdn.com/font-awesome/3.2.1/css/font-awesome.min.css">
    <g:render template="/localization/crowdin"/>
    <g:googleSiteTag />
    <g:render template="/common/hotjar"/>
    <asset:link rel="icon" href="favicon.ico" type="image/x-ico"/>

    <g:layoutHead/>
</head>
<body class="d-flex flex-column">
    <div style="flex: 1">
        <g:layoutBody />
    </div>
    <%-- AERIS: Africa CDC brand layer, after the webpack bundle's stylesheet so it wins --%>
    <link rel="stylesheet" href="${resource(dir:'css',file:'aeris-brand.css')}?v=${g.meta(name: 'build.time')}" type="text/css" media="all" />
<%= NewRelic.getBrowserTimingFooter() %>
</body>
</html>
