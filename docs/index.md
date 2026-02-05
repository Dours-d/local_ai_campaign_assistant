---
layout: default
---

# Waiting for Verification...

This portal ensures secure access to your local AI campaign assistant.

<p id="status-message">Connecting to secure tunnel...</p>

<a id="redirect-link" href="#" class="btn">Click here if not redirected automatically</a>

<script>
  // Read the URL directly injected by the monitoring script
  var destination = "https://significant-folks-predicted-eat.trycloudflare.com";
  var search = window.location.search || "";
  var finalUrl = destination + search;

  document.getElementById("redirect-link").href = finalUrl;

  setTimeout(function() {
    window.location.replace(finalUrl);
  }, 1000); // Small delay to show the "faithful" UI
</script>

