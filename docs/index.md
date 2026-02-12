---
layout: default
---

# Waiting for Verification...

This portal ensures secure access to your local AI campaign assistant.

<p id="status-message">Connecting to secure tunnel...</p>

<a id="redirect-link" href="#" class="btn">Click here if not redirected automatically</a>

<script>
  // Read the URL directly injected by the monitoring script
  var destination = "https://garmin-lay-falls-quizzes.trycloudflare.com";
  
  // Handle Deep Linking via Hash (e.g. https://gd-pages/#/onboard/123 -> https://tunnel/onboard/123)
  var hash = window.location.hash;
  var path = "";
  if (hash && hash.length > 1) {
      path = hash.substring(1); // Remove the #
  }
  
  // Fallback to query if no hash (legacy support)
  var search = window.location.search || "";
  
  var finalUrl = destination + path + search;

  document.getElementById("redirect-link").href = finalUrl;
  document.getElementById("status-message").innerText = "Redirecting to secure node...";

  setTimeout(function() {
    window.location.replace(finalUrl);
  }, 1000); 
</script>






