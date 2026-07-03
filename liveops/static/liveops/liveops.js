/**
 * liveops.js — channels_broadcast plugin for liveops.
 *
 * On DOMContentLoaded: scans the page for elements that carry both
 * data-liveop-channel and data-liveop-token, then calls
 * channelsBroadcast.init() with the subscription token so the
 * channels_broadcast client connects to the right operation channel.
 *
 * Overrides channelsBroadcast.addMessage to handle:
 *
 *   msg.liveop_html   — parse the HTML fragment and apply hx-swap-oob
 *                       by element id (outerHTML replace for oob="true",
 *                       append for oob="beforeend:#id"). Then calls
 *                       htmx.process(node) if htmx is present so that
 *                       hx-* attributes in the new content activate.
 *
 *   msg.liveop_chain  — the current operation chained to a new one;
 *                       re-initialise the socket for the next channel via
 *                       channelsBroadcast.init() (idempotent — closes old
 *                       socket cleanly, §17.10).
 *
 *   anything else     — delegate to the original addMessage handler.
 */
(function () {
    "use strict";

    // ------------------------------------------------------------------ //
    // OOB-swap helper                                                     //
    // ------------------------------------------------------------------ //

    function applyOobSwap(fragment) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(fragment, "text/html");
        var nodes = Array.prototype.slice.call(doc.body.children);

        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            var oob = node.getAttribute("hx-swap-oob");
            if (!oob) continue;

            var inserted = null;

            if (oob === "true") {
                // outerHTML replace by id
                var targetId = node.id;
                if (!targetId) continue;
                var target = document.getElementById(targetId);
                var clone = node.cloneNode(true);
                if (target) {
                    target.replaceWith(clone);
                    inserted = clone;
                } else {
                    document.body.appendChild(clone);
                    inserted = clone;
                }
            } else if (oob.indexOf("outerHTML:") === 0) {
                // outerHTML replace by explicit CSS selector
                // e.g. hx-swap-oob="outerHTML:#op-abc123" replaces the
                // selected element with this node (oob attr stripped).
                var outerSelector = oob.slice("outerHTML:".length).trim();
                var outerTarget = document.querySelector(outerSelector);
                var outerClone = node.cloneNode(true);
                outerClone.removeAttribute("hx-swap-oob");
                if (outerTarget) {
                    outerTarget.replaceWith(outerClone);
                } else {
                    document.body.appendChild(outerClone);
                }
                inserted = outerClone;
            } else if (oob.indexOf("beforeend:") === 0) {
                // beforeend:#some-id — append children
                var selector = oob.slice("beforeend:".length).trim();
                var appendTarget = document.querySelector(selector);
                if (!appendTarget) continue;
                var cloneNode = node.cloneNode(true);
                while (cloneNode.firstChild) {
                    appendTarget.appendChild(cloneNode.firstChild);
                }
                inserted = appendTarget;
            }

            // Let htmx wire up hx-* attributes in the new content.
            if (inserted && window.htmx) {
                try {
                    window.htmx.process(inserted);
                } catch (e) {
                    console.debug("live-operations: htmx.process threw", e);
                }
            }
        }
    }

    // ------------------------------------------------------------------ //
    // Initialisation                                                      //
    // ------------------------------------------------------------------ //

    function init() {
        var cn = window.channelsBroadcast;
        if (!cn) {
            console.warn(
                "live-operations: channelsBroadcast not loaded — " +
                "include channels_broadcast/js/notifications.js first"
            );
            return;
        }

        // Detail page: a per-operation container carrying a subscription token.
        var container = document.querySelector(
            "[data-liveop-channel][data-liveop-token]"
        );
        // List page: a marker element; we connect the user's audience channel
        // (no token) and refresh #liveop-list on each liveop_list_changed push.
        var listEl = document.querySelector("[data-liveop-list]");

        if (!container && !listEl) return;

        // Save the original addMessage so unknown payload types fall through.
        var _origAddMessage = cn.addMessage.bind(cn);

        cn.addMessage = function (message) {
            if (message.liveop_html) {
                applyOobSwap(message.liveop_html);
                return;
            }
            if (message.liveop_chain) {
                // Chain to next operation: re-init socket with new token.
                var next = message.liveop_chain;
                cn.init(null, { subscriptionToken: next.token });
                return;
            }
            if (message.liveop_finished) {
                var fin = message.liveop_finished;
                // Sync the cancel/restart controls to the terminal state
                // without a reload: hide Cancel, reveal Retry only on error.
                // The forms were rendered at page load with a valid CSRF
                // token, so they submit cleanly.
                var controls = document.getElementById("op-controls");
                if (controls) {
                    controls.setAttribute("data-op-state", fin.state);
                    var cancelForm = controls.querySelector(".op-controls-cancel");
                    var restartForm = controls.querySelector(".op-controls-restart");
                    if (cancelForm) cancelForm.hidden = true;
                    if (restartForm) restartForm.hidden = fin.state !== "FINISHED_ERROR";
                }
                // If the operation declared a success URL (get_success_url)
                // and it finished OK, navigate straight there — skip the
                // live/list page. Errors/cancellations stay put.
                if (fin.state === "FINISHED_OK" && fin.success_url) {
                    window.location.assign(fin.success_url);
                    return;
                }
                // Otherwise dispatch a DOM event carrying {pk, state, url} so
                // pages can react (e.g. navigate to the finished operation).
                // This forces no behaviour by itself.
                document.dispatchEvent(
                    new CustomEvent("liveop:finished", { detail: fin })
                );
                return;
            }
            if (message.liveop_list_changed) {
                // One of this user's operations was created/started/finished:
                // re-fetch the table fragment (HX-Request) into #liveop-list.
                refreshList();
                return;
            }
            // Unknown message type — delegate to default handler.
            _origAddMessage(message);
        };

        if (container) {
            // null extraChannels — the token carries the channel name.
            cn.init(null, { subscriptionToken: container.getAttribute("data-liveop-token") });
        } else {
            // Audience-only connection: the authenticated user is auto-subscribed
            // to their own channel; no token needed.
            cn.init();
        }
    }

    function refreshList() {
        var target = document.getElementById("liveop-list");
        if (!target || !window.htmx) return;
        try {
            window.htmx.ajax("GET", window.location.href, {
                target: "#liveop-list",
                swap: "innerHTML",
            });
        } catch (e) {
            console.debug("live-operations: list refresh failed", e);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        // DOM already ready (script loaded deferred or at end of body).
        init();
    }
})();
