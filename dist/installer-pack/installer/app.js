const copyButton = document.getElementById("copyCmd");
const note = document.getElementById("note");

const installCommand = "installer\\install.cmd";

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(installCommand);
    note.textContent = "Copied. Run it in an elevated CMD to install Fixbot.";
  } catch (error) {
    note.textContent = "Copy failed. Manually run: installer\\install.cmd";
  }
});
