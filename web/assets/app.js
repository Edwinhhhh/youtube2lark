const form = document.querySelector("#convertForm");
const submitButton = document.querySelector("#submitButton");
const downloadButton = document.querySelector("#downloadButton");
const message = document.querySelector("#message");
const previewTitle = document.querySelector("#previewTitle");
const markdownPreview = document.querySelector("#markdownPreview");
const videoMeta = document.querySelector("#videoMeta");
const thumbnail = document.querySelector("#thumbnail");
const videoTitle = document.querySelector("#videoTitle");
const videoChannel = document.querySelector("#videoChannel");
const captionMeta = document.querySelector("#captionMeta");
const cueCount = document.querySelector("#cueCount");
const useChromeCookiesInput = document.querySelector("#useChromeCookiesInput");
const cookiesFromBrowserInput = document.querySelector("#cookiesFromBrowserInput");

syncBrowserSelect();
useChromeCookiesInput.addEventListener("change", syncBrowserSelect);

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    url: document.querySelector("#urlInput").value.trim(),
    langs: document.querySelector("#langsInput").value.trim(),
    cookiesFromBrowser: useChromeCookiesInput.checked
      ? cookiesFromBrowserInput.value.trim()
      : "",
    cookies: document.querySelector("#cookiesInput").value.trim(),
    jsRuntimes: document.querySelector("#jsRuntimesInput").value.trim(),
    remoteComponents: document.querySelector("#remoteComponentsInput").value.trim(),
  };

  setBusy(true);
  setMessage("正在读取视频信息和字幕，这一步可能需要几十秒。", "");
  downloadButton.classList.add("disabled");
  downloadButton.href = "#";

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!data.ok) {
      throw new Error(data.error || "生成失败。");
    }

    renderResult(data);
    const cookiesNote = data.autoCookiesUsed ? " 已自动使用 Chrome 登录态重试。" : "";
    setMessage(`已生成 ${data.filename}${cookiesNote}`, "ok");
  } catch (error) {
    setMessage(enhanceError(error.message), "error");
  } finally {
    setBusy(false);
  }
});

function renderResult(data) {
  previewTitle.textContent = "Markdown 已生成";
  markdownPreview.value = data.markdown || "";
  cueCount.textContent = `${data.cueCount || 0} cues`;

  videoTitle.textContent = data.title || "";
  videoChannel.textContent = data.channel || "";
  captionMeta.textContent = `字幕：${data.captionLanguage || "-"} / ${data.captionSource || "-"}`;

  if (data.thumbnail) {
    thumbnail.src = data.thumbnail;
    thumbnail.alt = data.title || "YouTube thumbnail";
  } else {
    thumbnail.removeAttribute("src");
    thumbnail.alt = "";
  }

  videoMeta.classList.remove("hidden");
  downloadButton.href = data.downloadUrl;
  downloadButton.download = data.filename;
  downloadButton.classList.remove("disabled");
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
  submitButton.innerHTML = isBusy
    ? '<span class="button-icon">...</span>生成中'
    : '<span class="button-icon">MD</span>生成 Markdown';
}

function setMessage(text, type) {
  message.textContent = text;
  message.className = `message ${type || ""}`.trim();
}

function enhanceError(text) {
  if (/Failed to decrypt with DPAPI/i.test(text)) {
    return `${text}\n\nChrome 的 cookie 在当前 Windows/Chrome 版本下无法被 yt-dlp 解密。请改选 Edge 或 Firefox 并确保那个浏览器已登录 YouTube；或者导出 cookies.txt 后填入路径。`;
  }
  if (/not a bot|Sign in to confirm|cookies-from-browser/i.test(text)) {
    return `${text}\n\n请勾选“使用浏览器登录态”后再生成，并选择一个已经登录 YouTube 的浏览器。`;
  }
  if (/WinError 10013/.test(text)) {
    return `${text}\n\n本地服务没有外部网络权限，需要重启服务并允许访问 YouTube。`;
  }
  if (/does not expose captions|No supported caption track|没有通过 YouTube 暴露/i.test(text)) {
    return `${text}\n\n这个视频需要 ASR 转写兜底；当前原型先只做“已有字幕 -> Markdown”。`;
  }
  return text;
}

function syncBrowserSelect() {
  cookiesFromBrowserInput.disabled = !useChromeCookiesInput.checked;
}
