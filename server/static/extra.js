(function (undefined) {
    function newTab(name, id, url, payload, onload) {
        var tab = $("#" + id)

        if (tab.length) {
            $("a.nav-link[href='#" + id + "']").tab("show")
            return
        }

        var pane = $('<div role="tabpanel" class="tab-pane fade" />')
            .attr("id", id)
            .appendTo("#tab-contents")

        $.ajax({
            url: url,
            method: payload ? "POST" : "GET",
            contentType: payload ? "application/json" : undefined,
            data: payload ? JSON.stringify(payload) : undefined,
            success: function (data) {
                pane.html(data)
                if (onload) {
                    onload(pane)
                }
            }
        })

        var link = $('<a class="nav-link" role="tab" data-toggle="tab" />')
            .attr("href", "#" + id)
            .attr("aria-controls", id)
            .appendTo($('<li role="presentation" class="nav-item" />')
                .appendTo("#tabs"))

        $('<span class="text" />')
            .text(name)
            .appendTo(link)

        $('<button type="button" class="btn-close" aria-label="Close" />')
            .appendTo(link)

        link.tab("show")
    }

    function refreshCollectionsWith(data) {
        var active = $("#collections-nav .accordion-button:not(.collapsed)")
        active = active.length ? active.attr("data-collection-name") : null
        $("#collections-nav").html(data)
        if (active) {
            $("#collections-nav .accordion-button[data-collection-name='" + active + "']").click()
        }
    }

    function refreshCollections() {
        $.get("collections", refreshCollectionsWith)
    }

    function collectionTabId(collection) {
        return "collection-" +
            encodeURIComponent(collection).replaceAll(/[^A-Za-z0-9_-]/g, "_")
    }

    function collectionTabName(collection) {
        return collection.replace(/[\\\/]+$/, "").replace(/^.*[\\\/]/, "")
    }

    function requestTabId(collection, request) {
        return "request-" +
            encodeURIComponent(collection).replaceAll(/[^A-Za-z0-9_-]/g, "_") + "__" +
            encodeURIComponent(request || "").replaceAll(/[^A-Za-z0-9_-]/g, "_")
    }

    function runIdPostfix() {
        return "-run-" + String(Math.random()).replace(/^0\./, "")
    }

    $(function () {
        refreshCollections()

        $("#tabs").on("click", "a.nav-link", function (event) {
            event.preventDefault()
            $(this).tab("show")
        })

        $("#tabs").on("click", "button.btn-close", function (event) {
            event.preventDefault()
            event.stopPropagation()
            $($(this).closest("a").attr("href")).remove()
            $(this).closest("li").remove()
            if (!$("#tabs a.active").length) {
                $("#tabs a:first").tab("show")
            }
        })

        $("#new-collection").on("click", function (event) {
            event.preventDefault()
            newTab("New Collection", "new-collection-tab", "collection-form")
        })

        $("#refresh-collections").on("click", refreshCollections)

        $("#collections-nav").on("click", ".collection-new-request", function (event) {
            event.preventDefault()
            var collection = $(this).attr("href").replace(/^#/, "")
            newTab("New Request", "new-request-tab", "request-form", {
                collection: collection
            })
        })

        $("#collections-nav").on("click", ".collection-settings", function (event) {
            event.preventDefault()
            var collection = $(this).attr("href").replace(/^#/, "")
            newTab(collectionTabName(collection), collectionTabId(collection), "collection-form", {
                collection: collection
            })
        })

        $("#collections-nav").on("click", ".collection-run", function (event) {
            event.preventDefault()
            var collection = $(this).attr("href").replace(/^#/, "")
            newTab("Run " + collectionTabName(collection), collectionTabId(collection) + runIdPostfix(), "collection-run", {
                collection: collection
            })
        })

        $("#collections-nav").on("click", ".collection-remove", function (event) {
            event.preventDefault()
            var collection = $(this).attr("href").replace(/^#/, "")
            $.ajax({
                url: "collections",
                method: "DELETE",
                contentType: "application/json",
                data: JSON.stringify({
                    collection: collection
                }),
                complete: refreshCollectionsWith
            })
        })

        $("#collections-nav").on("click", ".collection-request", function (event) {
            event.preventDefault()
            var collection = $(this).attr("href").replace(/^#/, "")
            var request = $(this).text()
            newTab(request, requestTabId(collection, request), "request-form", {
                collection: collection,
                request: request
            })
        })

        $("#tab-contents").on("click", ".collection-form-variables-new-add", function (event) {
            event.preventDefault()
            var form = $(this).closest(".collection-form")
            var original = form.find(".collection-form-variables-row-prototype").last()
            var cloned = original.clone().removeClass("collection-form-variables-row-prototype")
            cloned.find(".collection-form-variables-enabled")[0].checked = form.find(".collection-form-variables-new-enabled")[0].checked
            cloned.find(".collection-form-variables-name").val(form.find(".collection-form-variables-new-name").val())
            cloned.find(".collection-form-variables-value").val(form.find(".collection-form-variables-new-value").val())
            form.find(".collection-form-variables-new-enabled")[0].checked = true
            form.find(".collection-form-variables-new-name").val("")
            form.find(".collection-form-variables-new-value").val("")
            cloned.insertBefore(original)
        })

        $("#tab-contents").on("click", ".collection-form-variables-remove", function (event) {
            event.preventDefault()
            $(this).closest(".input-group").remove()
        })

        $("#tab-contents").on("click", ".collection-form-save", function (event) {
            event.preventDefault()
            var form = $(this).closest(".collection-form")
            var collection = form.find(".collection-form-name").val()
            $.post({
                url: "collections",
                contentType: "application/json",
                data: JSON.stringify({
                    collection: collection,
                    variables: form.find(".collection-form-variables-row:not(.collection-form-variables-row-prototype)")
                            .map(function () {
                                return {
                                    name: $(this).find(".collection-form-variables-name").val(),
                                    value: $(this).find(".collection-form-variables-value").val(),
                                    enabled: !!$(this).find(".collection-form-variables-enabled")[0].checked
                                }
                            })
                            .get(),
                }),
                success: function (data) {
                    var pane = form.closest(".tab-pane")
                    var tab = $("#tabs a[href='#" + pane.attr("id") + "']")
                    form.parent().html(data)
                    refreshCollections()
                    if (tab.length) {
                        tab.find(".text").text(collectionTabName(collection))
                        var newId = collectionTabId(collection)
                        pane.attr("id", newId)
                        tab.attr("href", "#" + newId).attr("aria-controls", newId)
                    }
                }
            })
        })

        $("#tab-contents").on("click", ".request-form-headers-new-add", function (event) {
            event.preventDefault()
            var form = $(this).closest(".request-form")
            var original = form.find(".request-form-headers-row-prototype").last()
            var cloned = original.clone().removeClass("request-form-headers-row-prototype")
            cloned.find(".request-form-headers-enabled")[0].checked = form.find(".request-form-headers-new-enabled")[0].checked
            cloned.find(".request-form-headers-name").val(form.find(".request-form-headers-new-name").val())
            cloned.find(".request-form-headers-value").val(form.find(".request-form-headers-new-value").val())
            form.find(".request-form-headers-new-enabled")[0].checked = true
            form.find(".request-form-headers-new-name").val("")
            form.find(".request-form-headers-new-value").val("")
            cloned.insertBefore(original)
        })

        $("#tab-contents").on("click", ".request-form-headers-remove", function (event) {
            event.preventDefault()
            $(this).closest(".input-group").remove()
        })

        $("#tab-contents").on("click", ".request-form-save", function (event) {
            event.preventDefault()
            var form = $(this).closest("form")
            if (!form[0].reportValidity()) {
                return
            }
            var form = $(this).closest(".request-form")
            var collection = form.find(".request-form-collection").val()
            var request = form.find(".request-form-name").val()
            $.post({
                url: "requests",
                contentType: "application/json",
                data: JSON.stringify({
                    collection: collection,
                    request: request,
                    method: form.find(".request-form-method").val(),
                    url: form.find(".request-form-url").val(),
                    headers: form.find(".request-form-headers-row:not(.request-form-headers-row-prototype)")
                        .map(function () {
                            return {
                                name: $(this).find(".request-form-headers-name").val(),
                                value: $(this).find(".request-form-headers-value").val(),
                                enabled: !!$(this).find(".request-form-headers-enabled")[0].checked
                            }
                        })
                        .get(),
                    payload: form.find(".request-form-payload").val(),
                }),
                success: function (data) {
                    var pane = form.closest(".tab-pane")
                    var tab = $("#tabs a[href='#" + pane.attr("id") + "']")
                    form.parent().html(data)
                    refreshCollections()
                    if (tab.length) {
                        tab.find(".text").text(request)
                        var newId = requestTabId(collection, request)
                        pane.attr("id", newId)
                        tab.attr("href", "#" + newId).attr("aria-controls", newId)
                    }
                }
            })
        })

        $("#tab-contents").on("click", ".request-form-run", function (event) {
            event.preventDefault()
            var form = $(this).closest(".request-form")
            var collection = form.find(".request-form-collection").val()
            var request = form.find(".request-form-name").val()
            newTab("Run " + request, requestTabId(collection, request) + runIdPostfix(), "request-run", {
                collection: collection,
                request: request
            })
        })

        $("#tab-contents").on("click", ".collection-run-start", function (event) {
            event.preventDefault()
            var form = $(this).closest(".collection-run-form")
            var results = form.next(".collection-run-results")
            var collection = form.find(".collection-run-collection").val()
            var socket = new WebSocket("ws")
            results.find(".requests").html("")

            socket.addEventListener("message", function (event) {
                var evt = JSON.parse(event.data)
                switch (evt.type) {
                    case "collection-status":
                        results.find(".status").text(evt.data.status)
                        var percent = Math.round(evt.data.done * 100 / evt.data.total)
                        results.find(".progress").attr("aria-valuenow", percent)
                        results.find(".progress-bar").css("width", percent + "%")

                        if (evt.data.status == "started") {
                            results.find(".progress-bar").addClass("progress-bar-striped progress-bar-animated")
                        } else if (evt.data.status == "finished") {
                            results.find(".progress-bar").removeClass("progress-bar-striped progress-bar-animated")
                            socket.close()
                        }
                        break
                    case "request-result":
                        $("<a href='#' class='list-group-item list-group-item-action' />")
                            .addClass("list-group-item-" + (evt.data.result.response_status < 400 ? "success" : "danger"))
                            .text(evt.data.request)
                            .attr("data-result", JSON.stringify(evt.data.result))
                            .appendTo(results.find(".requests"))
                        break
                }
            })

            socket.addEventListener("open", function (event) {
                socket.send(JSON.stringify({
                    type: "collection-run",
                    data: { collection: collection }
                }))
            })
        })

        $("#tab-contents").on("click", ".collection-run-results .requests a", function (event) {
            event.preventDefault()
            var link = $(this)
            var result = JSON.parse(link.attr("data-result"))
            var request = link.text()
            var collection = link.closest(".collection-run-form").find(".collection-run-collection").val()
            newTab(
                request + " results",
                requestTabId(collection, request) + runIdPostfix(),
                "request-run-template/" + result.response_status,
                undefined,
                function (pane) {
                    pane.find(".request-method").val(result.request_method)
                    pane.find(".request-url").val(result.request_url)
                    pane.find(".request-headers").val(result.request_headers)
                    pane.find(".request-payload").val(result.request_payload)
                    pane.find(".response-headers").val(result.response_headers)
                    pane.find(".response-payload").val(result.response_payload)
                }
            )
        })
    })
})()
