// Set default theme to dark if not set
if (!localStorage.getItem("theme")) {
  localStorage.setItem("theme", "dark");
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return null;
}

document.addEventListener("DOMContentLoaded", () => {
    const DIET_COLOR_SWATCHES = ["#971d1f", "#ad5322", "#af882e", "#538d28", "#2b8066", "#375875"];
    const body = document.body;
    body.setAttribute("data-bs-theme", localStorage.getItem("theme"));

    // Theme switch button
    const themeToggleBtn = document.getElementById("theme-toggle");
    if (themeToggleBtn) {
        const icon = themeToggleBtn.querySelector("i");
        const text = themeToggleBtn.querySelector(".theme-text");

        function sync_toggle_button_html_with_theme() {
            const t = body.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
            if (t === "dark") {
                icon.className = "nav-icon bi bi-sun";
                if (text) text.textContent = "Light mode";
            } else {
                icon.className = "nav-icon bi bi-moon-stars";
                if (text) text.textContent = "Dark mode";
            }
        }

        themeToggleBtn.addEventListener("click", (e) => {
            e.preventDefault();
            const opposite = body.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            body.setAttribute("data-bs-theme", opposite);
            localStorage.setItem("theme", opposite);
            
            sync_toggle_button_html_with_theme();
        });
        // Theme switch button end

        sync_toggle_button_html_with_theme(); //Sync theme toggle button in sidebar upon page load
    }

    const currentPath = normalizePath(window.location.pathname);

    document.querySelectorAll("a[href]").forEach((link) => {
        const href = link.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;

        let linkPath;
        try {
            linkPath = normalizePath(new URL(href, window.location.origin).pathname);
        } catch {
            return;
        }
        const isExact = linkPath === currentPath;
        const isPrefix = linkPath !== "/" && currentPath.startsWith(linkPath + "/");

        if (isExact || isPrefix) {
            link.classList.add("active");

            const navItem = link.closest(".nav-item");
            if (navItem) navItem.classList.add("menu-open");

            const parentLink = navItem?.closest(".nav-treeview")?.previousElementSibling;
            if (parentLink?.classList?.contains("nav-link")) {
            parentLink.classList.add("active");
            }
        }
    });

    function normalizePath(path) {
        if (!path) return "/";
        const p = path.endsWith("/") && path.length > 1 ? path.slice(0, -1) : path;
        return p || "/";
    }

    const dietNavLoading = document.getElementById("diet-nav-loading");
    const dietNavTemplate = document.getElementById("diet-nav-item-template");
    if (dietNavLoading && dietNavTemplate?.content) {
        fetch("/api/diets/*")
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((diets) => {
                const dietNames = new Set();
                if (Array.isArray(diets)) {
                    diets.forEach((diet) => {
                        if (diet?.diet_name) {
                            dietNames.add(String(diet.diet_name));
                        }
                    });
                }

                if (dietNames.size === 0) {
                    dietNavLoading.querySelector("p").textContent = "No diets found.";
                    return;
                }

                const sortedNames = Array.from(dietNames).sort((a, b) => a.localeCompare(b));
                const parent = dietNavLoading.parentElement;
                sortedNames.forEach((name) => {
                    const item = dietNavTemplate.content.firstElementChild.cloneNode(true);
                    const link = item.querySelector("a");
                    const label = item.querySelector("p");
                    link.href = `/?diet_name=${encodeURIComponent(name)}`;
                    label.textContent = name;
                    parent.insertBefore(item, dietNavLoading);
                });
                dietNavLoading.remove();
            })
            .catch(() => {
                dietNavLoading.querySelector("p").textContent = "Failed to load diets.";
            });
    }

    const dietItemsHead = document.getElementById("diet-items-head");
    const dietItemsBody = document.getElementById("diet-items-body");
    const dietItemsStatus = document.getElementById("diet-items-status");
    const dietItemsSaveAll = document.getElementById("diet-items-save-all");
    const dietItemsAdd = document.getElementById("diet-items-add");
    if (!dietItemsHead || !dietItemsBody || !dietItemsStatus || !dietItemsSaveAll || !dietItemsAdd) return;

    const params = new URLSearchParams(window.location.search);
    const dietName = params.get("diet_name");
    if (!dietName) {
        dietItemsStatus.textContent = "Missing diet_name in the URL.";
        return;
    }

    dietItemsStatus.textContent = `Loading ${dietName} items...`;

    let activeEditRow = null;

    function setEditingRow(row) {
        if (activeEditRow && activeEditRow !== row) {
            activeEditRow.classList.remove("is-editing");
        }
        activeEditRow = row;
        row.classList.add("is-editing");
    }

    let lastLoadedItems = [];
    let foodsLoadPromise = null;
    let foodsById = new Map();
    let foodsList = [];
    let foodsFuse = null;

    function ensureFoodsLoaded() {
        if (foodsLoadPromise) {
            return foodsLoadPromise;
        }
        foodsLoadPromise = fetch("/api/foods")
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((foods) => {
                foodsById = new Map();
                foodsList = Array.isArray(foods) ? foods.slice() : [];
                foodsList.forEach((food) => {
                    if (food?.fdc_id != null) {
                        foodsById.set(food.fdc_id, food);
                    }
                });
                foodsList.sort((a, b) => {
                    const aName = String(a?.Name ?? "");
                    const bName = String(b?.Name ?? "");
                    return aName.localeCompare(bName);
                });
                if (window.Fuse) {
                    foodsFuse = new Fuse(foodsList, {
                        keys: ["Name"],
                        includeScore: true,
                        threshold: 0.4,
                        ignoreLocation: true,
                    });
                } else {
                    foodsFuse = null;
                }
            })
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to load foods: ${error.message}`;
                foodsById = new Map();
                foodsList = [];
            });
        return foodsLoadPromise;
    }

    function loadDietItems() {
        dietItemsStatus.textContent = `Loading ${dietName} items...`;
        dietItemsSaveAll.disabled = true;
        dietItemsAdd.disabled = true;
        activeEditRow = null;
        ensureFoodsLoaded()
            .then(() => fetch(`/api/diets/${encodeURIComponent(dietName)}/nutrition`))
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((items) => {
                if (!Array.isArray(items)) {
                    throw new Error("Unexpected response format.");
                }
                items.sort((a, b) => Number(a.sort_order) - Number(b.sort_order));
                lastLoadedItems = items.slice();

                if (items.length === 0) {
                    dietItemsStatus.textContent = `No items found for ${dietName}.`;
                    dietItemsHead.innerHTML = "";
                    dietItemsBody.innerHTML = "";
                    dietItemsSaveAll.disabled = true;
                    dietItemsAdd.disabled = false;
                    return;
                }

                const rawColumns = Object.keys(items[0] || {});
                const columns = [];
                if (rawColumns.includes("color")) {
                    columns.push("color");
                }
                if (rawColumns.includes("Name")) {
                    columns.push("Name");
                }
                if (rawColumns.includes("quantity")) {
                    columns.push("quantity");
                }
                rawColumns.forEach((col) => {
                    if (col === "color" || col === "Name" || col === "quantity") {
                        return;
                    }
                    columns.push(col);
                });
                if (columns.length === 0) {
                    dietItemsStatus.textContent = `No data fields found for ${dietName}.`;
                    dietItemsHead.innerHTML = "";
                    dietItemsBody.innerHTML = "";
                    dietItemsSaveAll.disabled = true;
                    dietItemsAdd.disabled = false;
                    return;
                }

                const headRow = document.createElement("tr");
                columns.forEach((col) => {
                    const th = document.createElement("th");
                    th.textContent = col;
                    if (col === "Name") {
                        th.classList.add("name-col");
                    }
                    if (col === "diet_name" || col === "fdc_id" || col === "sort_order") {
                        th.classList.add("is-hidden-col");
                    }
                    headRow.appendChild(th);
                });
                dietItemsHead.innerHTML = "";
                dietItemsHead.appendChild(headRow);

                const fragment = document.createDocumentFragment();
                items.forEach((item) => {
                    const row = document.createElement("tr");
                    if (item.color) {
                        row.style.backgroundColor = toRgba(item.color, 0.5);
                    }

                    const original = {
                        fdc_id: item.fdc_id ?? "",
                        quantity: item.quantity ?? "",
                        sort_order: item.sort_order ?? "",
                    };
                    row.dataset.dietName = item.diet_name ?? dietName;
                    row.dataset.originalFdcId = original.fdc_id;
                    row.dataset.originalQuantity = original.quantity;
                    row.dataset.originalSortOrder = original.sort_order;
                    row.dataset.originalColor = item.color ?? "";

                    row.addEventListener("click", (event) => {
                        if (event.target.closest("button")) {
                            return;
                        }
                        setEditingRow(row);
                    });

                    columns.forEach((col) => {
                        const cell = document.createElement("td");
                        const value = item[col];
                        if (col === "diet_name" || col === "fdc_id" || col === "sort_order") {
                            cell.classList.add("is-hidden-col");
                        }

                        if (col === "Name") {
                            cell.classList.add("name-col");
                            const display = document.createElement("span");
                            display.className = "cell-value";
                            const currentFood = foodsById.get(item.fdc_id);
                            display.textContent = currentFood?.Name ?? value ?? "";

                            const picker = document.createElement("div");
                            picker.className = "food-picker cell-input";

                            const input = document.createElement("input");
                            input.type = "text";
                            input.className = "form-control form-control-sm food-search";
                            input.value = display.textContent ?? "";

                            const options = document.createElement("div");
                            options.className = "food-options";

                            function renderOptions(query) {
                                const q = String(query || "").trim();
                                let top = [];
                                if (foodsFuse && q) {
                                    top = foodsFuse.search(q).slice(0, 20).map((result) => ({ food: result.item }));
                                } else {
                                    top = foodsList.slice(0, 20).map((food) => ({ food }));
                                }

                                options.innerHTML = "";
                                top.forEach(({ food }) => {
                                    const option = document.createElement("div");
                                    option.className = "food-option";
                                    option.textContent = food.Name ?? "";
                                    option.dataset.fdcId = food.fdc_id;
                                    option.addEventListener("mousedown", (event) => {
                                        event.preventDefault();
                                        const selectedId = Number(option.dataset.fdcId);
                                        const selectedFood = foodsById.get(selectedId);
                                        if (!selectedFood) {
                                            return;
                                        }
                                        input.value = selectedFood.Name ?? "";
                                        display.textContent = selectedFood.Name ?? "";
                                        const fdcInput = row.querySelector("input[data-column='fdc_id']");
                                        const fdcDisplay = row.querySelector(".fdc-id-display");
                                        if (fdcInput) {
                                            fdcInput.value = String(selectedFood.fdc_id);
                                        }
                                        if (fdcDisplay) {
                                            fdcDisplay.textContent = String(selectedFood.fdc_id);
                                        }
                                        options.style.display = "none";
                                        updateSaveAllState();
                                    });
                                    options.appendChild(option);
                                });

                                options.style.display = top.length > 0 ? "block" : "none";
                            }

                            input.addEventListener("input", () => {
                                renderOptions(input.value);
                            });
                            input.addEventListener("focus", () => {
                                renderOptions(input.value);
                            });
                            input.addEventListener("blur", () => {
                                setTimeout(() => {
                                    options.style.display = "none";
                                }, 150);
                            });

                            picker.appendChild(input);
                            picker.appendChild(options);
                            cell.appendChild(display);
                            cell.appendChild(picker);
                        } else if (col === "fdc_id") {
                            const display = document.createElement("span");
                            display.className = "fdc-id-display";
                            display.textContent = value ?? "";

                            const input = document.createElement("input");
                            input.type = "hidden";
                            input.value = value ?? "";
                            input.dataset.column = "fdc_id";

                            cell.appendChild(display);
                            cell.appendChild(input);
                        } else if (col === "color") {
                            const display = document.createElement("span");
                            display.className = "cell-value";
                            display.dataset.column = col;
                            display.textContent = value ?? "";
                            display.style.display = "none";

                            const input = document.createElement("input");
                            input.type = "hidden";
                            input.value = value ?? "";
                            input.dataset.column = col;

                            const picker = document.createElement("div");
                            picker.className = "color-picker cell-input";
                            DIET_COLOR_SWATCHES.forEach((color) => {
                                const swatch = document.createElement("span");
                                swatch.className = "color-swatch";
                                swatch.style.backgroundColor = color;
                                if (String(value).toLowerCase() === color.toLowerCase()) {
                                    swatch.classList.add("is-selected");
                                }
                                swatch.addEventListener("click", () => {
                                    const isSelected = swatch.classList.contains("is-selected");
                                    picker.querySelectorAll(".color-swatch").forEach((node) => {
                                        node.classList.remove("is-selected");
                                    });
                                    if (isSelected) {
                                        input.value = "";
                                        display.textContent = "";
                                        row.style.backgroundColor = "";
                                    } else {
                                        input.value = color;
                                        display.textContent = color;
                                        swatch.classList.add("is-selected");
                                        row.style.backgroundColor = toRgba(color, 0.5);
                                    }
                                    updateSaveAllState();
                                });
                                picker.appendChild(swatch);
                            });

                            cell.appendChild(display);
                            cell.appendChild(input);
                            cell.appendChild(picker);
                        } else if (col === "quantity" || col === "sort_order") {
                            const display = document.createElement("span");
                            display.className = "cell-value";
                            display.dataset.column = col;
                            display.textContent = value ?? "";

                            const input = document.createElement("input");
                            input.className = "form-control form-control-sm cell-input";
                            input.value = value ?? "";
                            input.dataset.column = col;
                            if (col === "sort_order") {
                                input.type = "number";
                                input.step = "1";
                            } else {
                                input.type = "number";
                                input.step = "0.01";
                            }
                            input.addEventListener("input", () => {
                                display.textContent = input.value;
                            });

                            cell.appendChild(display);
                            cell.appendChild(input);
                        } else {
                            cell.textContent = value ?? "";
                        }

                        row.appendChild(cell);
                    });

                    fragment.appendChild(row);
                });

                if (rawColumns.includes("Energy kcal")) {
                    const totalsRow = document.createElement("tr");
                    totalsRow.classList.add("totals-row");
                    columns.forEach((col, index) => {
                        const cell = document.createElement("td");
                        if (col === "diet_name" || col === "fdc_id" || col === "sort_order") {
                            cell.classList.add("is-hidden-col");
                        }
                        if (index === 0) {
                            cell.textContent = "Totals";
                        } else if (col === "Name" || col === "quantity" || col === "color" || col === "Unit") {
                            cell.textContent = "";
                        } else {
                            let total = 0;
                            items.forEach((item) => {
                                const fieldValue = item[col];
                                if (typeof fieldValue === "number" && Number.isFinite(fieldValue)) {
                                    total += fieldValue;
                                } else if (
                                    typeof fieldValue === "string" &&
                                    fieldValue.trim() !== "" &&
                                    !Number.isNaN(Number(fieldValue))
                                ) {
                                    total += Number(fieldValue);
                                }
                            });
                            cell.textContent = total.toFixed(2);
                        }
                        totalsRow.appendChild(cell);
                    });
                    fragment.appendChild(totalsRow);
                }

                dietItemsBody.innerHTML = "";
                dietItemsBody.appendChild(fragment);
                dietItemsStatus.textContent = `Loaded ${items.length} items for ${dietName}.`;

                if (window.Sortable) {
                    if (dietItemsBody._sortable) {
                        dietItemsBody._sortable.destroy();
                    }
                    dietItemsBody._sortable = new Sortable(dietItemsBody, {
                        animation: 150,
                        filter: "input,select,button,.food-options",
                        preventOnFilter: false,
                        onEnd: () => {
                            const rows = Array.from(dietItemsBody.querySelectorAll("tr"));
                            rows.forEach((row, index) => {
                                const newOrder = index + 1;
                                const sortInput = row.querySelector("input[data-column='sort_order']");
                                if (sortInput) {
                                    sortInput.value = String(newOrder);
                                }
                                const sortCellDisplay = row.querySelector(".cell-value[data-column='sort_order']");
                                if (sortCellDisplay && sortInput && sortCellDisplay.textContent !== sortInput.value) {
                                    sortCellDisplay.textContent = sortInput.value;
                                }
                            });
                            updateSaveAllState();
                        },
                    });
                }

                const inputs = dietItemsBody.querySelectorAll("input[data-column]");
                inputs.forEach((input) => {
                    input.addEventListener("input", () => {
                        updateSaveAllState();
                    });
                });
                updateSaveAllState();
                dietItemsAdd.disabled = false;
            })
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to load items: ${error.message}`;
                dietItemsSaveAll.disabled = false;
                dietItemsAdd.disabled = false;
            });
    }

    loadDietItems();

    function rowHasChanges(row) {
        const inputs = row.querySelectorAll("input[data-column]");
        const current = {};
        inputs.forEach((input) => {
            current[input.dataset.column] = input.value;
        });

        const originalFdcId = String(row.dataset.originalFdcId ?? "");
        const originalQuantity = String(row.dataset.originalQuantity ?? "");
        const originalSortOrder = String(row.dataset.originalSortOrder ?? "");
        const originalColor = String(row.dataset.originalColor ?? "");

        return (
            String(current.fdc_id ?? "") !== originalFdcId ||
            String(current.quantity ?? "") !== originalQuantity ||
            String(current.sort_order ?? "") !== originalSortOrder ||
            String(current.color ?? "") !== originalColor
        );
    }

    function updateSaveAllState() {
        const rows = Array.from(dietItemsBody.querySelectorAll("tr"));
        const hasChanges = rows.some((row) => {
            const dirty = rowHasChanges(row);
            row.classList.toggle("is-dirty", dirty);
            return dirty;
        });
        dietItemsSaveAll.disabled = !hasChanges;
    }

    dietItemsSaveAll.addEventListener("click", () => {
        const rows = Array.from(dietItemsBody.querySelectorAll("tr"));
        if (rows.length === 0) {
            dietItemsStatus.textContent = "No rows to save.";
            return;
        }

        const dirtyRows = rows.filter((row) => rowHasChanges(row));
        if (dirtyRows.length === 0) {
            dietItemsStatus.textContent = "No changes to save.";
            dietItemsSaveAll.disabled = true;
            return;
        }

        dietItemsSaveAll.disabled = true;
        dietItemsSaveAll.textContent = "Saving...";

        const requests = dirtyRows.map((row) => {
            const inputs = row.querySelectorAll("input[data-column]");
            const updated = {};
            inputs.forEach((input) => {
                updated[input.dataset.column] = input.value;
            });

            const payload = {
                diet_name: row.dataset.dietName ?? dietName,
                fdc_id: Number(updated.fdc_id),
                quantity: Number(updated.quantity),
                sort_order: Number(updated.sort_order),
                color: updated.color || null,
                original_fdc_id: Number(row.dataset.originalFdcId),
                original_quantity: Number(row.dataset.originalQuantity),
                original_sort_order: Number(row.dataset.originalSortOrder),
            };

            return fetch(`/api/diet/${encodeURIComponent(payload.diet_name)}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });
        });

        Promise.all(requests)
            .then((responses) => {
                const failed = responses.filter((response) => !response.ok);
                if (failed.length > 0) {
                    throw new Error(`Failed to save ${failed.length} row(s).`);
                }
                return loadDietItems();
            })
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to save rows: ${error.message}`;
            })
            .finally(() => {
                dietItemsSaveAll.disabled = false;
                dietItemsSaveAll.textContent = "Save All";
            });
    });

    dietItemsAdd.addEventListener("click", () => {
        dietItemsAdd.disabled = true;
        dietItemsStatus.textContent = "Adding diet item...";

        const maxSort = lastLoadedItems.reduce((max, item) => {
            const value = Number(item.sort_order);
            return Number.isFinite(value) ? Math.max(max, value) : max;
        }, 0);
        const nextSort = maxSort + 1;

        const payload = {
            diet_name: dietName,
            fdc_id: 170567,
            quantity: 100,
            sort_order: nextSort,
            color: null,
        };

        fetch("/api/diet", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then(() => {
                loadDietItems();
            })
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to add item: ${error.message}`;
            })
            .finally(() => {
                dietItemsAdd.disabled = false;
            });
    });

    function toRgba(color, alpha) {
        if (typeof color !== "string" || !color.trim()) {
            return "";
        }
        const hexMatch = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
        if (hexMatch) {
            let hex = hexMatch[1];
            if (hex.length === 3) {
                hex = hex.split("").map((c) => c + c).join("");
            }
            const r = parseInt(hex.slice(0, 2), 16);
            const g = parseInt(hex.slice(2, 4), 16);
            const b = parseInt(hex.slice(4, 6), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        const rgbMatch = color.trim().match(/^rgba?\(([^)]+)\)$/i);
        if (rgbMatch) {
            const parts = rgbMatch[1].split(",").map((p) => p.trim());
            const r = parts[0] ?? "0";
            const g = parts[1] ?? "0";
            const b = parts[2] ?? "0";
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        const probe = document.createElement("span");
        probe.style.color = color;
        document.body.appendChild(probe);
        const resolved = getComputedStyle(probe).color;
        probe.remove();
        const resolvedMatch = resolved.match(/^rgb\(([^)]+)\)$/i);
        if (!resolvedMatch) {
            return "";
        }
        const parts = resolvedMatch[1].split(",").map((p) => p.trim());
        const r = parts[0] ?? "0";
        const g = parts[1] ?? "0";
        const b = parts[2] ?? "0";
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
});
