document.addEventListener('DOMContentLoaded', () => {
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
        if (quickActionCategoryField) {
            quickActionCategoryField.classList.add('hidden');
        }
        if (quickActionManagerField) {
            quickActionManagerField.classList.toggle('hidden', !isManagerTransfer);
        }
        if (quickActionObjectField) {
            quickActionObjectField.classList.toggle('hidden', !isObjectAction);
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
});
