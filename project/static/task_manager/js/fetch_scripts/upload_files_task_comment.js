document.addEventListener("DOMContentLoaded", function () {
    const fileInput = document.getElementById("id_file");
    const fileListDisplay = document.getElementById("file-list");
    const uploadedFilesInput = document.getElementById("uploaded-files");
    const uploadedFiles = [];

    // Get token from localStorage or fetch from server
    let token = localStorage.getItem("access_token");
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Fetch session token if not available in localStorage
    if (!token) {
        fetch("/api/auth/session-token/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.key) {
                token = data.key;
                localStorage.setItem("access_token", token);
                console.log("Token received and saved");
            } else {
                console.error("Error getting token:", data);
            }
        })
        .catch(error => {
            console.error("Error getting token:", error);
        });
    }

    // Handler for file uploads
    fileInput.addEventListener("change", function (event) {
        const files = Array.from(event.target.files);
        files.forEach(file => uploadFile(file));
    });

    function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        // Create a temporary endpoint for file uploads during task creation
        const uploadUrl = "/api/upload-task-comment-file/";

        // Create list item with progress bar
        const listItem = document.createElement("li");
        listItem.className = "list-group-item d-flex justify-content-between align-items-center";
        listItem.innerHTML = `<span>${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                              <div class="progress w-50">
                                  <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 50%"></div>
                              </div>
                              <i class="ph-x text-danger" style="cursor: pointer;"></i>`;
        fileListDisplay.appendChild(listItem);

        const progressBar = listItem.querySelector(".progress-bar");
        const deleteButton = listItem.querySelector(".ph-x");

        // Remove file from list when delete button is clicked
        deleteButton.addEventListener("click", function () {
            listItem.remove();
            // Find and remove file from uploadedFiles array
            const fileIndex = uploadedFiles.findIndex(f => f.name === file.name);
            if (fileIndex !== -1) {
                uploadedFiles.splice(fileIndex, 1);
                uploadedFilesInput.value = JSON.stringify(uploadedFiles);
            }
        });

        // Upload file using temporary endpoint
        fetch(uploadUrl, {
            method: "POST",
            body: formData,
            headers: { 
                "X-CSRFToken": csrfToken,
                'Authorization': `Bearer ${token}`,
                "Accept": "application/json",
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.uploaded_files && data.uploaded_files.length > 0) {
                progressBar.classList.remove("progress-bar-animated");
                progressBar.style.width = "100%";
                progressBar.classList.add("bg-success");

                const fileData = data.uploaded_files[0];
                
                // Store file information for later use
                uploadedFiles.push({
                    name: fileData.name,
                    size: fileData.size,
                    url: fileData.url,
                    temp_id: fileData.temp_id  // Store temporary ID for associating with task
                });
                
                // Update hidden input with uploaded files data
                uploadedFilesInput.value = JSON.stringify(uploadedFiles);

                // Update list item to show uploaded file
                listItem.innerHTML = `<span class="me-auto">${file.name}</span>
                <div class="d-flex align-items-center">
                    <span class="text-muted me-2">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
                    <span class="badge bg-success me-2">Uploaded</span>
                    <i class="ph-x text-danger" style="cursor: pointer;"></i>
                </div>`;
                
                // Add delete handler after upload
                listItem.querySelector(".ph-x").addEventListener("click", function () {
                    listItem.remove();
                    const fileIndex = uploadedFiles.findIndex(f => f.name === file.name);
                    if (fileIndex !== -1) {
                        uploadedFiles.splice(fileIndex, 1);
                        uploadedFilesInput.value = JSON.stringify(uploadedFiles);
                    }
                });
            } else {
                throw new Error("Upload failed");
            }
        })
        .catch(error => {
            console.error("Upload error:", error);
            progressBar.classList.remove("progress-bar-animated");
            progressBar.classList.add("bg-danger");
            progressBar.style.width = "100%";
        });
    }
});