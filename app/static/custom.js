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

let userSettingsCache = null;
let userSettingsPromise = null;

function coerceBoolean(value, fallback = false) {
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
        if (value === "true") return true;
        if (value === "false") return false;
    }
    return fallback;
}

function coerceNumber(value, fallback) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
}

let msgToastTimer = null;
function showMsgToast() {
    const toast = document.querySelector(".msg-toast");
    if (!toast) return;
    toast.classList.add("is-visible");
    if (msgToastTimer) {
        clearTimeout(msgToastTimer);
    }
    msgToastTimer = setTimeout(() => {
        toast.classList.remove("is-visible");
    }, 1600);
}

document.addEventListener("DOMContentLoaded", () => {
    const DIET_COLOR_SWATCHES_DARK = ["#971d1f", "#ad5322", "#af882e", "#538d28", "#2b8066", "#375875"];
    const DIET_COLOR_SWATCHES_LIGHT = ["#d86a6b", "#d68a5a", "#d6b46a", "#8cc26a", "#6bb59c", "#7aa0b5"];
    const body = document.body;
    body.setAttribute("data-bs-theme", localStorage.getItem("theme"));
    document.documentElement.style.colorScheme = localStorage.getItem("theme");

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
            // 🔑 tell the browser its color scheme
            document.documentElement.style.colorScheme = opposite;
            
            sync_toggle_button_html_with_theme();
            if (typeof loadDietItems === "function") {
                const isDietPage = window.location.pathname === "/ui/diets";
                const params = new URLSearchParams(window.location.search);
                const hasDietName = params.has("diet_name") && params.get("diet_name");
                if (isDietPage && hasDietName) {
                    loadDietItems();
                }
            }
        });
        // Theme switch button end

        sync_toggle_button_html_with_theme(); //Sync theme toggle button in sidebar upon page load
    }

    function setActiveNavLinks() {
        const currentPath = normalizePath(window.location.pathname);
        const currentParams = new URLSearchParams(window.location.search);
        const currentDietName = currentParams.get("diet_name");

        document.querySelectorAll("a[href]").forEach((link) => {
            link.classList.remove("active");
            const navItem = link.closest(".nav-item");
            if (navItem) navItem.classList.remove("menu-open");
        });

        document.querySelectorAll("a[href]").forEach((link) => {
            const href = link.getAttribute("href");
            if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;

            let linkUrl;
            try {
                linkUrl = new URL(href, window.location.origin);
            } catch {
                return;
            }
            const linkPath = normalizePath(linkUrl.pathname);
            const isExact = linkPath === currentPath;
            const isPrefix = linkPath !== "/" && currentPath.startsWith(linkPath + "/");

            let isActive = isExact || isPrefix;
            if (linkPath === "/ui/diets") {
                const linkDietName = linkUrl.searchParams.get("diet_name");
                if (currentDietName) {
                    isActive = linkDietName === currentDietName;
                } else {
                    isActive = !linkDietName && isExact;
                }
            }

            if (isActive) {
                link.classList.add("active");

                const navItem = link.closest(".nav-item");
                if (navItem) navItem.classList.add("menu-open");

                const parentLink = navItem?.closest(".nav-treeview")?.previousElementSibling;
                if (parentLink?.classList?.contains("nav-link")) {
                    parentLink.classList.add("active");
                }
            }
        });
    }

    setActiveNavLinks();

    function normalizePath(path) {
        if (!path) return "/";
        const p = path.endsWith("/") && path.length > 1 ? path.slice(0, -1) : path;
        return p || "/";
    }

    const dietNavLoading = document.getElementById("diet-nav-loading");
    const dietNavTemplate = document.getElementById("diet-nav-item-template");
    const sidebarAddDietItem = document.getElementById("sidebar-add-diet-item");

    function loadDietSidebar() {
        const loadingItem = document.getElementById("diet-nav-loading");
        const template = document.getElementById("diet-nav-item-template");
        const parent = loadingItem?.parentElement || document.getElementById("navigation");
        if (!loadingItem || !template?.content || !parent) {
            return;
        }
        loadingItem.style.display = "";
        const loadingLabel = loadingItem.querySelector("p");
        if (loadingLabel) {
            loadingLabel.textContent = "Loading...";
        }
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
                    const emptyLabel = loadingItem.querySelector("p");
                    if (emptyLabel) {
                        emptyLabel.textContent = "No diets found.";
                    }
                    return;
                }
                

                const sortedNames = Array.from(dietNames).sort((a, b) => a.localeCompare(b));
                
                parent.querySelectorAll("[data-diet-link='true']").forEach((node) => node.remove());
                sortedNames.forEach((name) => {
                    const item = template.content.firstElementChild.cloneNode(true);
                    const link = item.querySelector("a");
                    const label = item.querySelector("p");
                    link.href = `/ui/diets?diet_name=${encodeURIComponent(name)}`;
                    label.textContent = name;
                    link.setAttribute("data-diet-link", "true");
                    parent.insertBefore(item, loadingItem);
                    console.log(name);
                });
                loadingItem.style.display = "none";
                setActiveNavLinks();
            })
            .catch(() => {
                const errorLabel = loadingItem.querySelector("p");
                if (errorLabel) {
                    errorLabel.textContent = "Failed to load diets.";
                }
            });
    }

    loadDietSidebar();

    if (sidebarAddDietItem) {
        sidebarAddDietItem.addEventListener("click", () => {
            const newDiet = `diet_${Date.now()}`;

            sidebarAddDietItem.disabled = true;

            const payload = {
                diet_name: newDiet,
                fdc_id: 170567,
                quantity: 100,
                sort_order: 1,
                color: "",
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
                window.location.href = `/ui/diets?diet_name=${encodeURIComponent(newDiet)}`;
            })
            .catch((error) => {
                alert(`Failed to add item: ${error.message}`);
            })
            .finally(() => {
                sidebarAddDietItem.disabled = false;
            });
        });
    }

    const foodsTableHead = document.getElementById("foods-table-head");
    const foodsTableBody = document.getElementById("foods-table-body");
    const foodsStatus = document.getElementById("foods-status");
    const foodsFdcForm = document.getElementById("foods-fdc-form");
    const foodsFdcInput = document.getElementById("foods-fdc-id");
    const foodColorProtein = document.getElementById("food-color-protein");
    const foodColorCarb = document.getElementById("food-color-carb");
    const foodColorFat = document.getElementById("food-color-fat");

    function getDietColorSwatches() {
        return localStorage.getItem("theme") === "light"
            ? DIET_COLOR_SWATCHES_LIGHT
            : DIET_COLOR_SWATCHES_DARK;
    }


    function parseNumber(value) {
        if (typeof value === "number" && Number.isFinite(value)) {
            return value;
        }
        if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) {
            return Number(value);
        }
        return 0;
    }

    function setDominantColorVars(vars) {
        const root = document.documentElement;
        if (vars.protein) {
            root.style.setProperty("--food-dominant-protein", vars.protein);
        }
        if (vars.carb) {
            root.style.setProperty("--food-dominant-carb", vars.carb);
        }
        if (vars.fat) {
            root.style.setProperty("--food-dominant-fat", vars.fat);
        }
    }

    function applyDominantColorsFromStorage() {
        const settings = getUserSettings();
        const stored = {
            protein: typeof settings["food-dominant-protein"] === "string"
                ? settings["food-dominant-protein"]
                : "",
            carb: typeof settings["food-dominant-carb"] === "string"
                ? settings["food-dominant-carb"]
                : "",
            fat: typeof settings["food-dominant-fat"] === "string"
                ? settings["food-dominant-fat"]
                : "",
        };
        setDominantColorVars(stored);
        return { stored };
    }

    function initDominantColorPickers() {
        if (!foodColorProtein || !foodColorCarb || !foodColorFat) {
            return;
        }
        let colorSaveTimer = null;
        function scheduleColorSave(nextSettings) {
            if (colorSaveTimer) {
                clearTimeout(colorSaveTimer);
            }
            colorSaveTimer = setTimeout(() => {
                colorSaveTimer = null;
                saveUserSettings(nextSettings)
                    .then(() => {
                        showMsgToast();
                    })
                    .catch(() => {});
            }, 250);
        }
        const { stored } = applyDominantColorsFromStorage();
        if (stored.protein) {
            foodColorProtein.value = stored.protein;
        }
        if (stored.carb) {
            foodColorCarb.value = stored.carb;
        }
        if (stored.fat) {
            foodColorFat.value = stored.fat;
        }

        foodColorProtein.addEventListener("input", () => {
            const value = foodColorProtein.value;
            setDominantColorVars({ protein: value });
            scheduleColorSave({ ...getUserSettings(), "food-dominant-protein": value });
        });
        foodColorCarb.addEventListener("input", () => {
            const value = foodColorCarb.value;
            setDominantColorVars({ carb: value });
            scheduleColorSave({ ...getUserSettings(), "food-dominant-carb": value });
        });
        foodColorFat.addEventListener("input", () => {
            const value = foodColorFat.value;
            setDominantColorVars({ fat: value });
            scheduleColorSave({ ...getUserSettings(), "food-dominant-fat": value });
        });

    }

    function getDominantNutrient(food) {
        const protein = parseNumber(food["Protein g"]);
        const carb = parseNumber(food["Carbohydrate, by difference g"]);
        const fat = parseNumber(food["Total lipid (fat) g"]);
        if (protein > carb && protein > fat) {
            return "protein";
        }
        if (carb > protein && carb > fat) {
            return "carb";
        }
        if (fat > protein && fat > carb) {
            return "fat";
        }
        return "";
    }

    function renderFoodsTable(foods) {
        if (!foodsTableHead || !foodsTableBody || !foodsStatus) {
            return;
        }
        if (!Array.isArray(foods) || foods.length === 0) {
            foodsTableHead.innerHTML = "";
            foodsTableBody.innerHTML = "";
            foodsStatus.textContent = "No foods found.";
            return;
        }

        const columns = Object.keys(foods[0] || {});
        const headRow = document.createElement("tr");
        const actionTh = document.createElement("th");
        actionTh.textContent = "Action";
        actionTh.setAttribute("data-searchable", "false");
        headRow.appendChild(actionTh);
        columns.forEach((col) => {
            const th = document.createElement("th");
            th.textContent = col;
            if (col !== "fdc_id" && col !== "Name") {
                th.setAttribute("data-searchable", "false");
            }
            headRow.appendChild(th);
        });
        foodsTableHead.innerHTML = "";
        foodsTableHead.appendChild(headRow);

        const fragment = document.createDocumentFragment();
        foods.forEach((food) => {
            const row = document.createElement("tr");
            const dominant = getDominantNutrient(food);
            if (dominant) {
                row.classList.add(`food-dominant-${dominant}`);
            }

            const actionCell = document.createElement("td");
            const editLink = document.createElement("a");
            editLink.className = "btn btn-sm btn-outline-primary me-2";
            editLink.textContent = "Edit";
            if (food?.fdc_id != null) {
                editLink.href = `/ui/foods/edit/${encodeURIComponent(food.fdc_id)}`;
            } else {
                editLink.href = "#";
                editLink.classList.add("disabled");
            }
            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "btn btn-outline-danger btn-sm";
            deleteBtn.textContent = "Delete";
            deleteBtn.dataset.fdcId = food?.fdc_id ?? "";
            deleteBtn.dataset.foodName = food?.Name ?? "";
            actionCell.appendChild(editLink);
            actionCell.appendChild(deleteBtn);
            row.appendChild(actionCell);

            columns.forEach((col) => {
                const cell = document.createElement("td");
                cell.textContent = food?.[col] ?? "";
                row.appendChild(cell);
            });

            fragment.appendChild(row);
        });

        foodsTableBody.innerHTML = "";
        foodsTableBody.appendChild(fragment);
        foodsStatus.textContent = `Loaded ${foods.length} foods.`;

        const tableEl = document.getElementById("foods-table");
        if (tableEl?._datatable) {
            tableEl._datatable.destroy();
        }
        if (tableEl) {
            tableEl._datatable = new simpleDatatables.DataTable(tableEl, {
                searchable: true,
                fixedHeight: false,
                paging: false,
            });
        }
        return tableEl?._datatable;

    }

    function loadFoods() {
        if (!foodsStatus) {
            return;
        }
        foodsStatus.textContent = "Loading foods...";
        fetch("/api/foods")
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((foods) => {
                renderFoodsTable(foods);
            })
            .catch((error) => {
                if (foodsStatus) {
                    foodsStatus.textContent = `Failed to load foods: ${error.message}`;
                }
            });
    }

    function deleteFood(fdcId, foodName = "") {
        const id = String(fdcId || "").trim();
        if (!id) {
            alert("Delete failed: missing FDC ID.");
            return;
        }
        if (!confirm(`Delete food ${id}${foodName ? ` (${foodName})` : ""}? This cannot be undone.`)) {
            return;
        }
        fetch(`/api/foods/${encodeURIComponent(id)}`, {
            method: "DELETE",
            credentials: "same-origin",
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then(() => {
                alert(`Deleted food ${id}${foodName ? ` (${foodName})` : ""}.`);
                window.location.reload();
            })
            .catch((error) => {
                alert(`Failed to delete food ${id}${foodName ? ` (${foodName})` : ""}: ${error.message}`);
            });
    }

    if (foodsTableHead && foodsTableBody && foodsStatus) {
        loadFoods();
    }

    const foodsTable = document.getElementById("foods-table");
    if (foodsTable && !foodsTable._deleteHandlerAttached) {
        foodsTable.addEventListener("click", (event) => {
            const target = event.target?.closest?.("button.btn.btn-outline-danger.btn-sm");
            if (!target || !foodsTable.contains(target)) {
                return;
            }
            deleteFood(target.dataset.fdcId || "", target.dataset.foodName || "");
        });
        foodsTable._deleteHandlerAttached = true;
    }

    let settingsReady = null;

    if (foodsFdcForm && foodsFdcInput) {
        function createOrUpdateFoodFromFdcId(fdcId) {
            return fetch(`/api/foods/create_update_food_from_fdcid/${encodeURIComponent(fdcId)}`, {
                method: "POST",
            }).then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.text();
            });
        }

        foodsFdcForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const fdcId = Number(foodsFdcInput.value);
            if (!Number.isFinite(fdcId) || fdcId <= 0) {
                alert("Please enter a valid FDC ID.");
                return;
            }
            foodsFdcForm.querySelector("button[type='submit']").disabled = true;
            createOrUpdateFoodFromFdcId(fdcId)
                .then((response) => {
                    alert(response);
                    foodsFdcInput.value = "";
                    window.location.reload();
                })
                .catch((error) => {
                    alert(`Failed to add/update food: ${error.message}`);
                })
                .finally(() => {
                    const submitButton = foodsFdcForm.querySelector("button[type='submit']");
                    if (submitButton) {
                        submitButton.disabled = false;
                    }
                });
        });
    }

    const foodsEditForm = document.getElementById("foods-edit-form");
    const foodsEditFields = document.getElementById("foods-edit-fields");
    const foodsEditStatus = document.getElementById("foods-edit-status");
    let foodsEditOriginal = new Map();

    function parseFdcIdFromPath() {
        const match = window.location.pathname.match(/\/ui\/foods\/edit\/(\d+)/);
        if (!match) {
            return null;
        }
        const value = Number(match[1]);
        return Number.isFinite(value) ? value : null;
    }

    function getEditInputValue(input) {
        if (input.dataset.type === "number") {
            const num = Number(input.value);
            return Number.isFinite(num) ? num : 0;
        }
        return input.value;
    }

    function updateEditSaveState() {
        if (!foodsEditForm || !foodsEditFields) {
            return;
        }
        const submitButton = foodsEditForm.querySelector("button[type='submit']");
        if (!submitButton) {
            return;
        }
        const inputs = foodsEditFields.querySelectorAll("input[data-field]");
        const hasChanges = Array.from(inputs).some((input) => {
            const field = input.dataset.field;
            if (!field) {
                return false;
            }
            const current = getEditInputValue(input);
            const original = foodsEditOriginal.get(field);
            return current !== original;
        });
        submitButton.disabled = !hasChanges;
    }

    function renderFoodsEditForm(food) {
        if (!foodsEditFields) {
            return;
        }
        foodsEditFields.innerHTML = "";
        foodsEditOriginal = new Map();
        Object.keys(food || {}).forEach((key) => {
            if (key === "Vitamin K, total µg") {
                return;
            }
            const value = food[key];
            const isNumber = typeof value === "number";
            foodsEditOriginal.set(key, isNumber ? value : (value ?? ""));

            const wrapper = document.createElement("div");
            wrapper.className = "col-12 col-md-6";

            const label = document.createElement("label");
            label.className = "form-label";
            label.textContent = key;

            const input = document.createElement("input");
            input.className = "form-control";
            input.dataset.field = key;
            input.dataset.type = isNumber ? "number" : "text";
            input.value = value ?? "";

            if (isNumber) {
                input.type = "number";
                input.step = "any";
            } else {
                input.type = "text";
            }

            if (key === "Vitamin K, total µg") {
                input.readOnly = true;
            }

            input.addEventListener("input", () => {
                updateEditSaveState();
            });

            wrapper.appendChild(label);
            wrapper.appendChild(input);
            foodsEditFields.appendChild(wrapper);
        });
        updateEditSaveState();
    }

    if (foodsEditForm && foodsEditFields && foodsEditStatus) {
        const fdcId = parseFdcIdFromPath();
        if (!fdcId) {
            foodsEditStatus.textContent = "Missing FDC ID in the URL.";
        } else {
            foodsEditStatus.textContent = "Loading food details...";
            fetch(`/api/foods/${encodeURIComponent(fdcId)}`)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Request failed with ${response.status}`);
                    }
                    return response.json();
                })
                .then((food) => {
                    renderFoodsEditForm(food);
                    foodsEditStatus.textContent = "Edit the fields and save your changes.";
                })
                .catch((error) => {
                    foodsEditStatus.textContent = `Failed to load food: ${error.message}`;
                    updateEditSaveState();
                });

            foodsEditForm.addEventListener("submit", (event) => {
                event.preventDefault();
                const inputs = foodsEditFields.querySelectorAll("input[data-field]");
                const payload = {};
                inputs.forEach((input) => {
                    const field = input.dataset.field;
                    if (!field) {
                        return;
                    }
                    payload[field] = getEditInputValue(input);
                });
                const originalFdcId = foodsEditOriginal.get("fdc_id");
                const nextFdcId = payload.fdc_id;

                foodsEditForm.querySelector("button[type='submit']").disabled = true;
                fetch(`/api/foods/${encodeURIComponent(fdcId)}`, {
                    method: "PUT",
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
                        alert("Food update was successful.");
                        foodsEditOriginal = new Map();
                        inputs.forEach((input) => {
                            const field = input.dataset.field;
                            if (!field) {
                                return;
                            }
                            foodsEditOriginal.set(field, getEditInputValue(input));
                        });
                        if (
                            Number.isFinite(Number(nextFdcId)) &&
                            Number(nextFdcId) !== Number(originalFdcId)
                        ) {
                            window.location.href = `/ui/foods/edit/${encodeURIComponent(Number(nextFdcId))}`;
                            return;
                        }
                    })
                    .catch((error) => {
                        alert(`Failed to update food: ${error.message}`);
                    })
                    .finally(() => {
                        const submitButton = foodsEditForm.querySelector("button[type='submit']");
                        if (submitButton) {
                            updateEditSaveState();
                        }
                    });
            });
        }
    }

    const dietColumnsStorageKey = "diet_columns";
    const dietRdaThresholdKey = "diet_rda_threshold";
    const dietUlThresholdKey = "diet_ul_threshold";
    const dietHideRdaUlValuesKey = "diet_hide_rda_ul_values";
    const requiredDietColumns = ["diet_name", "fdc_id", "quantity", "sort_order", "color"];

    function normalizeSettings(settings) {
        const source = settings && typeof settings === "object" ? settings : {};
        const normalized = { ...source };
        if (!Array.isArray(normalized.diet_columns)) {
            normalized.diet_columns = [];
        }
        normalized.diet_columns = normalizeDietColumns(normalized.diet_columns);
        const hideValues = coerceBoolean(normalized.diet_hide_rda_ul_values, undefined);
        if (hideValues !== undefined) {
            normalized.diet_hide_rda_ul_values = hideValues;
        }
        const rdaValue = coerceNumber(normalized.diet_rda_threshold, undefined);
        if (rdaValue !== undefined) {
            normalized.diet_rda_threshold = rdaValue;
        }
        const ulValue = coerceNumber(normalized.diet_ul_threshold, undefined);
        if (ulValue !== undefined) {
            normalized.diet_ul_threshold = ulValue;
        }
        if (typeof normalized["food-dominant-carb"] !== "string") {
            delete normalized["food-dominant-carb"];
        }
        if (typeof normalized["food-dominant-fat"] !== "string") {
            delete normalized["food-dominant-fat"];
        }
        if (typeof normalized["food-dominant-protein"] !== "string") {
            delete normalized["food-dominant-protein"];
        }
        return normalized;
    }

    function getUserSettings() {
        return userSettingsCache || {};
    }

    function loadUserSettings() {
        if (userSettingsPromise) {
            return userSettingsPromise;
        }
        userSettingsPromise = fetch("/api/users/me", { credentials: "same-origin" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((user) => {
                let settings = user?.settings;
                if (typeof settings === "string") {
                    try {
                        settings = JSON.parse(settings);
                    } catch {
                        settings = null;
                    }
                }
                userSettingsCache = normalizeSettings(settings || {});
                return userSettingsCache;
            })
            .catch(() => {
                userSettingsCache = normalizeSettings({});
                return userSettingsCache;
            });
        return userSettingsPromise;
    }

    function saveUserSettings(nextSettings) {
        const normalized = normalizeSettings(nextSettings || {});
        return fetch("/api/users/me", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ settings: normalized }),
        }).then((response) => {
            if (!response.ok) {
                throw new Error(`Request failed with ${response.status}`);
            }
            userSettingsCache = normalized;
            return normalized;
        });
    }

    settingsReady = loadUserSettings();
    settingsReady.finally(() => {
        applyDominantColorsFromStorage();
        initDominantColorPickers();
    });

    function normalizeDietColumns(columns) {
        const normalized = Array.from(new Set(columns));
        requiredDietColumns.forEach((col) => {
            if (!normalized.includes(col)) {
                normalized.push(col);
            }
        });
        return normalized;
    }

    function getSelectedDietColumns() {
        const settings = getUserSettings();
        const columns = Array.isArray(settings.diet_columns) ? settings.diet_columns : [];
        return normalizeDietColumns(columns).slice();
    }

    function initDietSettings() {
        if (window.location.pathname !== "/ui/settings") {
            return;
        }
        return loadUserSettings().then(() => {
            const list = document.getElementById("diet-columns-list");
            const saveBtn = document.getElementById("diet-columns-save");
            const status = document.getElementById("diet-columns-status");
            const countBadge = document.getElementById("diet-columns-selected-count");
            const resetAllBtn = document.getElementById("settings-reset-all");
            const resetAllStatus = document.getElementById("settings-reset-status");
            if (!list || !saveBtn) {
                return;
            }
            let originalSelection = new Set(getSelectedDietColumns());

        function renderList(columns) {
            const selected = new Set(getSelectedDietColumns());
            const requiredSet = new Set(requiredDietColumns);
            list.innerHTML = "";
            let selectedCount = 0;
            columns.forEach((col) => {
                if (requiredSet.has(col)) {
                    return;
                }
                const wrapper = document.createElement("div");
                wrapper.className = "col-12 col-md-3";

                const formCheck = document.createElement("div");
                formCheck.className = "form-check";

                const input = document.createElement("input");
                input.className = "form-check-input";
                input.type = "checkbox";
                input.id = `diet-col-${col.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;
                input.value = col;
                input.checked = selected.has(col);
                if (input.checked) {
                    selectedCount += 1;
                }

                const label = document.createElement("label");
                label.className = "form-check-label";
                label.setAttribute("for", input.id);
                label.textContent = col;

                formCheck.appendChild(input);
                formCheck.appendChild(label);
                wrapper.appendChild(formCheck);
                list.appendChild(wrapper);
            });
            const message = `${selectedCount} selected.`;
            status.textContent = message;
            if (countBadge) {
                countBadge.textContent = message;
            }
        }

        function updateSelectedCount() {
            const checkedCount = list.querySelectorAll("input[type='checkbox']:checked").length;
            const message = `${checkedCount} selected.`;
            status.textContent = message;
            if (countBadge) {
                countBadge.textContent = message;
            }
        }

        function getCurrentSelection() {
            return new Set(
                normalizeDietColumns(
                    Array.from(list.querySelectorAll("input[type='checkbox']:checked")).map((input) => input.value)
                )
            );
        }

        function selectionsEqual(a, b) {
            if (a.size !== b.size) return false;
            for (const value of a) {
                if (!b.has(value)) return false;
            }
            return true;
        }

        function updateSaveEnabled() {
            const current = getCurrentSelection();
            saveBtn.disabled = selectionsEqual(current, originalSelection);
        }

        function loadDietColumnsFromApi() {
            status.textContent = "Loading columns...";
            return fetch("/api/foods", { credentials: "same-origin" })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Request failed with ${response.status}`);
                    }
                    return response.json();
                })
                .then((foods) => {
                    const firstFood = Array.isArray(foods) && foods.length > 0 ? foods[0] : null;
                    if (!firstFood) {
                        throw new Error("No foods found.");
                    }
                    const cols = Object.keys(firstFood || {});
                    const unique = Array.from(new Set(cols));
                    const allColumns = Array.from(
                        new Set([...unique, ...getSelectedDietColumns()])
                    );
                    console.log("Diet columns:", allColumns);
                    renderList(allColumns);
                    originalSelection = new Set(getSelectedDietColumns());
                    updateSaveEnabled();
                    status.textContent = "";
                })
                .catch((error) => {
                    const selected = getSelectedDietColumns();
                    const allColumns = Array.from(new Set([...selected]));
                    console.log("Diet columns:", allColumns);
                    renderList(allColumns);
                    originalSelection = new Set(getSelectedDietColumns());
                    updateSaveEnabled();
                    status.textContent = `Failed to load columns: ${error.message}`;
                });
        }

        loadDietColumnsFromApi();

        function resetAllSettings() {
            if (resetAllStatus) {
                resetAllStatus.textContent = "Resetting...";
            }
            if (resetAllBtn) {
                resetAllBtn.disabled = true;
            }
            fetch("/api/users/me/reset_settings", {
                method: "POST",
                credentials: "same-origin",
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Request failed with ${response.status}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    userSettingsCache = normalizeSettings(data?.settings || {});
                    loadDietColumnsFromApi();
                    const { stored } = applyDominantColorsFromStorage();
                    if (foodColorProtein && stored.protein) {
                        foodColorProtein.value = stored.protein;
                    }
                    if (foodColorCarb && stored.carb) {
                        foodColorCarb.value = stored.carb;
                    }
                    if (foodColorFat && stored.fat) {
                        foodColorFat.value = stored.fat;
                    }
                    updateSelectedCount();
                    updateSaveEnabled();
                    showMsgToast();
                    if (resetAllStatus) {
                        resetAllStatus.textContent = "Reset to default.";
                    }
                })
                .catch((error) => {
                    if (resetAllStatus) {
                        resetAllStatus.textContent = `Reset failed: ${error.message}`;
                    }
                })
                .finally(() => {
                    if (resetAllBtn) {
                        resetAllBtn.disabled = false;
                    }
                });
        }

        list.addEventListener("change", (event) => {
            if (event.target && event.target.matches("input[type='checkbox']")) {
                updateSelectedCount();
                updateSaveEnabled();
            }
        });

        saveBtn.addEventListener("click", () => {
            const checked = Array.from(list.querySelectorAll("input[type='checkbox']:checked"))
                .map((input) => input.value);
            if (checked.length === 0 && requiredDietColumns.length === 0) {
                status.textContent = "Select at least one column.";
                return;
            }
            const normalized = normalizeDietColumns(checked);
            saveUserSettings({ ...getUserSettings(), [dietColumnsStorageKey]: normalized })
                .then((settings) => {
                    originalSelection = new Set(settings.diet_columns);
                    updateSaveEnabled();
                    updateSelectedCount();
                    showMsgToast();
                })
                .catch((error) => {
                    status.textContent = `Save failed: ${error.message}`;
                });
        });

            if (resetAllBtn) {
                resetAllBtn.addEventListener("click", () => {
                    resetAllSettings();
                });
            }
        });
    }

    function initDietThresholds() {
        if (window.location.pathname !== "/ui/rda_ul") {
            return;
        }
        const rdaThresholdInput = document.getElementById("diet-rda-threshold");
        const ulThresholdInput = document.getElementById("diet-ul-threshold");
        const hideRdaUlValuesInput = document.getElementById("diet-hide-rda-ul-values");
        const thresholdsStatus = document.getElementById("diet-thresholds-status");
        if (!rdaThresholdInput || !ulThresholdInput) {
            return;
        }
        return loadUserSettings().then(() => {
            function setThresholdInputs() {
                const settings = getUserSettings();
                const rdaValue = coerceNumber(settings[dietRdaThresholdKey], undefined);
                rdaThresholdInput.value = rdaValue === undefined ? "" : String(rdaValue);
                const ulValue = coerceNumber(settings[dietUlThresholdKey], undefined);
                ulThresholdInput.value = ulValue === undefined ? "" : String(ulValue);
                if (hideRdaUlValuesInput) {
                    const hideValue = coerceBoolean(settings[dietHideRdaUlValuesKey], undefined);
                    if (hideValue !== undefined) {
                        hideRdaUlValuesInput.checked = hideValue;
                    }
                }
            }

            let thresholdSaveTimer = null;

            function saveThresholds() {
                const rdaValue = Number(rdaThresholdInput.value);
                const ulValue = Number(ulThresholdInput.value);
                if (!Number.isFinite(rdaValue) || !Number.isFinite(ulValue)) {
                    if (thresholdsStatus) {
                        thresholdsStatus.textContent = "Enter valid numbers.";
                    }
                    return;
                }
                const next = {
                    ...getUserSettings(),
                    [dietRdaThresholdKey]: rdaValue,
                    [dietUlThresholdKey]: ulValue,
                };
                if (hideRdaUlValuesInput) {
                    next[dietHideRdaUlValuesKey] = Boolean(hideRdaUlValuesInput.checked);
                }
                saveUserSettings(next)
                    .then(() => {
                        if (thresholdsStatus) {
                            thresholdsStatus.textContent = "Saved.";
                        }
                        showMsgToast();
                    })
                    .catch((error) => {
                        if (thresholdsStatus) {
                            thresholdsStatus.textContent = `Save failed: ${error.message}`;
                        }
                    });
            }

            function scheduleThresholdSave() {
                if (thresholdSaveTimer) {
                    clearTimeout(thresholdSaveTimer);
                }
                thresholdSaveTimer = setTimeout(() => {
                    thresholdSaveTimer = null;
                    saveThresholds();
                }, 600);
            }

            setThresholdInputs();

            rdaThresholdInput.addEventListener("input", () => {
                if (thresholdsStatus) {
                    thresholdsStatus.textContent = "Saving...";
                }
                scheduleThresholdSave();
            });
            ulThresholdInput.addEventListener("input", () => {
                if (thresholdsStatus) {
                    thresholdsStatus.textContent = "Saving...";
                }
                scheduleThresholdSave();
            });
            if (hideRdaUlValuesInput) {
                hideRdaUlValuesInput.addEventListener("change", () => {
                    if (thresholdsStatus) {
                        thresholdsStatus.textContent = "Saving...";
                    }
                    scheduleThresholdSave();
                });
            }
        });
    }

    initDietSettings();
    initDietThresholds();

    const rdaTable = document.getElementById("rda-table");
    const rdaStatus = document.getElementById("rda-status");
    const ulTable = document.getElementById("ul-table");
    const ulStatus = document.getElementById("ul-status");

    function renderNutrientTable(tableEl, rows, label) {
        if (!tableEl) {
            return;
        }
        const headRow = document.createElement("tr");
        ["Nutrient", "Value"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            headRow.appendChild(th);
        });
        const thead = document.createElement("thead");
        thead.appendChild(headRow);

        const tbody = document.createElement("tbody");
        rows.forEach((row) => {
            const idRaw = row?.id ?? row?.ID;
            const nutrientRaw = row?.nutrient ?? row?.Nutrient ?? row?.NUTRIENT;
            const valueRaw = row?.value ?? row?.Value ?? row?.VALUE;
            const nutrient = String(nutrientRaw || "").trim();
            if (!nutrient) {
                return;
            }
            const tr = document.createElement("tr");
            const nutrientTd = document.createElement("td");
            nutrientTd.textContent = nutrient;
            const valueTd = document.createElement("td");
            const input = document.createElement("input");
            input.type = "number";
            input.step = "any";
            input.className = "form-control form-control-sm nutrient-value-input";
            input.value = valueRaw ?? "";
            input.dataset.id = idRaw ?? "";
            input.dataset.nutrient = nutrient;
            if (label) {
                input.setAttribute("aria-label", `${label} value for ${nutrient}`);
            }
            valueTd.appendChild(input);
            tr.appendChild(nutrientTd);
            tr.appendChild(valueTd);
            tbody.appendChild(tr);
        });

        tableEl.innerHTML = "";
        tableEl.appendChild(thead);
        tableEl.appendChild(tbody);
    }

    function loadNutrientTable(endpoint, tableEl, statusEl, label) {
        if (!tableEl || !statusEl) {
            return;
        }
        statusEl.textContent = `Loading ${label} values...`;
        fetch(endpoint, { credentials: "same-origin" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((rows) => {
                const data = Array.isArray(rows) ? rows.slice() : [];
                data.sort((a, b) => {
                    const aName = String(a?.nutrient ?? a?.Nutrient ?? a?.NUTRIENT ?? "");
                    const bName = String(b?.nutrient ?? b?.Nutrient ?? b?.NUTRIENT ?? "");
                    return aName.localeCompare(bName);
                });
                if (data.length === 0) {
                    tableEl.innerHTML = "";
                    statusEl.textContent = `No ${label} values found.`;
                    return;
                }
                renderNutrientTable(tableEl, data, label);
                statusEl.textContent = `Loaded ${data.length} ${label} values.`;
            })
            .catch((error) => {
                tableEl.innerHTML = "";
                statusEl.textContent = `Failed to load ${label} values: ${error.message}`;
            });

        if (!tableEl._nutrientHandlerAttached) {
            tableEl.addEventListener("change", (event) => {
                const input = event.target?.closest?.("input.nutrient-value-input");
                if (!input || !tableEl.contains(input)) {
                    return;
                }
                const id = String(input.dataset.id || "").trim();
                const nutrient = String(input.dataset.nutrient || "").trim();
                const value = Number(input.value);
                if (!id) {
                    statusEl.textContent = `${label} update failed: missing id.`;
                    return;
                }
                if (!Number.isFinite(value)) {
                    statusEl.textContent = `${label} update failed: invalid value.`;
                    return;
                }
                statusEl.textContent = "Saving...";
                fetch(`${endpoint}/${encodeURIComponent(id)}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    credentials: "same-origin",
                    body: JSON.stringify({ value, nutrient }),
                })
                    .then((response) => {
                        if (!response.ok) {
                            throw new Error(`Request failed with ${response.status}`);
                        }
                        return response.json();
                    })
                    .then((result) => {
                        const name = result?.nutrient || nutrient || "item";
                        statusEl.textContent = `${label} updated: ${name}.`;
                        showMsgToast();
                    })
                    .catch((error) => {
                        statusEl.textContent = `${label} update failed: ${error.message}`;
                    });
            });
            tableEl._nutrientHandlerAttached = true;
        }
    }

    if (rdaTable || ulTable) {
        loadNutrientTable("/api/rda", rdaTable, rdaStatus, "RDA");
        loadNutrientTable("/api/ul", ulTable, ulStatus, "UL");
    }

    const dietItemsHead = document.getElementById("diet-items-head");
    const dietItemsBody = document.getElementById("diet-items-body");
    const dietItemsStatus = document.getElementById("diet-items-status");
    const dietItemsHash = document.getElementById("diet-items-hash");
    const dietItemsSaveAll = document.getElementById("diet-items-save-all");
    const dietItemsAdd = document.getElementById("diet-items-add");
    const dietItemsClone = document.getElementById("diet-items-clone");
    const dietItemsDeleteAll = document.getElementById("diet-items-delete-all");
    const dietAutoSaveToast = document.querySelector(".msg-toast");
    if (!dietItemsHead || !dietItemsBody || !dietItemsStatus || !dietItemsAdd) return;
    const dietItemsTable = dietItemsBody.closest("table");
    let autoSaveTimer = null;
    let saveInFlight = false;
    let autoSaveQueued = false;
    let autoSaveToastTimer = null;
    let rdaByNutrient = new Map();
    let rdaLoadPromise = null;
    let ulByNutrient = new Map();
    let ulLoadPromise = null;
    function getStoredThreshold(key) {
        const settings = getUserSettings();
        return coerceNumber(settings[key], undefined);
    }
    function getStoredToggle(key, fallback = false) {
        const settings = getUserSettings();
        return coerceBoolean(settings[key], fallback);
    }
    function getRdaWarningThreshold() {
        return getStoredThreshold(dietRdaThresholdKey);
    }
    function getUlDangerThreshold() {
        return getStoredThreshold(dietUlThresholdKey);
    }
    function getHideRdaUlValues() {
        return getStoredToggle(dietHideRdaUlValuesKey, false);
    }
    function loadRda() {
        if (rdaLoadPromise) {
            return rdaLoadPromise;
        }
        rdaLoadPromise = fetch("/api/rda", { credentials: "same-origin" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((rows) => {
                const map = new Map();
                if (Array.isArray(rows)) {
                    rows.forEach((row) => {
                        const nutrientRaw = row?.nutrient ?? row?.Nutrient ?? row?.NUTRIENT;
                        const valueRaw = row?.value ?? row?.Value ?? row?.VALUE;
                        const nutrient = String(nutrientRaw || "").trim();
                        const value = Number(valueRaw);
                        if (nutrient && Number.isFinite(value)) {
                            map.set(nutrient, value);
                        }
                    });
                }
                rdaByNutrient = map;
                return map;
            })
            .catch(() => {
                rdaByNutrient = new Map();
                return rdaByNutrient;
            });
        return rdaLoadPromise;
    }

    function loadUl() {
        if (ulLoadPromise) {
            return ulLoadPromise;
        }
        ulLoadPromise = fetch("/api/ul", { credentials: "same-origin" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((rows) => {
                const map = new Map();
                if (Array.isArray(rows)) {
                    rows.forEach((row) => {
                        const nutrientRaw = row?.nutrient ?? row?.Nutrient ?? row?.NUTRIENT;
                        const valueRaw = row?.value ?? row?.Value ?? row?.VALUE;
                        const nutrient = String(nutrientRaw || "").trim();
                        const value = Number(valueRaw);
                        if (nutrient && Number.isFinite(value)) {
                            map.set(nutrient, value);
                        }
                    });
                }
                ulByNutrient = map;
                return map;
            })
            .catch(() => {
                ulByNutrient = new Map();
                return ulByNutrient;
            });
        return ulLoadPromise;
    }

    async function sha1Hex(str) {
        const encoded = new TextEncoder().encode(str);
        const digest = await crypto.subtle.digest("SHA-1", encoded);
        return Array.from(new Uint8Array(digest))
            .map((b) => b.toString(16).padStart(2, "0"))
            .join("");
    }

    function getCurrentDietSnapshot() {
        const rows = Array.from(dietItemsBody.querySelectorAll("tr")).filter(
            (row) => !row.classList.contains("totals-row")
        );
        const items = rows.map((row) => {
            const inputs = row.querySelectorAll("input[data-column]");
            const data = {
                diet_name: row.dataset.dietName ?? dietName,
                fdc_id: "",
                quantity: "",
                sort_order: "",
                color: "",
            };
            inputs.forEach((input) => {
                data[input.dataset.column] = input.value ?? "";
            });
            return data;
        });
        items.sort((a, b) => {
            const aSort = Number(a.sort_order) || 0;
            const bSort = Number(b.sort_order) || 0;
            if (aSort !== bSort) {
                return aSort - bSort;
            }
            return String(a.fdc_id).localeCompare(String(b.fdc_id));
        });
        return items;
    }

    async function updateDietHashDisplay() {
        if (!dietItemsHash) {
            return;
        }
        const snapshot = getCurrentDietSnapshot();
        if (snapshot.length === 0) {
            dietItemsHash.textContent = "";
            return;
        }
        const hash = await sha1Hex(JSON.stringify(snapshot));
        dietItemsHash.textContent = `SHA-1: ${hash.slice(0, 10)}`;
    }

    function setSaveAllEnabled(enabled) {
        if (!dietItemsSaveAll) {
            return;
        }
        dietItemsSaveAll.disabled = !enabled;
    }

    function showAutoSaveToast() {
        if (!dietAutoSaveToast) {
            return;
        }
        dietAutoSaveToast.classList.add("is-visible");
        if (autoSaveToastTimer) {
            clearTimeout(autoSaveToastTimer);
        }
        autoSaveToastTimer = setTimeout(() => {
            dietAutoSaveToast.classList.remove("is-visible");
        }, 1600);
    }

    function scheduleAutoSave(delay = 900) {
        if (activeEditRow) {
            return;
        }
        if (autoSaveTimer) {
            clearTimeout(autoSaveTimer);
        }
        autoSaveTimer = setTimeout(() => {
            autoSaveTimer = null;
            autoSaveDirtyRows();
        }, delay);
    }

    const params = new URLSearchParams(window.location.search);
    let dietName = params.get("diet_name");
    if (!dietName) {
        dietItemsStatus.textContent = "Missing diet_name in the URL.";
        return;
    }

    dietItemsStatus.textContent = `Loading ${dietName} items...`;

    const dietNameEditor = document.getElementById("diet-name-editor");
    const dietNameHeading = document.getElementById("diet-name-heading");
    const dietNameInput = document.getElementById("diet-name-input");

    function setDietNameEditing(isEditing) {
        if (!dietNameEditor) return;
        dietNameEditor.classList.toggle("is-editing", isEditing);
        if (isEditing && dietNameInput) {
            dietNameInput.focus();
            dietNameInput.select();
        }
    }

    function syncDietNameDisplay(name) {
        if (dietNameHeading) {
            dietNameHeading.textContent = name;
        }
        if (dietNameInput) {
            dietNameInput.value = name;
        }
    }

    if (dietNameEditor && dietNameHeading && dietNameInput) {
        dietNameHeading.addEventListener("click", () => {
            setDietNameEditing(true);
        });

        dietNameInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                dietNameInput.blur();
            } else if (event.key === "Escape") {
                syncDietNameDisplay(dietName);
                setDietNameEditing(false);
            }
        });

        dietNameInput.addEventListener("blur", () => {
            const newName = dietNameInput.value.trim();
            if (!newName) {
                syncDietNameDisplay(dietName);
                setDietNameEditing(false);
                return;
            }
            if (newName === dietName) {
                setDietNameEditing(false);
                return;
            }

            const payload = {
                diet_name_old: dietName,
                diet_name_new: newName,
            };

            dietItemsStatus.textContent = "Saving diet name...";
            fetch("/api/diet/name_only", {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Request failed with ${response.status}`);
                    }
                    dietName = newName;
                    syncDietNameDisplay(newName);
                    params.set("diet_name", newName);
                    const newUrl = `${window.location.pathname}?${params.toString()}`;
                    window.history.replaceState({}, "", newUrl);
                    loadDietSidebar();
                    return loadDietItems();
                })
                .catch((error) => {
                    dietItemsStatus.textContent = `Failed to save diet name: ${error.message}`;
                    syncDietNameDisplay(dietName);
                })
                .finally(() => {
                    setDietNameEditing(false);
                });
        });
    }

    let activeEditRow = null;

    function setEditingRow(row) {
        if (activeEditRow && activeEditRow !== row) {
            clearEditingRow({ commit: true });
        }
        activeEditRow = row;
        row.classList.add("is-editing");
        if (dietItemsTable) {
            dietItemsTable.classList.add("is-editing");
        }
    }

    function clearEditingRow({ commit = false } = {}) {
        const row = activeEditRow;
        if (row) {
            row.classList.remove("is-editing");
            activeEditRow = null;
        }
        if (dietItemsTable) {
            dietItemsTable.classList.remove("is-editing");
        }
        if (commit && row && rowHasChanges(row)) {
            if (autoSaveTimer) {
                clearTimeout(autoSaveTimer);
                autoSaveTimer = null;
            }
            autoSaveDirtyRows();
        }
    }

    document.addEventListener("click", (event) => {
        if (!activeEditRow) {
            return;
        }
        if (event.target.closest("#diet-items-body tr")) {
            return;
        }
        clearEditingRow({ commit: true });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        if (!activeEditRow) {
            return;
        }
        clearEditingRow({ commit: true });
    });

    function closeColorMenus(target) {
        document.querySelectorAll(".color-dropdown.is-open").forEach((menu) => {
            if (target && menu.contains(target)) {
                return;
            }
            menu.classList.remove("is-open");
        });
    }

    document.addEventListener("click", (event) => {
        if (event.target.closest(".color-dropdown")) {
            return;
        }
        closeColorMenus();
    });

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

    function deleteDietItem(row) {
        if (!row) {
            return;
        }
        const name = row.querySelector(".name-col .cell-value")?.textContent?.trim() || "this item";
        const payload = {
            diet_name: row.dataset.dietName ?? dietName,
            fdc_id: Number(row.dataset.originalFdcId),
            quantity: Number(row.dataset.originalQuantity),
            sort_order: Number(row.dataset.originalSortOrder),
            delete_all: false,
        };
        dietItemsStatus.textContent = "Deleting diet item...";
        fetch("/api/diet", {
            method: "DELETE",
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
            .then(() => loadDietItems())
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to delete item: ${error.message}`;
            });
    }

    function collectDirtyRows() {
        return Array.from(dietItemsBody.querySelectorAll("tr")).filter((row) => rowHasChanges(row));
    }

    function buildDietUpdatePayload(row) {
        const inputs = row.querySelectorAll("input[data-column]");
        const updated = {};
        inputs.forEach((input) => {
            updated[input.dataset.column] = input.value;
        });

        return {
            diet_name: row.dataset.dietName ?? dietName,
            fdc_id: Number(updated.fdc_id),
            quantity: Number(updated.quantity),
            sort_order: Number(updated.sort_order),
            color: updated.color || null,
            original_fdc_id: Number(row.dataset.originalFdcId),
            original_quantity: Number(row.dataset.originalQuantity),
            original_sort_order: Number(row.dataset.originalSortOrder),
        };
    }

    function saveDietRows(rows) {
        if (!rows.length) {
            return Promise.resolve();
        }
        const requests = rows.map((row) => {
            const payload = buildDietUpdatePayload(row);
            return fetch("/api/diet", {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });
        });

        return Promise.all(requests).then((responses) => {
            const failed = responses.filter((response) => !response.ok);
            if (failed.length > 0) {
                throw new Error(`Failed to save ${failed.length} row(s).`);
            }
            return loadDietItems();
        });
    }

    function autoSaveDirtyRows() {
        const dirtyRows = collectDirtyRows();
        if (dirtyRows.length === 0) {
            return;
        }
        if (saveInFlight) {
            autoSaveQueued = true;
            return;
        }
        saveInFlight = true;
        saveDietRows(dirtyRows)
            .then(() => {
                showAutoSaveToast();
            })
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to auto-save rows: ${error.message}`;
            })
            .finally(() => {
                saveInFlight = false;
                if (autoSaveQueued) {
                    autoSaveQueued = false;
                    scheduleAutoSave(200);
                }
            });
    }

    function loadDietItems() {
        dietItemsStatus.textContent = `Loading ${dietName} items...`;
        setSaveAllEnabled(false);
        dietItemsAdd.disabled = true;
        activeEditRow = null;
        return ensureFoodsLoaded()
            .then(() => loadRda())
            .then(() => loadUl())
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
                    setSaveAllEnabled(false);
                    dietItemsAdd.disabled = false;
                    return;
                }

                const rawColumns = Object.keys(items[0] || {});
                if (rdaByNutrient && rdaByNutrient.size > 0) {
                    const missingRda = Array.from(rdaByNutrient.keys()).filter(
                        (nutrient) => !rawColumns.includes(nutrient)
                    );
                    missingRda.forEach((nutrient) => {
                        console.warn(`RDA nutrient not found in diet columns: ${nutrient}`);
                    });
                }
                const selectedColumns = new Set(getSelectedDietColumns());
                const columns = ["delete_action"];
                if (rawColumns.includes("diet_name")) {
                    columns.push("diet_name");
                }
                if (rawColumns.includes("fdc_id")) {
                    columns.push("fdc_id");
                }
                if (rawColumns.includes("sort_order")) {
                    columns.push("sort_order");
                }
                if (rawColumns.includes("color")) {
                    columns.push("color");
                }
                if (rawColumns.includes("Name") && selectedColumns.has("Name")) {
                    columns.push("Name");
                }
                if (rawColumns.includes("quantity")) {
                    columns.push("quantity");
                }
                rawColumns.forEach((col) => {
                    if (col === "color" || col === "Name" || col === "quantity") {
                        return;
                    }
                    if (col === "diet_name" || col === "fdc_id" || col === "sort_order" || col === "Energy kJ") {
                        return;
                    }
                    if (!selectedColumns.has(col)) {
                        return;
                    }
                    columns.push(col);
                });
                if (columns.length === 0) {
                    dietItemsStatus.textContent = `No data fields found for ${dietName}.`;
                    dietItemsHead.innerHTML = "";
                    dietItemsBody.innerHTML = "";
                    setSaveAllEnabled(false);
                    dietItemsAdd.disabled = false;
                    return;
                }

                const headRow = document.createElement("tr");
                columns.forEach((col) => {
                    const th = document.createElement("th");
                    th.textContent = col === "delete_action" ? "" : col;
                    if (col === "Name") {
                        th.classList.add("name-col");
                    }
                    if (col === "quantity") {
                        th.classList.add("quantity-col");
                    }
                    if (col === "Unit") {
                        th.classList.add("unit-col");
                    }
                    if (col === "Price") {
                        th.classList.add("price-col");
                    }
                    if (col === "color") {
                        th.classList.add("color-col");
                    }
                    if (col === "delete_action") {
                        th.classList.add("delete-col");
                    }
                    if (col === "diet_name" || col === "fdc_id" || col === "sort_order" || col === "Energy kJ") {
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
                        if (col === "diet_name" || col === "fdc_id" || col === "sort_order" || col === "Energy kJ") {
                            cell.classList.add("is-hidden-col");
                        }
                        if (col === "quantity") {
                            cell.classList.add("quantity-col");
                        }
                        if ((col === "Name" || col === "quantity") && item.color) {
                            cell.style.backgroundColor = toRgba(item.color, 1);
                        }
                        if (col === "Unit") {
                            cell.classList.add("unit-col");
                        }
                        if (col === "Price") {
                            cell.classList.add("price-col");
                        }
                        if (col === "color") {
                            cell.classList.add("color-col");
                        }

                        if (col === "delete_action") {
                            cell.classList.add("delete-col");
                            const deleteBtn = document.createElement("button");
                            deleteBtn.type = "button";
                            deleteBtn.className = "btn btn-outline-danger btn-sm";
                            deleteBtn.textContent = "Delete";
                            deleteBtn.addEventListener("click", (event) => {
                                event.stopPropagation();
                                deleteDietItem(row);
                            });
                            cell.appendChild(deleteBtn);
                        } else if (col === "Name") {
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
                                        cell.classList.remove("is-open");
                                        updateSaveAllState();
                                        updateDietHashDisplay();
                                        scheduleAutoSave();
                                    });
                                    options.appendChild(option);
                                });

                                if (top.length > 0) {
                                    options.style.display = "block";
                                    cell.classList.add("is-open");
                                } else {
                                    options.style.display = "none";
                                    cell.classList.remove("is-open");
                                }
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
                                    cell.classList.remove("is-open");
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

                            const dropdown = document.createElement("div");
                            dropdown.className = "color-dropdown cell-input";

                            const toggle = document.createElement("button");
                            toggle.type = "button";
                            toggle.className = "btn btn-sm color-toggle";
                            toggle.innerHTML = '<i class="bi bi-eyedropper"></i>';
                            toggle.addEventListener("click", (event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                dropdown.classList.toggle("is-open");
                                closeColorMenus(dropdown);
                            });

                            const menu = document.createElement("div");
                            menu.className = "color-menu";
                            getDietColorSwatches().forEach((color) => {
                                const swatch = document.createElement("span");
                                swatch.className = "color-swatch";
                                swatch.style.backgroundColor = color;
                                if (String(value).toLowerCase() === color.toLowerCase()) {
                                    swatch.classList.add("is-selected");
                                }
                                swatch.addEventListener("click", () => {
                                    const isSelected = swatch.classList.contains("is-selected");
                                    menu.querySelectorAll(".color-swatch").forEach((node) => {
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
                                    updateDietHashDisplay();
                                    scheduleAutoSave();
                                    dropdown.classList.remove("is-open");
                                });
                                menu.appendChild(swatch);
                            });

                            dropdown.appendChild(toggle);
                            dropdown.appendChild(menu);

                            const colorActions = document.createElement("div");
                            colorActions.className = "d-flex align-items-center gap-2";
                            colorActions.appendChild(dropdown);

                            cell.appendChild(display);
                            cell.appendChild(input);
                            cell.appendChild(colorActions);
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
                                input.step = "1";
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
                    const highlightTotals = new Set([
                        "Price",
                        "Energy kcal",
                        "Protein g",
                        "Total lipid (fat) g",
                        "Carbohydrate, by difference g",
                    ]);
                    const totalsColorClass = {
                        "Protein g": "totals-protein",
                        "Total lipid (fat) g": "totals-fat",
                        "Carbohydrate, by difference g": "totals-carb",
                    };
                    function getColumnTotal(col) {
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
                        return total;
                    }

                    columns.forEach((col) => {
                        const cell = document.createElement("td");
                        if (col === "diet_name" || col === "fdc_id" || col === "sort_order" || col === "Energy kJ") {
                            cell.classList.add("is-hidden-col");
                        }
                        if (col === "delete_action") {
                            cell.classList.add("delete-col");
                            cell.textContent = "";
                        } else if (col === "color") {
                            cell.classList.add("color-col");
                            cell.textContent = "";
                        } else if (col === "Name") {
                            cell.classList.add("name-col");
                            cell.textContent = "Totals";
                        } else if (col === "quantity" || col === "Unit") {
                            if (col === "quantity") {
                                cell.classList.add("quantity-col");
                            }
                            cell.textContent = "";
                        } else {
                            const total = getColumnTotal(col);
                            const roundedTotal = total.toFixed(2);
                            if (col === "Price") {
                                cell.textContent = `$${roundedTotal}  `;
                            } else if (col === "Energy kcal") {
                                cell.textContent = `${roundedTotal} ⚡`;
                            } else if (
                                col === "Protein g" ||
                                col === "Carbohydrate, by difference g" ||
                                col === "Total lipid (fat) g"
                            ) {
                                const kcalPerGram = col === "Total lipid (fat) g" ? 9 : 4;
                                const percent = Math.round((total * kcalPerGram) / 2000 * 100);
                                cell.innerHTML = `${roundedTotal}<br>(${percent}%)`;
                            } else {
                                cell.textContent = roundedTotal;
                            }
                            if (highlightTotals.has(col)) {
                                const colorClass = totalsColorClass[col];
                                if (colorClass) {
                                    cell.classList.add(colorClass);
                                    cell.classList.add("totals-highlight");
                                } else {
                                    cell.classList.add("totals-highlight");
                                }
                            }
                        }
                        totalsRow.appendChild(cell);
                    });
                    fragment.appendChild(totalsRow);

                    if (rdaByNutrient && rdaByNutrient.size > 0) {
                        const rdaRow = document.createElement("tr");
                        rdaRow.classList.add("totals-row");
                        columns.forEach((col, colIndex) => {
                            const cell = document.createElement("td");
                            if (col === "diet_name" || col === "fdc_id" || col === "sort_order" || col === "Energy kJ") {
                                cell.classList.add("is-hidden-col");
                            }
                            if (col === "delete_action") {
                                cell.classList.add("delete-col");
                                cell.textContent = "";
                            } else if (col === "color") {
                                cell.classList.add("color-col");
                                cell.textContent = "";
                            } else if (col === "Name") {
                                cell.classList.add("name-col");
                                cell.textContent = "RDA %";
                            } else if (col === "quantity" || col === "Unit") {
                                if (col === "quantity") {
                                    cell.classList.add("quantity-col");
                                }
                                cell.textContent = "";
                            } else {
                                const total = getColumnTotal(col);
                                const rdaValue = rdaByNutrient.get(String(col || "").trim());
                                if (Number.isFinite(rdaValue) && rdaValue > 0) {
                                    const rdaPercent = Math.round((total / rdaValue) * 100);
                                    cell.innerHTML = getHideRdaUlValues()
                                        ? `${rdaPercent}%`
                                        : `${rdaValue}<br>${rdaPercent}%`;
                                    const rdaWarning = getRdaWarningThreshold();
                                    if (Number.isFinite(rdaWarning) && rdaPercent < rdaWarning) {
                                        cell.classList.add("text-warning");
                                        const totalCell = totalsRow.children?.[colIndex];
                                        if (totalCell) {
                                            totalCell.classList.add("text-warning");
                                        }
                                    }
                                } else {
                                    cell.textContent = "";
                                }
                            }
                            rdaRow.appendChild(cell);
                        });
                        fragment.appendChild(rdaRow);
                    }

                    if (ulByNutrient && ulByNutrient.size > 0) {
                        const ulRow = document.createElement("tr");
                        ulRow.classList.add("totals-row");
                        columns.forEach((col, colIndex) => {
                            const cell = document.createElement("td");
                            if (col === "diet_name" || col === "fdc_id" || col === "sort_order" || col === "Energy kJ") {
                                cell.classList.add("is-hidden-col");
                            }
                            if (col === "delete_action") {
                                cell.classList.add("delete-col");
                                cell.textContent = "";
                            } else if (col === "color") {
                                cell.classList.add("color-col");
                                cell.textContent = "";
                            } else if (col === "Name") {
                                cell.classList.add("name-col");
                                cell.textContent = "Upper Limit (UL) %";
                            } else if (col === "quantity" || col === "Unit") {
                                if (col === "quantity") {
                                    cell.classList.add("quantity-col");
                                }
                                cell.textContent = "";
                            } else {
                                const total = getColumnTotal(col);
                                const ulValue = ulByNutrient.get(col);
                                if (Number.isFinite(ulValue) && ulValue > 0) {
                                    const ulPercent = Math.round((total / ulValue) * 100);
                                    cell.innerHTML = getHideRdaUlValues()
                                        ? `${ulPercent}%`
                                        : `${ulValue}<br>${ulPercent}%`;
                                    const ulDanger = getUlDangerThreshold();
                                    if (Number.isFinite(ulDanger) && ulPercent > ulDanger) {
                                        cell.classList.add("text-danger");
                                        const totalCell = totalsRow.children?.[colIndex];
                                        if (totalCell) {
                                            totalCell.classList.add("text-danger");
                                        }
                                    }
                                } else {
                                    cell.textContent = "";
                                }
                            }
                            ulRow.appendChild(cell);
                        });
                        fragment.appendChild(ulRow);
                    }
                }

                dietItemsBody.innerHTML = "";
                dietItemsBody.appendChild(fragment);
                dietItemsStatus.textContent = `Loaded ${items.length} items for ${dietName}.`;
                updateDietHashDisplay();

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
                            updateDietHashDisplay();
                            scheduleAutoSave(200);
                        },
                    });
                }

                const inputs = dietItemsBody.querySelectorAll("input[data-column]");
                inputs.forEach((input) => {
                    input.addEventListener("input", () => {
                        updateSaveAllState();
                        updateDietHashDisplay();
                        scheduleAutoSave();
                    });
                });
                updateSaveAllState();
                updateDietHashDisplay();
                dietItemsAdd.disabled = false;
            })
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to load items: ${error.message}`;
                setSaveAllEnabled(true);
                dietItemsAdd.disabled = false;
            });
    }

    settingsReady.finally(() => {
        loadDietItems();
    });

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
        setSaveAllEnabled(hasChanges);
    }

    if (dietItemsSaveAll) {
    dietItemsSaveAll.addEventListener("click", () => {
        if (saveInFlight) {
            dietItemsStatus.textContent = "Save already in progress.";
            return;
        }
        if (autoSaveTimer) {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = null;
        }
        autoSaveQueued = false;
        const rows = Array.from(dietItemsBody.querySelectorAll("tr"));
        if (rows.length === 0) {
            dietItemsStatus.textContent = "No rows to save.";
            return;
        }

        const dirtyRows = rows.filter((row) => rowHasChanges(row));
        if (dirtyRows.length === 0) {
            dietItemsStatus.textContent = "No changes to save.";
            setSaveAllEnabled(false);
            return;
        }

        saveInFlight = true;
        dietItemsSaveAll.disabled = true;
        dietItemsSaveAll.textContent = "Saving...";

        saveDietRows(dirtyRows)
            .catch((error) => {
                dietItemsStatus.textContent = `Failed to save rows: ${error.message}`;
            })
            .finally(() => {
                saveInFlight = false;
                dietItemsSaveAll.disabled = false;
                dietItemsSaveAll.textContent = "Save All";
                if (autoSaveQueued) {
                    autoSaveQueued = false;
                    scheduleAutoSave(200);
                }
            });
    });
    }

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

    if (dietItemsClone) {
        dietItemsClone.addEventListener("click", () => {
            if (!dietName) {
                dietItemsStatus.textContent = "Missing diet name for cloning.";
                return;
            }
            if (!Array.isArray(lastLoadedItems)) {
                dietItemsStatus.textContent = "Diet items not loaded yet.";
                return;
            }
            dietItemsClone.disabled = true;
            const cloneName = `${dietName}_Cloned_${Date.now()}`;
            const itemsToClone = lastLoadedItems.map((item) => ({
                diet_name: cloneName,
                fdc_id: item.fdc_id,
                quantity: item.quantity,
                sort_order: item.sort_order,
                color: item.color ?? null,
            }));

            if (itemsToClone.length === 0) {
                dietItemsStatus.textContent = `No items to clone from ${dietName}.`;
                dietItemsClone.disabled = false;
                return;
            }

            dietItemsStatus.textContent = `Cloning ${dietName}...`;
            Promise.all(
                itemsToClone.map((payload) =>
                    fetch("/api/diet", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify(payload),
                    })
                )
            )
                .then((responses) => {
                    const failed = responses.filter((response) => !response.ok);
                    if (failed.length > 0) {
                        throw new Error(`Failed to clone ${failed.length} item(s).`);
                    }
                    window.location.href = `/ui/diets?diet_name=${encodeURIComponent(cloneName)}`;
                })
                .catch((error) => {
                    dietItemsStatus.textContent = `Failed to clone diet: ${error.message}`;
                })
                .finally(() => {
                    dietItemsClone.disabled = false;
                });
        });
    }

    if (dietItemsDeleteAll) {
        dietItemsDeleteAll.addEventListener("click", () => {
            if (!confirm(`Delete all items for ${dietName}? This cannot be undone.`)) {
                return;
            }
            dietItemsDeleteAll.disabled = true;
            dietItemsStatus.textContent = "Deleting all items...";
            fetch("/api/diet", {
                method: "DELETE",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ diet_name: dietName, delete_all: true }),
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Request failed with ${response.status}`);
                    }
                    return response.json();
                })
                .then(() => {
                    window.location.href = "/";
                })
                .catch((error) => {
                    dietItemsStatus.textContent = `Failed to delete all items: ${error.message}`;
                })
                .finally(() => {
                    dietItemsDeleteAll.disabled = false;
                });
        });
    }

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



