// Set default theme to dark if not set
if (!localStorage.getItem("theme")) {
  localStorage.setItem("theme", "dark");
}
let userSettingsCache = null;
let userSettingsPromise = null;

function calculateDietNutrition(food, dietItem) {
    const servingSizeRaw = food ? food["Serving Size"] : undefined;
    let servingSize = Number(servingSizeRaw);
    if (!Number.isFinite(servingSize)) {
        servingSize = 0;
    }

    const adjustedFood = { ...(food || {}) };
    delete adjustedFood["Serving Size"];

    const quantity = Number(dietItem?.quantity ?? 0);
    const safeQuantity = Number.isFinite(quantity) ? quantity : 0;

    Object.entries(food || {}).forEach(([key, value]) => {
        if (key === "fdc_id" || key === "Serving Size") {
        return;
        }
        if (typeof value === "number" && Number.isFinite(value)) {
        const adjustedValue = servingSize > 0
            ? Math.round((value / servingSize) * safeQuantity * 100) / 100
            : 0.0;
        adjustedFood[key] = adjustedValue;
        }
    });

    return { ...(dietItem || {}), ...adjustedFood };
}
  
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return null;
}



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

function toRgba(color, alpha) {
    if (typeof color !== "string" || !color.trim()) return "";
    const hexMatch = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hexMatch) {
        const hex = hexMatch[1].length === 3
            ? hexMatch[1].split("").map((c) => c + c).join("")
            : hexMatch[1];
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    return color;
}

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
            window.setActiveNavLinks();
        })
        .catch(() => {
            const errorLabel = loadingItem.querySelector("p");
            if (errorLabel) {
                errorLabel.textContent = "Failed to load diets.";
            }
        });
}


document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    body.setAttribute("data-bs-theme", localStorage.getItem("theme"));
    document.documentElement.style.colorScheme = localStorage.getItem("theme"); // 🔑 tell the browser its color scheme

    // Theme switch button logic
    const themeToggleBtn = document.getElementById("theme-toggle");
    if (themeToggleBtn) {
        const icon = themeToggleBtn.querySelector("i");
        const text = themeToggleBtn.querySelector(".theme-text");

        const t = body.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
        if (t === "dark") {
            icon.className = "nav-icon bi bi-sun";
            if (text) text.textContent = "Light mode";
        } else {
            icon.className = "nav-icon bi bi-moon-stars";
            if (text) text.textContent = "Dark mode";
        }

        themeToggleBtn.addEventListener("click", (e) => {
            e.preventDefault();
            const opposite = body.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            localStorage.setItem("theme", opposite);
            window.location.reload();
        });
        // Theme switch button logic end
    }

    function setActiveNavLinks() {
        const currentPath = normalizePath(window.location.pathname);
        const currentParams = new URLSearchParams(window.location.search);
        const currentDietName = normalizeDietName(currentParams.get("diet_name"));

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
                const linkDietName = normalizeDietName(linkUrl.searchParams.get("diet_name"));
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
    window.setActiveNavLinks = setActiveNavLinks;

    function normalizePath(path) {
        if (!path) return "/";
        const p = path.endsWith("/") && path.length > 1 ? path.slice(0, -1) : path;
        return p || "/";
    }

    function normalizeDietName(name) {
        if (!name) return "";
        return decodeURIComponent(String(name)).trim();
    }

    const dietNavLoading = document.getElementById("diet-nav-loading");
    const dietNavTemplate = document.getElementById("diet-nav-item-template");
    const sidebarAddDietItem = document.getElementById("sidebar-add-diet-item");

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
    const foodsCreateBtn = document.getElementById("foods-create-btn");
    const foodsFdcForm = document.getElementById("foods-fdc-form");
    const foodsFdcInput = document.getElementById("foods-fdc-id");
    const foodColorProtein = document.getElementById("food-color-protein");
    const foodColorCarb = document.getElementById("food-color-carb");
    const foodColorFat = document.getElementById("food-color-fat");

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

    function createFoodWithDatetime() {
        if (!foodsCreateBtn) {
            return;
        }
        const name = `New Food ${new Date().toISOString()}`;
        foodsCreateBtn.disabled = true;
        fetch("/api/foods/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({ name }),
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                const fdcId = data?.fdc_id;
                if (fdcId != null) {
                    alert(`Created food ${fdcId} (${name}).`);
                    window.location.href = `/ui/foods/edit/${encodeURIComponent(fdcId)}`;
                    return;
                }
                window.location.reload();
                return;
            })
            .catch((error) => {
                alert(`Failed to create food: ${error.message}`);
            })
            .finally(() => {
                foodsCreateBtn.disabled = false;
            });
    }

    if (foodsTableHead && foodsTableBody && foodsStatus) {
        loadFoods();
    }

    if (foodsCreateBtn) {
        foodsCreateBtn.addEventListener("click", () => {
            createFoodWithDatetime();
        });
    }

    const foodsTable = document.getElementById("foods-table");
    if (foodsTable) {
        foodsTable.addEventListener("click", (event) => {
            const target = event.target?.closest?.("button.btn.btn-outline-danger.btn-sm");
            if (!target || !foodsTable.contains(target)) {
                return;
            }
            deleteFood(target.dataset.fdcId || "", target.dataset.foodName || "");
        });
    }

    let settingsReady = null;

    if (foodsFdcForm && foodsFdcInput) {
        function createOrUpdateFoodFromFdcId(fdcId) {
            return fetch(`/api/foods/create_update_food_from_fdcid/${encodeURIComponent(fdcId)}`, {
                method: "POST",
            }).then((response) => {
                if (!response.ok) {
                    const contentType = response.headers.get("content-type") || "";
                    if (contentType.includes("application/json")) {
                        return response.json().then((data) => {
                            const detail = data?.detail || "Unknown error";
                            throw new Error(`Request failed with ${response.status}: ${detail}`);
                        });
                    }
                    return response.text().then((text) => {
                        const detail = text || "Unknown error";
                        throw new Error(`Request failed with ${response.status}: ${detail}`);
                    });
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
                })
                .then(() => {
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
    const requiredDietColumns = ["diet_name", "fdc_id", "quantity", "sort_order", "color", "Name"];
    const excludedDietColumns = ["Serving Size"];

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
                if (requiredSet.has(col) || excludedDietColumns.includes(col)) {
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
    }

    if (rdaTable || ulTable) {
        loadNutrientTable("/api/rda", rdaTable, rdaStatus, "RDA");
        loadNutrientTable("/api/ul", ulTable, ulStatus, "UL");
    }
});



