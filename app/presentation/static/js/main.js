// UI Interactions & Drag and Drop Handling

document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("dropZone");
    const photoInput = document.getElementById("photo");

    if (dropZone && photoInput) {
        // Trigger click on hidden input
        dropZone.addEventListener("click", (e) => {
            if (e.target.closest("button")) return;
            photoInput.click();
        });

        // Drag and drop events
        ["dragenter", "dragover"].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add("border-violet-500", "bg-slate-900");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove("border-violet-500", "bg-slate-900");
            }, false);
        });

        dropZone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                photoInput.files = files;
                handlePreview(files[0]);
            }
        }, false);
    }
});

function previewSelectedImage(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
        handlePreview(files[0]);
    }
}

function handlePreview(file) {
    if (!file.type.startsWith("image/")) {
        alert("Por favor selecciona un archivo de imagen válido (JPG, PNG, WEBP).");
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const previewContainer = document.getElementById("previewContainer");
        const dropPrompt = document.getElementById("dropPrompt");
        const imagePreview = document.getElementById("imagePreview");
        const fileName = document.getElementById("fileName");

        if (imagePreview && previewContainer && dropPrompt) {
            imagePreview.src = e.target.result;
            fileName.innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            dropPrompt.classList.add("hidden");
            previewContainer.classList.remove("hidden");
        }
    };
    reader.readAsDataURL(file);
}

function clearImagePreview(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const photoInput = document.getElementById("photo");
    const previewContainer = document.getElementById("previewContainer");
    const dropPrompt = document.getElementById("dropPrompt");
    const imagePreview = document.getElementById("imagePreview");

    if (photoInput) photoInput.value = "";
    if (imagePreview) imagePreview.src = "#";
    if (previewContainer) previewContainer.classList.add("hidden");
    if (dropPrompt) dropPrompt.classList.remove("hidden");
}

