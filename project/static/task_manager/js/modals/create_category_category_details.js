//
document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("categoryModal");
    const categoryModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const bookingsList = document.getElementById("categoryBookings");

    // Defensive cleanup
    modalEl.addEventListener("hidden.bs.modal", () => {
        document.body.classList.remove("modal-open");
        document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
    });

    // --- EVENT DELEGATION FOR DETAILS BUTTONS ---
    document.getElementById("categoriesTable").addEventListener("click", function (e) {
        const btn = e.target.closest("a.details-btn");
        if (!btn) return;

        e.preventDefault();
        const id = btn.dataset.id;

        fetch(`/api/categories/${id}/`)
            .then(r => r.json())
            .then(data => {
                if (data.error) return;

                // Fill form
                document.getElementById("editCategoryId").value = data.id;
                document.getElementById("editKeyword").value = data.keyword;
                document.getElementById("editPlan").value = data.plan;

                // Fill bookings list
                bookingsList.innerHTML = "";
                if (data.bookings.length > 0) {
                    data.bookings.forEach((b, idx) => {
                        const li = document.createElement("li");
                        li.className = "list-group-item d-flex justify-content-between align-items-center";
                        li.innerHTML = `
                            <div class="booking-left">
                                <span class="booking-idx">${idx + 1}.</span>
                                <span class="booking-label" title="${b.title.replace(/"/g, '&quot;')}">${b.title}</span>
                            </div>
                            <small class="text-muted">${b.editor || "No editor"}</small>
                        `;
                        bookingsList.appendChild(li);
                    });
                } else {
                    bookingsList.innerHTML = `<li class="list-group-item text-muted">No bookings found</li>`;
                }

                // Show modal
                categoryModal.show();
            });
    });

    // --- SAVE EDIT ---
    document.getElementById("editCategoryForm").addEventListener("submit", function (e) {
        e.preventDefault();
        const id = document.getElementById("editCategoryId").value;
        const formData = new FormData(this);

        fetch(`/api/categories/${id}/update/`, {
            method: "POST",
            headers: { "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value },
            body: formData
        })
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    console.error("Validation failed:", data.errors);
                    return;
                }

                // Update table row
                const row = document.querySelector(`#categoriesTable .delete-btn[data-id="${id}"]`).closest("tr");
                row.children[0].textContent = data.keyword;
                row.children[1].textContent = data.plan;

                // Close modal
                categoryModal.hide();
            });
    });
});
