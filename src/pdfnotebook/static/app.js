const state = {
  currentDocument: null,
  docId: null,
  pages: [],
  selectedPageNumber: null,
  generalMode: false,
  generalEntries: [],
  entrySnapshot: null,
  previewVisible: false,
};

const elements = {
  documentList: document.getElementById("documentList"),
  documentSelect: document.getElementById("documentSelect"),
  pageList: document.getElementById("pageList"),
  currentDocName: document.getElementById("currentDocumentName"),
  uploadForm: document.getElementById("uploadForm"),
  uploadFile: document.getElementById("uploadFile"),
  uploadName: document.getElementById("uploadName"),
  saveAndNextPageBtn: document.getElementById("saveAndNextPageBtn"),
  skipPageBtn: document.getElementById("skipPageBtn"),
  saveAndNextEntryBtn: document.getElementById("saveAndNextEntryBtn"),
  authorInput: document.getElementById("authorInput"),
  userInput: document.getElementById("userInput"),
  outputInput: document.getElementById("outputInput"),
  pageHeading: document.getElementById("pageHeading"),
  entryCount: document.getElementById("entryCount"),
  tagsInput: document.getElementById("tagsInput"),
  pagePreview: document.getElementById("pagePreview"),
  openPreview: document.getElementById("openPreview"),
  togglePreviewBtn: document.getElementById("togglePreviewBtn"),
  previewPanel: document.getElementById("previewPanel"),
  previewSummary: document.getElementById("previewSummary"),
  workspacePanel: document.getElementById("workspacePanel"),
  generalPanel: document.getElementById("generalPanel"),
  generalSection: document.getElementById("generalSection"),
  generalModeToggle: document.getElementById("generalModeToggle"),
  generalAuthor: document.getElementById("generalAuthor"),
  generalTags: document.getElementById("generalTags"),
  generalUserInput: document.getElementById("generalUserInput"),
  generalOutputInput: document.getElementById("generalOutputInput"),
  saveGeneralBtn: document.getElementById("saveGeneralBtn"),
  generalEntriesList: document.getElementById("generalEntriesList"),
  loadLastEntry: document.getElementById("loadLastEntry"),
  loadRandomEntry: document.getElementById("loadRandomEntry"),
  entrySnapshot: document.getElementById("entrySnapshot"),
  downloadPageBtn: document.getElementById("downloadPageBtn"),
  progressComplete: document.getElementById("progressComplete"),
  progressSkipped: document.getElementById("progressSkipped"),
  progressLabel: document.getElementById("progressLabel"),
  statusArea: null,
};

let statusReset;

document.addEventListener("DOMContentLoaded", () => {
  if (elements.uploadForm) {
    elements.uploadForm.addEventListener("submit", handleUpload);
  }
  elements.documentList.addEventListener("click", handleDocumentClick);
  elements.pageList.addEventListener("click", handlePageClick);
  if (elements.saveAndNextPageBtn) {
    elements.saveAndNextPageBtn.addEventListener("click", handleSaveAndNextPage);
  }
  if (elements.saveAndNextEntryBtn) {
    elements.saveAndNextEntryBtn.addEventListener("click", handleSaveAndNextEntry);
  }
  if (elements.skipPageBtn) {
    elements.skipPageBtn.addEventListener("click", handleSkip);
  }
  elements.downloadPageBtn.addEventListener("click", handlePageDownload);
  elements.generalModeToggle.addEventListener("click", toggleGeneralMode);
  elements.saveGeneralBtn.addEventListener("click", handleGeneralSave);
  elements.loadLastEntry.addEventListener("click", () =>
    loadEntrySnapshot("latest")
  );
  elements.loadRandomEntry.addEventListener("click", () =>
    loadEntrySnapshot("random")
  );
  elements.documentSelect.addEventListener("change", handleDocumentSelect);
  elements.togglePreviewBtn.addEventListener("click", togglePreview);
  document.getElementById("refreshDocs").addEventListener("click", loadDocuments);
  loadDocuments();
});

async function fetchJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(url, {
    ...options,
    headers,
  });
  const isJson = response.headers.get("Content-Type")?.includes("application/json");
  if (!response.ok) {
    const payload = isJson ? await response.json() : {};
    throw new Error(payload.error || "Request failed.");
  }
  if (isJson) {
    return response.json();
  }
  return null;
}

function showStatus(message, type = "info", keep = false) {
  if (!elements.statusArea) return;
  elements.statusArea.textContent = message;
  elements.statusArea.dataset.state = type;
  if (!keep) {
    clearTimeout(statusReset);
    statusReset = setTimeout(() => {
      elements.statusArea.textContent = "Ready for a document.";
      elements.statusArea.dataset.state = "info";
    }, 4500);
  }
}

async function loadDocuments() {
  try {
    showUploadSection(false);
    const payload = await fetchJson("/api/documents");
    const docs = payload.documents || [];
    renderDocList(docs);
    renderDocSelect(docs);
    if (docs.length) {
      const targetId =
        state.docId && docs.some((doc) => doc.id === state.docId)
          ? state.docId
          : docs[0].id;
      await selectDocument(targetId);
    }
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

async function deleteDocument(docId) {
  if (!confirm("Permanently delete this document and all its notes?")) {
    return;
  }
  try {
    await fetchJson(`/api/documents/${docId}`, {
      method: "DELETE",
    });
    if (state.docId === docId) {
      state.docId = null;
      state.pages = [];
      clearPageDetails();
    }
    await loadDocuments();
    showStatus("Document deleted.", "success");
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

async function loadGeneralEntries() {
  if (!state.docId) return;
  try {
    const payload = await fetchJson(`/api/general/${state.docId}`);
    state.generalEntries = payload.entries || [];
    renderGeneralEntries();
    if (payload.latest) {
      applyGeneralAutofill(payload.latest);
    }
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

async function loadEntrySnapshot(mode) {
  if (!state.docId) {
    showStatus("Pick a document first.", "error");
    return;
  }
  try {
    const payload = await fetchJson(`/api/entry/${mode}/${state.docId}`);
    state.entrySnapshot = payload.entry;
    renderEntrySnapshot(`Showing ${mode} entry`);
  } catch (exc) {
    showStatus(exc.message, "error");
    state.entrySnapshot = null;
    renderEntrySnapshot("No entry available.");
  }
}

function renderDocList(docs) {
  if (!elements.documentList) return;
  elements.documentList.innerHTML = "";
  if (!docs.length) {
    elements.documentList.innerHTML =
      "<p class='empty'>No documents yet. Upload one to begin.</p>";
    state.docId = null;
    state.currentDocument = null;
    state.generalMode = true;
    renderDocSelect([]);
    updateDocSelection();
    updateWorkspaceVisibility();
    return;
  }
  docs.forEach((doc) => {
    const item = document.createElement("div");
    item.className = `doc-item ${state.docId === doc.id ? "active" : ""}`;
    item.dataset.docId = doc.id;
    item.innerHTML = `
      <div class="doc-text">
        <span>${doc.name}</span>
        <small>${doc.page_count} pages • Uploaded ${new Date(doc.created_at).toLocaleString()}</small>
      </div>
      <button type="button" class="doc-delete" data-doc-id="${doc.id}" aria-label="Delete document">
        ×
      </button>
    `;
    elements.documentList.appendChild(item);
  });
  renderDocSelect(docs);
  updateDocSelection();
  updateWorkspaceVisibility();
}

function renderDocSelect(docs) {
  if (!elements.documentSelect) return;
  elements.documentSelect.innerHTML = `<option value="">None</option>`;
  const newOption = document.createElement("option");
  newOption.value = "new";
  newOption.textContent = "➕ New document";
  elements.documentSelect.appendChild(newOption);
  docs.forEach((doc) => {
    const option = document.createElement("option");
    option.value = doc.id;
    option.textContent = doc.name;
    elements.documentSelect.appendChild(option);
  });
  elements.documentSelect.value = state.docId || "";
}

function showUploadSection(show) {
  const section = document.getElementById("uploadSection");
  if (!section) return;
  section.classList.toggle("hidden", !show);
}

function updateDocSelection() {
  document.querySelectorAll(".doc-item").forEach((item) => {
    const matches = item.dataset.docId === state.docId;
    item.classList.toggle("active", matches);
  });
}

async function handleDocumentClick(event) {
  const deleteButton = event.target.closest(".doc-delete");
  if (deleteButton) {
    const { docId } = deleteButton.dataset;
    if (docId) {
      await deleteDocument(docId);
    }
    return;
  }
  const button = event.target.closest(".doc-item");
  if (!button) return;
  const { docId } = button.dataset;
  if (docId) {
    await selectDocument(docId);
  }
}

async function selectDocument(docId) {
  if (!docId) return;
  if (state.docId === docId) {
    return;
  }
  state.docId = docId;
  state.generalMode = false;
  updateDocSelection();
  updateWorkspaceVisibility();
  showUploadSection(false);
  try {
    const payload = await fetchJson(`/api/pages/${docId}`);
    state.currentDocument = payload.document;
    state.pages = payload.pages;
    elements.currentDocName.textContent = `${payload.document.name} (${payload.document.page_count} pages)`;
    renderPageList();
    if (state.pages.length) {
      await selectPage(state.pages[0].page_number);
    } else {
      clearPageDetails();
    }
    await loadGeneralEntries();
    state.entrySnapshot = null;
    renderEntrySnapshot("Entry preview");
    if (elements.documentSelect) {
      elements.documentSelect.value = docId;
    }
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

function renderPageList() {
  if (!state.pages.length) {
    elements.pageList.innerHTML =
      "<p class='empty'>Upload a document to list pages.</p>";
    updateProgressBar();
    return;
  }
  elements.pageList.innerHTML = "";
  state.pages.forEach((page) => {
    const item = document.createElement("button");
    item.type = "button";
    const classes = ["page-item"];
    if (state.selectedPageNumber === page.page_number) {
      classes.push("active");
    }
    if (page.skipped) {
      classes.push("skipped");
    }
    item.className = classes.join(" ");
    item.dataset.pageNumber = page.page_number;
    const statuses = [];
    if (page.complete) statuses.push("✓ complete");
    if (page.ignored) statuses.push("Ignored");
    if (page.skipped) statuses.push("Skipped");
    const statusText = statuses.length ? statuses.join(" • ") : "Pending";
    item.innerHTML = `
      <div>
        <span class="page-number">Page ${page.page_number}</span>
        <span class="page-status">${statusText}</span>
      </div>
      <div class="page-entry-count">${page.entry_count} ${page.entry_count === 1 ? "entry" : "entries"}</div>
    `;
    elements.pageList.appendChild(item);
  });
  updateProgressBar();
}

function updateProgressBar() {
  if (!elements.progressComplete || !elements.progressSkipped || !elements.progressLabel) return;
  const total = state.pages.length;
  if (!total) {
    elements.progressComplete.style.width = "0%";
    elements.progressSkipped.style.width = "0%";
    elements.progressLabel.textContent = "No pages loaded";
    return;
  }
  const completed = state.pages.filter((page) => page.complete).length;
  const skipped = state.pages.filter((page) => page.skipped && !page.complete).length;
  const completePct = ((completed / total) * 100).toFixed(1);
  const skippedPct = ((skipped / total) * 100).toFixed(1);
  elements.progressComplete.style.width = `${completePct}%`;
  elements.progressSkipped.style.width = `${skippedPct}%`;
  elements.progressLabel.textContent = `${completed} complete · ${skipped} skipped · ${total} total`;
}

function handlePageClick(event) {
  const button = event.target.closest(".page-item");
  if (!button) return;
  const pageNumber = Number(button.dataset.pageNumber);
  if (!pageNumber) return;
  selectPage(pageNumber);
}

async function selectPage(pageNumber) {
  if (!state.docId) return;
  state.selectedPageNumber = pageNumber;
  if (!state.pages.length) return;
  try {
    const payload = await fetchJson(`/api/pages/${state.docId}/${pageNumber}`);
    const page = payload.page;
    elements.authorInput.value = page.author;
    elements.userInput.value = page.user_input;
    elements.outputInput.value = page.output;
    elements.tagsInput.value = page.tags || "";
    elements.pageHeading.textContent = `Page ${page.page_number}`;
    const selectedPage = state.pages.find((p) => p.page_number === pageNumber);
    const entryTotal = selectedPage ? selectedPage.entry_count : 0;
    elements.entryCount.textContent = `${entryTotal} ${
      entryTotal === 1 ? "entry" : "entries"
    }`;
    if (selectedPage) {
      selectedPage.complete = page.complete;
      selectedPage.ignored = page.ignored;
    }
    if (elements.saveAndNextPageBtn) {
      elements.saveAndNextPageBtn.disabled = false;
    }
    if (elements.saveAndNextEntryBtn) {
      elements.saveAndNextEntryBtn.disabled = false;
    }
    if (elements.skipPageBtn) {
      elements.skipPageBtn.disabled = false;
    }
    elements.downloadPageBtn.disabled = false;
    updatePagePreview(pageNumber);
    renderPageList();
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

function updatePagePreview(pageNumber) {
  if (!state.docId || !pageNumber) {
    elements.pagePreview.src = "";
    elements.openPreview.href = "#";
    return;
  }
  const previewUrl = `/pages/${state.docId}/${String(pageNumber).padStart(3, "0")}`;
  elements.pagePreview.src = previewUrl;
  elements.openPreview.href = previewUrl;
}

function updatePreviewState() {
  if (!elements.previewPanel) return;
  const collapsed = !state.previewVisible;
  elements.previewPanel.classList.toggle("collapsed", collapsed);
  if (elements.previewSummary) {
    elements.previewSummary.style.display = collapsed ? "block" : "none";
  }
}

function togglePreview() {
  state.previewVisible = !state.previewVisible;
  elements.togglePreviewBtn.textContent = state.previewVisible
    ? "Hide preview"
    : "Show preview";
  updatePreviewState();
  if (state.previewVisible && state.selectedPageNumber) {
    updatePagePreview(state.selectedPageNumber);
  }
}

function clearPageDetails() {
  elements.authorInput.value = "";
  elements.userInput.value = "";
  elements.outputInput.value = "";
  elements.tagsInput.value = "";
  elements.pageHeading.textContent = "Choose a page to work on";
  elements.entryCount.textContent = "0 entries";
  if (elements.saveAndNextPageBtn) {
    elements.saveAndNextPageBtn.disabled = true;
  }
  if (elements.saveAndNextEntryBtn) {
    elements.saveAndNextEntryBtn.disabled = true;
  }
  if (elements.skipPageBtn) {
    elements.skipPageBtn.disabled = true;
  }
  elements.downloadPageBtn.disabled = true;
  state.selectedPageNumber = null;
  updateProgressBar();
  updateWorkspaceVisibility();
  state.previewVisible = false;
  if (elements.togglePreviewBtn) {
    elements.togglePreviewBtn.textContent = "Show preview";
  }
  updatePreviewState();
}

async function handleUpload(event) {
  event.preventDefault();
  const formData = new FormData();
  if (!elements.uploadFile.files.length) {
    showStatus("Select a PDF before uploading.", "error");
    return;
  }
  formData.append("file", elements.uploadFile.files[0]);
  if (elements.uploadName.value) {
    formData.append("name", elements.uploadName.value);
  }
  try {
    const response = await fetch("/api/documents", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Upload failed.");
    }
    state.docId = payload.doc_id;
    showStatus("PDF uploaded and split successfully.", "success");
    elements.uploadFile.value = "";
    elements.uploadName.value = "";
    await loadDocuments();
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

async function handleSaveAndNextPage() {
  if (!state.docId || !state.selectedPageNumber) {
    showStatus("Pick a document and page first.", "error");
    return;
  }
  await persistEntry();
  moveToNextPage();
}

async function handleSaveAndNextEntry() {
  if (!state.docId || !state.selectedPageNumber) {
    showStatus("Pick a document and page first.", "error");
    return;
  }
  await persistEntry();
  handleNewEntry();
}

async function persistEntry() {
  const page = state.pages.find((p) => p.page_number === state.selectedPageNumber);
  const payload = {
    doc_id: state.docId,
    page_number: state.selectedPageNumber,
    author: elements.authorInput.value,
    user_input: elements.userInput.value,
    output: elements.outputInput.value,
    complete: page ? page.complete : false,
    tags: elements.tagsInput.value,
  };
  try {
    const response = await fetchJson("/api/entry", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const page = state.pages.find((p) => p.page_number === state.selectedPageNumber);
    if (page) {
      page.entry_count = response.entry_count;
      page.complete = payload.complete;
    }
    renderPageList();
    await selectPage(state.selectedPageNumber);
    showStatus(`Saved entry ${response.entry_count} for page ${state.selectedPageNumber}.`, "success");
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

function handleNewEntry() {
  elements.userInput.value = "";
  elements.outputInput.value = "";
  showStatus("Cleared fields for a new entry.", "info");
}

async function handleSkip() {
  if (!state.docId || !state.selectedPageNumber) {
    showStatus("Select a page first.", "error");
    return;
  }
  try {
    const page = state.pages.find(
      (p) => p.page_number === state.selectedPageNumber
    );
    const nextState = page ? !page.skipped : true;
    const response = await fetchJson("/api/skip", {
      method: "POST",
      body: JSON.stringify({
        doc_id: state.docId,
        page_number: state.selectedPageNumber,
        skipped: nextState,
      }),
    });
    if (page) {
      page.skipped = response.skipped;
    }
    renderPageList();
    showStatus(
      `Page ${state.selectedPageNumber} ${response.skipped ? "skipped" : "unskipped"}.`,
      "info"
    );
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

function moveToNextPage() {
  const index = state.pages.findIndex((p) => p.page_number === state.selectedPageNumber);
  if (index === -1 || index + 1 >= state.pages.length) {
    showStatus("You've reached the last page.", "info");
    return;
  }
  selectPage(state.pages[index + 1].page_number);
}

function handlePageDownload() {
  if (!state.docId || !state.selectedPageNumber) {
    showStatus("Select a page first.", "error");
    return;
  }
  if (!confirm("Download this single-page PDF?")) {
    return;
  }
  const url = `/pages/${state.docId}/${String(state.selectedPageNumber).padStart(
    3,
    "0"
  )}`;
  window.open(url, "_blank");
}

async function handleGeneralSave() {
  if (!state.docId) {
    showStatus("Choose a document first.", "error");
    return;
  }
  const payload = {
    doc_id: state.docId,
    author: elements.generalAuthor.value,
    user_input: elements.generalUserInput.value,
    output: elements.generalOutputInput.value,
    tags: elements.generalTags.value,
  };
  try {
    const response = await fetchJson("/api/general", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.generalEntries = response.entries || [];
    renderGeneralEntries();
    if (response.latest) {
      applyGeneralAutofill(response.latest);
    }
    showStatus("Saved general entry.", "success");
  } catch (exc) {
    showStatus(exc.message, "error");
  }
}

async function handleDocumentSelect(event) {
  const docId = event.target.value;
  if (docId === "new") {
    state.docId = null;
    state.pages = [];
    state.currentDocument = null;
    state.generalMode = false;
    clearPageDetails();
    showUploadSection(true);
    updateDocSelection();
    updateWorkspaceVisibility();
    return;
  }
  if (!docId) {
    state.docId = null;
    state.pages = [];
    state.currentDocument = null;
    state.generalMode = true;
    clearPageDetails();
    updateDocSelection();
    updateWorkspaceVisibility();
    return;
  }
  await selectDocument(docId);
}

function renderGeneralEntries() {
  if (!elements.generalEntriesList) return;
  if (!state.generalEntries.length) {
    elements.generalEntriesList.innerHTML =
      "<p class='empty'>No general entries yet.</p>";
    return;
  }
  elements.generalEntriesList.innerHTML = "";
  state.generalEntries.forEach((entry) => {
    const item = document.createElement("div");
    item.className = "entry";
    item.innerHTML = `
      <div class="entry-header">
        <strong>${entry.author || "Untitled"}</strong>
        <span>${new Date(entry.created_at).toLocaleString()}</span>
      </div>
      <p>${entry.user_input || "(no input)"}</p>
      <p>${entry.output || "(no output)"}</p>
      <div class="tags">${entry.tags || "untagged"}</div>
    `;
    elements.generalEntriesList.appendChild(item);
  });
}

function renderEntrySnapshot(heading = "Entry preview") {
  if (!elements.entrySnapshot) return;
  const entry = state.entrySnapshot;
  if (!entry) {
    elements.entrySnapshot.innerHTML =
      "<p class='empty'>Click a button to load the latest or random entry.</p>";
    return;
  }
  elements.entrySnapshot.innerHTML = `
    <div class="snapshot-item">
      <strong>${heading}</strong>
      <small>Page ${entry.page_number} • ${entry.created_at}</small>
      <p>Author: ${entry.author || "—"}</p>
      <p>Tags: ${entry.tags || "untagged"}</p>
      <p class="muted">${entry.user_input || "(no input)"}</p>
      <p class="muted">${entry.output || "(no output)"}</p>
      <p>${entry.complete ? "Marked complete" : "Incomplete"}</p>
    </div>
  `;
}

function updateWorkspaceVisibility() {
  const hasDoc = Boolean(state.docId);
  const showDocument = hasDoc && !state.generalMode;
  if (elements.workspacePanel) {
    elements.workspacePanel.classList.toggle("hidden", !showDocument);
  }
  const showGeneral = state.generalMode || !hasDoc;
  if (elements.generalSection) {
    elements.generalSection.classList.toggle("active", showGeneral);
  }
  if (elements.previewPanel && !showDocument) {
    state.previewVisible = false;
    if (elements.togglePreviewBtn) {
      elements.togglePreviewBtn.textContent = "Show preview";
    }
  }
  updatePreviewState();
  if (elements.generalModeToggle) {
    elements.generalModeToggle.textContent = showGeneral
      ? "Hide general mode"
      : "Enter general mode";
  }
}

function applyGeneralAutofill(entry) {
  if (!entry) return;
  if (entry.author) {
    elements.generalAuthor.value = entry.author;
  }
  if (entry.tags) {
    elements.generalTags.value = entry.tags;
  }
}

function toggleGeneralMode() {
  state.generalMode = !state.generalMode;
  updateWorkspaceVisibility();
  showStatus(
    state.generalMode ? "General mode active" : "Back to page entries",
    "info"
  );
}
