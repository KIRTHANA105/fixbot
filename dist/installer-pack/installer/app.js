const copyButton = document.getElementById("copyCmd");
const note = document.getElementById("note");

const installCommand = "installer\\install.cmd";

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(installCommand);
    note.textContent =
      "Copied. After download, run it in an elevated CMD to install Fixbot.";
  } catch (error) {
    note.textContent =
      "Copy failed. Manually run after download: installer\\install.cmd";
  }
});
