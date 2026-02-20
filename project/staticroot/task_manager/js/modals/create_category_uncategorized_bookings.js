// Shows all the bookings that haven't been assigned to a Category yet.
// It also will display an editor for the booking if it has one. Otherwise, "No editor".
document.addEventListener("DOMContentLoaded", () => {
    const uncategorizedBtn = document.getElementById("showUncategorized");
    const uncategorizedList = document.getElementById("uncategorizedList");
    const uncategorizedModalEl = document.getElementById("uncategorizedModal");
    const uncategorizedModal = new bootstrap.Modal(uncategorizedModalEl);

    if (!uncategorizedBtn) return; // safety check

    uncategorizedBtn.addEventListener("click", function (e) {
        e.preventDefault();

        uncategorizedList.innerHTML = `<li class="list-group-item text-muted">Loading...</li>`;

        fetch("/api/bookings/uncategorized/")
            .then(r => r.json())
            .then(data => {
                uncategorizedList.innerHTML = "";

                if (data.bookings?.length > 0) {
                    data.bookings.forEach((b, idx) => {
                        const li = document.createElement("li");
                        li.className = "list-group-item d-flex justify-content-between align-items-center";
                        li.innerHTML = `
                          <div>
                            <strong>${idx + 1}.</strong> ${b.title || "Unknown"}
                          </div>
                          <small class="text-muted">${b.editor || "No editor"}</small>
                        `;
                        uncategorizedList.appendChild(li);
                    });
                } else {
                    uncategorizedList.innerHTML = `
                        <li class="list-group-item text-muted">No uncategorized bookings 🎉</li>
                    `;
                }

                uncategorizedModal.show();
            })
            .catch(err => {
                uncategorizedList.innerHTML = `
                    <li class="list-group-item text-danger">Error loading bookings</li>
                `;
                console.error(err);
                uncategorizedModal.show();
            });
    });
});
