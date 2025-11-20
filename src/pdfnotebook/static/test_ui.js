const state = {
    docId: null,
    pages: [],
    selectedPageNumber: null,
};

const elements = {
    documentSelect: document.getElementById("documentSelect"),
    pageList: document.getElementById("pageList"),
    workspacePanel: document.getElementById("workspacePanel"),
    emptyState: document.getElementById("emptyState"),
    pageHeading: document.getElementById("pageHeading"),
    entryCount: document.getElementById("entryCount"),
    authorInput: document.getElementById("authorInput"),
    tagsInput: document.getElementById("tagsInput"),
    userInput: document.getElementById("userInput"),
    outputInput: document.getElementById("outputInput"),
    downloadPageBtn: document.getElementById("downloadPageBtn"),
    saveBtn: document.getElementById("saveBtn"),
    uploadSection: document.getElementById("uploadSection"),
    uploadForm: document.getElementById("uploadForm"),
    uploadName: document.getElementById("uploadName"),
    uploadFile: document.getElementById("uploadFile"),
    cancelUpload: document.getElementById("cancelUpload"),
    progressArea: document.getElementById("progressArea"),
    progressBar: document.getElementById("progressBar"),
    progressText: document.getElementById("progressText"),
    generalPanel: document.getElementById("generalPanel"),
    genAuthor: document.getElementById("genAuthor"),
    genTags: document.getElementById("genTags"),
    genInput: document.getElementById("genInput"),
    genOutput: document.getElementById("genOutput"),
    genAttachment: document.getElementById("genAttachment"),
    saveGeneralBtn: document.getElementById("saveGeneralBtn"),
    generalList: document.getElementById("generalList"),
    attachmentInput: document.getElementById("attachmentInput"),
    currentAttachment: document.getElementById("currentAttachment"),
    newEntryBtn: document.getElementById("newEntryBtn"),
};

document.addEventListener("DOMContentLoaded", () => {
    loadDocuments();
    elements.documentSelect.addEventListener("change", handleDocumentSelect);
    elements.pageList.addEventListener("click", handlePageClick);
    elements.downloadPageBtn.addEventListener("click", handlePageDownload);
    elements.saveBtn.addEventListener("click", handleSave);
    elements.uploadForm.addEventListener("submit", handleUpload);
    elements.cancelUpload.addEventListener("click", hideUpload);
    elements.saveGeneralBtn.addEventListener("click", handleGeneralSave);
    elements.newEntryBtn.addEventListener("click", handleNewEntry);
});

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || "Request failed");
    }
    return response.json();
}

async function loadDocuments() {
    try {
        const payload = await fetchJson("/api/documents");
        const docs = payload.documents || [];
        renderDocSelect(docs);
    } catch (err) {
        console.error(err);
        elements.documentSelect.innerHTML = "<option>Error loading docs</option>";
    }
}

function renderDocSelect(docs) {
    elements.documentSelect.innerHTML = `<option value="">-- Select Document --</option>`;
    elements.documentSelect.innerHTML += `<option value="new">➕ New Document</option>`;
    elements.documentSelect.innerHTML += `<option value="global-general">📓 General Notebook</option>`;
    docs.forEach((doc) => {
        if (doc.id === "global-general") return; // Skip if already in list (though usually it's not in list_documents if created manually? Actually list_documents returns all. We should filter or just let it be. Let's filter to avoid duplicate if it appears.)
        const option = document.createElement("option");
        option.value = doc.id;
        option.textContent = `${doc.name} (${doc.page_count} pages)`;
        elements.documentSelect.appendChild(option);
    });
    if (state.docId) {
        elements.documentSelect.value = state.docId;
    }
}

async function handleDocumentSelect(event) {
    const docId = event.target.value;

    if (docId === "new") {
        showUpload(true);
        state.docId = null;
        state.pages = [];
        renderPageList();
        showWorkspace(false);
        showGeneral(false);
        return;
    }

    showUpload(false);

    if (!docId) {
        state.docId = null;
        state.pages = [];
        renderPageList();
        showWorkspace(false);
        showGeneral(false);
        return;
    }

    state.docId = docId;

    if (docId === "global-general") {
        state.pages = [];
        renderPageList();
        showWorkspace(false);
        showGeneral(true);
        loadGeneralEntries();
        return;
    }

    showGeneral(false);

    try {
        const payload = await fetchJson(`/api/pages/${docId}`);
        state.pages = payload.pages;
        renderPageList();
        updateProgress();
        showWorkspace(false);
    } catch (err) {
        console.error(err);
    }
}

function showGeneral(show) {
    if (show) {
        elements.generalPanel.classList.remove("hidden");
        elements.emptyState.classList.add("hidden");
        elements.progressArea.classList.add("hidden");
    } else {
        elements.generalPanel.classList.add("hidden");
    }
}

async function loadGeneralEntries() {
    try {
        const res = await fetchJson(`/api/general/global-general`);
        const entries = res.entries || [];
        renderGeneralEntries(entries);
    } catch (err) {
        console.error(err);
    }
}

function renderGeneralEntries(entries) {
    elements.generalList.innerHTML = "";
    if (!entries.length) {
        elements.generalList.innerHTML = "<p class='empty'>No entries yet.</p>";
        return;
    }
    entries.forEach(entry => {
        const div = document.createElement("div");
        div.className = "minimal-card";
        div.style.padding = "1rem";
        div.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
                <strong>${entry.author || "Anonymous"}</strong>
                <small>${new Date(entry.created_at).toLocaleString()}</small>
            </div>
            <p><strong>Input:</strong> ${entry.user_input}</p>
            <p><strong>Output:</strong> ${entry.output}</p>
            ${entry.attachment_path ? `<p><a href="/attachments/${entry.attachment_path}" target="_blank">📎 View Attachment</a></p>` : ''}
            <small style="color:var(--text-muted)">Tags: ${entry.tags}</small>
        `;
        elements.generalList.appendChild(div);
    });
}

async function handleGeneralSave() {
    const formData = new FormData();
    formData.append("doc_id", "global-general");
    formData.append("author", elements.genAuthor.value);
    formData.append("user_input", elements.genInput.value);
    formData.append("output", elements.genOutput.value);
    formData.append("tags", elements.genTags.value);

    if (elements.genAttachment.files[0]) {
        formData.append("attachment", elements.genAttachment.files[0]);
    }

    try {
        await fetchJson("/api/general", {
            method: "POST",
            body: formData
        });

        elements.genInput.value = "";
        elements.genOutput.value = "";
        elements.genAttachment.value = ""; // Reset file input
        loadGeneralEntries();

    } catch (err) {
        alert(err.message);
    }
}

function showUpload(show) {
    if (show) {
        elements.uploadSection.classList.remove("hidden");
    } else {
        elements.uploadSection.classList.add("hidden");
    }
}

function hideUpload() {
    elements.documentSelect.value = state.docId || "";
    showUpload(false);
}

async function handleUpload(e) {
    e.preventDefault();
    const formData = new FormData();
    const file = elements.uploadFile.files[0];
    if (!file) return;

    formData.append("file", file);
    if (elements.uploadName.value) {
        formData.append("name", elements.uploadName.value);
    }

    try {
        const res = await fetch("/api/documents", {
            method: "POST",
            body: formData
        });
        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();

        elements.uploadFile.value = "";
        elements.uploadName.value = "";
        showUpload(false);

        await loadDocuments();
        state.docId = data.doc_id;
        elements.documentSelect.value = state.docId;

        // Trigger load
        const payload = await fetchJson(`/api/pages/${state.docId}`);
        state.pages = payload.pages;
        renderPageList();
        updateProgress();
        showWorkspace(false);

    } catch (err) {
        alert(err.message);
    }
}

function renderPageList() {
    if (!state.pages.length) {
        elements.pageList.innerHTML = "<p class='empty'>No pages found.</p>";
        elements.progressArea.classList.add("hidden");
        return;
    }
    elements.progressArea.classList.remove("hidden");
    elements.pageList.innerHTML = "";
    state.pages.forEach((page) => {
        const item = document.createElement("div");
        item.className = `page-item ${state.selectedPageNumber === page.page_number ? "active" : ""}`;
        item.dataset.pageNumber = page.page_number;
        item.innerHTML = `
      <div>
        <span class="page-number">Page ${page.page_number}</span>
        <span class="page-status">${page.complete ? "✓ Complete" : "Pending"}</span>
      </div>
    `;
        elements.pageList.appendChild(item);
    });
}

function updateProgress() {
    if (!state.pages.length) return;
    const completed = state.pages.filter(p => p.complete).length;
    const total = state.pages.length;
    const pct = Math.round((completed / total) * 100);
    elements.progressBar.style.width = `${pct}%`;
    elements.progressText.textContent = `${pct}% Complete (${completed}/${total})`;
}

function handlePageClick(event) {
    const item = event.target.closest(".page-item");
    if (!item) return;
    const pageNumber = Number(item.dataset.pageNumber);
    selectPage(pageNumber);
}

async function selectPage(pageNumber) {
    state.selectedPageNumber = pageNumber;

    // Update UI selection
    document.querySelectorAll(".page-item").forEach(el => {
        el.classList.toggle("active", Number(el.dataset.pageNumber) === pageNumber);
    });

    try {
        const payload = await fetchJson(`/api/pages/${state.docId}/${pageNumber}`);
        const page = payload.page;

        elements.pageHeading.textContent = `Page ${page.page_number}`;
        elements.authorInput.value = page.author || "";
        elements.tagsInput.value = page.tags || "";
        elements.userInput.value = page.user_input || "";
        elements.outputInput.value = page.output || "";

        const listPage = state.pages.find(p => p.page_number === pageNumber);
        const count = listPage ? listPage.entry_count : "?";
        elements.entryCount.textContent = `${count} entries`;

        elements.userInput.value = page.user_input || "";
        elements.outputInput.value = page.output || "";

        if (page.attachment_path) {
            elements.currentAttachment.innerHTML = `Current: <a href="/attachments/${page.attachment_path}" target="_blank">📎 View Attachment</a>`;
        } else {
            elements.currentAttachment.textContent = "";
        }
        elements.attachmentInput.value = ""; // Reset file input
        showWorkspace(true);
    } catch (err) {
        console.error(err);
    }
}

async function handleSave() {
    if (!state.docId || !state.selectedPageNumber) return;

    const formData = new FormData();
    formData.append("doc_id", state.docId);
    formData.append("page_number", state.selectedPageNumber);
    formData.append("author", elements.authorInput.value);
    formData.append("user_input", elements.userInput.value);
    formData.append("output", elements.outputInput.value);
    formData.append("tags", elements.tagsInput.value);
    formData.append("complete", true);

    if (elements.attachmentInput.files[0]) {
        formData.append("attachment", elements.attachmentInput.files[0]);
    }

    try {
        const response = await fetchJson("/api/entry", {
            method: "POST",
            body: formData // fetch handles Content-Type for FormData
        });

        // Update entry count from response
        if (response.entry_count !== undefined) {
            elements.entryCount.textContent = `${response.entry_count} entries`;
            // Also update the page in the list if we want to track it there, though it's not currently shown in the list item
            const page = state.pages.find(p => p.page_number === state.selectedPageNumber);
            if (page) {
                page.entry_count = response.entry_count;
            }
        }

        // Update local state
        const page = state.pages.find(p => p.page_number === state.selectedPageNumber);
        if (page) {
            page.complete = true;
            page.author = elements.authorInput.value;
            page.user_input = elements.userInput.value;
            page.output = elements.outputInput.value;
            page.tags = elements.tagsInput.value;
            // We can't easily update attachment_path without re-fetching, 
            // but we can reload the page list to show status
        }
        renderPageList();
        updateProgress();
        // Reload page details to get the new attachment path if needed, 
        // but for now just keeping it simple.

        // Show simple feedback
        const originalText = elements.saveBtn.textContent;
        elements.saveBtn.textContent = "Saved!";
        setTimeout(() => elements.saveBtn.textContent = originalText, 2000);

    } catch (err) {
        alert("Failed to save: " + err.message);
    }
}

function showWorkspace(show) {
    if (show) {
        elements.workspacePanel.classList.remove("hidden");
        elements.emptyState.classList.add("hidden");
    } else {
        elements.workspacePanel.classList.add("hidden");
        elements.emptyState.classList.remove("hidden");
    }
}

function handlePageDownload() {
    if (!state.docId || !state.selectedPageNumber) return;
    const url = `/pages/${state.docId}/${String(state.selectedPageNumber).padStart(3, "0")}`;
    window.open(url, "_blank");
}

async function handleNewEntry() {
    // "New Entry" behaves exactly like "Save Changes" in that it saves the current form state as a new entry.
    // The backend add_entry function always adds a new entry to the history.
    // So we can just reuse handleSave, or call it directly.
    // If we wanted to clear the form *after* saving, we would do that here.
    // But the user request implies just adding a button to trigger the entry creation.
    // Let's reuse handleSave but maybe give different feedback?
    // For now, reusing handleSave is the safest bet to ensure consistency.
    await handleSave();
}
