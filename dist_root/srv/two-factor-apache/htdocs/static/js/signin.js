document.forms[0].onsubmit = function(event) {
  let otp = document.getElementById("otp").value;
  event.currentTarget.action = "do-login?otp=" + encodeURIComponent(otp);
};
