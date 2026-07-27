const form = document.getElementById("setup-form");
const errorEl = document.getElementById("error");
const submitBtn = document.getElementById("submit-btn");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorEl.textContent = "";
  submitBtn.disabled = true;
  submitBtn.textContent = "Saving...";

  try {
    await window.firstRun.saveApiKeys({
      GROQ_API_KEY: document.getElementById("groq").value.trim(),
      HUGGINGFACEHUB_API_TOKEN: document.getElementById("hf").value.trim(),
      GEMINI_API_KEY: document.getElementById("gemini").value.trim(),
    });
  } catch (err) {
    errorEl.textContent = err?.message || "Could not save settings.";
    submitBtn.disabled = false;
    submitBtn.textContent = "Save and continue";
  }
});
