const form = document.querySelector("#contact-form");
const status = document.querySelector("#form-status");
const button = form.querySelector("button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.className = "";
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  button.disabled = true;
  status.textContent = "Sending…";
  const payload = Object.fromEntries(new FormData(form).entries());

  try {
    const response = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error?.message || "Could not send the message.");
    }
    status.textContent = "Message received. Check your inbox for confirmation.";
    form.reset();
  } catch (error) {
    status.className = "error";
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
