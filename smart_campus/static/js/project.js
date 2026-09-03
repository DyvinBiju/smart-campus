/* Project specific Javascript goes here. */

/* Auto-dismiss alert messages after 3 seconds (3000ms) */
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(function () {
    var alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function (alert) {
      if (window.bootstrap && bootstrap.Alert) {
        var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        bsAlert.close();
      } else {
        alert.classList.remove("show");
        alert.classList.add("fade");
        setTimeout(function () {
          alert.remove();
        }, 500);
      }
    });
  }, 3000);
});
