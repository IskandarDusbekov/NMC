document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (form.dataset.submitting === 'true') {
                event.preventDefault();
                return;
            }

            form.dataset.submitting = 'true';

            const submitter = event.submitter;
            if (submitter && submitter.name) {
                const marker = document.createElement('input');
                marker.type = 'hidden';
                marker.name = submitter.name;
                marker.value = submitter.value;
                marker.dataset.generatedSubmitter = 'true';
                form.appendChild(marker);
            }

            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach((button) => {
                if (!button.dataset.originalLabel) {
                    button.dataset.originalLabel = button.tagName === 'INPUT' ? button.value : button.textContent.trim();
                }
            });

            window.setTimeout(() => {
                submitButtons.forEach((button) => {
                    button.disabled = true;
                    button.classList.add('opacity-60', 'cursor-not-allowed');
                    if (button === submitter) {
                        if (button.tagName === 'INPUT') {
                            button.value = 'Saqlanmoqda...';
                        } else {
                            button.textContent = 'Saqlanmoqda...';
                        }
                    }
                });
            }, 0);
        });
    });

    const sidebar = document.getElementById('app-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const openButtons = document.querySelectorAll('[data-sidebar-open]');

    function openSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
    }

    function closeSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
    }

    openButtons.forEach((button) => {
        button.addEventListener('click', openSidebar);
    });

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    const objectModal = document.getElementById('object-info-modal');
    const objectModalOpenButtons = document.querySelectorAll('[data-object-modal-open]');
    const objectModalCloseButtons = document.querySelectorAll('[data-object-modal-close]');

    function setObjectStatus(statusKey, statusLabel) {
        const statusBadge = document.getElementById('object-modal-status');
        if (!statusBadge) return;

        statusBadge.textContent = statusLabel || '-';
        statusBadge.className = 'rounded-full px-3 py-1 text-xs font-semibold';

        if (statusKey === 'active') {
            statusBadge.classList.add('bg-emerald-50', 'text-emerald-600');
            return;
        }
        if (statusKey === 'paused') {
            statusBadge.classList.add('bg-amber-50', 'text-amber-600');
            return;
        }
        statusBadge.classList.add('bg-slate-100', 'text-slate-600');
    }

    function setText(id, value) {
        const element = document.getElementById(id);
        if (!element) return;
        element.textContent = value || '-';
    }

    function openObjectModal(button) {
        if (!objectModal || !button) return;

        setText('object-modal-name', button.dataset.objectName);
        setText('object-modal-address', button.dataset.objectAddress);
        setObjectStatus(button.dataset.objectStatusKey, button.dataset.objectStatus);
        setText('object-modal-start-date', button.dataset.objectStartDate);
        setText('object-modal-end-date', button.dataset.objectEndDate);
        setText('object-modal-budget-uzs', button.dataset.objectBudgetUzs);
        setText('object-modal-budget-usd', button.dataset.objectBudgetUsd);
        setText('object-modal-expense-uzs', button.dataset.objectExpenseUzs);
        setText('object-modal-expense-usd', button.dataset.objectExpenseUsd);
        setText('object-modal-work-items', `${button.dataset.objectWorkItems || '-'} ta`);
        setText('object-modal-progress', button.dataset.objectProgress);
        setText('object-modal-description', button.dataset.objectDescription);

        objectModal.classList.remove('hidden');
        objectModal.classList.add('flex');
        document.body.classList.add('overflow-hidden');
    }

    function closeObjectModal() {
        if (!objectModal) return;
        objectModal.classList.add('hidden');
        objectModal.classList.remove('flex');
        document.body.classList.remove('overflow-hidden');
    }

    objectModalOpenButtons.forEach((button) => {
        button.addEventListener('click', () => openObjectModal(button));
    });

    objectModalCloseButtons.forEach((button) => {
        button.addEventListener('click', closeObjectModal);
    });

    if (objectModal) {
        objectModal.addEventListener('click', (event) => {
            if (event.target === objectModal) {
                closeObjectModal();
            }
        });
    }

    const descriptionModal = document.getElementById('description-preview-modal');
    const descriptionModalTitle = document.getElementById('description-preview-title');
    const descriptionModalText = document.getElementById('description-preview-text');

    document.querySelectorAll('[data-description-modal-open]').forEach((button) => {
        button.addEventListener('click', () => {
            if (!descriptionModal || !descriptionModalTitle || !descriptionModalText) return;
            descriptionModalTitle.textContent = button.dataset.descriptionTitle || 'Izoh';
            descriptionModalText.textContent = button.dataset.descriptionText || '-';
            descriptionModal.classList.remove('hidden');
            descriptionModal.classList.add('flex');
            document.body.classList.add('overflow-hidden');
        });
    });

    function openGenericModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.body.classList.add('overflow-hidden');
    }

    function closeGenericModal(modal) {
        if (!modal) return;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        document.body.classList.remove('overflow-hidden');
    }

    document.querySelectorAll('[data-modal-open]').forEach((button) => {
        button.addEventListener('click', () => openGenericModal(button.dataset.modalOpen));
    });

    document.querySelectorAll('[data-modal-close]').forEach((button) => {
        button.addEventListener('click', () => closeGenericModal(button.closest('[data-modal]')));
    });

    document.querySelectorAll('[data-modal]').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeGenericModal(modal);
            }
        });
    });

    document.querySelectorAll('[data-toggle-panel]').forEach((button) => {
        button.addEventListener('click', () => {
            const panel = document.getElementById(button.dataset.togglePanel);
            if (!panel) return;
            const willOpen = panel.classList.contains('hidden');
            panel.classList.toggle('hidden');
            button.textContent = willOpen
                ? (button.dataset.openLabel || 'Yashirish')
                : (button.dataset.closedLabel || 'Ochish');
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeObjectModal();
            document.querySelectorAll('[data-modal]').forEach(closeGenericModal);
        }
    });

    const workerTypeInput = document.querySelector('[data-worker-type-input]');
    const workerMonthlyField = document.getElementById('worker-monthly-salary-field');
    const workerMonthlyInput = document.querySelector('[data-worker-monthly-input]');
    const workerMonthlyCurrencyField = document.getElementById('worker-monthly-currency-field');
    const workerMonthlyCurrencyInput = document.querySelector('[data-worker-monthly-currency]');

    function toggleWorkerMonthlySalary() {
        if (!workerTypeInput || !workerMonthlyField || !workerMonthlyInput) return;

        const shouldShow = workerTypeInput.value === 'monthly';
        workerMonthlyField.classList.toggle('hidden', !shouldShow);
        workerMonthlyInput.disabled = !shouldShow;
        if (workerMonthlyCurrencyField && workerMonthlyCurrencyInput) {
            workerMonthlyCurrencyField.classList.toggle('hidden', !shouldShow);
            workerMonthlyCurrencyInput.disabled = !shouldShow;
        }

        if (!shouldShow) {
            workerMonthlyInput.value = '';
            if (workerMonthlyCurrencyInput) {
                workerMonthlyCurrencyInput.value = '';
            }
        }
    }

    if (workerTypeInput) {
        workerTypeInput.addEventListener('change', toggleWorkerMonthlySalary);
        toggleWorkerMonthlySalary();
    }

    const salarySourceWalletInput = document.querySelector('[data-salary-source-wallet]');
    const salaryManagerField = document.getElementById('salary-manager-field');
    const salaryObjectField = document.getElementById('salary-object-field');

    function toggleSalarySourceFields() {
        if (!salarySourceWalletInput) return;
        const source = salarySourceWalletInput.value;
        if (salaryManagerField) {
            salaryManagerField.classList.toggle('hidden', source !== 'MANAGER');
            salaryManagerField.querySelectorAll('select, input, textarea').forEach((input) => {
                input.disabled = source !== 'MANAGER';
            });
        }
        if (salaryObjectField) {
            const shouldShowObject = source === 'OBJECT' || source === 'MANAGER';
            salaryObjectField.classList.toggle('hidden', !shouldShowObject);
            salaryObjectField.querySelectorAll('select, input, textarea').forEach((input) => {
                input.disabled = !shouldShowObject;
            });
        }
    }

    if (salarySourceWalletInput) {
        salarySourceWalletInput.addEventListener('change', toggleSalarySourceFields);
        toggleSalarySourceFields();
    }

    const paymentWorkerInput = document.querySelector('[data-work-item-payment-worker]');
    const paymentWorkItemInput = document.querySelector('[data-work-item-payment-item]');
    function filterPaymentWorkItems() {
        if (!paymentWorkerInput || !paymentWorkItemInput) return;

        const workerId = paymentWorkerInput.value;
        let firstAvailableValue = '';

        Array.from(paymentWorkItemInput.options).forEach((option) => {
            if (!option.value) {
                option.hidden = false;
                option.disabled = false;
                return;
            }

            const matchesWorker = !workerId || option.dataset.workerId === workerId;
            option.hidden = !matchesWorker;
            option.disabled = !matchesWorker;
            if (matchesWorker && !firstAvailableValue) {
                firstAvailableValue = option.value;
            }
        });

        const selectedOption = paymentWorkItemInput.options[paymentWorkItemInput.selectedIndex];
        if (selectedOption && selectedOption.disabled) {
            paymentWorkItemInput.value = firstAvailableValue;
        }
        if (!paymentWorkItemInput.value && firstAvailableValue) {
            paymentWorkItemInput.value = firstAvailableValue;
        }
    }

    if (paymentWorkerInput && paymentWorkItemInput) {
        paymentWorkerInput.addEventListener('change', filterPaymentWorkItems);
        filterPaymentWorkItems();
    }

    const quickActionInput = document.querySelector('[data-company-quick-action]');
    const quickActionCategoryField = document.getElementById('company-quick-category-field');
    const quickActionManagerField = document.getElementById('company-quick-manager-field');
    const quickActionObjectField = document.getElementById('company-quick-object-field');
    const quickActionTargetCurrencyField = document.getElementById('company-quick-target-currency-field');
    const quickActionExchangeRateField = document.getElementById('company-quick-exchange-rate-field');
    const quickActionCategoryInput = document.querySelector('[data-company-quick-category]');
    const quickActionPresetButtons = document.querySelectorAll('[data-quick-action-preset]');

    function filterQuickActionCategories() {
        if (!quickActionInput || !quickActionCategoryInput) return;
        const action = quickActionInput.value;
        const requiredType = action === 'COMPANY_INCOME' ? 'INCOME' : action === 'COMPANY_EXPENSE' ? 'EXPENSE' : '';
        let firstValue = '';

        Array.from(quickActionCategoryInput.options).forEach((option) => {
            if (!option.value) {
                option.hidden = false;
                option.disabled = false;
                return;
            }
            const matches = !requiredType || option.dataset.categoryType === requiredType;
            option.hidden = !matches;
            option.disabled = !matches;
            if (matches && !firstValue) {
                firstValue = option.value;
            }
        });

        const selectedOption = quickActionCategoryInput.options[quickActionCategoryInput.selectedIndex];
        if (selectedOption && selectedOption.disabled) {
            quickActionCategoryInput.value = firstValue;
        }
    }

    function toggleQuickActionFields() {
        if (!quickActionInput) return;
        const isManagerTransfer = quickActionInput.value === 'MANAGER_TRANSFER';
        const isObjectAction = quickActionInput.value === 'OBJECT_FUNDING' || quickActionInput.value === 'OBJECT_RETURN';
        const isConvertibleTransfer = quickActionInput.value === 'MANAGER_TRANSFER' || quickActionInput.value === 'OBJECT_FUNDING';
        const needsCategory = quickActionInput.value === 'COMPANY_EXPENSE';
        if (quickActionCategoryField) {
            quickActionCategoryField.classList.toggle('hidden', !needsCategory);
        }
        if (quickActionManagerField) {
            quickActionManagerField.classList.toggle('hidden', !isManagerTransfer);
        }
        if (quickActionObjectField) {
            quickActionObjectField.classList.toggle('hidden', !isObjectAction);
        }
        if (quickActionTargetCurrencyField) {
            quickActionTargetCurrencyField.classList.toggle('hidden', !isConvertibleTransfer);
        }
        if (quickActionExchangeRateField) {
            quickActionExchangeRateField.classList.toggle('hidden', !isConvertibleTransfer);
        }
        filterQuickActionCategories();
    }

    if (quickActionInput) {
        quickActionInput.addEventListener('change', toggleQuickActionFields);
        toggleQuickActionFields();
    }

    quickActionPresetButtons.forEach((button) => {
        button.addEventListener('click', () => {
            if (!quickActionInput) return;
            quickActionInput.value = button.dataset.quickActionPreset;
            toggleQuickActionFields();
        });
    });

    const expenseCategoryInput = document.querySelector('[data-expense-category]');
    const expenseItemInput = document.querySelector('[data-expense-item]');
    const expenseUnitInput = document.querySelector('[data-expense-unit]');
    const expenseDetailWrappers = document.querySelectorAll('[data-expense-detail-wrapper]');

    function filterExpenseItems() {
        if (!expenseCategoryInput || !expenseItemInput) return;
        const categoryId = expenseCategoryInput.value;
        let firstValue = '';

        Array.from(expenseItemInput.options).forEach((option) => {
            if (!option.value) {
                option.hidden = false;
                option.disabled = false;
                return;
            }
            const matchesCategory = !categoryId || option.dataset.categoryId === categoryId;
            option.hidden = !matchesCategory;
            option.disabled = !matchesCategory;
            if (matchesCategory && !firstValue) {
                firstValue = option.value;
            }
        });

        const selectedOption = expenseItemInput.options[expenseItemInput.selectedIndex];
        if (selectedOption && selectedOption.disabled) {
            expenseItemInput.value = firstValue;
        }
    }

    function applyExpenseItemDefaultUnit() {
        if (!expenseItemInput || !expenseUnitInput) return;
        const selectedOption = expenseItemInput.options[expenseItemInput.selectedIndex];
        const defaultUnitId = selectedOption ? selectedOption.dataset.defaultUnitId : '';
        if (defaultUnitId) {
            expenseUnitInput.value = defaultUnitId;
        }
    }

    function toggleExpenseDetailFields() {
        if (!expenseCategoryInput) return;
        const selectedOption = expenseCategoryInput.options[expenseCategoryInput.selectedIndex];
        const detailMode = selectedOption ? selectedOption.dataset.detailMode : 'SIMPLE';
        const visibleFields = {
            MATERIAL: ['expense_item', 'quantity', 'unit', 'unit_price'],
            FOOD: ['expense_item'],
            FUEL: ['expense_item'],
            SIMPLE: [],
        }[detailMode || 'SIMPLE'] || [];

        filterExpenseItems();
        applyExpenseItemDefaultUnit();

        expenseDetailWrappers.forEach((wrapper) => {
            const fieldName = wrapper.dataset.expenseDetailWrapper;
            const isVisible = visibleFields.includes(fieldName);
            wrapper.classList.toggle('hidden', !isVisible);
            wrapper.querySelectorAll('input, select, textarea').forEach((input) => {
                input.disabled = !isVisible;
                if (!isVisible) {
                    input.value = '';
                }
            });
        });
    }

    if (expenseCategoryInput) {
        expenseCategoryInput.addEventListener('change', toggleExpenseDetailFields);
        if (expenseItemInput) {
            expenseItemInput.addEventListener('change', applyExpenseItemDefaultUnit);
        }
        toggleExpenseDetailFields();
    }

    const dashboardCurrencyButtons = document.querySelectorAll('[data-dashboard-currency]');
    const dashboardCurrencyTargets = document.querySelectorAll('[data-dashboard-currency-target]');

    function setDashboardCurrency(currency) {
        dashboardCurrencyButtons.forEach((button) => {
            const isActive = button.dataset.dashboardCurrency === currency;
            button.classList.toggle('bg-blue-600', isActive && currency === 'UZS');
            button.classList.toggle('bg-emerald-600', isActive && currency === 'USD');
            button.classList.toggle('text-white', isActive);
            button.classList.toggle('text-slate-500', !isActive);
        });
        dashboardCurrencyTargets.forEach((target) => {
            target.classList.toggle('hidden', target.dataset.dashboardCurrencyTarget !== currency);
        });
    }

    dashboardCurrencyButtons.forEach((button) => {
        button.addEventListener('click', () => setDashboardCurrency(button.dataset.dashboardCurrency));
    });

    if (dashboardCurrencyButtons.length) {
        setDashboardCurrency('UZS');
    }
});
